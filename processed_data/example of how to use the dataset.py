import shutil

from utils import place_list,compute_min_max
import json
import pyproj
import gzip
import os
import pandas as pd
import pickle
import networkx as nx



place_list = {
    # Europe
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

    # Asia
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

# Cities without transit data always have a connectivity value of zero; however, we still included them in the dataset in case the user wants to make use of the other calculated urban metrics
cities_without_transit_data=[
"Lima Metropolitana, Lima, Perù",
"Moscow, Russia",
"Medellin, Colombia",
"Mumbai, India",
"Seoul, South Korea",
"São Paulo, Brazil",
"Ho Chi Minh City, Vietnam",
"City of Cape Town, South Africa",
"Hanoi, Vietnam",
"Shanghai, China",
"Beijing, China",
]
for place_name in sorted(    [p for p in place_list if p not in cities_without_transit_data] , key=lambda x: x[0]):
    print(place_name)
    json_path = f"{place_name}.json.gz"
    df_urban_metrics = pd.read_json(json_path, compression='gzip')
    print(f"City Metrics")
    print("Print Head:")
    print(df_urban_metrics.columns)
    print(df_urban_metrics.head())
    print("\nNumber of rows:", len(df_urban_metrics))

    proximity_dict = df_urban_metrics.set_index('index')['proximity'].to_dict()
    entropy_dict = df_urban_metrics.set_index('index')['entropy'].to_dict()
    density_dict = df_urban_metrics.set_index('index')['density'].to_dict()

    csv_path = f"{place_name}.csv.gz"
    df_edges = pd.read_csv(csv_path, compression='gzip')
    print(f"City PoIs")
    print("Print Head:")
    print(df_edges.columns)
    print(df_edges.head())
    print("\nNumber of rows:", len(df_edges))

    G = nx.DiGraph()

    for osm_id, proximity in proximity_dict.items():
        G.add_node(osm_id, proximity=proximity,entropy=entropy_dict[osm_id],density=density_dict[osm_id])

    for _, row in df_edges.iterrows():
        source = row['source_id']
        target = row['target_id']
        travel_time = row['travel_time']
        mode = row['type']  # walk o transit

        G.add_edge(source, target, weight=travel_time, type=mode)

    print("Number of nodes:", G.number_of_nodes())
    print("Number of edges:", G.number_of_edges())

    print("Nodes example (first 5 nodes):")
    for n, data in list(G.nodes(data=True))[:5]:
        print(n, data)
    print("Edges example (first 5 edges):")
    for u, v, data in list(G.edges(data=True))[:5]:
        print(u, v, data)

    print("\n\n\n\n")