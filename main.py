from data_extractor import (
    fetch_and_filter_locations, 
    get_or_calculate_distances, 
    build_solver_data, 
    generate_interactive_map
)
from ACOsolver import ACOSolver

def main():
    print(" OPTYMALIZACJA STACJI ŁADOWANIA - KRAKÓW")
    print("==================================================")
    
    print("\n--- POBIERANIE I PRZYGOTOWANIE DANYCH ---")
    demand_gdf, stations_gdf = fetch_and_filter_locations(n_demand=50, n_stations=20)
    
    dist_matrix = get_or_calculate_distances(demand_gdf, stations_gdf)
    model_data = build_solver_data(demand_gdf, stations_gdf, dist_matrix)
    
    print("\n--- GENEROWANIE MAPY POCZĄTKOWEJ ---")
    generate_interactive_map(demand_gdf, stations_gdf, filename="mapa_krakowa_start.html")
    
    print("\n--- URUCHOMIENIE ALGORYTMU MRÓWKOWEGO ---")
    print(f"Budżet: {model_data['budget']} PLN")
    print("Rozpoczynam poszukiwanie optymalnego rozwiązania...")
    
    solver = ACOSolver(
        demand_points=model_data['demand_points'],
        dist_matrix=model_data['dist_matrix'],
        costs_f=model_data['costs_f'],
        costs_c=model_data['costs_c'],
        budget=model_data['budget'],
        M=model_data['M'],
        n_ants=20,         # Liczba mrówek
        n_iterations=50    # Liczba iteracji (pokoleń)
    )
    
    best_sol, best_val = solver.run()
    
    print(" WYNIK KOŃCOWY")
    print("==================================================")
    print(f"Najlepszy całkowity koszt (Z): {best_val}")
    print(f"Wybrane stacje (Indeks J, Liczba ładowarek):")
    
    if not best_sol:
        print(" -> Brak wybranych stacji (budżet za mały lub błąd algorytmu).")
    else:
        for j, k in sorted(best_sol):
            print(f" -> Stacja nr {j:02d}: {k} ładowarek (Koszt: {model_data['costs_f'][j] + k * model_data['costs_c'][j]} PLN)")

    print("\n--- GENEROWANIE MAPY WYNIKOWEJ ---")
    generate_interactive_map(demand_gdf, stations_gdf, best_sol=best_sol, filename="mapa_krakowa_wynik.html")
    print("Gotowe!")

if __name__ == "__main__":
    main()