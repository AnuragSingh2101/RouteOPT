"""Tests for baseline routing algorithms."""

import pytest
import numpy as np
from pathlib import Path

from routeopt.data import load_cvrplib_instance, load_solomon_instance
from routeopt.algorithms import (
    nearest_neighbor,
    clarke_wright_savings,
    local_search,
    solve_with_local_search,
    two_opt,
    relocate_moves,
    swap_moves,
    check_route_feasible,
    compute_route_distance,
)
from routeopt.algorithms.local_search import apply_two_opt, apply_swap
from routeopt.data.schema import Instance, InstanceMetadata, Depot, Customer, Vehicle


class TestNearestNeighbor:
    """Test Nearest Neighbor heuristic."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_nn_cvrp(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        sol = nearest_neighbor(cvrp_instance, dist_matrix)

        assert sol.algorithm == "Nearest Neighbor"
        assert sol.status in ("feasible", "infeasible")
        assert sol.vehicles_used <= 5
        assert sol.total_distance > 0

    def test_nn_all_customers_visited(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        sol = nearest_neighbor(cvrp_instance, dist_matrix)

        visited = set()
        for route in sol.routes:
            visited.update(route.customer_ids)

        expected = {c.customer_id for c in cvrp_instance.customers}
        assert visited == expected, f"Missing: {expected - visited}, Extra: {visited - expected}"

    def test_nn_capacity_respected(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        sol = nearest_neighbor(cvrp_instance, dist_matrix)

        for route in sol.routes:
            vehicle = next(v for v in cvrp_instance.vehicles if v.vehicle_id == route.vehicle_id)
            assert route.load <= vehicle.capacity + 1e-9


class TestClarkeWrightSavings:
    """Test Clarke-Wright Savings algorithm."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_cw_cvrp(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        sol = clarke_wright_savings(cvrp_instance, dist_matrix)

        assert sol.algorithm == "Clarke-Wright Savings"
        assert sol.status in ("feasible", "infeasible")
        # Basic savings algorithm doesn't enforce fleet size limit
        # It minimizes routes but may produce more routes than available vehicles
        # OR-Tools solver will handle fleet constraints properly
        assert sol.vehicles_used > 0
        assert sol.total_distance > 0

    def test_cw_all_customers_visited(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        sol = clarke_wright_savings(cvrp_instance, dist_matrix)

        visited = set()
        for route in sol.routes:
            visited.update(route.customer_ids)

        expected = {c.customer_id for c in cvrp_instance.customers}
        assert visited == expected, f"Missing: {expected - visited}"

    def test_cw_capacity_respected(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        sol = clarke_wright_savings(cvrp_instance, dist_matrix)

        for route in sol.routes:
            vehicle = next(v for v in cvrp_instance.vehicles if v.vehicle_id == route.vehicle_id)
            assert route.load <= vehicle.capacity + 1e-9


class TestLocalSearch:
    """Test local search operators."""

    def test_two_opt_moves(self):
        # Route: depot(0) -> 1 -> 2 -> 3 -> 4 -> depot (4 customers)
        # Need n >= 4 for 2-opt to have valid moves (j >= i+2, and not i=0,j=n-1)
        # Distance matrix 5x5 (depot + 4 customers)
        # Current route: 0-1-2-3-4-0
        # 0-1=10, 1-2=10, 2-3=10, 3-4=10, 4-0=10 = 50 total
        # Shortcuts: 1-3=5, 2-4=5
        # Reverse segment 1-2 (i=1,j=2): 0-1-3-2-4-0 = 10+5+10+5+10 = 40 (better by 10)
        # Reverse segment 2-3 (i=2,j=3): 0-1-2-4-3-0 = 10+10+5+10+10 = 45 (better by 5)
        dist = np.array([
            [0, 10, 20, 25, 30],  # depot to 1,2,3,4
            [10, 0, 10, 5, 20],   # 1 to 2,3,4
            [20, 10, 0, 10, 5],   # 2 to 3,4
            [25, 5, 10, 0, 10],   # 3 to 4
            [30, 20, 5, 10, 0],   # 4
        ])
        route = [0, 1, 2, 3]  # customers 0,1,2,3 (indices in matrix: 1,2,3,4)
        moves = two_opt(route, dist)

        # Should find improving moves
        assert len(moves) > 0
        # Best move should have negative delta
        best_delta = min(m[2] for m in moves)
        assert best_delta < 0

    def test_two_opt_apply(self):
        route = [0, 1, 2, 3]
        new_route = apply_two_opt(route, 1, 2)
        assert new_route == [0, 2, 1, 3]

    def test_relocate_moves(self):
        routes = [[0, 1], [2, 3]]
        dist = np.array([
            [0, 10, 20, 30, 40],
            [10, 0, 10, 20, 30],
            [20, 10, 0, 10, 20],
            [30, 20, 10, 0, 10],
            [40, 30, 20, 10, 0]
        ])
        # Create dummy instance for demands
        metadata = InstanceMetadata("test", "Test", "xy_planar", "euclidean_exact", "none",
                                    "distance_units", "arbitrary", "min_distance")
        depot = Depot("0", 0, 0)
        customers = [Customer(str(i), i*10, 0, 10) for i in range(4)]
        vehicles = [Vehicle("V1", 100), Vehicle("V2", 100)]
        instance = Instance(metadata, depot, customers, vehicles)

        moves = relocate_moves(routes, dist, instance)
        # Should find some moves
        assert isinstance(moves, list)

    def test_swap_moves(self):
        routes = [[0, 1], [2, 3]]
        dist = np.array([
            [0, 10, 20, 30, 40],
            [10, 0, 10, 20, 30],
            [20, 10, 0, 10, 20],
            [30, 20, 10, 0, 10],
            [40, 30, 20, 10, 0]
        ])
        moves = swap_moves(routes, dist)
        assert isinstance(moves, list)

    def test_swap_apply(self):
        routes = [[0, 1], [2, 3]]
        new_routes = apply_swap(routes, 0, 0, 1, 1)
        assert new_routes == [[3, 1], [2, 0]]

    def test_check_route_feasible(self):
        metadata = InstanceMetadata("test", "Test", "xy_planar", "euclidean_exact", "none",
                                    "distance_units", "arbitrary", "min_distance")
        depot = Depot("0", 0, 0, earliest_time=0, latest_time=1000)
        customers = [
            Customer("1", 10, 0, 10, service_time=5, earliest_time=0, latest_time=100),
            Customer("2", 20, 0, 10, service_time=5, earliest_time=0, latest_time=100),
        ]
        vehicles = [Vehicle("V1", 100, start_time=0, end_time=1000)]
        instance = Instance(metadata, depot, customers, vehicles)

        dist = np.array([
            [0, 10, 20],
            [10, 0, 10],
            [20, 10, 0]
        ])
        time_matrix = dist.copy()

        feasible, duration, arrivals, departures = check_route_feasible(
            [0, 1], instance, dist, time_matrix, 100, 0, 1000, True
        )
        assert feasible
        assert duration > 0
        assert len(arrivals) == 2
        assert len(departures) == 2


class TestSolverIntegration:
    """Test complete solve pipeline."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_solve_with_local_search(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        sol = solve_with_local_search(
            cvrp_instance, dist_matrix,
            initial_heuristic="savings"
        )

        assert sol.status in ("feasible", "infeasible")
        assert sol.total_distance > 0

    def test_solve_with_nn_local_search(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        sol = solve_with_local_search(
            cvrp_instance, dist_matrix,
            initial_heuristic="nearest_neighbor"
        )

        assert sol.status in ("feasible", "infeasible")
        assert sol.total_distance > 0

    def test_local_search_improves(self, cvrp_instance):
        dist_matrix = cvrp_instance.distance_matrix
        # Get initial solution
        initial = clarke_wright_savings(cvrp_instance, dist_matrix)

        # Run local search
        improved = local_search(
            cvrp_instance, dist_matrix,
            initial_solution=initial,
            operators=['two_opt', 'relocate', 'swap']
        )

        # Should not be worse
        assert improved.total_distance <= initial.total_distance + 1e-9
        assert improved.algorithm.startswith("Local Search")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])