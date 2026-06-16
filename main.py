from random_data_loader import generate_test_data
from ACOsolver import ACOSolver

import pandas as pd
import matplotlib.pyplot as plt

# ======================
# GENEROWANIE DATASETÓW
# ======================

datasets = []

for seed in range(20):

    data = generate_test_data(seed=seed)

    datasets.append(data)

# ======================
# PARAMETRY TESTÓW
# ======================

heuristics = [
    "cost",
    "demand",
    "weighted_demand"
]

alphas = [0.2, 0.5, 1]

betas = [0.2, 0.6, 1]

results = []

# ======================
# BENCHMARK
# ======================

for dataset_id, data in enumerate(datasets):

    print(f"\nDATASET {dataset_id}")

    for heuristic in heuristics:

        for alpha in alphas:

            for beta in betas:

                solver = ACOSolver(
                    demand_points=data['demand_points'],
                    dist_matrix=data['dist_matrix'],
                    costs_f=data['costs_f'],
                    costs_c=data['costs_c'],
                    budget=data['budget'],
                    M=data['M'],
                    heuristic=heuristic,
                    alpha=alpha,
                    beta=beta,
                    n_iterations=50,
                    n_ants=10
                )

                best_sol, best_val = solver.run()

                print(
                    f"Heuristic={heuristic}, "
                    f"alpha={alpha}, "
                    f"beta={beta}, "
                    f"Z={best_val}"
                )

                results.append({
                    "dataset": dataset_id,
                    "heuristic": heuristic,
                    "alpha": alpha,
                    "beta": beta,
                    "best_z": best_val
                })

# ======================
# DATAFRAME
# ======================

df = pd.DataFrame(results)

print("\n===== ŚREDNIE WYNIKI =====")

summary = (
    df.groupby(
        ["heuristic", "alpha", "beta"]
    )["best_z"]
    .mean()
    .reset_index()
)

print(summary)

# ======================
# WYKRES
# ======================

for heuristic in heuristics:

    subset = df[df["heuristic"] == heuristic]

    grouped = subset.groupby("beta")["best_z"].mean()

    plt.figure()

    plt.plot(grouped.index, grouped.values)

    plt.title(f"Heuristic: {heuristic}")

    plt.xlabel("Beta")

    plt.ylabel("Average Best Z")

    plt.savefig(f"heuristic_{heuristic}.png")