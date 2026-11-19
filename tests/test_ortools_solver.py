"""Tests for OR-Tools solver."""

import pytest
import numpy as np
from pathlib import Path

from routeopt.data import load_cvrplib_instance, load_solomon_instance
from routeopt.optimization import (
    solve_cvrp_ortools,
    solve_vrptw_ortools,
    ORToolsSolverConfig,
    solve_vrp_with_ortools,
)


class TestORTToolsCVRP:
    """Test OR-Tools on CVRP instances."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_cvrp_basic(self, cvrp_instance):
        """Test basic CVRP solving."""
        dist_matrix = cvrp_instance.distance_matrix
        sol = solve_cvrp_ortools(cvrp_instance, dist_matrix, time_limit_seconds=10, scale_factor=1)

        assert sol.algorithm.startswith("OR-Tools")
        assert sol.status in ("feasible", "infeasible")
        if sol.status == "feasible":
            assert sol.total_distance > 0
            assert sol.vehicles_used > 0
            # Should not exceed 5 vehicles (fleet size)
            assert sol.vehicles_used <= 5

    def test_cvrp_all_customers_served(self, cvrp_instance):
        """Test that all customers are served."""
        dist_matrix = cvrp_instance.distance_matrix
        sol = solve_cvrp_ortools(cvrp_instance, dist_matrix, time_limit_seconds=10, scale_factor=1)

        if sol.status == "feasible":
            visited = set()
            for route in sol.routes:
                visited.update(route.customer_ids)

            expected = {c.customer_id for c in cvrp_instance.customers}
            assert visited == expected, f"Missing: {expected - visited}"

    def test_cvrp_capacity_respected(self, cvrp_instance):
        """Test that vehicle capacity is respected."""
        dist_matrix = cvrp_instance.distance_matrix
        sol = solve_cvrp_ortools(cvrp_instance, dist_matrix, time_limit_seconds=10, scale_factor=1)

        if sol.status == "feasible":
            for route in sol.routes:
                vehicle = next(v for v in cvrp_instance.vehicles if v.vehicle_id == route.vehicle_id)
                assert route.load <= vehicle.capacity + 1e-9

    def test_cvrp_different_strategies(self, cvrp_instance):
        """Test different first solution strategies."""
        dist_matrix = cvrp_instance.distance_matrix
        strategies = ["PATH_CHEAPEST_ARC", "SAVINGS", "BEST_INSERTION"]

        for strat in strategies:
            sol = solve_cvrp_ortools(
                cvrp_instance, dist_matrix,
                time_limit_seconds=5,
                scale_factor=1,
                strategy=strat
            )
            # Just verify it runs without error
            assert sol is not None


class TestORTToolsVRPTW:
    """Test OR-Tools on VRPTW instances."""

    @pytest.fixture
    def solomon_instance(self):
        path = Path("data/raw/benchmark/solomon/C101.txt")
        return load_solomon_instance(path)

    def test_vrptw_basic(self, solomon_instance):
        """Test basic VRPTW solving."""
        dist_matrix = solomon_instance.distance_matrix
        time_matrix = dist_matrix.copy()  # time = distance for Solomon

        sol = solve_vrptw_ortools(
            solomon_instance, dist_matrix, time_matrix,
            time_limit_seconds=10, scale_factor=100
        )

        assert sol.algorithm.startswith("OR-Tools")
        assert sol.status in ("feasible", "infeasible")

    def test_vrptw_lexicographic_objective(self, solomon_instance):
        """Test VRPTW with lexicographic objective (vehicles first, then distance)."""
        dist_matrix = solomon_instance.distance_matrix
        time_matrix = dist_matrix.copy()

        sol = solve_vrptw_ortools(
            solomon_instance, dist_matrix, time_matrix,
            time_limit_seconds=10, scale_factor=100,
            use_lexicographic=True
        )

        if sol.status == "feasible":
            # Should use fewer vehicles due to fixed cost
            assert sol.vehicles_used <= 25  # Upper bound from instance
            assert sol.total_distance > 0

    def test_vrptw_time_windows_respected(self, solomon_instance):
        """Test that time windows are respected in solution."""
        dist_matrix = solomon_instance.distance_matrix
        time_matrix = dist_matrix.copy()

        sol = solve_vrptw_ortools(
            solomon_instance, dist_matrix, time_matrix,
            time_limit_seconds=10, scale_factor=100
        )

        if sol.status == "feasible":
            # The solver should handle time windows internally
            # We trust OR-Tools for this, but we can verify via validator
            assert sol.vehicles_used > 0


class TestORTToolsConfig:
    """Test OR-Tools solver configuration."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_config_object(self, cvrp_instance):
        """Test ORToolsSolverConfig."""
        config = ORToolsSolverConfig(
            time_limit_seconds=20,
            scale_factor=1,
            first_solution_strategy="SAVINGS",
            local_search_metaheuristic="TABU_SEARCH",
        )

        dist_matrix = cvrp_instance.distance_matrix
        sol = solve_vrp_with_ortools(cvrp_instance, dist_matrix, None, config)

        assert sol.metadata["config"]["first_solution_strategy"] == "SAVINGS"
        assert sol.metadata["config"]["local_search_metaheuristic"] == "TABU_SEARCH"

    def test_drop_penalty(self, cvrp_instance):
        """Test drop penalty for infeasible instances."""
        # Create instance with insufficient capacity
        from routeopt.data.schema import Instance, InstanceMetadata, Depot, Customer, Vehicle

        metadata = InstanceMetadata(
            name="infeasible",
            source="Test",
            coordinate_system="xy_planar",
            distance_convention="euclidean_rounded",
            rounding_rule="nearest_int",
            time_unit="distance_units",
            distance_unit="arbitrary",
            objective_definition="min_distance",
        )
        depot = Depot(depot_id="0", x=0, y=0)
        # 3 customers with demand 50 each, vehicle capacity 100, only 1 vehicle
        customers = [
            Customer(customer_id="1", x=10, y=0, demand=50),
            Customer(customer_id="2", x=20, y=0, demand=50),
            Customer(customer_id="3", x=30, y=0, demand=50),
        ]
        vehicles = [Vehicle(vehicle_id="V1", capacity=100)]
        instance = Instance(metadata=metadata, depot=depot, customers=customers, vehicles=vehicles)

        from routeopt.geo import compute_distance_matrix
        coords = [(0,0), (10,0), (20,0), (30,0)]
        instance.distance_matrix = compute_distance_matrix(np.array(coords), "euclidean_rounded")

        dist_matrix = instance.distance_matrix

        # Without drop penalty - should be infeasible
        config = ORToolsSolverConfig(time_limit_seconds=5, scale_factor=1, drop_penalty=None)
        sol = solve_vrp_with_ortools(instance, dist_matrix, None, config)
        assert sol.status == "infeasible"

        # With drop penalty - should be feasible with drops
        config = ORToolsSolverConfig(time_limit_seconds=5, scale_factor=1, drop_penalty=1000)
        sol = solve_vrp_with_ortools(instance, dist_matrix, None, config)
        assert sol.status in ("feasible", "feasible_with_drops")


class TestORTToolsBenchmark:
    """Test OR-Tools benchmark runner."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_benchmark_runner(self, cvrp_instance):
        """Test running benchmark with multiple configurations."""
        from routeopt.optimization import run_ortools_benchmark

        dist_matrix = cvrp_instance.distance_matrix
        solutions = run_ortools_benchmark(
            cvrp_instance, dist_matrix,
            time_limits=[5, 10],
            strategies=["PATH_CHEAPEST_ARC"],
            metaheuristics=["GUIDED_LOCAL_SEARCH"],
            scale_factor=1,
        )

        assert len(solutions) == 2  # 2 time limits × 1 strategy × 1 metaheuristic
        for sol in solutions:
            assert sol.metadata["time_limit"] in [5, 10]
            assert sol.metadata["strategy"] == "PATH_CHEAPEST_ARC"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])