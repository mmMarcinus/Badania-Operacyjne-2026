import sys
import os
import pandas as pd
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_extractor import fetch_and_filter_locations, get_or_calculate_distances, build_solver_data
from ACOsolver import ACOSolver
from evaluator import assign_demand1

def run_budget_experiment():
    print(" EKSPERYMENT 1: WRAŻLIWOŚĆ NA CIĘCIA BUDŻETOWE")
    print("==================================================")

    print("Pobieranie i przygotowanie danych bazy (Kraków)...")
    demand_gdf, stations_gdf = fetch_and_filter_locations(n_demand=50, n_stations=20)
    dist_matrix = get_or_calculate_distances(demand_gdf, stations_gdf)
    base_model_data = build_solver_data(demand_gdf, stations_gdf, dist_matrix)
    
    original_budget = 15_000
    
    budget_multipliers = [1.0, 0.8, 0.6, 0.4, 0.2, 0.01]
    results = []

    print(f"\nBudżet bazowy (100%): {original_budget / 1000}k PLN")

    for multiplier in budget_multipliers:
        current_budget = original_budget * multiplier
        print(f"\n---> Uruchamianie wariantu: {int(multiplier * 100)}% budżetu ({int(current_budget / 1000)}k PLN)")
        
        solver = ACOSolver(
            demand_points=base_model_data['demand_points'],
            dist_matrix=base_model_data['dist_matrix'],
            costs_f=base_model_data['costs_f'],
            costs_c=base_model_data['costs_c'],
            budget=current_budget,
            M=base_model_data['M'],
            n_ants=20,       
            n_iterations=50  
        )
        
        best_sol, best_z = solver.run()
        
        transport_cost = 0
        penalty_cost = 0
        budget_spent = 0
        stations_opened = 0
        total_chargers = 0
        
        if best_sol:
            x, s = assign_demand1(best_sol, base_model_data['demand_points'], base_model_data['dist_matrix'])
            
            penalty_cost = sum(s.values()) * base_model_data['P']
            transport_cost = sum(base_model_data['dist_matrix'][i][j] * amount for (i, j), amount in x.items())
            
            budget_spent = sum(base_model_data['costs_f'][j] + k * base_model_data['costs_c'][j] for j, k in best_sol)
            stations_opened = len(best_sol)
            total_chargers = sum(k for j, k in best_sol)
        else:
            penalty_cost = sum(base_model_data['demand_points'].values()) * base_model_data['P']
        
        results.append({
            "Wariant_Budzetu": f"{int(multiplier * 100)}%",
            "Limit_k_PLN": round(current_budget / 1000, 1),
            "Wydano_k_PLN": round(budget_spent / 1000, 1),
            "Funkcja_Z_k": round(best_z / 1000, 1) if best_sol else round(penalty_cost / 1000, 1),
            "Koszt_Transportu_k": round(transport_cost / 1000, 1),
            "Kary_k_PLN": round(penalty_cost / 1000, 1),
            "Otwarte_Stacje": stations_opened,
            "Liczba_Ladowarek": total_chargers
        })

    df = pd.DataFrame(results)
    os.makedirs('results', exist_ok=True)
    csv_path = 'results/budget_experiment_metrics.csv'
    df.to_csv(csv_path, index=False)
    print(f"\n[ZAPISANO] Tabularne wyniki eksperymentu: {csv_path}")
    print(df.to_string())

    plt.figure(figsize=(10, 6))
    
    variants = df["Wariant_Budzetu"]
    transports = df["Koszt_Transportu_k"]
    penalties = df["Kary_k_PLN"]

    p1 = plt.bar(variants, transports, color='royalblue', label='Koszty Transportu (Dojazdy)')
    p2 = plt.bar(variants, penalties, bottom=transports, color='crimson', label='Kary (Popyt Nieobsłużony)')

    plt.title('Składowe funkcji celu (Z) przy cięciach budżetowych', fontsize=14)
    plt.xlabel('Dostępny Budżet (% bazy)', fontsize=12)
    plt.ylabel('Wartość (tys. PLN)', fontsize=12)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for i in range(len(variants)):
        total_z = transports[i] + penalties[i]
        plt.text(i, total_z + (0.02 * total_z), f"Z = {int(total_z)}k", ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plot_path = 'results/budget_experiment_plot.png'
    plt.savefig(plot_path)
    print(f"[ZAPISANO] Wykres eksperymentu: {plot_path}")

if __name__ == "__main__":
    run_budget_experiment()