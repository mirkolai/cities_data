import networkx as nx
import gzip
import random
import pandas as pd
import glob

for graphml_path in glob.glob("../output/* - walk & transit.graphml.gz"):
    """The data in the output folder must be generated using the data collection pipeline. We have not included them in the repository (https://github.com/mirkolai/cities) for two reasons:
    - The files are large.
    - They would be copies of data from OpenStreetMap .
    """

    print(graphml_path)
    city_name = graphml_path.split('/')[-1].replace(' - walk & transit.graphml.gz', '').strip()

    with gzip.open(graphml_path, 'rb') as f:
        G = nx.read_graphml(f)
    flag=0
    for u, v, data in G.edges(data=True):
        if data['type']=='public_transit':
            flag=1
        weight = data.get('weight') or data.get('d3')  # fallback se diverso
        data['weight'] = float(weight) if weight else 1.0  # default fallback
    if not flag:
        continue
    valid_nodes = [
        n for n, d in G.nodes(data=True)
        if 'x' in d and 'y' in d
    ]

    pairs = []
    attempts = 0
    while len(pairs) < 100 and attempts < 1000:
        a, b = random.sample(valid_nodes, 2)
        try:
            length = nx.shortest_path_length(G, source=a, target=b, weight='weight')
            pairs.append((a, b, length))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        attempts += 1

    rows = []
    for a, b, dist in pairs:
        rows.append({
            'source_id': a,
            'source_lon': G.nodes[a].get('x'),
            'source_lat': G.nodes[a].get('y'),
            'destination_id': b,
            'destination_lon': G.nodes[b].get('x'),
            'destination_lat': G.nodes[b].get('y'),
            'time': dist,
        })

    df = pd.DataFrame(rows)
    df.to_csv(f'technical_validation_3_pairs/{city_name}.csv', index=False)

