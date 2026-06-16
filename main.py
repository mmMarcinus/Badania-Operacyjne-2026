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
# =======
# import pandas as pd
# import matplotlib.pyplot as plt

# # ======================
# # GENEROWANIE DATASETÓW
# # ======================

# datasets = []

# for seed in range(20):

#     data = generate_test_data(seed=seed)

#     datasets.append(data)

# # ======================
# # PARAMETRY TESTÓW
# # ======================

# heuristics = [
#     "cost",
#     "demand",
#     "weighted_demand"
# ]

# alphas = [0.2, 0.5, 1]

# betas = [0.2, 0.6, 1]

# results = []

# # ======================
# # BENCHMARK
# # ======================

# for dataset_id, data in enumerate(datasets):

#     print(f"\nDATASET {dataset_id}")

#     for heuristic in heuristics:

#         for alpha in alphas:

#             for beta in betas:

#                 solver = ACOSolver(
#                     demand_points=data['demand_points'],
#                     dist_matrix=data['dist_matrix'],
#                     costs_f=data['costs_f'],
#                     costs_c=data['costs_c'],
#                     budget=data['budget'],
#                     M=data['M'],
#                     heuristic=heuristic,
#                     alpha=alpha,
#                     beta=beta,
#                     n_iterations=50,
#                     n_ants=10
#                 )

#                 best_sol, best_val = solver.run()

#                 print(
#                     f"Heuristic={heuristic}, "
#                     f"alpha={alpha}, "
#                     f"beta={beta}, "
#                     f"Z={best_val}"
#                 )

#                 results.append({
#                     "dataset": dataset_id,
#                     "heuristic": heuristic,
#                     "alpha": alpha,
#                     "beta": beta,
#                     "best_z": best_val
#                 })

# # ======================
# # DATAFRAME
# # ======================

# df = pd.DataFrame(results)

# print("\n===== ŚREDNIE WYNIKI =====")

# summary = (
#     df.groupby(
#         ["heuristic", "alpha", "beta"]
#     )["best_z"]
#     .mean()
#     .reset_index()
# )

# print(summary)

# # ======================
# # WYKRES
# # ======================

# for heuristic in heuristics:

#     subset = df[df["heuristic"] == heuristic]

#     grouped = subset.groupby("beta")["best_z"].mean()

#     plt.figure()

#     plt.plot(grouped.index, grouped.values)

#     plt.title(f"Heuristic: {heuristic}")

#     plt.xlabel("Beta")

#     plt.ylabel("Average Best Z")

#     plt.savefig(f"heuristic_{heuristic}.png")
