import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_extractor import fetch_and_filter_locations, get_or_calculate_distances, build_solver_data
from ACOsolver import ACOSolver
from evaluator import assign_demand1

def run_m_experiment():
    print(" EKSPERYMENT 2: CENTRALIZACJA VS DECENTRALIZACJA")
    print("==================================================")

    print("Pobieranie i przygotowanie danych bazy (Kraków)...")
    demand_gdf, stations_gdf = fetch_and_filter_locations(n_demand=50, n_stations=20)
    dist_matrix = get_or_calculate_distances(demand_gdf, stations_gdf)
    base_model_data = build_solver_data(demand_gdf, stations_gdf, dist_matrix)

    m_variants = [2, 4, 6, 8, 12]
    results = []

    for m_val in m_variants:
        print(f"\n---> Uruchamianie wariantu: Limit M = {m_val} ładowarek/stację")
        
        solver = ACOSolver(
            demand_points=base_model_data['demand_points'],
            dist_matrix=base_model_data['dist_matrix'],
            costs_f=base_model_data['costs_f'],
            costs_c=base_model_data['costs_c'],
            budget=base_model_data['budget'],
            M=m_val,         
            n_ants=20,       
            n_iterations=50  
        )
        
        best_sol, best_z = solver.run()
        
        transport_cost = 0
        penalty_cost = 0
        stations_opened = 0
        total_chargers = 0
        unserved_cars = 0
        
        if best_sol:
            x, s = assign_demand1(best_sol, base_model_data['demand_points'], base_model_data['dist_matrix'])
            
            unserved_cars = sum(s.values())
            penalty_cost = unserved_cars * base_model_data['P']
            transport_cost = sum(base_model_data['dist_matrix'][i][j] * amount for (i, j), amount in x.items())
            
            stations_opened = len(best_sol)
            total_chargers = sum(k for j, k in best_sol)
        else:
            unserved_cars = sum(base_model_data['demand_points'].values())
            penalty_cost = unserved_cars * base_model_data['P']
        
        results.append({
            "Limit_M": m_val,
            "Otwarte_Stacje": stations_opened,
            "Liczba_Ladowarek": total_chargers,
            "Calkowity_Dystans_m": transport_cost,
            "Nieobsluzone_Auta": unserved_cars,
            "Funkcja_Z": best_z
        })

    df = pd.DataFrame(results)
    os.makedirs('results', exist_ok=True)
    csv_path = 'results/m_limit_metrics.csv'
    df.to_csv(csv_path, index=False)
    print(f"\n[ZAPISANO] Tabularne wyniki eksperymentu: {csv_path}")
    print(df.to_string())

    fig, ax1 = plt.subplots(figsize=(10, 6))

    color1 = 'tab:blue'
    ax1.set_xlabel('Maksymalna liczba ładowarek na stacji (M)', fontsize=12)
    ax1.set_ylabel('Calkowity Dystans Kierowców (m)', color=color1, fontsize=12)
    line1 = ax1.plot(df["Limit_M"], df["Calkowity_Dystans_m"], color=color1, marker='o', linewidth=2, label='Całkowity dystans')
    ax1.tick_params(axis='y', labelcolor=color1)

    ax2 = ax1.twinx()  
    color2 = 'tab:green'
    ax2.set_ylabel('Liczba Otwartych Stacji', color=color2, fontsize=12)
    line2 = ax2.plot(df["Limit_M"], df["Otwarte_Stacje"], color=color2, marker='s', linestyle='--', linewidth=2, label='Liczba stacji')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim(bottom=0, top=max(df["Otwarte_Stacje"]) + 2)

    plt.title('Zjawisko Centralizacji: Wpływ limitu M na wielkość sieci i dystans użytkowników', fontsize=14)
    fig.tight_layout()
    
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper right')
    
    plt.grid(alpha=0.3)
    plot_path = 'results/m_limit_plot.png'
    plt.savefig(plot_path)
    print(f"[ZAPISANO] Wykres eksperymentu: {plot_path}")

if __name__ == "__main__":
    run_m_experiment()