"""Tests for evaluation module."""

import pytest
import numpy as np
from pathlib import Path

from routeopt.data import load_cvrplib_instance
from routeopt.algorithms import nearest_neighbor, clarke_wright_savings
from routeopt.evaluation import (
    compute_metrics,
    validate_solution,
    validate_route,
    compute_optimality_gap,
    compare_solutions_lexicographic,
    BenchmarkResult,
    BenchmarkRunner,
)


class TestMetrics:
    """Test metrics computation."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_compute_metrics_basic(self, cvrp_instance):
        """Test basic metrics computation."""
        dist_matrix = cvrp_instance.distance_matrix
        sol = nearest_neighbor(cvrp_instance, dist_matrix)

        metrics = compute_metrics(sol, cvrp_instance, dist_matrix)

        assert isinstance(metrics.total_distance, float)
        assert metrics.total_distance > 0
        assert metrics.vehicles_used == sol.vehicles_used
        assert 0 <= metrics.capacity_utilization <= 1
        assert metrics.avg_route_distance > 0

    def test_compute_metrics_with_reference(self, cvrp_instance):
        """Test metrics with reference distance."""
        dist_matrix = cvrp_instance.distance_matrix
        sol = nearest_neighbor(cvrp_instance, dist_matrix)

        metrics = compute_metrics(sol, cvrp_instance, dist_matrix, reference_distance=784)

        assert metrics.gap_percent is not None
        assert metrics.reference_distance == 784

    def test_optimality_gap(self):
        """Test optimality gap calculation."""
        gap = compute_optimality_gap(800, 784)
        expected = ((800 - 784) / 784) * 100
        assert abs(gap - expected) < 1e-6

    def test_lexicographic_compare(self):
        """Test lexicographic comparison."""
        from routeopt.data.schema import Solution, Route

        # Create mock solutions
        sol1 = Solution(
            instance_name="test", algorithm="A", routes=[],
            total_distance=100, total_duration=100, vehicles_used=3,
            runtime_seconds=1, status="feasible", objective_value=100
        )
        sol2 = Solution(
            instance_name="test", algorithm="B", routes=[],
            total_distance=90, total_duration=90, vehicles_used=4,
            runtime_seconds=1, status="feasible", objective_value=90
        )

        # sol1 uses fewer vehicles (3 vs 4) -> should be better
        assert compare_solutions_lexicographic(sol1, sol2) == -1
        assert compare_solutions_lexicographic(sol2, sol1) == 1

        # Same vehicles, compare distance
        sol3 = Solution(
            instance_name="test", algorithm="C", routes=[],
            total_distance=80, total_duration=80, vehicles_used=3,
            runtime_seconds=1, status="feasible", objective_value=80
        )
        assert compare_solutions_lexicographic(sol3, sol1) == -1  # sol3 better distance


class TestRouteValidator:
    """Test independent route validation."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_validate_route(self, cvrp_instance):
        """Test single route validation."""
        dist_matrix = cvrp_instance.distance_matrix
        sol = nearest_neighbor(cvrp_instance, dist_matrix)

        if sol.routes:
            route = sol.routes[0]
            result = validate_route(route, cvrp_instance, dist_matrix)

            # numpy bool_ is not isinstance of bool, check value instead
            assert result.feasible in (True, False, np.True_, np.False_)
            assert result.vehicle_id == route.vehicle_id
            assert result.distance >= 0

    def test_validate_solution(self, cvrp_instance):
        """Test full solution validation."""
        dist_matrix = cvrp_instance.distance_matrix
        sol = nearest_neighbor(cvrp_instance, dist_matrix)

        result = validate_solution(sol, cvrp_instance, dist_matrix)

        assert result.overall_feasible in (True, False, np.True_, np.False_)
        assert result.instance_name == sol.instance_name
        assert result.algorithm == sol.algorithm
        assert len(result.route_results) == len(sol.routes)

    def test_validate_solution_catches_duplicates(self, cvrp_instance):
        """Test validator catches duplicate customers."""
        from routeopt.data.schema import Solution, Route

        dist_matrix = cvrp_instance.distance_matrix
        # Use an actual customer ID from the instance
        valid_cust_id = cvrp_instance.customers[0].customer_id

        # Create solution with duplicate
        dup_route = Route(
            vehicle_id="V1",
            customer_ids=[valid_cust_id, valid_cust_id],  # Duplicate
            distance=100, duration=100, load=20,
            arrival_times=[], departure_times=[]
        )
        bad_sol = Solution(
            instance_name="test", algorithm="Test", routes=[dup_route],
            total_distance=100, total_duration=100, vehicles_used=1,
            runtime_seconds=1, status="feasible", objective_value=100
        )

        result = validate_solution(bad_sol, cvrp_instance, dist_matrix)
        assert not result.overall_feasible
        assert valid_cust_id in result.duplicate_customers


class TestBenchmarkRunner:
    """Test benchmark runner."""

    @pytest.fixture
    def cvrp_instance(self):
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_benchmark_result_dataclass(self):
        """Test BenchmarkResult creation."""
        result = BenchmarkResult(
            instance_name="test",
            instance_source="CVRPLIB",
            num_customers=10,
            algorithm="Test",
            total_distance=100.0,
            total_duration=100.0,
            vehicles_used=2,
            capacity_utilization=0.8,
            avg_route_duration=50.0,
            max_route_duration=60.0,
            runtime_seconds=1.0,
            feasible=True,
            status="feasible",
        )
        assert result.instance_name == "test"
        assert result.gap_percent is None

    def test_benchmark_runner_creation(self, tmp_path):
        """Test BenchmarkRunner creation."""
        runner = BenchmarkRunner(output_dir=tmp_path)
        assert runner.output_dir == tmp_path
        assert runner.time_limits == [10, 30, 60]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])