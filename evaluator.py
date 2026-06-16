import heapq
from constants import P, K

def assign_demand1(ant_sol, demand_points, dist_matrix):
    
    global K
    capacities = {j: k * K for j, k in ant_sol}  # zalozenie ze mrowki zwracaja liste krotek, do dostosowania pozniej
    remaining_demand = {i: w_i for i, w_i in demand_points.items()}
    
    x = {} 

    possible_pairs=[]
    for i in demand_points.keys():
        for j in capacities.keys():
            possible_pairs.append((i, j))
            
    pairs = sorted(possible_pairs, key=lambda p: dist_matrix[p[0]][p[1]])
    
    for i, j in pairs:
        if remaining_demand[i] > 0 and capacities[j] > 0:
            amount = min(remaining_demand[i], capacities[j])
            x[(i,j)] = amount
            remaining_demand[i] -= amount
            capacities[j] -= amount

            
    return x, remaining_demand


def assign_demand2(ant_sol, demand_points, dist_matrix):
    active_stations = {j for j, k in ant_sol}
    capacities = {j: k * K for j, k in ant_sol}
    remaining_demand = {i: w_i for i, w_i in demand_points.items()}
    x = {}

    def get_regret(i):
        available = [(dist_matrix[i][j], j) for j in active_stations]
        if not available:
            return None
        
        available.sort()
        
        best_dist, best_j = available[0]
        if len(available) > 1:
            regret = available[1][0] - best_dist
        else:
            regret = P - best_dist # do przemyslenia            
        return (-regret, i, best_j, best_dist)
    
    queue = []
    for i in remaining_demand:
        r_data = get_regret(i)
        if r_data:
            heapq.heappush(queue, r_data)
    
    while queue and active_stations:
        neg_regret, i, j, dist = heapq.heappop(queue)
        amount = min(remaining_demand[i], capacities[j])
        x[(i, j)] = amount
        remaining_demand[i] -= amount
        capacities[j] -= amount

        if capacities[j] == 0:  
            # nowa kolejka, strasznie nieoptymalne
            # mozliwe ze zrobienie listy i posortowanie jej wyjdzie lepiej
            active_stations.remove(j)
            queue = []
            for p_id, dem in remaining_demand.items():
                if dem > 0:
                    r_data = get_regret(p_id)
                    if r_data:
                        heapq.heappush(queue, r_data)
        
        # Jeśli capacities[j] > 0, to punkt i jest w pełni obsłużony.
        # Nie robimy nic, pętla bierze kolejny element z istniejącej kolejki.

    return x, remaining_demand
    

def calculate_z(d, ant_sol, demand_points, assign_func):
    z = 0
    x, s = assign_func(ant_sol, demand_points, d)   # to mogą być stałe albo przekazywane jako argumenty
    for val in s.values():
        z += val
    z *= P
    for (i, j), amount in x.items():
        z += d[i][j] * amount        
    return z