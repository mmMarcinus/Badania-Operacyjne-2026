import random
import math
from constants import P, K #


def generate_test_data(n_demand=20, n_locations=10, area_size=100, seed=None):
    """
    Generuje dane testowe dla problemu optymalizacji stacji ładowania.

    Args:
        n_demand: liczba punktów popytu.
        n_locations: liczba potencjalnych lokalizacji stacji.
        area_size: rozmiar obszaru w jednostkach.
        seed: opcjonalny seed do deterministycznego losowania.
    """
    rng = random.Random(seed)
    
    # Generowanie współrzędnych punktów popytu (I)
    demand_coords = [(rng.uniform(0, area_size), rng.uniform(0, area_size)) 
                     for _ in range(n_demand)]
    
    # Generowanie współrzędnych potencjalnych lokalizacji (J)
    loc_coords = [(rng.uniform(0, area_size), rng.uniform(0, area_size)) 
                  for _ in range(n_locations)]
    
    # Tworzenie słownika demand_points {i: w_i}
    # Popyt (liczba aut) od 5 do 30 na punkt
    demand_points = {i: rng.randint(5, 30) for i in range(n_demand)}
    
    # Tworzenie macierzy odległości dist_matrix[i][j]
    dist_matrix = []
    for i in range(n_demand):
        row = []
        for j in range(n_locations):
            d = math.sqrt((demand_coords[i][0] - loc_coords[j][0])**2 + 
                          (demand_coords[i][1] - loc_coords[j][1])**2)
            row.append(round(d, 2))
        dist_matrix.append(row)
        
    # Koszty i parametry techniczne
    costs_f = [rng.randint(500, 1500) for _ in range(n_locations)] # f_j
    costs_c = [rng.randint(100, 300) for _ in range(n_locations)]  # c_j
    
    M = 5  # Maksymalna liczba ładowarek na stację
    
    # Budżet: ustawiony tak, by starczyło na około 40-60% stacji z pełnym wyposażeniem
    avg_station_cost = (sum(costs_f)/n_locations) + (M/2 * sum(costs_c)/n_locations)
    budget = round(avg_station_cost * (n_locations * 0.5)) 
    
    return { 
        "demand_points": demand_points,
        "dist_matrix": dist_matrix,
        "costs_f": costs_f,
        "costs_c": costs_c,
        "budget": budget,
        "M": M,
        "P": P, 
        "K": K 
    }

if __name__ == "__main__":
    # Test generatora
    data = generate_test_data()
    print(f"Wygenerowano {len(data['demand_points'])} punktów popytu.")
    print(f"Wygenerowano {len(data['costs_f'])} potencjalnych lokalizacji.")
    print(f"Dostępny budżet: {data['budget']}")