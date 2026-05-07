import random
import numpy as np
from constants import P, K 
from evaluator import calculate_z, assign_demand1, assign_demand2

class ACOSolver:
    def __init__(self, demand_points, dist_matrix, costs_f, costs_c, budget, M, 
                 n_ants=10, n_iterations=50, alpha=1, beta=2, evaporation=0.1):
        self.demand_points = demand_points
        self.dist_matrix = dist_matrix
        self.costs_f = costs_f  # Koszty stałe stacji
        self.costs_c = costs_c  # Koszty ładowarki
        self.budget = budget    # Budżet B
        self.M = M              # Maksymalna liczba ładowarek
        
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.alpha = alpha  # Waga feromonu
        self.beta = beta    # Waga heurystyki
        self.evaporation = evaporation
        
        # Inicjalizacja feromonów dla każdej lokalizacji j
        self.num_locations = len(costs_f)
        self.pheromones = np.ones(self.num_locations)

    def _get_heuristic(self, j):
        """Heurystyka: preferujemy tańsze lokalizacje."""
        return 1.0 / (self.costs_f[j] + self.costs_c[j])

    def construct_solution(self):
        """Pojedyncza mrówka buduje rozwiązanie respektując budżet."""
        ant_sol = []
        current_budget = self.budget
        available_indices = list(range(self.num_locations))
        
        # Mrówka wybiera losowo stacje, dopóki ma budżet
        while available_indices and current_budget > 0:
            # Obliczanie prawdopodobieństw
            probs = []
            for j in available_indices:
                p = (self.pheromones[j] ** self.alpha) * (self._get_heuristic(j) ** self.beta)
                probs.append(p)
            
            probs = np.array(probs) / sum(probs)
            chosen_idx = np.random.choice(available_indices, p=probs)
            
            # Losowanie liczby ładowarek k_j (1 do M)
            k_j = random.randint(1, self.M)
            cost = self.costs_f[chosen_idx] + (k_j * self.costs_c[chosen_idx])
            
            if cost <= current_budget:
                ant_sol.append((chosen_idx, k_j))
                current_budget -= cost
            
            available_indices.remove(chosen_idx)
            
        return ant_sol

    def run(self):
        best_z = float('inf')
        best_sol = None

        for i in range(self.n_iterations):
            solutions = []
            for _ in range(self.n_ants):
                sol = self.construct_solution()
                # Obliczanie Z dla mrówki
                z = calculate_z(d=self.dist_matrix, ant_sol=sol, demand_points=self.demand_points, assign_func=assign_demand1)
                solutions.append((sol, z))
                
                if z < best_z:
                    best_z = z
                    best_sol = sol

            # Parowanie feromonów
            self.pheromones *= (1 - self.evaporation)
            
            # Wzmocnienie
            for sol, z in solutions:
                reward = 1.0 / z  
                for j, k in sol:
                    self.pheromones[j] += reward

            print(f"Iteracja {i+1}: Najlepsze Z = {best_z}")

        return best_sol, best_z