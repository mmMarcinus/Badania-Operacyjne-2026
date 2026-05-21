import random
import numpy as np
from constants import P, K 
from evaluator import calculate_z, assign_demand1, assign_demand2

class ACOSolver:
    def __init__(self, demand_points, dist_matrix, costs_f, costs_c, budget, M,  heuristic="cost",
                 n_ants=10, n_iterations=50, alpha=1, beta=2, evaporation=0.1):
        self.demand_points = demand_points
        self.dist_matrix = dist_matrix
        self.costs_f = costs_f  # Koszty stałe stacji
        self.costs_c = costs_c  # Koszty ładowarki
        self.budget = budget    # Budżet B
        self.M = M              # Maksymalna liczba ładowarek
        self.heuristic = heuristic
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.alpha = alpha  # Waga feromonu
        self.beta = beta    # Waga heurystyki
        self.evaporation = evaporation
        
        # Inicjalizacja feromonów dla każdej lokalizacji j
        self.num_locations = len(costs_f)
        self.pheromones = np.ones(self.num_locations)

    def _get_heuristic(self, j, threshold=30):
        cost = (self.costs_f[j] + self.costs_c[j])
        cost = max(cost, 1e-6)

        # Heurystyka: preferujemy tańsze lokalizacje
        if self.heuristic == "cost":
            return 1.0 / cost
        
        # oprócz kosztu lokalizacji, bierzemy pod uwagę też zapotrzebowanie w okolicy
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
        return 1.0 / cost

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
            
            total = sum(probs)

            if total == 0:
                probs = np.ones(len(probs)) / len(probs)
            else:
                probs = np.array(probs) / total
            chosen_idx = np.random.choice(available_indices, p=probs)
            
            # Losowanie liczby ładowarek k_j (1 do M)
            # k_j = random.randint(1, self.M)

            # Wyznaczanie liczby ładowarek (k_j) na podstawie popytu
            threshold = 30
            nearby_demand = 0
            for i in self.demand_points:
                if self.dist_matrix[i][chosen_idx] < threshold:
                    nearby_demand += self.demand_points[i]
            
            # Ile ładowarek potrzebujemy, żeby pokryć ten popyt? (Sufit z dzielenia: popyt / wydajność K)
            # Jeśli nearby_demand == 0, stawiamy minimum 1 ładowarkę, skoro już wybraliśmy tę stację
            needed_k = int(np.ceil(nearby_demand / K)) if nearby_demand > 0 else 1
            
            # Ograniczamy liczbę ładowarek do maksymalnej dopuszczalnej wartości M
            k_j = min(needed_k, self.M)

            cost = self.costs_f[chosen_idx] + (k_j * self.costs_c[chosen_idx])


            
            # if cost <= current_budget:
            #     ant_sol.append((chosen_idx, k_j))
            #     current_budget -= cost

            while cost > current_budget and k_j > 0:
                k_j -= 1
                if k_j > 0:
                    cost = self.costs_f[chosen_idx] + (k_j * self.costs_c[chosen_idx])

            if k_j > 0 and cost <= current_budget:
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

            #print(f"Iteracja {i+1}: Najlepsze Z = {best_z}")

        return best_sol, best_z