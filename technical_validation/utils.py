import gzip
import os.path

from pyproj import Transformer, CRS
import pandas as pd
from shapely import Polygon
import geopandas as gpd
from functools import lru_cache
import json
import math

istat_codes={
"Bari, Italy": "072006",
"Bologna, Italy": "037006",
"Catania, Italy": "087015",
"Genoa, Italy": "010025",
"Florence, Italy": "048017",
"Naples, Italy": "063049",
"Milan, Italy": "015146",
"Palermo, Italy": "082053",
"Rome, Italy": "058091",
"Turin, Italy": "001272"
}

def round_to_significant(number):
    number = int(number)
    magnitude = 10 ** (len(str(number)) - 1)
    rounded_number = round(number / magnitude) * magnitude
    return rounded_number


def scale_value(value, domain_min, domain_max, range_min, range_max):
    scaled_value = range_min + (value - domain_min) * (range_max - range_min) / (domain_max - domain_min)
    scaled_value = max(range_min, min(range_max, scaled_value))
    return int(scaled_value)

cluster_colors =[
    "#a6cee3",
    "#1f78b4",
    "#b2df8a",
    "#33a02c",
    "#fb9a99",
    "#e31a1c",
    "#fdbf6f",
    "#ff7f00",
    "#cab2d6",
    "#6a3d9a",
    "#ffff99",
    "#b15928"
]

@lru_cache()
def compute_min_max():
    mins={}
    maxs={}
    for col in ['proximity', 'entropy', 'density']:
        mins[col]=None
        maxs[col]=None
    for place_name, _, country_code in sorted(place_list, key=lambda x: x[0])[:5]:
        proximity_density_diversity_data = json.load(gzip.open(f'output/{place_name} PoI accessibility.json.gz', "rt"))
        proximity_density_diversity_df = pd.DataFrame.from_dict(proximity_density_diversity_data, orient='index')

        proximity_density_diversity_df = proximity_density_diversity_df.rename(columns={'diversity': 'entropy'})

        final_gdf = proximity_density_diversity_df.dropna().copy()

        def calculate_proximity(x):
            if not x:

                return 61
            if len(x.keys()) < 7:
                return 61

            return max(x.values())

        final_gdf['proximity'] = proximity_density_diversity_df['proximity'].apply(calculate_proximity)
        final_gdf = final_gdf[final_gdf['proximity'] <= 60]

        for col in ['proximity', 'entropy', 'density']:
            col_min = final_gdf[col].min()
            col_max = final_gdf[col].max()
            if mins[col] is None or mins[col]>col_min:
                mins[col] = col_min
            if maxs[col] is None or maxs[col]<col_max:
                maxs[col] = col_max
    return mins,maxs


def load_data(place_name):
    mins,maxs=compute_min_max()
    proximity_density_diversity_data = json.load(gzip.open(f'output/{place_name} PoI accessibility.json.gz',"rt"))
    pop_data = json.load(gzip.open(f'output/{place_name} Pop.json.gz',"rt"))

    if os.path.isfile(f"output/{place_name} closeness.json.gz"):
        connectivity_data = json.load(gzip.open(f'output/{place_name} closeness.json.gz',"rt"))
    else:
        connectivity_data={}
        for key, value in proximity_density_diversity_data.items():
            connectivity_data[key]={"closeness":0}

    neighborhood_data = json.load(gzip.open(f'output/{place_name} infomap.json.gz',"rt"))

    proximity_density_diversity_df = pd.DataFrame.from_dict(proximity_density_diversity_data, orient='index')


    proximity_density_diversity_df = proximity_density_diversity_df.rename(columns={'diversity': 'entropy'})

    final_gdf =proximity_density_diversity_df.dropna().copy()

    def calculate_proximity(x):
        if not x:
            return 61
        if len(x.keys())<7:
            return 61

        return max(x.values())

    final_gdf['proximity'] = proximity_density_diversity_df['proximity'].apply(calculate_proximity)
    final_gdf = final_gdf[final_gdf['proximity'] <= 60]


    for col in ['proximity', 'entropy', 'density']:
        final_gdf[col + '_norm'] = (final_gdf[col] - mins[col]) / (maxs[col] - mins[col])

    final_gdf['proximity_norm'] = 1 - final_gdf['proximity_norm']

    final_gdf['PoI-Accessibility_norm'] = final_gdf[['proximity_norm', 'entropy_norm', 'density_norm']].mean(axis=1)


    pop_df = pd.DataFrame(list(pop_data.items()), columns=['index', 'population'])
    pop_df['index'] = pop_df['index'].astype(str)
    final_gdf = final_gdf.reset_index().rename(columns={'index': 'index'})
    final_gdf['index'] = final_gdf['index'].astype(str)


    final_gdf = final_gdf.merge(pop_df, on='index', how='left')


    connectivity_data_cleaned = {
        index: values['closeness'] for index, values in connectivity_data.items()
    }
    connectivity_df = pd.DataFrame(list(connectivity_data_cleaned.items()), columns=['index', 'connectivity'])
    connectivity_df['connectivity'] = pd.to_numeric(connectivity_df['connectivity'],
                                                    errors='coerce')
    connectivity_df = connectivity_df.dropna(subset=['connectivity'])
    connectivity_df['index'] = connectivity_df['index'].astype(str)
    final_gdf = final_gdf.merge(connectivity_df, on='index', how='left')

    col_min = final_gdf['connectivity'].min()
    col_max = final_gdf['connectivity'].max()
    final_gdf['connectivity_norm'] = (final_gdf['connectivity'] /col_max)  if col_max >0 else 0



    final_gdf['PoI-Accessibility_norm'] = final_gdf[
        ['proximity_norm', 'entropy_norm', 'density_norm']
    ].mean(axis=1)



    neighborhood_df = pd.DataFrame(list(neighborhood_data["1"].items()), columns=['index', 'neighborhood'])
    neighborhood_df['index'] = neighborhood_df['index'].astype(str)
    final_gdf = final_gdf.merge(neighborhood_df, on='index', how='left')


    return final_gdf

def load_data_ari(place_name):
    mins,maxs=compute_min_max()
    proximity_density_diversity_data = json.load(gzip.open(f'output/{place_name} PoI accessibility.json.gz',"rt"))
    pop_data = json.load(gzip.open(f'output/{place_name} Pop.json.gz',"rt"))

    if os.path.isfile(f"output/{place_name} closeness.json.gz"):
        connectivity_data = json.load(gzip.open(f'output/{place_name} closeness.json.gz',"rt"))
    else:
        connectivity_data={}
        for key, value in proximity_density_diversity_data.items():
            connectivity_data[key]={"closeness":0}

    neighborhood_data = json.load(gzip.open(f'extended_output/{place_name} infomap.json.gz',"rt"))

    proximity_density_diversity_df = pd.DataFrame.from_dict(proximity_density_diversity_data, orient='index')


    proximity_density_diversity_df = proximity_density_diversity_df.rename(columns={'diversity': 'entropy'})

    final_gdf =proximity_density_diversity_df.dropna().copy()
    def calculate_proximity(x):
        if not x:  # Se x è vuoto
            return 61
        if len(x.keys())<7:
            return 61

        return max(x.values())

    final_gdf['proximity'] = proximity_density_diversity_df['proximity'].apply(calculate_proximity)
    final_gdf = final_gdf[final_gdf['proximity'] <= 60]


    for col in ['proximity', 'entropy', 'density']:


        final_gdf[col + '_norm'] = (final_gdf[col] - mins[col]) / (maxs[col] - mins[col])
    final_gdf['proximity_norm'] = 1 - final_gdf['proximity_norm']

    final_gdf['PoI-Accessibility_norm'] = final_gdf[['proximity_norm', 'entropy_norm', 'density_norm']].mean(axis=1)


    pop_df = pd.DataFrame(list(pop_data.items()), columns=['index', 'population'])
    pop_df['index'] = pop_df['index'].astype(str)
    final_gdf = final_gdf.reset_index().rename(columns={'index': 'index'})  # Assicurati che 'index' sia allineato
    final_gdf['index'] = final_gdf['index'].astype(str)


    final_gdf = final_gdf.merge(pop_df, on='index', how='left')




    connectivity_data_cleaned = {
        index: values['closeness'] for index, values in connectivity_data.items()
    }
    connectivity_df = pd.DataFrame(list(connectivity_data_cleaned.items()), columns=['index', 'connectivity'])
    connectivity_df['connectivity'] = pd.to_numeric(connectivity_df['connectivity'],
                                                    errors='coerce')
    connectivity_df = connectivity_df.dropna(subset=['connectivity'])
    connectivity_df['index'] = connectivity_df['index'].astype(str)
    final_gdf = final_gdf.merge(connectivity_df, on='index', how='left')

    col_min = final_gdf['connectivity'].min()
    col_max = final_gdf['connectivity'].max()
    final_gdf['connectivity_norm'] = (final_gdf['connectivity'] - col_min) / (col_max - col_min) if (col_max - col_min)>0 else 0



    final_gdf['PoI-Accessibility_norm'] = final_gdf[
        ['proximity_norm', 'entropy_norm', 'density_norm']
    ].mean(axis=1)


    neighborhood_df = pd.DataFrame(list(neighborhood_data["1"].items()), columns=['index', 'neighborhood'])
    neighborhood_df['index'] = neighborhood_df['index'].astype(str)
    final_gdf = final_gdf.merge(neighborhood_df, on='index', how='left')


    return final_gdf


def optimal_columns(num_elements, max_elements_per_row):
    best_columns = 1
    min_rows = float('inf')
    min_empty_cells = float('inf')

    for columns in range(1, max_elements_per_row + 1):
        rows = math.ceil(num_elements / columns)
        empty_cells = (rows * columns) - num_elements

        if rows < min_rows or (rows == min_rows and empty_cells < min_empty_cells):
            min_rows = rows
            min_empty_cells = empty_cells
            best_columns = columns

    return best_columns


place_list = [
    ("Lima Metropolitana, Lima, Perù", 1, "PER"), # Manila
    ("Moscow, Russia", 1, "RUS"), # Manila
    ("Taipei, Taiwan", 1, "TWN"), # Manila
    ("Bari, Italy", 1, "ITA"), # Manila
    ("Bologna, Italy", 1, "ITA"), # Manila
    ("Catania, Italy", 1, "ITA"), # Manila
    ("Genoa, Italy", 1, "ITA"), # Manila
    ("Florence, Italy", 102.41, "ITA"), # Florence
    ("Naples, Italy", 1, "ITA"),  # Milan
    ("Milan, Italy", 181.76, "ITA"),  # Milan
    ("Palermo, Italy", 1, "ITA"),  # Milan
    ("Rome, Italy", 1285, "ITA"),  # Rome
    ("Turin, Italy", 130.17, "ITA"),  # Turin 130.17

    ("Manila, Philippines", 42.88, "PHL"), # Manila
    ("Municipality of Athens, Greece", 38.96, "GRC"), # Athens
    ("Zurich, Switzerland", 87.88, "CHE"), # Zurich
    ("The Hague, Netherlands", 98.12, "NLD"), # The Hague
    ("Paris, France", 105.4, "FRA"), # Paris
    ("Toulouse, France", 118.3, "FRA"), # Toulouse
    ("Dublin, Ireland", 117.8, "IRL"), # Dublin
    ("Vancouver, Canada", 114.97, "CAN"), # Vancouver
    ("Manchester, United Kingdom", 115.6, "GBR"), # Manchester
    ("San Francisco, United States", 121.4, "USA"), # San Francisco
    ("Miami, United States", 143.1, "USA"), # Miami
    ("Barcelona, Spain", 101.4, "ESP"), # Barcelona
    ("Lisbon, Portugal", 100.05, "PRT"), # Lisbon
    ("Nottingham, United Kingdom", 74.61, "GBR"), # Nottingham
    ("Washington, D.C., United States", 177, "USA"), # Washington, D.C.
    ("Copenhagen Kommune, Denmark", 179.8, "DNK"), # Copenhagen
    ("Stockholm, Sweden", 188, "SWE"), # Stockholm
    ("Helsinki, Finland", 213.8, "FIN"), # Helsinki
    ("Seattle, United States", 217, "USA"), # Seattle
    ("Amsterdam, Noord-Holland, Netherlands", 219.3, "NLD"), # Amsterdam
    ("Philadelphia, United States", 369.6, "USA"), # Philadelphia
    ("Bogota, Colombia", 1587, "COL"), # Bogota
    ("Mexico City, Mexico", 1485, "MEX"), # Mexico City
    ("Warsaw, Poland", 517.24, "POL"), # Warsaw
    ("City of Prague, Czechia", 496, "CZE"), # Prague
    ("Oslo, Norway", 454, "NOR"), # Oslo
    ("Montreal (region administrative), Canada", 431.5, "CAN"), # Montreal
    ("Vienna, Austria", 414.65, "AUT"), # Vienna
    ("San Diego, United States", 964.5, "USA"), # San Diego
    ("Greater London, United Kingdom", 1572, "GBR"), # London
    ("Calgary, Canada", 825.3, "CAN"), # Calgary
    ("Chicago, United States", 606.1, "USA"), # Chicago
    ("Seoul, South Korea", 605.21, "KOR"), # Seoul
    ("Madrid, Spain", 604.3, "ESP"), # Madrid
    ("Jakarta, Indonesia", 661.5, "IDN"), # Jakarta
    ("Edmonton, Canada", 684.4, "CAN"), # Edmonton
    ("Singapore, Singapore", 728.6, "SGP"), # Singapore
    ("Nairobi, Kenya", 696, "KEN"), # Nairobi
    ("City of New York City, United States", 789, "USA"), # New York City
    ("Houston, United States", 1651.1, "USA"), # Houston
    ("City of Los Angeles, United States", 1302, "USA"), # Los Angeles
    ("Bangkok, Thailand", 1568.7, "THA"), # Bangkok
    ("Auckland, New Zealand", 1086, "NZL"), # Auckland
    ("Istanbul, Turkey", 5343, "TUR"), # Istanbul
    ("Rio de Janeiro, Brazil", 1221, "BRA"), # Rio de Janeiro
    ("Ottawa, Canada", 2790.3, "CAN"), # Ottawa
    ("Melbourne, City of Melbourne, Victoria, Australia", 9992.5, "AUS"), # Melbourne
    ("Beijing, China", 16410.5, "CHN"), # Beijing
    ("Shanghai, China", 6340.5, "CHN"), # Shanghai
    ("Adelaide, Australia", 3259.8, "AUS"), # Adelaide
    ("Brisbane, Australia", 15826, "AUS"), # Brisbane
    ("City of Cape Town, South Africa", 2461, "ZAF"), # Cape Town
    ("Ho Chi Minh City, Vietnam", 2095.6, "VNM"), # Ho Chi Minh City
    ("Tokyo, Japan", 2194, "JPN"), # Tokyo
    ("Sydney, Australia", 12367.7, "AUS"), # Sydney
    ("Región Metropolitana de Santiago, Chile", 15403.2, "CHL"), # Santiago

    #nuove
    ("Munich, Germany", 310.7, "DEU"),  # Munich
    ("Edinburgh, United Kingdom", 264, "GBR"),  # Edinburgh
    ("Berlin, Germany", 891.7, "DEU"),  # Berlin
    ("Budapest, Hungary", 525.2, "HUN"),  # Budapest
    ("Tallinn, Estonia", 159.3, "EST"),  # Tallinn
    ("Osaka, Japan", 225, "JPN"),  # Osaka
    ("Sapporo, Japan", 1121.3, "JPN"),  # Sapporo
    ("Fortaleza, Brazil", 314.9, "BRA"),  # Fortaleza
    ("Milwaukee, USA", 251.7, "USA"),  # Milwaukee
    ("Fukuoka, Japan", 343.4, "JPN"),  # Fukuoka
    ("Buenos Aires, Argentina", 203, "ARG"),  # Buenos Aires
    ("Medellin, Colombia", 380.6, "COL"),  # Medellin
    ("São Paulo, Brazil", 1521.1, "BRA"),  # São Paulo
    ("Boston, Massachusetts,USA", 232.1, "USA"),  # Boston
    ("Minneapolis, Minnesota, USA", 151.3, "USA"),  # Minneapolis
    ("Addis Ababa, Ethiopia", 527, "ETH"),  # Addis Ababa
    ("Detroit, Michigan, USA", 369, "USA"),  # Detroit
    ("Mumbai, India", 603.4, "IND"),  # Mumbai
    ("Hanoi, Vietnam", 3359, "VNM"),  # Hanoi
    ("Dallas, Texas, USA", 997.1, "USA"),  # Dallas
    ("Rotterdam, Netherlands", 324.1, "NLD"),  # Rotterdam
    ("San Antonio, Texas, USA", 1214.4, "USA"),  # San Antonio
    ("Atlanta, Georgia, USA", 348.6, "USA"),  # Atlanta

]

city_to_continent = {
    # Europa
    "Bari, Italy": "Europe",
    "Bologna, Italy": "Europe",
    "Catania, Italy": "Europe",
    "Genoa, Italy": "Europe",
    "Florence, Italy": "Europe",
    "Naples, Italy": "Europe",
    "Milan, Italy": "Europe",
    "Palermo, Italy": "Europe",
    "Rome, Italy": "Europe",
    "Turin, Italy": "Europe",
    "Municipality of Athens, Greece": "Europe",
    "Zurich, Switzerland": "Europe",
    "The Hague, Netherlands": "Europe",
    "Paris, France": "Europe",
    "Toulouse, France": "Europe",
    "Dublin, Ireland": "Europe",
    "Manchester, United Kingdom": "Europe",
    "Barcelona, Spain": "Europe",
    "Lisbon, Portugal": "Europe",
    "Nottingham, United Kingdom": "Europe",
    "Copenhagen Kommune, Denmark": "Europe",
    "Stockholm, Sweden": "Europe",
    "Helsinki, Finland": "Europe",
    "Amsterdam, Noord-Holland, Netherlands": "Europe",
    "Warsaw, Poland": "Europe",
    "City of Prague, Czechia": "Europe",
    "Oslo, Norway": "Europe",
    "Vienna, Austria": "Europe",
    "Greater London, United Kingdom": "Europe",
    "Madrid, Spain": "Europe",
    "Istanbul, Turkey": "Europe",
    "Munich, Germany": "Europe",
    "Edinburgh, United Kingdom": "Europe",
    "Berlin, Germany": "Europe",
    "Budapest, Hungary": "Europe",
    "Tallinn, Estonia": "Europe",
    "Rotterdam, Netherlands": "Europe",
    "Moscow, Russia": "Europe",


    # North America
    "Vancouver, Canada": "North America",
    "San Francisco, United States": "North America",
    "Miami, United States": "North America",
    "Washington, D.C., United States": "North America",
    "Seattle, United States": "North America",
    "Philadelphia, United States": "North America",
    "Montreal (region administrative), Canada": "North America",
    "San Diego, United States": "North America",
    "Calgary, Canada": "North America",
    "Chicago, United States": "North America",
    "City of New York City, United States": "North America",
    "Houston, United States": "North America",
    "City of Los Angeles, United States": "North America",
    "Ottawa, Canada": "North America",
    "Milwaukee, USA": "North America",
    "Boston, Massachusetts,USA": "North America",
    "Minneapolis, Minnesota, USA": "North America",
    "Detroit, Michigan, USA": "North America",
    "Dallas, Texas, USA": "North America",
    "San Antonio, Texas, USA": "North America",
    "Atlanta, Georgia, USA": "North America",
    "Edmonton, Canada": "North America",
    # Latin America and Caribbean
    "Bogota, Colombia": "Latin America and Caribbean",
    "Mexico City, Mexico": "Latin America and Caribbean",
    "Rio de Janeiro, Brazil": "Latin America and Caribbean",
    "Región Metropolitana de Santiago, Chile": "Latin America and Caribbean",
    "Buenos Aires, Argentina": "Latin America and Caribbean",
    "Medellin, Colombia": "Latin America and Caribbean",
    "São Paulo, Brazil": "Latin America and Caribbean",
    "Fortaleza, Brazil": "Latin America and Caribbean",
    "Lima Metropolitana, Lima, Perù": "Latin America and Caribbean",

    # Africa
    "Nairobi, Kenya": "Africa",
    "City of Cape Town, South Africa": "Africa",
    "Addis Ababa, Ethiopia": "Africa",

    # Oceania
    "Auckland, New Zealand": "Oceania",
    "Melbourne, City of Melbourne, Victoria, Australia": "Oceania",
    "Adelaide, Australia": "Oceania",
    "Brisbane, Australia": "Oceania",
    "Sydney, Australia": "Oceania",

    # Asia (non richiesto, ma per completezza)
    "Manila, Philippines": "Asia",
    "Seoul, South Korea": "Asia",
    "Jakarta, Indonesia": "Asia",
    "Singapore, Singapore": "Asia",
    "Bangkok, Thailand": "Asia",
    "Beijing, China": "Asia",
    "Shanghai, China": "Asia",
    "Ho Chi Minh City, Vietnam": "Asia",
    "Tokyo, Japan": "Asia",
    "Osaka, Japan": "Asia",
    "Sapporo, Japan": "Asia",
    "Fukuoka, Japan": "Asia",
    "Mumbai, India": "Asia",
    "Hanoi, Vietnam": "Asia",
    "Taipei, Taiwan":"Asia"
}








continent_to_color={

    "North America": "#FFD700",#
    "Latin America and Caribbean":	"#ff7f00",#
    "Europe":	"#984ea3",#
    "Africa":	"#4daf4a",#
    "Asia":	"#377eb8"	,#
    "Oceania":	"#e41a1c",#
}

country_tif_urls = {
    "PHL": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/PHL/phl_ppp_2020_constrained.tif",  # Philippines
    "ITA": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/ITA/ita_ppp_2020_constrained.tif",  # Italy
    "FRA": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/FRA/fra_ppp_2020_constrained.tif",  # Italy
    "ESP": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/ESP/esp_ppp_2020_constrained.tif",  # Spain
    "CHE": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/CHE/che_ppp_2020_constrained.tif",  # Switzerland
    "GRC": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/GRC/grc_ppp_2020_constrained.tif",  # Greece
    "SWE": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/SWE/swe_ppp_2020_constrained.tif",  # Sweden
    "TWN": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/TWN/twn_ppp_2020_constrained.tif",  # Taiwan
    "KOR": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/KOR/kor_ppp_2020_constrained.tif",  # South Korea
    "ARG": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/ARG/arg_ppp_2020_constrained.tif",  # Argentina
    "PRT": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/PRT/prt_ppp_2020_constrained.tif",  # Portugal
    "DEU": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/DEU/deu_ppp_2020_constrained.tif",  # Germany
    "HUN": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/HUN/hun_ppp_2020_constrained.tif",  # Hungary
    "DNK": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/DNK/dnk_ppp_2020_constrained.tif",  # Denmark
    "NLD": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/NLD/nld_ppp_2020_constrained.tif",  # Netherlands
    "RUS": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/RUS/rus_ppp_2020_constrained.tif",  # Russia
    "CAN": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/CAN/can_ppp_2020_constrained.tif",  # Canada
    "GBR": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/GBR/gbr_ppp_2020_constrained.tif",  # United Kingdom
    "USA": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/USA/usa_ppp_2020_constrained.tif",  # United States
    "CHL": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/CHL/chl_ppp_2020_constrained.tif",  # Chile
    "SGP": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/SGP/sgp_ppp_2020_constrained.tif",  # Singapore
    "JPN": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/JPN/jpn_ppp_2020_constrained.tif",  # Japan
    "COL": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/COL/col_ppp_2020_constrained.tif",  # Colombia
    "MEX": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/MEX/mex_ppp_2020_constrained.tif",  # Mexico
    "POL": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/POL/pol_ppp_2020_constrained.tif",  # Poland
    "PER": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/PER/per_ppp_2020_constrained.tif",  # Peru
    "TUR": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/TUR/tur_ppp_2020_constrained.tif",  # Turkey
    "IDN": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/IDN/idn_ppp_2020_constrained.tif",  # Indonesia
    "CHN": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/CHN/chn_ppp_2020_constrained.tif",  # China
    "ZAF": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/maxar_v1/ZAF/zaf_ppp_2020_constrained.tif",  # South Africa
    "THA": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/THA/tha_ppp_2020_constrained.tif",  # Thailand
    "BRA": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/BRA/bra_ppp_2020_constrained.tif",  # Brazil
    "CZE": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/CZE/cze_ppp_2020_constrained.tif",  # Czechia
    "FIN": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/FIN/fin_ppp_2020_constrained.tif",  # Finland
    "AUT": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/AUT/aut_ppp_2020_constrained.tif",  # Austria
    "VNM": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/VNM/vnm_ppp_2020_constrained.tif",  # Vietnam
    "KEN": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/maxar_v1/KEN/ken_ppp_2020_constrained.tif",  # Kenya
    "NOR": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/NOR/nor_ppp_2020_constrained.tif",  # Norway
    "AUS": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/AUS/aus_ppp_2020_constrained.tif",  # Australia
    "NZL": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/NZL/nzl_ppp_2020_constrained.tif",  # New Zealand
    "IRL": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/IRL/irl_ppp_2020_constrained.tif",  # Ireland
    "EST": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/EST/est_ppp_2020_constrained.tif",  # Estonia
    "ETH": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/maxar_v1/ETH/eth_ppp_2020_constrained.tif",  # Ethiopia
    "IND": "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/IND/ind_ppp_2020_constrained.tif",  # India
}



"""
transit stop non esiste
public_transport è una key non un tag, quindi ho messo tutti i tag di questa chiave
gym deprecato usare fitness_station
leisure=skatepark in approvazione tengo quindi anche sport=skateboard anche se è deprecato
aggiunto 'college' ad education e tolto da health_and_wellbeing, credo un errore

https://journals.sagepub.com/doi/suppl/10.1177/23998083221131044/suppl_file/sj-pdf-1-epb-10.1177_23998083221131044.pdf
"""
categories = {
    'mobility': {
        'tags': {
            'public_transport': ['station', 'stop_position', 'platform', 'stop_area', 'stop_area_group'],
            'highway': ['bus_stop'],
            'amenity': ['bus_station']
        }
    },
    'active_living': {
        'tags': {
            'leisure': [
                'fitness_centre', 'sports_centre', 'park', 'pitch', 'playground',
                'swimming_pool', 'garden', 'golf_course', 'ice_rink', 'dog_park',
                'nature_reserve', 'marina', 'fitness_station'
            ],
            'landuse': ['recreation_ground', 'skatepark', 'skate_park'],
            'sport': ['skateboard'],
            'amenity': ['bicycle_parking']
        }
    },
    'entertainment': {
        'tags': {
            'amenity': ['pub', 'bar', 'theatre', 'cinema', 'nightclub', 'events_venue']
        }
    },
    'food': {
        'tags': {
            'amenity': ['restaurant', 'cafe', 'food_court', 'marketplace', 'community_centre']
        }
    },
    'community': {
        'tags': {
            'amenity': ['library', 'social_facility', 'social_centre', 'townhall']
        }
    },
    'education': {
        'tags': {
            'amenity': ['school', 'childcare', 'child_care', 'kindergarten', 'university', 'college']
        }
    },
    'health_and_wellbeing': {
        'tags': {
            'amenity': ['pharmacy', 'dentist', 'clinic', 'hospital', 'doctors']
        }
    }
}


def get_queryable_tags(categories):
    """
    Retrieve a dictionary of tags queryable in osmnx from the given categories.

    Parameters:
    categories (dict): Dictionary of categories with tags.

    Returns:
    dict: A dictionary where keys are tag types and values are lists of tags.
    """
    # Initialize a dictionary to collect all tags
    queryable_tags = {}

    for category, data in categories.items():
        for key, values in data['tags'].items():
            if key not in queryable_tags:
                queryable_tags[key] = list(set(values))  # Use set to remove duplicates
            else:
                queryable_tags[key] += list(set(values))
    return queryable_tags


def get_extended_bebop_from_graph(G, max_distance_meters):
    """
    Obtain an extended Bounding Box of Points (BeBOP) from a graph.

    Parameters:
    subG (networkx.Graph): The graph from which to compute the BeBOP.
    max_distance_meters (float): Maximum distance to extend the bounding box by, in meters.

    Returns:
    shapely.geometry.box: The extended bounding box.
    """
    # Extract node coordinates (longitude, latitude)
    node_coords = [(data['x'], data['y']) for _, data in G.nodes(data=True)]

    if len(node_coords) == 0:
        raise ValueError("The graph has no nodes.")

    # Create the initial bounding box
    min_x, min_y, max_x, max_y = (min(p[0] for p in node_coords),
                                  min(p[1] for p in node_coords),
                                  max(p[0] for p in node_coords),
                                  max(p[1] for p in node_coords))

    # Convert bounding box coordinates to projected coordinates (meters)
    transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
    min_x_proj, min_y_proj = transformer.transform(min_x, min_y)
    max_x_proj, max_y_proj = transformer.transform(max_x, max_y)

    # Extend the bounding box in projected coordinates
    buffer_x = max_distance_meters
    buffer_y = max_distance_meters

    min_x_proj -= buffer_x
    max_x_proj += buffer_x
    min_y_proj -= buffer_y
    max_y_proj += buffer_y

    # Convert extended bounding box back to geographic coordinates
    min_x, min_y = transformer.transform(min_x_proj, min_y_proj, direction='INVERSE')
    max_x, max_y = transformer.transform(max_x_proj, max_y_proj, direction='INVERSE')

    # Return the extended bounding box
    extended_bbox = (max_y, min_y, max_x, min_x)

    return extended_bbox


def filter_pois_by_tags(pois, tags):
    """
    Filter POIs based on the provided tags, retaining rows that satisfy at least one filter.

    Parameters:
    - pois (pd.DataFrame): DataFrame containing POIs with various tags.
    - tags (dict): Dictionary where keys are tag types and values are lists of tag values to filter by.

    Returns:
    - pd.DataFrame: Filtered POIs that match at least one of the tag criteria.
    """
    # Convert tags dictionary to a set of conditions for filtering
    conditions = []
    # print(tags)
    for key, values in tags.items():
        if key in pois.columns:
            condition = pois[key].isin(values)
            conditions.append(condition)
        # for value in values:
        #    if value in pois.columns:
        #        condition = pois[value].notnull()
        #        conditions.append(condition)

    if not conditions:
        raise ValueError("No valid tags found in POIs DataFrame columns.")
    # print(conditions)
    # Combine all conditions with logical OR
    combined_condition = pd.concat(conditions, axis=1).any(axis=1)

    # Apply combined condition to filter POIs
    filtered_pois = pois[combined_condition]

    return filtered_pois


def filter_pois_by_polygon(pois, polygon):
    """
    Filter POIs to include only those within the given polygon.
    """

    # Filter the POIs
    pois_within_polygon = pois[pois.geometry.intersects(polygon)]

    return pois_within_polygon


def calculate_area_in_square_meters(polygon):
    """
    Calculate the area of a given polygon in square meters.

    Parameters:
    polygon (shapely.geometry.Polygon): The polygon for which to calculate the area.

    Returns:
    float: The area of the polygon in square meters.
    """
    if isinstance(polygon, Polygon) or   isinstance(polygon, Polygon):

        # Define the projection to convert from WGS84 to Web Mercator
        wgs84 = CRS.from_epsg(4326)  # WGS84 latitude/longitude
        web_mercator = CRS.from_epsg(3857)  # Web Mercator projection

        # Transformer to convert from WGS84 to Web Mercator
        transformer = Transformer.from_crs(wgs84, web_mercator, always_xy=True)

        # Project the polygon to Web Mercator
        projected_coords = [transformer.transform(x, y) for x, y in polygon.exterior.coords]
        projected_polygon = Polygon(projected_coords)

        # Calculate the area in square meters
        area = projected_polygon.area
    else:
        area=None

    return area

def calculate_area_in_square_km(polygon):
    """
    Calcola l'area di un dato poligono in chilometri quadrati (km²).

    Parametri:
    polygon (shapely.geometry.Polygon): Il poligono per il quale calcolare l'area.

    Restituisce:
    float: L'area del poligono in chilometri quadrati (km²).
    """
    if isinstance(polygon, Polygon):
        # Definisci la proiezione per convertire da WGS84 a Web Mercator
        wgs84 = CRS.from_epsg(4326)  # WGS84 latitudine/longitudine
        web_mercator = CRS.from_epsg(3857)  # Proiezione Web Mercator

        # Trasformatore per convertire da WGS84 a Web Mercator
        transformer = Transformer.from_crs(wgs84, web_mercator, always_xy=True)

        # Proietta il poligono in Web Mercator
        projected_coords = [transformer.transform(x, y) for x, y in polygon.exterior.coords]
        projected_polygon = Polygon(projected_coords)

        # Calcola l'area in metri quadrati
        area_m2 = projected_polygon.area

        # Converte l'area in km²
        area_km2 = area_m2 / 1000000
    else:
        area_km2 = None

    return area_km2


def map_census_to_community(community_hulls, geodf):
    """
    Maps census_id to community labels based on which polygon they fall into.

    Parameters:
    - community_hulls (dict): A dictionary of community labels containing convex and concave hulls.
    - geodf (GeoDataFrame): A GeoDataFrame containing census_id and geometry.

    Returns:
    - dict: A dictionary mapping census_id to community_label.
    """
    # Initialize the result dictionary
    census_to_community = {}

    # Iterate over community levels
    for level, communities in community_hulls.items():
        # Iterate over each community in the level
        for community_label, hulls in communities.items():
            # Get the convex hull polygon for this community
            convex_hull = hulls['convex_hull'].iloc[0]

            # Check which census areas fall within this convex hull
            for idx, row in geodf.iterrows():
                if row['geometry'].intersects(convex_hull):
                    # If the geometry intersects, map the census_id to the community label
                    census_to_community[row['census_id']] = community_label

    return census_to_community

