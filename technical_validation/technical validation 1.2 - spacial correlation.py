import gzip

import geopandas as gpd
import pandas as pd
import numpy as np
import glob

from shapely.geometry import Point
from shapely import wkb
from shapely.errors import GEOSException
from shapely.ops import unary_union
from scipy.stats import pearsonr
from tqdm import tqdm
import warnings
import networkx as nx
warnings.filterwarnings("ignore", category=UserWarning)

# ========= PARAMETERS =========
CELL_SIZE = 0.01
OUTPUT_FILE = "technical validation 2 - summary.csv"

# ========= CATEGORIES =========
categories = {
    'mobility': {'tags': {'public_transport': ['station', 'stop_position', 'platform', 'stop_area', 'stop_area_group'],
                          'highway': ['bus_stop'],
                          'amenity': ['bus_station']}},
    'active_living': {'tags': {'leisure': ['fitness_centre', 'sports_centre', 'park', 'pitch', 'playground',
                                           'swimming_pool', 'garden', 'golf_course', 'ice_rink', 'dog_park',
                                           'nature_reserve', 'marina', 'fitness_station'],
                               'landuse': ['recreation_ground', 'skatepark', 'skate_park'],
                               'sport': ['skateboard'],
                               'amenity': ['bicycle_parking']}},
    'entertainment': {'tags': {'amenity': ['pub', 'bar', 'theatre', 'cinema', 'nightclub', 'events_venue']}},
    'food': {'tags': {'amenity': ['restaurant', 'cafe', 'food_court', 'marketplace', 'community_centre']}},
    'community': {'tags': {'amenity': ['library', 'social_facility', 'social_centre', 'townhall']}},
    'education': {'tags': {'amenity': ['school', 'childcare', 'child_care', 'kindergarten', 'university', 'college']}},
    'health_and_wellbeing': {'tags': {'amenity': ['pharmacy', 'dentist', 'clinic', 'hospital', 'doctors']}}
}

categories_overture = {
    'mobility': ['transportation'],
    'active_living': ['active_life'],
    'entertainment': ['arts_and_entertainment', 'attractions_and_activities'],
    'food': ['eat_and_drink'],
    'community': ['library','hospice','town_hall','child_care_and_day_care'],
    'education': ['education'],
    'health_and_wellbeing': ['health_and_medical']
}

def build_city_boundary_from_graph(G, buffer_size=0.002):
    points = [
        Point(data["x"], data["y"])
        for _, data in G.nodes(data=True)
        if "x" in data and "y" in data
    ]

    if len(points) == 0:
        raise ValueError("No node coordinates found")

    gdf = gpd.GeoSeries(points, crs="EPSG:4326")

    boundary = gdf.union_all().convex_hull

    boundary = boundary.buffer(buffer_size)

    return boundary


def categorize_poi(row):
    for cat, rules in categories.items():
        for key, values in rules['tags'].items():
            val = row.get(key)
            if pd.notnull(val) and val in values:
                return cat
    return None


def categorize_overture(row):
    place_type = row.get("categories")
    if not place_type:
        return None
    if isinstance(place_type, dict):
        place_type = place_type.get("primary", None)

    for cat, values in categories_overture.items():
        if place_type in values:
            return cat
    return None


def load_osm_pois(csv_path, city_boundary):
    df = pd.read_csv(csv_path, compression='gzip')

    df['geometry'] = gpd.GeoSeries.from_wkt(df['geometry'])
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

    gdf = gdf[gdf.geometry.geom_type.isin(['Point'])]
    gdf = gdf[gdf.within(city_boundary)]

    gdf['category'] = gdf.apply(categorize_poi, axis=1)

    return gdf.dropna(subset=['category'])


def load_overture_pois(feather_path, city_boundary):
    df = pd.read_feather(feather_path)

    def safe_load(x):
        try:
            return wkb.loads(x) if x else None
        except GEOSException:
            return None

    df['geometry'] = df['geometry'].apply(safe_load)
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

    gdf = gdf[gdf.geometry.geom_type.isin(['Point'])]

    gdf = gdf[gdf.within(city_boundary)]

    gdf['category'] = gdf.apply(categorize_overture, axis=1)

    return gdf.dropna(subset=['category'])


def assign_cells(gdf, cell_size=CELL_SIZE):
    gdf = gdf.copy()
    gdf['xcell'] = (gdf.geometry.x // cell_size).astype(int)
    gdf['ycell'] = (gdf.geometry.y // cell_size).astype(int)
    return gdf.groupby(['xcell','ycell']).size()


def compute_spatial_corr(osm_gdf, overture_gdf, categories_list):
    results = []

    for cat in [None] + categories_list:
        osm_sel = osm_gdf if cat is None else osm_gdf[osm_gdf['category']==cat]
        ovt_sel = overture_gdf if cat is None else overture_gdf[overture_gdf['category']==cat]

        if len(osm_sel) == 0 or len(ovt_sel) == 0:
            results.append({'category': cat or 'TOTAL', 'corr': np.nan, 'pvalue': np.nan})
            continue

        osm_cells = assign_cells(osm_sel)
        ovt_cells = assign_cells(ovt_sel)

        merged = pd.DataFrame({'osm': osm_cells, 'ovt': ovt_cells}).fillna(0)

        if merged['osm'].sum() > 0 and merged['ovt'].sum() > 0:
            corr, pvalue = pearsonr(merged['osm'], merged['ovt'])
        else:
            corr, pvalue = np.nan, np.nan

        results.append({'category': cat or 'TOTAL', 'corr': corr, 'pvalue': pvalue})

    return results


all_results = []

files = sorted(glob.glob("../output/* PoI.feather.zstd"))

for filename in tqdm(files, desc="Validating cities"):

    city = filename.split('/')[-1].replace(' PoI.feather.zstd', '').strip()
    osm_path = f"../output/{city}.csv.gz"

    try:

        graphml_path = osm_path.replace('.csv.gz', ' extended.graphml.gz').strip()
        print(graphml_path)
        with gzip.open(graphml_path, 'rb') as f:
            G = nx.read_graphml(f)
        city_boundary = build_city_boundary_from_graph(G)
        del G


        osm = load_osm_pois(osm_path, city_boundary)
        overture = load_overture_pois(filename, city_boundary)
        del city_boundary

        res = compute_spatial_corr(osm, overture, list(categories.keys()))

        for r in res:
            r['city'] = city

        all_results.extend(res)

        pd.DataFrame(all_results).to_csv(OUTPUT_FILE, index=False)

    except Exception as e:
        print(f"Errore con {city}: {e}")
        continue


df = pd.DataFrame(all_results)

category_labels = {
    'mobility': 'Mobility',
    'active_living': 'Active living',
    'entertainment': 'Entertainment',
    'food': 'Food',
    'community': 'Community',
    'education': 'Education',
    'health_and_wellbeing': 'Health and wellbeing',
    'TOTAL': 'Overall'
}

df['category_label'] = df['category'].map(category_labels).fillna(df['category'])

final_summary = df.groupby('category')['corr'].mean().to_frame()
final_summary['mean_pvalue'] = df.groupby('category')['pvalue'].mean()

print(final_summary.sort_values('corr', ascending=False))


import seaborn as sns
import matplotlib.pyplot as plt

plt.figure(figsize=(6, 3.8))

sns.boxplot(
    data=df,
    x="corr",
    y="category_label",
    orient="h",
    showfliers=False,
    palette="Set3"
)

plt.axvline(0, color="gray", linestyle="--", linewidth=1)
for spine in plt.gca().spines.values():
     spine.set_visible(False)
plt.xlabel("Pearson correlation")
plt.ylabel("")
plt.tight_layout()
plt.show()
