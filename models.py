import pandas as pd
import numpy as np

class DemandPoint:
    def __init__(self, id, lat, lon, weight):
        self.id = id
        self.coords = (lat, lon)
        self.weight = weight

class CandidateLocation:
    def __init__(self, id, lat, lon, fixed_cost, install_cost):
        self.id = id
        self.coords = (lat, lon)
        self.fixed_cost = fixed_cost     
        self.install_cost = install_cost 

class OptimizationModelData:
    def __init__(self, demand_points, candidate_locations):
        self.I = demand_points
        self.J = candidate_locations
        self.dist_matrix = None 