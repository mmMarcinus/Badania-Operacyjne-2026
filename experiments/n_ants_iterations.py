import json
import time
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from ACOsolver import ACOSolver
from random_data_loader import generate_test_data

BASE_CONFIG = {
    "num_ants": 20,
    "num_iterations": 100,
}

EXPERIMENTS = {
    "num_ants": [5, 10, 20, 50, 100],
    "num_iterations": [10, 20, 50, 100, 200]
}

def run_single_series(param_name, param_values, repeats=10):
    """Uruchamia testy dla wybranego parametru"""
    data = generate_test_data(seed=42)
    series_results = []
    
    for val in param_values:
        print(f" -> Testuję {param_name} = {val} ({repeats} uruchomień)...")
        costs = []
        execution_times = []
        
        current_config = BASE_CONFIG.copy()
        current_config[param_name] = val
        
        for _ in range(repeats):
            start_time = time.time()
            
            aco = ACOSolver(
                demand_points=data['demand_points'],
                dist_matrix=data['dist_matrix'],
                costs_f=data['costs_f'],
                costs_c=data['costs_c'],
                budget=data['budget'],
                M=data['M'],
                heuristic="cost",
                alpha=0.5,
                beta=1,
                n_iterations=current_config["num_iterations"],
                n_ants=current_config["num_ants"]
            )
            _, best_cost = aco.run()
            
            end_time = time.time()
            costs.append(best_cost)
            execution_times.append(end_time - start_time)
            
        series_results.append({
            "param_value": val,
            "min_cost": float(np.min(costs)),
            "max_cost": float(np.max(costs)),
            "mean_cost": float(np.mean(costs)),
            "std_dev_cost": float(np.std(costs)),
            "mean_time_s": float(np.mean(execution_times))
        })
        
    return series_results

def process_and_save(param_name, results):
    """Buduje DataFrame, drukuje tabele (tekst + markdown), zapisuje pliki w /results."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(script_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    df = pd.DataFrame(results)
    
    headers = {
        "param_value": param_name,
        "min_cost": "Min Koszt",
        "max_cost": "Max Koszt",
        "mean_cost": "Średni Koszt",
        "std_dev_cost": "Odchylenie Std",
        "mean_time_s": "Czas (s)"
    }
    df = df[list(headers.keys())].rename(columns=headers)
    
    df["Średni Koszt"] = df["Średni Koszt"].round(2)
    df["Odchylenie Std"] = df["Odchylenie Std"].round(2)
    df["Czas (s)"] = df["Czas (s)"].round(4)
    
    print(f"\n=== TABELA DLA PARAMETRU: {param_name} ===")
    # print(df.to_string(index=False))
    # print("\n[Kod Markdown do sprawozdania]:")
    print(df.to_markdown(index=False))
    
    json_path = os.path.join(results_dir, f"results_{param_name}.json")
    df.to_json(json_path, orient="records", indent=4, force_ascii=False)

    plt.figure(figsize=(10, 5))
    plt.errorbar(
        df[param_name], 
        df["Średni Koszt"], 
        yerr=df["Odchylenie Std"], 
        fmt='-o', color='b', ecolor='r', capsize=5, 
        label=r'Średni koszt $\pm$ std_dev'
    )
    
    plt.title(f"Wpływ parametru '{param_name}' na ostateczny koszt (Z)")
    plt.xlabel(param_name)
    plt.ylabel('Koszt (Z)')
    plt.grid(True, linestyle='--')
    plt.legend()
    
    plot_path = os.path.join(results_dir, f"plot_{param_name}.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    
    print(f"\n[Zapisano pliki]:\n  -> {json_path}\n  -> {plot_path}\n" + "-"*40)

def main():
    
    for param_name, values in EXPERIMENTS.items():
        print(f"\nRozpoczynam badanie parametru: {param_name}")
        raw_results = run_single_series(param_name, values)
        process_and_save(param_name, raw_results)
        
    print("\nWszystkie eksperymenty zakończone. Wyniki znajdziesz w folderze: experiments/results/")

if __name__ == "__main__":
    main()