import os
import json
import osmnx as ox
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from constants import COST_F, COST_C, M_LIMIT, BUDGET, P, K
import folium

def generate_interactive_map(demand_gdf, stations_gdf, best_sol=None, filename="mapa_krakowa.html"):
    print("\nGenerowanie interaktywnej mapy...")
    
    m = folium.Map(location=[50.0614, 19.9383], zoom_start=13, tiles="cartodbpositron")
    
    for i, row in demand_gdf.iterrows():
        radius_size = max(5, row['area_sqm'] / 1000) 
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius_size,
            color='#3186cc',
            fill=True,
            fill_color='#3186cc',
            fill_opacity=0.6,
            tooltip=f"Popyt #{i}<br>Powierzchnia: {row['area_sqm']:.0f} m²"
        ).add_to(m)

    chosen_stations = {j: k for j, k in best_sol} if best_sol else {}

    for j, row in stations_gdf.iterrows():
        is_chosen = j in chosen_stations
        
        if is_chosen:
            k_ładowarek = chosen_stations[j]
            folium.Marker(
                location=[row['lat'], row['lon']],
                icon=folium.Icon(color='green', icon='bolt', prefix='fa'),
                tooltip=f"<b>OTWARTA STACJA #{j}</b><br>Liczba ładowarek: {k_ładowarek}"
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=4,
                color='gray',
                fill=True,
                tooltip=f"Potencjalna lokalizacja #{j} (Nieczynna)"
            ).add_to(m)

    m.save(filename)
    print(f"Mapa gotowa! Otwórz plik '{filename}' w swojej przeglądarce.")


def fetch_and_filter_locations(place_name="Kraków, Poland", n_demand=30, n_stations=20):
    print(f"Pobieranie danych dla obszaru: {place_name}...")
    
    tags_J = {'amenity': ['parking', 'fuel'], 'shop': 'mall'}
    tags_I = {'building': ['office', 'university', 'commercial']} 
    
    print("Pobieranie potencjalnych lokalizacji stacji (J)...")
    gdf_J = ox.features_from_place(place_name, tags_J)
    print("Pobieranie punktów popytu (I)...")
    gdf_I = ox.features_from_place(place_name, tags_I)

    def process_gdf(gdf, top_n):
        gdf_filtered = gdf[gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])].copy()
        gdf_proj = gdf_filtered.to_crs(gdf_filtered.estimate_utm_crs())
        gdf_filtered['area_sqm'] = gdf_proj.geometry.area
        gdf_top = gdf_filtered.sort_values(by='area_sqm', ascending=False).head(top_n).copy()
        gdf_top['geometry'] = gdf_top.geometry.centroid
        
        gdf_top['lat'] = gdf_top.geometry.y
        gdf_top['lon'] = gdf_top.geometry.x
        
        return gdf_top.reset_index(drop=True)
    
    print("Przetwarzanie i filtrowanie danych...")
    stations_gdf = process_gdf(gdf_J, n_stations)
    demand_gdf = process_gdf(gdf_I, n_demand)
    
    return demand_gdf, stations_gdf

def get_or_calculate_distances(demand_gdf, stations_gdf, place_name="Kraków, Poland", cache_file="krakow_distances.json"):
    if os.path.exists(cache_file):
        print(f"Znaleziono plik cache, Ładowanie macierzy odległości z {cache_file}...")
        with open(cache_file, 'r') as f:
            return json.load(f)
            
    print("Brak pliku cache. Pobieranie siatki drogowej dla miasta...")
    G = ox.graph_from_place(place_name, network_type="drive")
    
    print("Obliczanie najkrótszych ścieżek...")
    dist_matrix = []
    
    demand_nodes = ox.distance.nearest_nodes(G, demand_gdf['lon'].tolist(), demand_gdf['lat'].tolist())
    station_nodes = ox.distance.nearest_nodes(G, stations_gdf['lon'].tolist(), stations_gdf['lat'].tolist())
    
    for i, d_node in enumerate(demand_nodes):
        row = []
        for j, s_node in enumerate(station_nodes):
            try:
                dist = nx.shortest_path_length(G, d_node, s_node, weight='length')
                row.append(round(dist, 2))
            except nx.NetworkXNoPath:
                row.append(100000.0)
        dist_matrix.append(row)
        
    with open(cache_file, 'w') as f:
        json.dump(dist_matrix, f)
    print(f"Zapisano macierz odległości do {cache_file}.")
        
    return dist_matrix

def build_solver_data(demand_gdf, stations_gdf, dist_matrix):
    demand_points = {}
    for i, row in demand_gdf.iterrows():
        cars = max(5, int(row['area_sqm'] / 150))
        demand_points[i] = cars

    n_stations = len(stations_gdf)
    costs_f = [COST_F] * n_stations
    costs_c = [COST_C] * n_stations
    
    return { 
        "demand_points": demand_points,
        "dist_matrix": dist_matrix,
        "costs_f": costs_f,
        "costs_c": costs_c,
        "budget": BUDGET,
        "M": M_LIMIT,
        "P": P, 
        "K": K 
    }

if __name__ == "__main__":
    demand_gdf, stations_gdf = fetch_and_filter_locations(n_demand=50, n_stations=20)
    
    dist_matrix = get_or_calculate_distances(demand_gdf, stations_gdf)
    
    model_data = build_solver_data(demand_gdf, stations_gdf, dist_matrix)
    
    print("\n--- ZESTAWIENIE DANYCH MODELU ---")
    print(f"Liczba punktów popytu (I): {len(model_data['demand_points'])}")
    print(f"Liczba stacji (J): {len(model_data['costs_f'])}")
    print(f"Przykładowy popyt w p. 0: {model_data['demand_points'][0]} aut")
    print(f"Dystans z p. 0 do stacji 0: {model_data['dist_matrix'][0][0]} m")

    generate_interactive_map(demand_gdf, stations_gdf, filename="mapa_krakowa_start.html")
    
    example_solution = [(0, 5), (4, 2), (12, 6)]
    
    generate_interactive_map(demand_gdf, stations_gdf, best_sol=example_solution, filename="mapa_krakowa_wynik.html")