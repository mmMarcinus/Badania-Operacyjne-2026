"""
PIPELINE BADAWCZY — Optymalizacja sieci stacji ładowania EV algorytmem ACO
==========================================================================
Testuje:
  - 5 heurystyk: cost, demand, weighted_demand, coverage_efficiency, gravity
  - Siatka alpha x beta
  - Strategia wzmacniania feromonów: elitarne (top-3) vs. wszystkie mrówki
  - Krzywe zbieżności (Z per iteracja) dla najlepszych konfiguracji
  - Pełen zestaw wykresów porównawczych

ROZMIAR DANYCH: zmniejszony dla rozsądnego czasu obliczeń (~15-25 min).
"""

import math
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from ACOsolver import ACOSolver

# ---------------------------------------------------------------------------
# FLAGI STERUJĄCE
# ---------------------------------------------------------------------------
USE_SYNTHETIC_DATA = True
TEST_ELITE_VS_ALL  = True   # False = tylko elite-3, szybciej x2
PLOT_CONVERGENCE   = True
OUTPUT_DIR         = ""

# ---------------------------------------------------------------------------
# PARAMETRY DANYCH SYNTETYCZNYCH — zmniejszone żeby było szybko
# ---------------------------------------------------------------------------
N_DEMAND    = 80    # było 300
N_LOCATIONS = 30    # było 80

# ---------------------------------------------------------------------------
# PARAMETRY GRID SEARCH — mniej powtórzeń
# ---------------------------------------------------------------------------
HEURISTICS   = ["cost", "demand", "weighted_demand", "coverage_efficiency", "gravity"]
ALPHAS       = [0.2, 0.5, 1.0]
BETAS        = [0.5, 1.0, 2.0]
N_REPEATS    = 2     # było 3
N_ANTS       = 10    # było 15
N_ITERATIONS = 20    # było 25


# ===========================================================================
# ŁADOWANIE DANYCH
# ===========================================================================

def load_data():
    if USE_SYNTHETIC_DATA:
        from random_data_loader import generate_test_data
        print("Generowanie syntetycznego zbioru danych testowych...")
        return generate_test_data(
            n_demand=N_DEMAND,
            n_locations=N_LOCATIONS,
            area_size=20000,
            demand_min=10,
            demand_max=100,
            cost_f_min=2000,
            cost_f_max=8000,
            cost_c_min=300,
            cost_c_max=900,
            M=8,
            budget_factor=0.5,
            seed=42,
        )
    else:
        from data_extractor import (
            fetch_and_filter_locations,
            get_or_calculate_distances,
            build_solver_data,
        )
        demand_gdf, stations_gdf = fetch_and_filter_locations(n_demand=50, n_stations=20)
        dist_matrix = get_or_calculate_distances(demand_gdf, stations_gdf)
        return build_solver_data(demand_gdf, stations_gdf, dist_matrix)


# ===========================================================================
# DIAGNOSTYKA DANYCH WEJŚCIOWYCH
# ===========================================================================

def print_diagnostics(model_data):
    total_stations   = len(model_data['costs_f'])
    total_demand_pts = len(model_data['demand_points'])
    budget           = model_data['budget']
    M                = model_data['M']

    koszt_min = sum(model_data['costs_f'][j] + 1 * model_data['costs_c'][j]
                    for j in range(total_stations))
    koszt_max = sum(model_data['costs_f'][j] + M * model_data['costs_c'][j]
                    for j in range(total_stations))

    avg_cost_full = koszt_max / total_stations
    approx_k      = max(1, min(total_stations, round(budget / avg_cost_full)))
    approx_comb   = math.comb(total_stations, approx_k)
    total_per_cfg = N_ANTS * N_ITERATIONS * N_REPEATS

    print("\n" + "=" * 60)
    print("DIAGNOSTYKA DANYCH WEJŚCIOWYCH")
    print("=" * 60)
    print(f"  Punkty popytu:                        {total_demand_pts}")
    print(f"  Kandydaci na stacje:                  {total_stations}")
    print(f"  Budżet:                               {budget}")
    print(f"  Max ładowarek / stacja (M):           {M}")
    print(f"  Koszt wszystkich stacji (1 ład.):     {koszt_min:,.0f}")
    print(f"  Koszt wszystkich stacji (M ład.):     {koszt_max:,.0f}  "
          f"({100 * koszt_max / budget:.1f}% budżetu)")
    print(f"  Szac. liczba stacji w budżecie:       ~{approx_k} z {total_stations}")
    print(f"  Orientacyjna liczba kombinacji:       {approx_comb:.3e}")
    print(f"  Prób / konfigurację (ants×iter×rep):  {total_per_cfg}")
    print("=" * 60)

    return total_stations, budget, approx_comb


# ===========================================================================
# PRECOMPUTE nearest-station lookup (dla coverage_efficiency)
# ===========================================================================

def precompute_nearest(demand_points, dist_matrix, num_locations):
    """
    Dla każdego punktu popytu i zwraca posortowaną listę (dystans, j).
    Obliczane raz — używane przez coverage_efficiency żeby nie sortować
    n_locations razy per wywołanie heurystyki (było O(n²) → teraz O(n)).
    """
    nearest = {}
    for i in demand_points:
        dists = sorted(
            ((dist_matrix[i][jj], jj) for jj in range(num_locations)),
            key=lambda x: x[0]
        )
        nearest[i] = dists
    return nearest


# ===========================================================================
# SOLVER Z ZAPISEM KRZYWEJ ZBIEŻNOŚCI + PRECOMPUTED NEAREST
# ===========================================================================

class ACOSolverWithConvergence(ACOSolver):
    """
    Rozszerza ACOSolver o:
      - zapis best_z per iteracja (krzywe zbieżności)
      - parametr elite_k (ile mrówek zostawia feromon; 0 = wszystkie)
      - precomputed _nearest dla szybkiej coverage_efficiency
    """

    def __init__(self, *args, elite_k=3, nearest=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.elite_k = elite_k
        self._nearest = nearest  # słownik {i: [(dist, j), ...]} lub None

    def _get_heuristic(self, j, threshold=1700):
        cost = (self.costs_f[j] + self.costs_c[j])
        cost = max(cost, 1e-6)

        if self.heuristic == "cost":
            return 1.0 / cost

        elif self.heuristic == "demand":
            nearby_demand = 0
            for i in self.demand_points:
                if self.dist_matrix[i][j] < threshold:
                    nearby_demand += self.demand_points[i]
            return nearby_demand / cost

        elif self.heuristic == "weighted_demand":
            score = 0
            for i in self.demand_points:
                score += self.demand_points[i] / (self.dist_matrix[i][j] + 1)
            return score / cost

        elif self.heuristic == "coverage_efficiency":
            # Używa preobliczonego lookupa — O(n_demand) zamiast O(n_demand * n_loc * log)
            covered_uniquely = 0
            for i in self.demand_points:
                if self._nearest is None:
                    # fallback jeśli nie podano nearest
                    distances = sorted(self.dist_matrix[i])
                    nearest_d = distances[0]
                    second_d  = distances[1] if len(distances) > 1 else float('inf')
                    nearest_j_candidates = [
                        jj for jj in range(self.num_locations)
                        if self.dist_matrix[i][jj] == nearest_d
                    ]
                    is_nearest = (j in nearest_j_candidates)
                else:
                    nearest_d, nearest_j = self._nearest[i][0]
                    second_d             = self._nearest[i][1][0] if len(self._nearest[i]) > 1 else float('inf')
                    is_nearest           = (nearest_j == j)

                if is_nearest and second_d > threshold:
                    covered_uniquely += self.demand_points[i]
            return (covered_uniquely + 1) / cost

        elif self.heuristic == "gravity":
            score = 0
            for i in self.demand_points:
                d = self.dist_matrix[i][j] + 1
                score += self.demand_points[i] / (d ** 2)
            return score / cost

        return 1.0 / cost

    def run(self):
        from evaluator import calculate_z, assign_demand1

        best_z   = float('inf')
        best_sol = None
        self.convergence = []

        for _ in range(self.n_iterations):
            solutions = []
            for _ in range(self.n_ants):
                sol = self.construct_solution()
                z   = calculate_z(
                    d=self.dist_matrix,
                    ant_sol=sol,
                    demand_points=self.demand_points,
                    assign_func=assign_demand1,
                )
                solutions.append((sol, z))
                if z < best_z:
                    best_z   = z
                    best_sol = sol

            # Parowanie feromonów
            self.pheromones *= (1 - self.evaporation)

            # Wzmocnienie — elitarne lub wszystkie
            if self.elite_k and self.elite_k > 0:
                candidates = sorted(solutions, key=lambda x: x[1])[: self.elite_k]
            else:
                candidates = solutions

            for sol, z in candidates:
                reward = 1.0 / z
                for j, _k in sol:
                    self.pheromones[j] += reward

            self.convergence.append(best_z)

        return best_sol, best_z


# ===========================================================================
# JEDNA KONFIGURACJA → WYNIKI
# ===========================================================================

def run_config(model_data, heuristic, alpha, beta, elite_k, nearest):
    scores, n_stations_list, costs_list, convergences = [], [], [], []

    for _ in range(N_REPEATS):
        solver = ACOSolverWithConvergence(
            demand_points=model_data['demand_points'],
            dist_matrix=model_data['dist_matrix'],
            costs_f=model_data['costs_f'],
            costs_c=model_data['costs_c'],
            budget=model_data['budget'],
            M=model_data['M'],
            heuristic=heuristic,
            alpha=alpha,
            beta=beta,
            n_ants=N_ANTS,
            n_iterations=N_ITERATIONS,
            elite_k=elite_k,
            nearest=nearest,
        )
        sol, best_val = solver.run()
        scores.append(best_val)
        n_stations_list.append(len(sol))
        costs_list.append(sum(
            model_data['costs_f'][j] + k * model_data['costs_c'][j]
            for j, k in sol
        ))
        convergences.append(solver.convergence)

    avg_z    = float(np.mean(scores))
    std_z    = float(np.std(scores))
    avg_n    = float(np.mean(n_stations_list))
    avg_cost = float(np.mean(costs_list))
    avg_conv = list(np.mean(convergences, axis=0))

    return avg_z, std_z, avg_n, avg_cost, avg_conv


# ===========================================================================
# GRID SEARCH
# ===========================================================================

def grid_search(model_data, budget, nearest):
    results = []
    strategies = [(3, "elite-3"), (0, "all-ants")] if TEST_ELITE_VS_ALL else [(3, "elite-3")]

    total_configs = len(HEURISTICS) * len(ALPHAS) * len(BETAS) * len(strategies)
    done = 0
    t0   = time.time()

    for elite_k, strat_label in strategies:
        for heuristic in HEURISTICS:
            for alpha in ALPHAS:
                for beta in BETAS:
                    done    += 1
                    elapsed  = time.time() - t0
                    eta      = (elapsed / done) * (total_configs - done) if done > 1 else 0
                    print(
                        f"  [{done:3d}/{total_configs}] "
                        f"strat={strat_label:9s} heur={heuristic:20s} "
                        f"α={alpha} β={beta}  "
                        f"(upłynęło: {elapsed:.0f}s, ETA: {eta:.0f}s)",
                        end="", flush=True,
                    )

                    avg_z, std_z, avg_n, avg_cost, avg_conv = run_config(
                        model_data, heuristic, alpha, beta, elite_k, nearest
                    )
                    budget_pct = 100 * avg_cost / budget

                    print(
                        f"  →  Z={avg_z:.2f} (std={std_z:.2f}) "
                        f"| stacji={avg_n:.1f} | budżet={budget_pct:.1f}%"
                    )

                    results.append({
                        "strategy":        strat_label,
                        "heuristic":       heuristic,
                        "alpha":           alpha,
                        "beta":            beta,
                        "avg_z":           avg_z,
                        "std_z":           std_z,
                        "avg_n_stations":  avg_n,
                        "avg_cost":        avg_cost,
                        "budget_util_pct": budget_pct,
                        "convergence":     avg_conv,
                    })

    return pd.DataFrame(results)


# ===========================================================================
# DIAGNOSTYKA WYNIKÓW
# ===========================================================================

def print_results_summary(df, budget):
    print("\n" + "=" * 60)
    print("PODSUMOWANIE WYNIKÓW GRID SEARCH")
    print("=" * 60)

    top10 = df.nsmallest(10, "avg_z")[
        ["strategy", "heuristic", "alpha", "beta",
         "avg_z", "std_z", "avg_n_stations", "budget_util_pct"]
    ].reset_index(drop=True)
    print("\nTOP 10 konfiguracji (najniższe Z):")
    print(top10.to_string())

    print("\nŚrednie Z według heurystyki:")
    h_rank = (df.groupby("heuristic")["avg_z"]
                .agg(["mean", "std", "min"])
                .sort_values("mean")
                .rename(columns={"mean": "avg_Z", "std": "std_Z", "min": "best_Z"}))
    print(h_rank.to_string())

    if TEST_ELITE_VS_ALL:
        print("\nŚrednie Z według strategii wzmacniania:")
        s_rank = (df.groupby("strategy")["avg_z"]
                    .agg(["mean", "std", "min"])
                    .sort_values("mean")
                    .rename(columns={"mean": "avg_Z", "std": "std_Z", "min": "best_Z"}))
        print(s_rank.to_string())

    spread    = df["avg_z"].max() - df["avg_z"].min()
    avg_noise = df["std_z"].mean()
    ratio     = spread / avg_noise if avg_noise > 0 else float('inf')
    print(f"\nRozpiętość best_z między konfiguracjami: {spread:.2f}")
    print(f"Średni std_z (szum wewnątrz konfiguracji): {avg_noise:.2f}")
    print(f"Stosunek sygnał/szum: {ratio:.2f}x  "
          f"({'✓ różnice realne' if ratio > 3 else '⚠ dużo szumu'})")


# ===========================================================================
# WYKRESY
# ===========================================================================

def _fname(name):
    return f"{OUTPUT_DIR}{name}.png" if OUTPUT_DIR else f"{name}.png"


def plot_heuristic_comparison(df):
    grouped = df.groupby("heuristic")["avg_z"].agg(["mean", "std"]).sort_values("mean")
    colors  = cm.tab10(np.linspace(0, 0.6, len(grouped)))

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(grouped.index, grouped["mean"], yerr=grouped["std"],
                  color=colors, capsize=5, edgecolor="black", linewidth=0.7)
    ax.set_title("Porównanie heurystyk — średnie Z (niżej = lepiej)", fontsize=13)
    ax.set_xlabel("Heurystyka")
    ax.set_ylabel("Średnie Z")
    ax.bar_label(bars, fmt="%.0f", padding=6, fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    path = _fname("01_heuristic_comparison")
    plt.savefig(path, dpi=150); plt.close()
    print(f"  -> {path}")


def plot_alpha_beta_heatmaps(df):
    for heuristic in HEURISTICS:
        sub   = df[df["heuristic"] == heuristic]
        pivot = sub.pivot_table(index="alpha", columns="beta", values="avg_z", aggfunc="mean")

        fig, ax = plt.subplots(figsize=(7, 4))
        im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn_r",
                       vmin=pivot.values.min(), vmax=pivot.values.max())
        plt.colorbar(im, ax=ax, label="Średnie Z")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([str(b) for b in pivot.columns])
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([str(a) for a in pivot.index])
        ax.set_xlabel("Beta (β)"); ax.set_ylabel("Alpha (α)")
        ax.set_title(f"Heatmapa α×β  |  heurystyka: {heuristic}", fontsize=12)

        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                ax.text(j, i, f"{pivot.values[i, j]:.0f}",
                        ha="center", va="center", fontsize=8,
                        color="black" if pivot.values[i, j] < pivot.values.mean() else "white")

        plt.tight_layout()
        path = _fname(f"02_heatmap_{heuristic}")
        plt.savefig(path, dpi=150); plt.close()
        print(f"  -> {path}")


def plot_beta_lines(df):
    fig, ax = plt.subplots(figsize=(9, 5))
    colors  = cm.tab10(np.linspace(0, 0.9, len(HEURISTICS)))
    for heuristic, color in zip(HEURISTICS, colors):
        sub     = df[df["heuristic"] == heuristic]
        grouped = sub.groupby("beta")["avg_z"].mean()
        ax.plot(grouped.index, grouped.values, marker="o",
                label=heuristic, color=color, linewidth=2)
    ax.set_title("Wpływ parametru β na jakość — wszystkie heurystyki", fontsize=13)
    ax.set_xlabel("Beta (β)"); ax.set_ylabel("Średnie Z (niżej = lepiej)")
    ax.legend(title="Heurystyka", fontsize=9); ax.grid(linestyle="--", alpha=0.5)
    plt.tight_layout()
    path = _fname("03_beta_lines")
    plt.savefig(path, dpi=150); plt.close()
    print(f"  -> {path}")


def plot_alpha_lines(df):
    fig, ax = plt.subplots(figsize=(9, 5))
    colors  = cm.tab10(np.linspace(0, 0.9, len(HEURISTICS)))
    for heuristic, color in zip(HEURISTICS, colors):
        sub     = df[df["heuristic"] == heuristic]
        grouped = sub.groupby("alpha")["avg_z"].mean()
        ax.plot(grouped.index, grouped.values, marker="s",
                label=heuristic, color=color, linewidth=2)
    ax.set_title("Wpływ parametru α na jakość — wszystkie heurystyki", fontsize=13)
    ax.set_xlabel("Alpha (α)"); ax.set_ylabel("Średnie Z (niżej = lepiej)")
    ax.legend(title="Heurystyka", fontsize=9); ax.grid(linestyle="--", alpha=0.5)
    plt.tight_layout()
    path = _fname("04_alpha_lines")
    plt.savefig(path, dpi=150); plt.close()
    print(f"  -> {path}")


def plot_elite_vs_all(df):
    if df["strategy"].nunique() < 2:
        return
    grouped = df.groupby(["heuristic", "strategy"])["avg_z"].mean().unstack()
    x, width = np.arange(len(grouped.index)), 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, col in enumerate(grouped.columns):
        ax.bar(x + i * width, grouped[col], width,
               label=col, edgecolor="black", linewidth=0.6)
    ax.set_title("Elitarne vs. wszystkie mrówki — średnie Z per heurystyka", fontsize=12)
    ax.set_xlabel("Heurystyka"); ax.set_ylabel("Średnie Z (niżej = lepiej)")
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(grouped.index, rotation=15)
    ax.legend(title="Strategia"); ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    path = _fname("05_elite_vs_all")
    plt.savefig(path, dpi=150); plt.close()
    print(f"  -> {path}")


def plot_convergence_curves(df):
    top5   = df.nsmallest(5, "avg_z")
    worst3 = df.nlargest(3, "avg_z")

    fig, ax = plt.subplots(figsize=(10, 6))
    colors_good = cm.Blues(np.linspace(0.5, 0.9, len(top5)))
    colors_bad  = cm.Reds(np.linspace(0.5, 0.9, len(worst3)))

    for idx, (_, row) in enumerate(top5.iterrows()):
        lbl = f"[TOP] {row['heuristic']} α={row['alpha']} β={row['beta']}"
        if TEST_ELITE_VS_ALL:
            lbl += f" ({row['strategy']})"
        ax.plot(row["convergence"], color=colors_good[idx], linewidth=2, label=lbl)

    for idx, (_, row) in enumerate(worst3.iterrows()):
        lbl = f"[WORST] {row['heuristic']} α={row['alpha']} β={row['beta']}"
        if TEST_ELITE_VS_ALL:
            lbl += f" ({row['strategy']})"
        ax.plot(row["convergence"], color=colors_bad[idx],
                linewidth=1.5, linestyle="--", label=lbl)

    ax.set_title("Krzywe zbieżności — TOP-5 vs. WORST-3 konfiguracji", fontsize=13)
    ax.set_xlabel("Iteracja"); ax.set_ylabel("Najlepsze Z (niżej = lepiej)")
    ax.legend(fontsize=7, loc="upper right"); ax.grid(linestyle="--", alpha=0.4)
    plt.tight_layout()
    path = _fname("06_convergence_curves")
    plt.savefig(path, dpi=150); plt.close()
    print(f"  -> {path}")


def plot_budget_utilization(df):
    fig, ax    = plt.subplots(figsize=(9, 5))
    colors     = cm.tab10(np.linspace(0, 0.9, len(HEURISTICS)))
    color_map  = dict(zip(HEURISTICS, colors))
    for heuristic in HEURISTICS:
        sub = df[df["heuristic"] == heuristic]
        ax.scatter(sub["budget_util_pct"], sub["avg_z"],
                   color=color_map[heuristic], label=heuristic,
                   alpha=0.7, s=50, edgecolors="black", linewidths=0.4)
    ax.set_title("Zużycie budżetu vs. jakość rozwiązania", fontsize=13)
    ax.set_xlabel("Średnie zużycie budżetu [%]"); ax.set_ylabel("Średnie Z (niżej = lepiej)")
    ax.legend(title="Heurystyka", fontsize=9); ax.grid(linestyle="--", alpha=0.4)
    plt.tight_layout()
    path = _fname("07_budget_vs_quality")
    plt.savefig(path, dpi=150); plt.close()
    print(f"  -> {path}")


def plot_std_stability(df):
    grouped = df.groupby("heuristic")["std_z"].mean().sort_values()
    colors  = cm.tab10(np.linspace(0, 0.6, len(grouped)))
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(grouped.index, grouped.values, color=colors,
                  edgecolor="black", linewidth=0.7)
    ax.set_title("Stabilność algorytmu — średnie std_z per heurystyka\n"
                 "(niżej = bardziej deterministyczny)", fontsize=12)
    ax.set_xlabel("Heurystyka"); ax.set_ylabel("Średnie std_z")
    ax.bar_label(bars, fmt="%.0f", padding=4, fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    path = _fname("08_stability_std")
    plt.savefig(path, dpi=150); plt.close()
    print(f"  -> {path}")


def generate_all_plots(df):
    print("\nGenerowanie wykresów...")
    plot_heuristic_comparison(df)
    plot_alpha_beta_heatmaps(df)
    plot_beta_lines(df)
    plot_alpha_lines(df)
    if TEST_ELITE_VS_ALL:
        plot_elite_vs_all(df)
    if PLOT_CONVERGENCE:
        plot_convergence_curves(df)
    plot_budget_utilization(df)
    plot_std_stability(df)


# ===========================================================================
# ZAPIS CSV
# ===========================================================================

def save_results(df):
    df_csv = df.drop(columns=["convergence"], errors="ignore")
    path   = "wyniki_grid_search.csv"
    df_csv.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"\nWyniki zapisano do: {path}")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print("=" * 60)
    print("  PIPELINE BADAWCZY — Sieć stacji ładowania EV (ACO)")
    print("=" * 60)

    model_data = load_data()
    total_stations, budget, approx_comb = print_diagnostics(model_data)

    # Preoblicz lookup najbliższych stacji — używany przez coverage_efficiency
    print("\nPreobliczanie lookupa najbliższych stacji (coverage_efficiency)...", end="", flush=True)
    nearest = precompute_nearest(
        model_data['demand_points'],
        model_data['dist_matrix'],
        len(model_data['costs_f'])
    )
    print(" gotowe.")

    total_configs = len(HEURISTICS) * len(ALPHAS) * len(BETAS)
    if TEST_ELITE_VS_ALL:
        total_configs *= 2

    # Szacowanie czasu: coverage_efficiency ~2x wolniejsza nawet z lookupem,
    # pozostałe ~1s/konfigurację przy tych rozmiarach danych
    print(f"\nGrid search: {total_configs} konfiguracji × {N_REPEATS} powtórzeń")
    print(f"Szacowany czas: ~{total_configs * 2 // 60}–{total_configs * 3 // 60} min")
    print("\nRozpoczynam...\n")

    t_start = time.time()
    df      = grid_search(model_data, budget, nearest)
    t_total = time.time() - t_start

    print(f"\nGrid search zakończony w {t_total:.1f}s ({t_total/60:.1f} min)")

    print_results_summary(df, budget)
    generate_all_plots(df)
    save_results(df)

    best_row = df.loc[df["avg_z"].idxmin()]
    print("\n" + "=" * 60)
    print("NAJLEPSZA KONFIGURACJA:")
    print(f"  Heurystyka: {best_row['heuristic']}")
    print(f"  Alpha:      {best_row['alpha']}")
    print(f"  Beta:       {best_row['beta']}")
    if TEST_ELITE_VS_ALL:
        print(f"  Strategia:  {best_row['strategy']}")
    print(f"  Średnie Z:  {best_row['avg_z']:.2f}  (std={best_row['std_z']:.2f})")
    print(f"  Śr. stacji: {best_row['avg_n_stations']:.1f} / {total_stations}")
    print(f"  Śr. budżet: {best_row['avg_cost']:.0f}  ({best_row['budget_util_pct']:.1f}%)")
    print("=" * 60)
    print("\nEksperyment zakończony pomyślnie!")


if __name__ == "__main__":
    main()