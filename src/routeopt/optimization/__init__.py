"""Mathematical optimization module."""

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

from .ortools_solver import (
    solve_vrp_with_ortools,
    solve_cvrp_ortools,
    solve_vrptw_ortools,
    run_ortools_benchmark,
    ORToolsSolverConfig,
)

from .exact_milp import (
    solve_cvrp_exact_mtz,
    create_tiny_instance_for_testing,
)

from .constraints import (
    add_break_constraints,
    add_vehicle_compatibility,
    add_load_balance_penalty,
    add_route_duration_balance,
    add_precedence_constraints,
    add_pickup_delivery_pairs,
    add_skill_constraints,
    add_zone_restrictions,
    add_consecutive_visit_constraint,
)

from .objectives import (
    solve_with_objective,
    ObjectiveType,
    ObjectiveConfig,
    generate_tradeoff_table,
    solve_lexicographic,
    add_span_cost_to_time_dimension,
    add_vehicle_fixed_cost,
    set_arc_cost_for_duration,
    compute_objective_components,
)

__all__ = [
    # VRP Model
    "create_routing_model",
    "add_capacity_dimension",
    "add_time_dimension",
    "add_max_route_duration",
    "configure_search_parameters",
    "solve_with_parameters",
    "extract_solution",
    "ORToolsModel",
    # OR-Tools Solver
    "solve_vrp_with_ortools",
    "solve_cvrp_ortools",
    "solve_vrptw_ortools",
    "run_ortools_benchmark",
    "ORToolsSolverConfig",
    # Exact MILP
    "solve_cvrp_exact_mtz",
    "create_tiny_instance_for_testing",
    # Constraints
    "add_break_constraints",
    "add_vehicle_compatibility",
    "add_load_balance_penalty",
    "add_route_duration_balance",
    "add_precedence_constraints",
    "add_pickup_delivery_pairs",
    "add_skill_constraints",
    "add_zone_restrictions",
    "add_consecutive_visit_constraint",
    # Objectives
    "solve_with_objective",
    "ObjectiveType",
    "ObjectiveConfig",
    "generate_tradeoff_table",
    "solve_lexicographic",
    "add_span_cost_to_time_dimension",
    "add_vehicle_fixed_cost",
    "set_arc_cost_for_duration",
    "compute_objective_components",
]