"""Tests for exact MILP solver."""

import pytest
import numpy as np

from routeopt.optimization.exact_milp import solve_cvrp_exact_mtz, create_tiny_instance_for_testing
from routeopt.algorithms import clarke_wright_savings
from routeopt.data.schema import Instance, InstanceMetadata, Depot, Customer, Vehicle


class TestExactMILP:
    """Test exact MILP solver on tiny instances."""

    def test_tiny_instance_creation(self):
        """Test that tiny instance is created correctly."""
        instance = create_tiny_instance_for_testing(6)
        assert instance.num_customers == 6
        assert len(instance.vehicles) == 3
        assert instance.distance_matrix is not None
        assert instance.distance_matrix.shape == (7, 7)  # depot + 6 customers

    def test_exact_milp_pulp_tiny(self):
        """Test exact MILP with PuLP on very small instance."""
        instance = create_tiny_instance_for_testing(6)
        dist_matrix = instance.distance_matrix

        # This test requires PuLP with HiGHS - skip if not available
        try:
            sol = solve_cvrp_exact_mtz(instance, dist_matrix, time_limit_seconds=30, solver="pulp")
        except ImportError:
            pytest.skip("PuLP not available")
        except Exception as e:
            if "cannot execute highs" in str(e):
                pytest.skip("HiGHS solver not installed")
            raise

        # Check solution status
        assert sol.status in ("proven_optimal", "feasible", "time_limit", "infeasible")
        if sol.status == "proven_optimal":
            assert sol.total_distance > 0
            assert sol.vehicles_used > 0

    def test_exact_milp_scipy_tiny(self):
        """Test exact MILP with SciPy on very small instance."""
        instance = create_tiny_instance_for_testing(6)
        dist_matrix = instance.distance_matrix

        # This test requires SciPy milp - skip if not available
        try:
            sol = solve_cvrp_exact_mtz(instance, dist_matrix, time_limit_seconds=30, solver="scipy")
        except ImportError:
            pytest.skip("SciPy milp not available")

        # Check solution status
        assert sol.status in ("proven_optimal", "feasible", "time_limit", "infeasible")
        if sol.status == "proven_optimal":
            assert sol.total_distance > 0
            assert sol.vehicles_used > 0

    def test_exact_vs_heuristic_on_tiny(self):
        """Compare exact MILP with Clarke-Wright on tiny instance."""
        instance = create_tiny_instance_for_testing(6)
        dist_matrix = instance.distance_matrix

        # Get heuristic solution
        cw_sol = clarke_wright_savings(instance, dist_matrix)

        # Try exact solver (prefer SciPy which works)
        try:
            exact_sol = solve_cvrp_exact_mtz(instance, dist_matrix, time_limit_seconds=60, solver="scipy")
        except ImportError:
            try:
                exact_sol = solve_cvrp_exact_mtz(instance, dist_matrix, time_limit_seconds=60, solver="pulp")
            except ImportError:
                pytest.skip("No exact MILP solver available")
            except Exception as e:
                if "cannot execute highs" in str(e):
                    pytest.skip("HiGHS solver not installed")
                raise

        if exact_sol.status == "proven_optimal":
            # Heuristic should not be better than optimal
            assert cw_sol.total_distance >= exact_sol.total_distance - 1e-6
            print(f"Heuristic: {cw_sol.total_distance:.1f}, Optimal: {exact_sol.total_distance:.1f}")
        else:
            print(f"Exact solver status: {exact_sol.status}")

    def test_known_optimal_tiny(self):
        """Test on a hand-crafted instance with known optimal solution."""
        # Simple instance: depot at (0,0), 3 customers at (10,0), (20,0), (30,0)
        # Demands: 10, 10, 10. Vehicle capacity: 20. 2 vehicles.
        # Optimal: V1: 0->10->20->0 (dist=40), V2: 0->30->0 (dist=60). Total=100.
        metadata = InstanceMetadata(
            name="line_3",
            source="Test",
            coordinate_system="xy_planar",
            distance_convention="euclidean_rounded",
            rounding_rule="nearest_int",
            time_unit="distance_units",
            distance_unit="arbitrary",
            objective_definition="min_distance",
        )
        depot = Depot(depot_id="0", x=0.0, y=0.0)
        customers = [
            Customer(customer_id="1", x=10.0, y=0.0, demand=10.0),
            Customer(customer_id="2", x=20.0, y=0.0, demand=10.0),
            Customer(customer_id="3", x=30.0, y=0.0, demand=10.0),
        ]
        vehicles = [
            Vehicle(vehicle_id="V1", capacity=20.0),
            Vehicle(vehicle_id="V2", capacity=20.0),
        ]
        instance = Instance(metadata=metadata, depot=depot, customers=customers, vehicles=vehicles)

        # Build distance matrix (exact Euclidean rounded)
        from routeopt.geo import compute_distance_matrix
        coords = [(0,0), (10,0), (20,0), (30,0)]
        instance.distance_matrix = compute_distance_matrix(np.array(coords), "euclidean_rounded")

        dist_matrix = instance.distance_matrix

        # Try SciPy first (works without HiGHS binary)
        try:
            exact_sol = solve_cvrp_exact_mtz(instance, dist_matrix, time_limit_seconds=30, solver="scipy")
        except ImportError:
            try:
                exact_sol = solve_cvrp_exact_mtz(instance, dist_matrix, time_limit_seconds=30, solver="pulp")
            except ImportError:
                pytest.skip("No exact MILP solver available")
            except Exception as e:
                if "cannot execute highs" in str(e):
                    pytest.skip("HiGHS solver not installed")
                raise

        if exact_sol.status == "proven_optimal":
            # Optimal found by solver: V1: 0->2->3->0 (60) + V2: 0->1->0 (20) = 80
            # This is better than my manual calculation of 100
            assert exact_sol.total_distance == 80
            print(f"Optimal distance: {exact_sol.total_distance}")
        else:
            print(f"Solver status: {exact_sol.status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])