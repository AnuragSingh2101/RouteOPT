"""OR-Tools solver wrapper for VRP/VRPTW."""

from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Optional, Literal
import numpy as np

from ..data.schema import Instance, Solution, Route
from .vrp_model import (
    create_routing_model,
    add_capacity_dimension,
    add_time_dimension,
    add_max_route_duration,
    configure_search_parameters,
    solve_with_parameters,
    extract_solution,
    ORToolsModel,
)


@dataclass
class ORToolsSolverConfig:
    """Configuration for OR-Tools solver."""
    time_limit_seconds: int = 30
    scale_factor: int = 1
    first_solution_strategy: str = "PATH_CHEAPEST_ARC"
    local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH"
    log_search: bool = False
    use_fixed_vehicle_cost: bool = False  # For lexicographic vehicle minimization (Solomon)
    fixed_vehicle_cost: int = 1000000
    consider_time_windows: bool = False
    consider_max_duration: bool = True
    drop_penalty: Optional[int] = None  # If set, allow dropping customers with this penalty


def solve_vrp_with_ortools(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    config: Optional[ORToolsSolverConfig] = None,
) -> Solution:
    """
    Solve VRP/VRPTW using OR-Tools.

    Args:
        instance: VRP instance
        distance_matrix: n x n distance matrix (depot at 0)
        time_matrix: n x n time matrix (optional, defaults to distance_matrix)
        config: Solver configuration

    Returns:
        Solution with routes, distances, status
    """
    if config is None:
        config = ORToolsSolverConfig()

    # Adjust config based on instance type
    if instance.metadata.source == "Solomon" and instance.metadata.objective_definition == "lexicographic_vehicles_then_distance":
        config.use_fixed_vehicle_cost = True
        config.fixed_vehicle_cost = 1000000
        config.scale_factor = 100  # Solomon uses exact Euclidean

    start_time = time.time()

    # Determine if we need time dimension
    need_time_dimension = config.consider_time_windows and instance.has_time_windows

    # Create routing model
    model = create_routing_model(
        instance,
        distance_matrix,
        time_matrix,
        scale_factor=config.scale_factor,
        use_fixed_vehicle_cost=config.use_fixed_vehicle_cost,
        fixed_vehicle_cost=config.fixed_vehicle_cost,
        add_time_dimension_flag=need_time_dimension,
    )

    # Add capacity dimension
    add_capacity_dimension(model, instance, distance_matrix, config.scale_factor)

    # Add time dimension if time windows or VRPTW
    if need_time_dimension:
        if time_matrix is None:
            time_matrix = distance_matrix
        add_time_dimension(model, instance, time_matrix, config.scale_factor)

        # Add max route duration if specified
        if config.consider_max_duration:
            add_max_route_duration(model, instance, config.scale_factor)

    # Handle optional customer dropping (disjunctions)
    if config.drop_penalty is not None:
        _add_drop_penalties(model, instance, config.drop_penalty * config.scale_factor)

    # Configure search
    search_params = configure_search_parameters(
        time_limit_seconds=config.time_limit_seconds,
        first_solution_strategy=config.first_solution_strategy,
        local_search_metaheuristic=config.local_search_metaheuristic,
        log_search=config.log_search,
    )

    # Solve
    assignment = solve_with_parameters(model, search_params)

    runtime = time.time() - start_time

    # Extract solution
    result = extract_solution(
        model, instance, distance_matrix, time_matrix,
        assignment, config.scale_factor
    )

    # Determine status
    if assignment is None:
        status = "infeasible"
    else:
        # Check if all customers served
        served = set()
        for route in result["routes"]:
            served.update(route.customer_ids)
        expected = {c.customer_id for c in instance.customers}
        if served == expected:
            status = "feasible"
        elif config.drop_penalty is not None:
            status = "feasible_with_drops"
        else:
            status = "infeasible"

    return Solution(
        instance_name=instance.metadata.name,
        algorithm=f"OR-Tools ({config.first_solution_strategy}+{config.local_search_metaheuristic})",
        routes=result["routes"],
        total_distance=result["total_distance"],
        total_duration=result["total_duration"],
        vehicles_used=result["vehicles_used"],
        runtime_seconds=runtime,
        status=status,
        objective_value=result.get("objective_value", result["total_distance"]),
        metadata={
            "solver": "ortools",
            "config": config.__dict__,
            "objective_value_raw": result.get("objective_value", 0),
        },
    )


def _add_drop_penalties(
    model: ORToolsModel,
    instance: Instance,
    penalty: int,
) -> None:
    """Add disjunctions to allow dropping customers with penalty."""
    for i in range(1, instance.num_nodes):  # Skip depot
        index = model.manager.NodeToIndex(i)
        model.routing.AddDisjunction([index], penalty)


def solve_cvrp_ortools(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_limit_seconds: int = 30,
    scale_factor: int = 1,
    strategy: str = "PATH_CHEAPEST_ARC",
    metaheuristic: str = "GUIDED_LOCAL_SEARCH",
) -> Solution:
    """Convenience function for CVRP with OR-Tools."""
    config = ORToolsSolverConfig(
        time_limit_seconds=time_limit_seconds,
        scale_factor=scale_factor,
        first_solution_strategy=strategy,
        local_search_metaheuristic=metaheuristic,
        consider_time_windows=False,
    )
    return solve_vrp_with_ortools(instance, distance_matrix, None, config)


def solve_vrptw_ortools(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: np.ndarray,
    time_limit_seconds: int = 30,
    scale_factor: int = 100,
    strategy: str = "PATH_CHEAPEST_ARC",
    metaheuristic: str = "GUIDED_LOCAL_SEARCH",
    use_lexicographic: bool = True,
) -> Solution:
    """Convenience function for VRPTW with OR-Tools."""
    config = ORToolsSolverConfig(
        time_limit_seconds=time_limit_seconds,
        scale_factor=scale_factor,
        first_solution_strategy=strategy,
        local_search_metaheuristic=metaheuristic,
        consider_time_windows=True,
        consider_max_duration=True,
        use_fixed_vehicle_cost=use_lexicographic,
        fixed_vehicle_cost=1000000 * scale_factor,
    )
    return solve_vrp_with_ortools(instance, distance_matrix, time_matrix, config)


def run_ortools_benchmark(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    time_limits: list[int] = [10, 30, 60],
    strategies: list[str] = ["PATH_CHEAPEST_ARC", "SAVINGS"],
    metaheuristics: list[str] = ["GUIDED_LOCAL_SEARCH", "TABU_SEARCH"],
    scale_factor: int = 1,
    is_vrptw: bool = False,
) -> list[Solution]:
    """
    Run OR-Tools with multiple configurations for benchmarking.

    Returns:
        List of solutions from different configurations
    """
    solutions = []

    for tl in time_limits:
        for strat in strategies:
            for meta in metaheuristics:
                config = ORToolsSolverConfig(
                    time_limit_seconds=tl,
                    scale_factor=scale_factor,
                    first_solution_strategy=strat,
                    local_search_metaheuristic=meta,
                    consider_time_windows=is_vrptw,
                )
                sol = solve_vrp_with_ortools(instance, distance_matrix, time_matrix, config)
                sol.metadata["time_limit"] = tl
                sol.metadata["strategy"] = strat
                sol.metadata["metaheuristic"] = meta
                solutions.append(sol)

    return solutions