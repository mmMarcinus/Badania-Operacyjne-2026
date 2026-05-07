from random_data_loader import generate_test_data
from ACOsolver import ACOSolver

data = generate_test_data(n_demand=30, n_locations=10)

solver = ACOSolver(
    demand_points=data['demand_points'],
    dist_matrix=data['dist_matrix'],
    costs_f=data['costs_f'],
    costs_c=data['costs_c'],
    budget=data['budget'],
    M=data['M']
)

best_sol, best_val = solver.run()

print("\n--- WYNIK KOŃCOWY ---")
print(f"Najlepszy koszt (Z): {best_val}")
print(f"Wybrane stacje (indeks, liczba ładowarek): {best_sol}")