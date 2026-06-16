import random
import math
from constants import P, K


def generate_test_data(n_demand=300, n_locations=80, area_size=20000,
                        demand_min=10, demand_max=100,
                        cost_f_min=2000, cost_f_max=8000,
                        cost_c_min=300, cost_c_max=900,
                        M=8, budget_factor=0.5, seed=None):
    """
    Generuje DUŻY, syntetyczny zbiór danych testowych dla problemu optymalizacji
    sieci stacji ładowania - tak, by przestrzeń możliwych rozwiązań była zbyt duża,
    żeby ACO mogło ją w pełni przeszukać. Dzięki temu różnice między heurystykami
    i parametrami alpha/beta powinny być widoczne, a algorytm nie będzie zawsze
    trafiał w (prawie) optymalne rozwiązanie.

    WAŻNE - skala: `ACOSolver` ma zahardkodowany próg "pobliskiego popytu"
    `threshold = 1700` (pochodzi z prawdziwych danych Krakowa, gdzie współrzędne
    były w metrach). Dlatego `area_size` MUSI być w tej samej skali (metry),
    rzędu kilkunastu-kilkudziesięciu tysięcy. Jeśli area_size będzie zbyt mały
    (np. 100 jak w oryginalnej wersji), próg 1700 będzie zawsze spełniony i
    heurystyki "demand"/"weighted_demand" staną się praktycznie identyczne
    z "cost". Jeśli area_size będzie absurdalnie duży, będzie odwrotnie -
    nearby_demand zawsze wyjdzie 0.

    Args:
        n_demand: liczba punktów popytu.
        n_locations: liczba potencjalnych lokalizacji stacji.
        area_size: rozmiar obszaru w METRACH (patrz uwaga wyżej).
        demand_min/demand_max: zakres popytu (liczba aut) na punkt popytu.
        cost_f_min/cost_f_max: zakres kosztu stałego otwarcia stacji.
        cost_c_min/cost_c_max: zakres kosztu pojedynczej ładowarki.
        M: maksymalna liczba ładowarek na stację.
        budget_factor: jaką część "kosztu wszystkich stacji przy średnim koszcie"
                       pokrywa budżet. Mniej = trudniejszy, bardziej selektywny
                       problem = większa efektywna przestrzeń kombinacji.
        seed: opcjonalny seed do deterministycznego losowania (powtarzalne testy).
    """
    rng = random.Random(seed)

    # Generowanie współrzędnych punktów popytu (I)
    demand_coords = [(rng.uniform(0, area_size), rng.uniform(0, area_size))
                      for _ in range(n_demand)]

    # Generowanie współrzędnych potencjalnych lokalizacji (J)
    loc_coords = [(rng.uniform(0, area_size), rng.uniform(0, area_size))
                  for _ in range(n_locations)]

    # Tworzenie słownika demand_points {i: w_i}
    demand_points = {i: rng.randint(demand_min, demand_max) for i in range(n_demand)}

    # Tworzenie macierzy odległości dist_matrix[i][j]
    dist_matrix = []
    for i in range(n_demand):
        row = []
        for j in range(n_locations):
            d = math.sqrt((demand_coords[i][0] - loc_coords[j][0]) ** 2 +
                          (demand_coords[i][1] - loc_coords[j][1]) ** 2)
            row.append(round(d, 2))
        dist_matrix.append(row)

    # Koszty i parametry techniczne
    costs_f = [rng.randint(cost_f_min, cost_f_max) for _ in range(n_locations)]
    costs_c = [rng.randint(cost_c_min, cost_c_max) for _ in range(n_locations)]

    # Budżet skalowany tak, by tylko część stacji zmieściła się w nim w pełni
    # wyposażonych - im mniejszy budget_factor, tym mocniej algorytm musi
    # selekcjonować, a kombinatoryka wyboru "które stacje" rośnie.
    avg_station_cost = (sum(costs_f) / n_locations) + (M / 2 * sum(costs_c) / n_locations)
    budget = round(avg_station_cost * (n_locations * budget_factor))

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
    # Test generatora - ustawiamy seed dla powtarzalności
    data = generate_test_data(seed=42)
    print(f"Wygenerowano {len(data['demand_points'])} punktów popytu.")
    print(f"Wygenerowano {len(data['costs_f'])} potencjalnych lokalizacji.")
    print(f"Dostępny budżet: {data['budget']}")
    avg_cost = (sum(data['costs_f']) + data['M'] * sum(data['costs_c'])) / len(data['costs_f'])
    print(f"Średni koszt stacji (przy max ładowarkach): {avg_cost:.2f}")
    print(f"Szacowana liczba stacji do wybrania: ~{data['budget'] / avg_cost:.1f} z {len(data['costs_f'])}")