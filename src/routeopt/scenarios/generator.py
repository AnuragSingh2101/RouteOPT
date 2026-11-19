"""Scenario generation for VRP sensitivity analysis."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Literal
import numpy as np
import pandas as pd
from pathlib import Path

from ..data.schema import (
    Instance, InstanceMetadata, Depot, Customer, Vehicle,
)


class CoordinateDistribution(Enum):
    """Coordinate distribution types for synthetic customers."""
    UNIFORM = "uniform"
    CLUSTERED = "clustered"
    MIXED = "mixed"
    SOLOMON_R = "solomon_r"  # Random
    SOLOMON_C = "solomon_c"  # Clustered
    SOLOMON_RC = "solomon_rc"  # Mixed


@dataclass
class ScenarioConfig:
    """Configuration for scenario generation."""
    # Customer settings
    num_customers: int = 20
    demand_distribution: Literal["uniform", "normal", "bimodal"] = "uniform"
    demand_min: float = 1.0
    demand_max: float = 30.0
    demand_mean: float = 15.0
    demand_std: float = 5.0

    # Depot settings
    depot_x: float = 50.0
    depot_y: float = 50.0
    depot_earliest: float = 0.0
    depot_latest: float = 1000.0

    # Coordinate distribution
    coord_distribution: CoordinateDistribution = CoordinateDistribution.UNIFORM
    coord_bounds: tuple[float, float, float, float] = (0, 100, 0, 100)  # min_x, max_x, min_y, max_y
    num_clusters: int = 3
    cluster_std: float = 10.0

    # Fleet settings
    num_vehicles: int = 5
    vehicle_capacity: float = 100.0
    vehicle_start_time: float = 0.0
    vehicle_end_time: float = 1000.0
    max_route_duration: Optional[float] = None

    # Service time
    service_time_min: float = 0.0
    service_time_max: float = 10.0
    service_time_fixed: Optional[float] = None

    # Time windows
    time_window_width: float = 200.0  # Width of time window
    time_window_density: float = 1.0  # Fraction of customers with time windows
    time_window_start_min: float = 0.0
    time_window_start_max: float = 800.0

    # Random seed
    seed: int = 42

    # Output
    instance_name: str = "scenario"
    instance_source: str = "Scenario"


def generate_coordinates(
    config: ScenarioConfig,
    rng: np.random.Generator,
) -> list[tuple[float, float]]:
    """Generate customer coordinates based on distribution type."""
    coords = []
    min_x, max_x, min_y, max_y = config.coord_bounds

    if config.coord_distribution == CoordinateDistribution.UNIFORM:
        # Uniform random in bounds
        for _ in range(config.num_customers):
            x = rng.uniform(min_x, max_x)
            y = rng.uniform(min_y, max_y)
            coords.append((x, y))

    elif config.coord_distribution == CoordinateDistribution.CLUSTERED:
        # Clustered around random centers
        centers = [
            (rng.uniform(min_x, max_x), rng.uniform(min_y, max_y))
            for _ in range(config.num_clusters)
        ]
        for _ in range(config.num_customers):
            center = rng.choice(centers)
            x = rng.normal(center[0], config.cluster_std)
            y = rng.normal(center[1], config.cluster_std)
            # Clip to bounds
            x = np.clip(x, min_x, max_x)
            y = np.clip(y, min_y, max_y)
            coords.append((x, y))

    elif config.coord_distribution == CoordinateDistribution.MIXED:
        # Mix of uniform and clustered
        n_clustered = config.num_customers // 2
        n_uniform = config.num_customers - n_clustered

        centers = [
            (rng.uniform(min_x, max_x), rng.uniform(min_y, max_y))
            for _ in range(config.num_clusters)
        ]
        for _ in range(n_clustered):
            center = rng.choice(centers)
            x = rng.normal(center[0], config.cluster_std)
            y = rng.normal(center[1], config.cluster_std)
            x = np.clip(x, min_x, max_x)
            y = np.clip(y, min_y, max_y)
            coords.append((x, y))

        for _ in range(n_uniform):
            x = rng.uniform(min_x, max_x)
            y = rng.uniform(min_y, max_y)
            coords.append((x, y))

    elif config.coord_distribution == CoordinateDistribution.SOLOMON_R:
        # Solomon R: uniform random
        for _ in range(config.num_customers):
            x = rng.uniform(min_x, max_x)
            y = rng.uniform(min_y, max_y)
            coords.append((x, y))

    elif config.coord_distribution == CoordinateDistribution.SOLOMON_C:
        # Solomon C: clustered
        centers = [
            (rng.uniform(min_x, max_x), rng.uniform(min_y, max_y))
            for _ in range(config.num_clusters)
        ]
        for _ in range(config.num_customers):
            center = rng.choice(centers)
            x = rng.normal(center[0], config.cluster_std)
            y = rng.normal(center[1], config.cluster_std)
            x = np.clip(x, min_x, max_x)
            y = np.clip(y, min_y, max_y)
            coords.append((x, y))

    elif config.coord_distribution == CoordinateDistribution.SOLOMON_RC:
        # Solomon RC: mixed
        n_clustered = config.num_customers // 2
        n_uniform = config.num_customers - n_clustered

        centers = [
            (rng.uniform(min_x, max_x), rng.uniform(min_y, max_y))
            for _ in range(config.num_clusters)
        ]
        for _ in range(n_clustered):
            center = rng.choice(centers)
            x = rng.normal(center[0], config.cluster_std)
            y = rng.normal(center[1], config.cluster_std)
            x = np.clip(x, min_x, max_x)
            y = np.clip(y, min_y, max_y)
            coords.append((x, y))

        for _ in range(n_uniform):
            x = rng.uniform(min_x, max_x)
            y = rng.uniform(min_y, max_y)
            coords.append((x, y))

    return coords


def generate_demands(
    config: ScenarioConfig,
    rng: np.random.Generator,
) -> list[float]:
    """Generate customer demands based on distribution."""
    demands = []
    for _ in range(config.num_customers):
        if config.demand_distribution == "uniform":
            d = rng.uniform(config.demand_min, config.demand_max)
        elif config.demand_distribution == "normal":
            d = rng.normal(config.demand_mean, config.demand_std)
            d = np.clip(d, config.demand_min, config.demand_max)
        elif config.demand_distribution == "bimodal":
            # Two peaks: small and large demands
            if rng.random() < 0.5:
                d = rng.uniform(config.demand_min, config.demand_mean)
            else:
                d = rng.uniform(config.demand_mean, config.demand_max)
        else:
            d = config.demand_mean
        demands.append(float(d))
    return demands


def generate_service_times(
    config: ScenarioConfig,
    rng: np.random.Generator,
) -> list[float]:
    """Generate service times."""
    if config.service_time_fixed is not None:
        return [config.service_time_fixed] * config.num_customers
    return [float(rng.uniform(config.service_time_min, config.service_time_max))
            for _ in range(config.num_customers)]


def generate_time_windows(
    config: ScenarioConfig,
    coords: list[tuple[float, float]],
    rng: np.random.Generator,
) -> tuple[list[Optional[float]], list[Optional[float]]]:
    """Generate time windows for customers."""
    earliest = []
    latest = []

    for (x, y) in coords:
        if rng.random() < config.time_window_density:
            # Customer has time window
            center = rng.uniform(config.time_window_start_min, config.time_window_start_max)
            half_width = config.time_window_width / 2
            e = max(0, center - half_width)
            l = center + half_width
            earliest.append(e)
            latest.append(l)
        else:
            earliest.append(None)
            latest.append(None)

    return earliest, latest


def create_scenario_instance(config: ScenarioConfig) -> Instance:
    """
    Create a VRP instance from scenario configuration.

    Args:
        config: Scenario configuration

    Returns:
        Instance ready for solving
    """
    rng = np.random.default_rng(config.seed)

    # Generate coordinates
    coords = generate_coordinates(config, rng)

    # Generate demands
    demands = generate_demands(config, rng)

    # Generate service times
    service_times = generate_service_times(config, rng)

    # Generate time windows
    earliest, latest = generate_time_windows(config, coords, rng)

    # Create depot
    depot = Depot(
        depot_id="0",
        x=config.depot_x,
        y=config.depot_y,
        earliest_time=config.depot_earliest,
        latest_time=config.depot_latest,
    )

    # Create customers
    customers = []
    for i in range(config.num_customers):
        customers.append(Customer(
            customer_id=str(i + 1),
            x=coords[i][0],
            y=coords[i][1],
            demand=demands[i],
            service_time=service_times[i],
            earliest_time=earliest[i],
            latest_time=latest[i],
        ))

    # Create vehicles
    vehicles = []
    for i in range(config.num_vehicles):
        vehicles.append(Vehicle(
            vehicle_id=f"V{i+1}",
            capacity=config.vehicle_capacity,
            start_time=config.vehicle_start_time,
            end_time=config.vehicle_end_time,
            max_route_duration=config.max_route_duration,
        ))

    # Create metadata
    metadata = InstanceMetadata(
        name=config.instance_name,
        source=config.instance_source,
        coordinate_system="xy_planar",
        distance_convention="euclidean_exact",
        rounding_rule="none",
        time_unit="distance_units",
        distance_unit="arbitrary",
        objective_definition="min_distance",
    )

    instance = Instance(
        metadata=metadata,
        depot=depot,
        customers=customers,
        vehicles=vehicles,
    )

    # Build distance matrix
    from ..geo import compute_distance_matrix
    all_coords = [(depot.x, depot.y)] + [(c.x, c.y) for c in customers]
    instance.distance_matrix = compute_distance_matrix(
        np.array(all_coords), "euclidean_exact"
    )

    return instance


def create_scenario_config(
    num_customers: int = 20,
    num_vehicles: int = 5,
    vehicle_capacity: float = 100.0,
    demand_distribution: str = "uniform",
    coord_distribution: str = "uniform",
    time_window_density: float = 0.0,
    seed: int = 42,
    **kwargs,
) -> ScenarioConfig:
    """Factory function to create scenario config with common parameters."""
    return ScenarioConfig(
        num_customers=num_customers,
        num_vehicles=num_vehicles,
        vehicle_capacity=vehicle_capacity,
        demand_distribution=demand_distribution,
        coord_distribution=CoordinateDistribution(coord_distribution),
        time_window_density=time_window_density,
        seed=seed,
        instance_name=f"scenario_n{num_customers}_v{num_vehicles}_cap{int(vehicle_capacity)}",
        **kwargs,
    )


def run_sensitivity_analysis(
    base_config: ScenarioConfig,
    param_name: str,
    param_values: list,
    num_seeds: int = 5,
    solver_func=None,
) -> pd.DataFrame:
    """
    Run sensitivity analysis by varying one parameter.

    Args:
        base_config: Base scenario configuration
        param_name: Parameter to vary (e.g., 'num_customers', 'vehicle_capacity')
        param_values: List of values to test
        num_seeds: Number of random seeds per parameter value
        solver_func: Function to solve instance (instance, dist_matrix) -> Solution

    Returns:
        DataFrame with results
    """
    results = []

    for value in param_values:
        for seed_offset in range(num_seeds):
            # Create modified config
            config_dict = base_config.__dict__.copy()
            config_dict[param_name] = value
            config_dict['seed'] = base_config.seed + seed_offset * 1000
            config_dict['instance_name'] = f"{base_config.instance_name}_{param_name}{value}_s{seed_offset}"

            test_config = ScenarioConfig(**config_dict)

            # Create instance
            instance = create_scenario_instance(test_config)

            # Solve if solver provided
            if solver_func is not None:
                try:
                    sol = solver_func(instance, instance.distance_matrix)
                    results.append({
                        'param_name': param_name,
                        'param_value': value,
                        'seed': test_config.seed,
                        'instance_name': test_config.instance_name,
                        'num_customers': test_config.num_customers,
                        'num_vehicles': test_config.num_vehicles,
                        'vehicle_capacity': test_config.vehicle_capacity,
                        'total_distance': sol.total_distance,
                        'total_duration': sol.total_duration,
                        'vehicles_used': sol.vehicles_used,
                        'feasible': sol.status == 'feasible',
                        'status': sol.status,
                        'runtime': sol.runtime_seconds,
                    })
                except Exception as e:
                    results.append({
                        'param_name': param_name,
                        'param_value': value,
                        'seed': test_config.seed,
                        'instance_name': test_config.instance_name,
                        'error': str(e),
                    })
            else:
                results.append({
                    'param_name': param_name,
                    'param_value': value,
                    'seed': test_config.seed,
                    'instance_name': test_config.instance_name,
                    'num_customers': test_config.num_customers,
                    'num_vehicles': test_config.num_vehicles,
                    'vehicle_capacity': test_config.vehicle_capacity,
                })

    return pd.DataFrame(results)


def summarize_sensitivity_results(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize sensitivity analysis results."""
    if df.empty:
        return pd.DataFrame()

    # Group by parameter value
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    summary = df.groupby('param_value')[numeric_cols].agg(['mean', 'std', 'count'])
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    return summary.reset_index()


# Predefined scenario templates
SCENARIO_TEMPLATES = {
    "small_cvrp": ScenarioConfig(
        num_customers=20,
        num_vehicles=5,
        vehicle_capacity=100,
        instance_name="small_cvrp",
    ),
    "medium_cvrp": ScenarioConfig(
        num_customers=50,
        num_vehicles=10,
        vehicle_capacity=150,
        instance_name="medium_cvrp",
    ),
    "large_cvrp": ScenarioConfig(
        num_customers=100,
        num_vehicles=20,
        vehicle_capacity=200,
        instance_name="large_cvrp",
    ),
    "vrptw_medium": ScenarioConfig(
        num_customers=50,
        num_vehicles=15,
        vehicle_capacity=100,
        time_window_density=1.0,
        time_window_width=200,
        time_window_start_min=0,
        time_window_start_max=800,
        instance_name="vrptw_medium",
    ),
    "high_demand": ScenarioConfig(
        num_customers=30,
        num_vehicles=8,
        vehicle_capacity=80,
        demand_distribution="bimodal",
        demand_min=20,
        demand_max=60,
        instance_name="high_demand",
    ),
    "tight_capacity": ScenarioConfig(
        num_customers=25,
        num_vehicles=5,
        vehicle_capacity=60,
        demand_distribution="normal",
        demand_mean=30,
        demand_std=10,
        instance_name="tight_capacity",
    ),
    "clustered_customers": ScenarioConfig(
        num_customers=40,
        num_vehicles=8,
        vehicle_capacity=120,
        coord_distribution=CoordinateDistribution.CLUSTERED,
        num_clusters=4,
        cluster_std=15.0,
        instance_name="clustered_customers",
    ),
}


def get_template(name: str) -> ScenarioConfig:
    """Get a predefined scenario template."""
    if name not in SCENARIO_TEMPLATES:
        raise ValueError(f"Unknown template: {name}. Available: {list(SCENARIO_TEMPLATES.keys())}")
    return SCENARIO_TEMPLATES[name]