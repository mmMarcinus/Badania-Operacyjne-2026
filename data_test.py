import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd

def get_road_distance(G, point_a, point_b):
    node_a = ox.distance.nearest_nodes(G, point_a[1], point_a[0])
    node_b = ox.distance.nearest_nodes(G, point_b[1], point_b[0])
    return nx.shortest_path_length(G, node_a, node_b, weight='length')

print("rozpoczynam pobieranie")
G = ox.graph_from_place("Kraków, Poland", network_type="drive")
print("kończe pobieranie")

n = 120 
place_name = "Kraków, Poland"
tags = {'amenity': 'parking'}

print(f"Pobieranie danych...")
parkingi = ox.features_from_place(place_name, tags)

parkingi['capacity_num'] = pd.to_numeric(parkingi['capacity'], errors='coerce')

parkingi_filtered = parkingi[parkingi['capacity_num'] > n].copy()

parkingi_filtered['geometry'] = parkingi_filtered.geometry.centroid
parkingi_filtered['lat'] = parkingi_filtered.geometry.y
parkingi_filtered['lon'] = parkingi_filtered.geometry.x

print(f"Liczba wszystkich parkingów w Krakowie: {len(parkingi)}")
print(f"Liczba parkingów z pojemnością > {n}: {len(parkingi_filtered)}")

ax = parkingi_filtered.plot(markersize=15, color='green', alpha=0.7, figsize=(10, 10))
plt.title(f"Lokalizacje (Parkingi z capacity > {n})")
plt.show()