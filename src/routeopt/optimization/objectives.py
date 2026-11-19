"""Objective variants for VRP optimization."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import numpy as np

from ..data.schema import Instance
from .ortools_solver import solve_vrp_with_ortools, ORToolsSolverConfig


class ObjectiveType(Enum):
    """Supported objective types."""
    MIN_DISTANCE = "min_distance"
    MIN_VEHICLES = "min_vehicles"
    MIN_DURATION = "min_duration"
    BALANCE_WORKLOAD = "balance_workload"
    MIN_MAX_DURATION = "min_max_duration"
    WEIGHTED_COMBINATION = "weighted_combination"


@dataclass
class ObjectiveConfig:
    """Configuration for objective variants."""
    objective_type: ObjectiveType = ObjectiveType.MIN_DISTANCE
    
    # For weighted combination
    weight_distance: float = 1.0
    weight_vehicles: float = 0.0
    weight_duration: float = 0.0
    weight_max_duration: float = 0.0
    weight_balance: float = 0.0
    
    # For balance workload
    span_cost_coefficient: float = 100.0  # coefficient for route duration variance
    
    # For min-max duration
    max_duration_weight: float = 1000.0


def solve_with_objective(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    objective_config: Optional[ObjectiveConfig] = None,
    base_config: Optional[ORToolsSolverConfig] = None,
    time_limit_seconds: int = 30,
    scale_factor: int = 1,
) -> tuple:
    """
    Solve VRP with specified objective.

    Args:
        instance: VRP instance
        distance_matrix: Distance matrix
        time_matrix: Time matrix (optional)
        objective_config: Objective configuration
        base_config: Base OR-Tools config
        time_limit_seconds: Solver time limit
        scale_factor: Distance scaling factor

    Returns:
        Tuple of (Solution, objective_value_dict)
    """
    if objective_config is None:
        objective_config = ObjectiveConfig()

    if base_config is None:
        base_config = ORToolsSolverConfig()

    config = ORToolsSolverConfig(
        time_limit_seconds=base_config.time_limit_seconds,
        scale_factor=base_config.scale_factor,
        first_solution_strategy=base_config.first_solution_strategy,
        local_search_metaheuristic=base_config.local_search_metaheuristic,
        log_search=base_config.log_search,
        use_fixed_vehicle_cost=base_config.use_fixed_vehicle_cost,
        fixed_vehicle_cost=base_config.fixed_vehicle_cost,
        consider_time_windows=base_config.consider_time_windows,
        consider_max_duration=base_config.consider_max_duration,
        drop_penalty=base_config.drop_penalty,
    )

    # Apply objective-specific settings
    if objective_config.objective_type == ObjectiveType.MIN_DISTANCE:
        # Default: minimize total distance
        pass

    elif objective_config.objective_type == ObjectiveType.MIN_VEHICLES:
        # Lexicographic: minimize vehicles first, then distance
        config.use_fixed_vehicle_cost = True
        config.fixed_vehicle_cost = int(1e6 * config.scale_factor)

    elif objective_config.objective_type == ObjectiveType.MIN_DURATION:
        # Minimize total travel time
        if time_matrix is not None:
            # Swap distance and time matrices
            pass  # OR-Tools uses arc cost evaluator for objective

    elif objective_config.objective_type == ObjectiveType.BALANCE_WORKLOAD:
        # Add span cost coefficient for workload balancing
        config.consider_max_duration = True
        # Will be applied in add_time_dimension via span cost

    elif objective_config.objective_type == ObjectiveType.MIN_MAX_DURATION:
        # Minimize maximum route duration
        config.consider_max_duration = True

    elif objective_config.objective_type == ObjectiveType.WEIGHTED_COMBINATION:
        # Use weighted combination - need custom arc costs
        # For now, use fixed vehicle cost if weight_vehicles > 0
        if objective_config.weight_vehicles > 0:
            config.use_fixed_vehicle_cost = True
            config.fixed_vehicle_cost = int(objective_config.weight_vehicles * 1e6 * config.scale_factor)

    # Solve
    solution = solve_vrp_with_ortools(instance, distance_matrix, time_matrix, config)

    # Compute objective components
    obj_values = compute_objective_components(solution, instance, distance_matrix, time_matrix, scale_factor)

    return solution, obj_values


def compute_objective_components(
    solution,
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray],
    scale_factor: int,
) -> dict:
    """Compute individual objective components from a solution."""
    total_distance = solution.total_distance
    total_duration = solution.total_duration
    vehicles_used = solution.vehicles_used

    # Max route duration
    max_route_duration = max((r.duration for r in solution.routes), default=0)

    # Workload balance (coefficient of variation of route durations)
    if solution.routes:
        durations = [r.duration for r in solution.routes]
        mean_duration = np.mean(durations)
        std_duration = np.std(durations)
        cv_duration = std_duration / mean_duration if mean_duration > 0 else 0
    else:
        cv_duration = 0

    return {
        "distance": total_distance,
        "duration": total_duration,
        "vehicles": vehicles_used,
        "max_route_duration": max_route_duration,
        "workload_cv": cv_duration,
        "weighted": (
            total_distance +
            1000 * vehicles_used +
            total_duration * 0.1
        ),
    }


def generate_tradeoff_table(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    time_limit_seconds: int = 30,
    scale_factor: int = 1,
) -> list[dict]:
    """
    Generate trade-off table by solving with different objectives.

    Returns:
        List of dicts with objective values for each variant
    """
    objectives = [
        (ObjectiveType.MIN_DISTANCE, "Min Distance"),
        (ObjectiveType.MIN_VEHICLES, "Min Vehicles"),
        (ObjectiveType.MIN_DURATION, "Min Duration"),
        (ObjectiveType.BALANCE_WORKLOAD, "Balance Workload"),
        (ObjectiveType.MIN_MAX_DURATION, "Min Max Duration"),
    ]

    results = []
    for obj_type, label in objectives:
        obj_config = ObjectiveConfig(objective_type=obj_type)
        sol, obj_vals = solve_with_objective(
            instance, distance_matrix, time_matrix,
            objective_config=obj_config,
            time_limit_seconds=time_limit_seconds,
            scale_factor=scale_factor,
        )
        obj_vals["label"] = label
        obj_vals["status"] = sol.status
        obj_vals["runtime"] = sol.runtime_seconds
        results.append(obj_vals)

    return results


def solve_lexicographic(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    primary: ObjectiveType = ObjectiveType.MIN_VEHICLES,
    secondary: ObjectiveType = ObjectiveType.MIN_DISTANCE,
    time_limit_seconds: int = 30,
    scale_factor: int = 1,
) -> tuple:
    """
    Solve with lexicographic objective (two-phase).

    Phase 1: Optimize primary objective
    Phase 2: Fix primary at optimal, optimize secondary

    Returns:
        Tuple of (Solution, primary_value, secondary_value)
    """
    # Phase 1: Primary objective
    obj_config1 = ObjectiveConfig(objective_type=primary)
    sol1, obj1 = solve_with_objective(
        instance, distance_matrix, time_matrix,
        objective_config=obj_config1,
        time_limit_seconds=time_limit_seconds,
        scale_factor=scale_factor,
    )

    primary_value = obj1[primary.value]

    # Phase 2: Add constraint to fix primary, optimize secondary
    # This would require adding constraints to the model
    # For now, use weighted combination with large weight on primary
    obj_config2 = ObjectiveConfig(
        objective_type=ObjectiveType.WEIGHTED_COMBINATION,
        weight_vehicles=1e6 if primary == ObjectiveType.MIN_VEHICLES else 0,
        weight_distance=1e6 if primary == ObjectiveType.MIN_DISTANCE else 0,
        weight_duration=1e6 if primary == ObjectiveType.MIN_DURATION else 0,
    )
    # Add secondary weights
    if secondary == ObjectiveType.MIN_VEHICLES:
        obj_config2.weight_vehicles = 1
    elif secondary == ObjectiveType.MIN_DISTANCE:
        obj_config2.weight_distance = 1
    elif secondary == ObjectiveType.MIN_DURATION:
        obj_config2.weight_duration = 1

    sol2, obj2 = solve_with_objective(
        instance, distance_matrix, time_matrix,
        objective_config=obj_config2,
        time_limit_seconds=time_limit_seconds,
        scale_factor=scale_factor,
    )

    return sol2, obj1, obj2


def add_span_cost_to_time_dimension(
    routing,
    time_dimension,
    coefficient: float,
) -> None:
    """
    Add span cost coefficient to time dimension for workload balancing.

    The span cost penalizes the difference between max and min route duration.
    """
    time_dimension.SetGlobalSpanCostCoefficient(int(coefficient))


def add_vehicle_fixed_cost(
    routing,
    vehicle_costs: list[float],
) -> None:
    """Add fixed cost per vehicle."""
    for v, cost in enumerate(vehicle_costs):
        routing.SetFixedCostOfVehicle(int(cost), v)


def set_arc_cost_for_duration(
    routing,
    time_callback_index: int,
) -> None:
    """Set arc cost evaluator to time (duration) instead of distance."""
    routing.SetArcCostEvaluatorOfAllVehicles(time_callback_index)