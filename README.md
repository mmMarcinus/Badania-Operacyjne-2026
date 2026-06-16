# Optymalizacja Sieci Stacji Ładowania Pojazdów Elektrycznych (ACO)

Projekt zrealizowany w ramach przedmiotu Badania Operacyjne. Wykorzystuje Algorytm Mrówkowy (Ant Colony Optimization) do rozwiązania problemu lokalizacji obiektów z ograniczeniami wydajnościowymi (CFLP - Capacitated Facility Location Problem). 

Algorytm operuje na rzeczywistych danych topograficznych i drogowych dla miasta Krakowa, pobieranych za pomocą OpenStreetMap (OSMnx).

## Wymagania wstępne

Projekt używa menedżera pakietów i środowisk wirtualnych `uv`. Upewnij się, że masz zainstalowanego Pythona w wersji 3.10 lub nowszej oraz narzędzie `uv`.

## Instalacja

1. Sklonuj repozytorium lub pobierz pliki projektu.
2. Otwórz terminal w głównym katalogu projektu.
3. Utwórz środowisko wirtualne za pomocą `uv`:
   ```bash
   uv venv
   ```
4. Aktywuj środowisko wirtualne:
   - System Windows (PowerShell):
     ```powershell
     .venv\Scripts\activate
     ```
   - System Linux / macOS:
     ```bash
     source .venv/bin/activate
     ```
5. Zainstaluj wymagane biblioteki za pomocą `uv pip`:
   ```bash
   uv pip install osmnx networkx pandas matplotlib folium numpy
   ```

## Uruchamianie projektu

### Główny algorytm
Aby uruchomić główny program, który pobiera dane, odpala algorytm mrówkowy i generuje mapy interaktywne, wpisz:
```bash
uv run main.py
```
Zostaną wygenerowane dwa pliki HTML: `mapa_krakowa_start.html` oraz `mapa_krakowa_wynik.html`. Przy pierwszym uruchomieniu pobranie grafu drogowego z OSM może zająć kilka minut (wynik zostanie zapisany w pliku cache `krakow_distances.json`).

### Eksperymenty badawcze
W projekcie zawarto również skrypty przeprowadzające zautomatyzowane eksperymenty badawcze. Ich wyniki w postaci plików `.csv` oraz wykresów `.png` zapisywane są w folderze `experiments/results/`.

Aby uruchomić np. badanie wrażliwości na cięcia budżetowe:
```bash
uv run experiments/budget_experiment.py
```

## Struktura plików

* `main.py` - Główny skrypt spinający ekstraktor danych i solver.
* `ACOsolver.py` - Silnik Algorytmu Mrówkowego (ACO).
* `evaluator.py` - Funkcje oceny rozwiązań i przypisywania popytu do stacji.
* `data_extractor.py` - Skrypt odpowiadający za pobieranie, czyszczenie i cache'owanie danych geoinformatycznych z OSM.
* `constants.py` - Definicje stałych ekonomicznych i technicznych (budżet, koszty, wydajność).
* `experiments/` - Folder zawierający skrypty testowe do badań operacyjnych oraz ich wyniki.