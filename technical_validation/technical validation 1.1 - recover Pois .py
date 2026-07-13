import glob
import gzip
import os
import time
import traceback

import geopandas as gpd
import networkx as nx
import overturemaps
import pandas as pd

from shapely.geometry import Point, box
from shapely.wkt import loads as wkt_loads
import hashlib
import os
import pandas as pd

CACHE_DIR = "./overture_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def bbox_cache_file(bbox):
    key = "_".join(f"{x:.6f}" for x in bbox)

    digest = hashlib.md5(
        key.encode()
    ).hexdigest()

    return os.path.join(
        CACHE_DIR,
        f"{digest}.feather"
    )

# ============================================================
# GRID
# ============================================================

def split_bbox(west, south, east, north, n=3):
    lon_step = (east - west) / n
    lat_step = (north - south) / n

    boxes = []

    for i in range(n):
        for j in range(n):
            boxes.append(
                (
                    west + i * lon_step,
                    south + j * lat_step,
                    west + (i + 1) * lon_step,
                    south + (j + 1) * lat_step,
                )
            )

    return boxes


def adaptive_grid(bbox):
    west, south, east, north = bbox

    area = (east - west) * (north - south)

    if area > 1.0:
        n = 20
    #elif area > 0.25:
    #    n = 10
    #elif area > 0.05:
    #    n = 5
    else:
        n = 1

    print("GRID =", n, "x", n)

    return split_bbox(west, south, east, north, n=n)


# ============================================================
# GRAPH
# ============================================================

def graph_nodes_gdf(G):

    points = []

    for _, data in G.nodes(data=True):

        if "x" not in data or "y" not in data:
            continue

        try:
            points.append(
                Point(
                    float(data["x"]),
                    float(data["y"])
                )
            )
        except Exception:
            pass

    gdf = gpd.GeoDataFrame(
        geometry=points,
        crs="EPSG:4326"
    )


    _ = gdf.sindex

    return gdf


def bbox_intersects_graph(bbox, graph_nodes):

    bbox_geom = box(*bbox)

    hits = list(
        graph_nodes.sindex.intersection(
            bbox_geom.bounds
        )
    )

    return len(hits) > 0


# ============================================================
# OVERTURE
# ============================================================

def query_overture_bbox(bbox):

    cache_file = bbox_cache_file(bbox)

    # -------------------------
    # CACHE HIT
    # -------------------------
    if os.path.isfile(cache_file):

        print("CACHE HIT:", bbox)

        try:
            return pd.read_feather(cache_file)
        except Exception:
            os.remove(cache_file)

    # -------------------------
    # DOWNLOAD
    # -------------------------
    try:

        table = (
            overturemaps
            .record_batch_reader("place", bbox)
            .read_all()
        )

        df = table.to_pandas()

        df.to_feather(cache_file)

        return df

    except Exception as e:

        print("tile error:", bbox)
        print(e)

        return None


def get_overture_safe(bbox):
    # --------------------------------------------------------
    # GRAPH
    # --------------------------------------------------------

    graphml_path = (
        extended_gzip_filename
        .replace(
            ".csv.gz",
            " extended.graphml.gz"
        )
        .strip()
    )

    print("Loading graph:")
    print(graphml_path)

    with gzip.open(graphml_path, "rb") as f:
        G = nx.read_graphml(f)

    graph_nodes = graph_nodes_gdf(G)

    print(
        "Graph nodes:",
        len(graph_nodes)
    )
    boxes = adaptive_grid(bbox)

    dfs = []

    total_tiles = len(boxes)
    queried_tiles = 0
    skipped_tiles = 0
    to_do_boxes=[]

    for b in boxes:
        if  bbox_intersects_graph(b, graph_nodes):
            to_do_boxes.append(b)
        else:
            skipped_tiles+=1

    del G
    del graph_nodes
    for b in to_do_boxes:

        queried_tiles += 1

        print(
            f"QUERY {queried_tiles+skipped_tiles}/{total_tiles}:",
            b
        )

        df = query_overture_bbox(b)

        if df is not None and len(df) > 0:
            dfs.append(df)

        time.sleep(0.5)

    print(
        "Queried:",
        queried_tiles,
        "Skipped:",
        skipped_tiles
    )

    if not dfs:
        return None

    return pd.concat(
        dfs,
        ignore_index=True
    )


# ============================================================
# UTILS
# ============================================================

def deduplicate(df):

    if df is None:
        return None

    if "id" in df.columns:
        return df.drop_duplicates(subset="id")

    return df.drop_duplicates()


def get_bbox_from_graph(G):

    lons = [
        float(data["x"])
        for _, data in G.nodes(data=True)
    ]

    lats = [
        float(data["y"])
        for _, data in G.nodes(data=True)
    ]

    return (
        min(lons),
        min(lats),
        max(lons),
        max(lats)
    )


# ============================================================
# MAIN
# ============================================================

for extended_gzip_filename in glob.glob("../output/*.csv.gz"):

    city_code = (
        extended_gzip_filename
        .split("/")[-1]
        .replace(".csv.gz", "")
        .strip()
    )

    print("\n==========================")
    print(city_code)
    print("==========================")

    output_path = (
        f"../output/{city_code} PoI.feather.zstd"
    )

    if os.path.isfile(output_path):
        print("Already done")
        continue

    # --------------------------------------------------------
    # OSM dataframe
    # --------------------------------------------------------

    osm_df = pd.read_csv(
        extended_gzip_filename,
        compression="gzip"
    )

    osm_df["geometry"] = (
        osm_df["geometry"]
        .apply(wkt_loads)
    )

    osm_gdf = gpd.GeoDataFrame(
        osm_df,
        geometry="geometry",
        crs="EPSG:4326"
    )

    west, south, east, north = (
        osm_gdf.total_bounds
    )

    bbox = (
        west,
        south,
        east,
        north
    )

    print("OSM bbox:", bbox)



    # --------------------------------------------------------
    # OVERTURE DOWNLOAD
    # --------------------------------------------------------

    done = False

    while not done:

        try:

            df = get_overture_safe(
                bbox
            )

            if df is None or len(df) == 0:

                print(
                    "Empty result, retrying..."
                )

                time.sleep(30)

                continue

            df = deduplicate(df)

            print(
                "Unique POIs:",
                len(df)
            )
            df["geometry"] = gpd.GeoSeries.from_wkb(df["geometry"])
            gdf = gpd.GeoDataFrame(
                df,
                geometry="geometry",
                crs="EPSG:4326"
            )

            gdf.to_feather(
                output_path,
                compression="zstd"
            )

            print(
                "DONE:",
                city_code
            )

            done = True

        except Exception as e:

            print(
                "GLOBAL ERROR:"
            )

            traceback.print_exc()

            time.sleep(60)

    time.sleep(5)
