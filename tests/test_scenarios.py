"""Tests for scenario generation."""

import pytest
import numpy as np
import pandas as pd

from routeopt.scenarios import (
    ScenarioConfig,
    CoordinateDistribution,
    create_scenario_instance,
    create_scenario_config,
    get_template,
    run_sensitivity_analysis,
    summarize_sensitivity_results,
    SCENARIO_TEMPLATES,
)
from routeopt.data.schema import Instance


class TestScenarioConfig:
    """Test ScenarioConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = ScenarioConfig()
        assert config.num_customers == 20
        assert config.num_vehicles == 5
        assert config.vehicle_capacity == 100.0
        assert config.seed == 42

    def test_custom_config(self):
        """Test custom configuration."""
        config = ScenarioConfig(
            num_customers=50,
            num_vehicles=10,
            vehicle_capacity=200.0,
            seed=123,
        )
        assert config.num_customers == 50
        assert config.num_vehicles == 10
        assert config.vehicle_capacity == 200.0
        assert config.seed == 123


class TestCoordinateGeneration:
    """Test coordinate generation for different distributions."""

    def test_uniform_coordinates(self):
        """Test uniform coordinate generation."""
        config = ScenarioConfig(
            num_customers=10,
            coord_distribution=CoordinateDistribution.UNIFORM,
            coord_bounds=(0, 100, 0, 100),
            seed=42,
        )
        instance = create_scenario_instance(config)
        assert len(instance.customers) == 10
        for c in instance.customers:
            assert 0 <= c.x <= 100
            assert 0 <= c.y <= 100

    def test_clustered_coordinates(self):
        """Test clustered coordinate generation."""
        config = ScenarioConfig(
            num_customers=20,
            coord_distribution=CoordinateDistribution.CLUSTERED,
            coord_bounds=(0, 100, 0, 100),
            num_clusters=3,
            cluster_std=10.0,
            seed=42,
        )
        instance = create_scenario_instance(config)
        assert len(instance.customers) == 20
        for c in instance.customers:
            assert 0 <= c.x <= 100
            assert 0 <= c.y <= 100

    def test_mixed_coordinates(self):
        """Test mixed coordinate generation."""
        config = ScenarioConfig(
            num_customers=10,
            coord_distribution=CoordinateDistribution.MIXED,
            coord_bounds=(0, 100, 0, 100),
            seed=42,
        )
        instance = create_scenario_instance(config)
        assert len(instance.customers) == 10

    def test_solomon_r_coordinates(self):
        """Test Solomon R coordinate generation."""
        config = ScenarioConfig(
            num_customers=10,
            coord_distribution=CoordinateDistribution.SOLOMON_R,
            coord_bounds=(0, 100, 0, 100),
            seed=42,
        )
        instance = create_scenario_instance(config)
        assert len(instance.customers) == 10

    def test_solomon_c_coordinates(self):
        """Test Solomon C coordinate generation."""
        config = ScenarioConfig(
            num_customers=10,
            coord_distribution=CoordinateDistribution.SOLOMON_C,
            coord_bounds=(0, 100, 0, 100),
            num_clusters=3,
            seed=42,
        )
        instance = create_scenario_instance(config)
        assert len(instance.customers) == 10

    def test_solomon_rc_coordinates(self):
        """Test Solomon RC coordinate generation."""
        config = ScenarioConfig(
            num_customers=10,
            coord_distribution=CoordinateDistribution.SOLOMON_RC,
            coord_bounds=(0, 100, 0, 100),
            num_clusters=3,
            seed=42,
        )
        instance = create_scenario_instance(config)
        assert len(instance.customers) == 10


class TestDemandGeneration:
    """Test demand generation."""

    def test_uniform_demands(self):
        """Test uniform demand generation."""
        config = ScenarioConfig(
            num_customers=10,
            demand_distribution="uniform",
            demand_min=10,
            demand_max=50,
            seed=42,
        )
        instance = create_scenario_instance(config)
        for c in instance.customers:
            assert 10 <= c.demand <= 50

    def test_normal_demands(self):
        """Test normal demand generation."""
        config = ScenarioConfig(
            num_customers=100,
            demand_distribution="normal",
            demand_mean=20,
            demand_std=5,
            demand_min=5,
            demand_max=40,
            seed=42,
        )
        instance = create_scenario_instance(config)
        demands = [c.demand for c in instance.customers]
        assert 5 <= min(demands) <= max(demands) <= 40
        # Check mean is roughly correct
        assert 18 < np.mean(demands) < 22

    def test_bimodal_demands(self):
        """Test bimodal demand generation."""
        config = ScenarioConfig(
            num_customers=100,
            demand_distribution="bimodal",
            demand_min=10,
            demand_max=50,
            demand_mean=30,
            seed=42,
        )
        instance = create_scenario_instance(config)
        demands = [c.demand for c in instance.customers]
        # Should have values in both low and high ranges
        low = [d for d in demands if d < 30]
        high = [d for d in demands if d >= 30]
        assert len(low) > 0
        assert len(high) > 0


class TestServiceTimeGeneration:
    """Test service time generation."""

    def test_fixed_service_time(self):
        """Test fixed service time."""
        config = ScenarioConfig(
            num_customers=10,
            service_time_fixed=5.0,
            seed=42,
        )
        instance = create_scenario_instance(config)
        for c in instance.customers:
            assert c.service_time == 5.0

    def test_variable_service_time(self):
        """Test variable service time."""
        config = ScenarioConfig(
            num_customers=10,
            service_time_min=0,
            service_time_max=10,
            seed=42,
        )
        instance = create_scenario_instance(config)
        for c in instance.customers:
            assert 0 <= c.service_time <= 10


class TestTimeWindowGeneration:
    """Test time window generation."""

    def test_no_time_windows(self):
        """Test no time windows."""
        config = ScenarioConfig(
            num_customers=10,
            time_window_density=0.0,
            seed=42,
        )
        instance = create_scenario_instance(config)
        for c in instance.customers:
            assert c.earliest_time is None
            assert c.latest_time is None

    def test_all_time_windows(self):
        """Test all customers have time windows."""
        config = ScenarioConfig(
            num_customers=10,
            time_window_density=1.0,
            time_window_width=200,
            time_window_start_min=0,
            time_window_start_max=800,
            seed=42,
        )
        instance = create_scenario_instance(config)
        for c in instance.customers:
            assert c.earliest_time is not None
            assert c.latest_time is not None
            assert c.earliest_time >= 0
            assert c.latest_time > c.earliest_time


class TestInstanceCreation:
    """Test complete instance creation."""

    def test_create_instance(self):
        """Test creating a complete instance."""
        config = ScenarioConfig(
            num_customers=20,
            num_vehicles=5,
            vehicle_capacity=100,
            seed=42,
        )
        instance = create_scenario_instance(config)

        assert isinstance(instance, Instance)
        assert instance.num_customers == 20
        assert len(instance.vehicles) == 5
        assert instance.vehicles[0].capacity == 100
        assert instance.distance_matrix is not None
        assert instance.distance_matrix.shape == (21, 21)  # depot + 20 customers

    def test_reproducibility(self):
        """Test that same seed produces same instance."""
        config1 = ScenarioConfig(num_customers=10, seed=42)
        config2 = ScenarioConfig(num_customers=10, seed=42)

        inst1 = create_scenario_instance(config1)
        inst2 = create_scenario_instance(config2)

        assert np.allclose(inst1.distance_matrix, inst2.distance_matrix)
        for c1, c2 in zip(inst1.customers, inst2.customers):
            assert c1.x == c2.x
            assert c1.y == c2.y
            assert c1.demand == c2.demand

    def test_different_seeds_produce_different_instances(self):
        """Test that different seeds produce different instances."""
        config1 = ScenarioConfig(num_customers=10, seed=42)
        config2 = ScenarioConfig(num_customers=10, seed=43)

        inst1 = create_scenario_instance(config1)
        inst2 = create_scenario_instance(config2)

        # Should be different (very high probability)
        assert not np.allclose(inst1.distance_matrix, inst2.distance_matrix)


class TestScenarioConfigFactory:
    """Test factory function."""

    def test_create_scenario_config(self):
        """Test factory function."""
        config = create_scenario_config(
            num_customers=30,
            num_vehicles=8,
            vehicle_capacity=150,
            demand_distribution="normal",
            coord_distribution="clustered",
            time_window_density=0.5,
            seed=999,
        )
        assert config.num_customers == 30
        assert config.num_vehicles == 8
        assert config.vehicle_capacity == 150
        assert config.demand_distribution == "normal"
        assert config.coord_distribution == CoordinateDistribution.CLUSTERED
        assert config.time_window_density == 0.5
        assert config.seed == 999


class TestTemplates:
    """Test predefined templates."""

    def test_get_template(self):
        """Test getting predefined templates."""
        for name in SCENARIO_TEMPLATES:
            template = get_template(name)
            assert isinstance(template, ScenarioConfig)
            assert template.instance_name == name

    def test_unknown_template_raises(self):
        """Test unknown template raises error."""
        with pytest.raises(ValueError):
            get_template("nonexistent")


class TestSensitivityAnalysis:
    """Test sensitivity analysis."""

    def test_run_sensitivity_analysis(self):
        """Test running sensitivity analysis."""
        base_config = ScenarioConfig(
            num_customers=10,
            num_vehicles=3,
            vehicle_capacity=50,
            seed=42,
        )

        # Mock solver that returns dummy solution
        def mock_solver(instance, dist_matrix):
            from routeopt.data.schema import Solution, Route
            return Solution(
                instance_name=instance.metadata.name,
                algorithm="Mock",
                routes=[Route(
                    vehicle_id="V1",
                    customer_ids=[c.customer_id for c in instance.customers[:5]],
                    distance=100, duration=100, load=50,
                    arrival_times=[], departure_times=[]
                )],
                total_distance=100, total_duration=100, vehicles_used=1,
                runtime_seconds=0.1, status="feasible", objective_value=100
            )

        df = run_sensitivity_analysis(
            base_config,
            "num_customers",
            [10, 15, 20],
            num_seeds=2,
            solver_func=mock_solver,
        )

        assert len(df) == 6  # 3 values * 2 seeds
        assert 'param_name' in df.columns
        assert 'param_value' in df.columns
        assert 'total_distance' in df.columns

    def test_summarize_sensitivity_results(self):
        """Test summarizing sensitivity results."""
        df = pd.DataFrame({
            'param_value': [10, 10, 15, 15, 20, 20],
            'total_distance': [100, 105, 150, 155, 200, 210],
            'vehicles_used': [1, 1, 2, 2, 3, 3],
        })

        summary = summarize_sensitivity_results(df)
        assert len(summary) == 3  # 3 unique param_values
        assert 'total_distance_mean' in summary.columns
        assert 'total_distance_std' in summary.columns


class TestSolverIntegration:
    """Test integration with solvers (basic smoke test)."""

    def test_instance_with_solver(self):
        """Test created instance works with OR-Tools."""
        config = ScenarioConfig(
            num_customers=10,
            num_vehicles=3,
            vehicle_capacity=50,
            seed=42,
        )
        instance = create_scenario_instance(config)

        from routeopt.optimization import solve_cvrp_ortools
        sol = solve_cvrp_ortools(instance, instance.distance_matrix, time_limit_seconds=5)

        assert sol.status in ("feasible", "infeasible")
        if sol.status == "feasible":
            assert sol.total_distance > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])