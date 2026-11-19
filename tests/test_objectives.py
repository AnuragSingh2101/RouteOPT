"""Tests for objective variants."""

import pytest
import numpy as np
from pathlib import Path

from routeopt.data import load_cvrplib_instance
from routeopt.optimization import (
    solve_with_objective,
    ObjectiveType,
    ObjectiveConfig,
    generate_tradeoff_table,
    compute_objective_components,
)
from routeopt.optimization.ortools_solver import ORToolsSolverConfig


class TestObjectives:
    """Test objective variants."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_min_distance_objective(self, cvrp_instance):
        """Test default min distance objective."""
        dist_matrix = cvrp_instance.distance_matrix
        obj_config = ObjectiveConfig(objective_type=ObjectiveType.MIN_DISTANCE)
        
        sol, obj_vals = solve_with_objective(
            cvrp_instance, dist_matrix,
            objective_config=obj_config,
            time_limit_seconds=10,
            scale_factor=1,
        )
        
        assert sol.status in ("feasible", "infeasible")
        if sol.status == "feasible":
            assert "distance" in obj_vals
            assert "vehicles" in obj_vals
            assert obj_vals["distance"] == sol.total_distance

    def test_min_vehicles_objective(self, cvrp_instance):
        """Test lexicographic min vehicles objective."""
        dist_matrix = cvrp_instance.distance_matrix
        obj_config = ObjectiveConfig(objective_type=ObjectiveType.MIN_VEHICLES)
        
        sol, obj_vals = solve_with_objective(
            cvrp_instance, dist_matrix,
            objective_config=obj_config,
            time_limit_seconds=10,
            scale_factor=1,
        )
        
        assert sol.status in ("feasible", "infeasible")
        if sol.status == "feasible":
            assert obj_vals["vehicles"] == sol.vehicles_used

    def test_compute_objective_components(self, cvrp_instance):
        """Test computing objective components from solution."""
        dist_matrix = cvrp_instance.distance_matrix
        obj_config = ObjectiveConfig(objective_type=ObjectiveType.MIN_DISTANCE)
        
        sol, obj_vals = solve_with_objective(
            cvrp_instance, dist_matrix,
            objective_config=obj_config,
            time_limit_seconds=10,
            scale_factor=1,
        )
        
        if sol.status == "feasible":
            comps = compute_objective_components(sol, cvrp_instance, dist_matrix, None, 1)
            assert "distance" in comps
            assert "duration" in comps
            assert "vehicles" in comps
            assert "max_route_duration" in comps
            assert "workload_cv" in comps

    def test_generate_tradeoff_table(self, cvrp_instance):
        """Test generating trade-off table."""
        dist_matrix = cvrp_instance.distance_matrix
        
        # Run with short time limit for testing
        results = generate_tradeoff_table(
            cvrp_instance, dist_matrix,
            time_limit_seconds=5,
            scale_factor=1,
        )
        
        assert len(results) > 0
        for r in results:
            assert "label" in r
            assert "status" in r
            assert "runtime" in r


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])