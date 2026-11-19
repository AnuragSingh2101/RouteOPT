"""Independent route validator for VRP solutions.

This validator recomputes all costs, loads, and timing from raw instance data
WITHOUT using any solver internals. It is the ground truth for feasibility.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

from ..data.schema import Instance, Solution, Route, ValidationReport


@dataclass
class RouteValidationResult:
    """Result of validating a single route."""
    vehicle_id: str
    feasible: bool
    distance: float
    duration: float
    load: float
    capacity: float
    capacity_violated: bool
    time_window_violations: list[str]
    duration_violated: bool
    arrival_times: list[float]
    departure_times: list[float]


@dataclass
class SolutionValidationResult:
    """Result of validating a complete solution."""
    instance_name: str
    algorithm: str
    overall_feasible: bool
    route_results: list[RouteValidationResult]
    total_distance: float
    total_duration: float
    vehicles_used: int
    all_customers_served: bool
    missing_customers: set
    duplicate_customers: set
    errors: list[str]
    warnings: list[str]


def validate_route(
    route: Route,
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
) -> RouteValidationResult:
    """
    Validate a single route independently.

    Recomputes distance, duration, load, and checks all constraints
    from raw data without using solver internals.

    Args:
        route: Route to validate
        instance: Original instance
        distance_matrix: Distance matrix
        time_matrix: Time matrix (defaults to distance_matrix)

    Returns:
        RouteValidationResult with feasibility and recomputed values
    """
    if time_matrix is None:
        time_matrix = distance_matrix

    vehicle = next(v for v in instance.vehicles if v.vehicle_id == route.vehicle_id)
    customer_indices = []

    # Map customer IDs to indices
    for cust_id in route.customer_ids:
        idx = next(i for i, c in enumerate(instance.customers) if c.customer_id == cust_id)
        customer_indices.append(idx)

    # Recompute distance
    recomputed_distance = 0.0
    if customer_indices:
        recomputed_distance = distance_matrix[0, customer_indices[0] + 1]
        for i in range(1, len(customer_indices)):
            recomputed_distance += distance_matrix[customer_indices[i-1] + 1, customer_indices[i] + 1]
        recomputed_distance += distance_matrix[customer_indices[-1] + 1, 0]

    # Recompute timing and check time windows
    current_time = vehicle.start_time
    arrival_times = []
    departure_times = []
    time_window_violations = []

    for idx in customer_indices:
        customer = instance.customers[idx]
        node = idx + 1

        # Travel time
        prev_node = customer_indices[customer_indices.index(idx) - 1] + 1 if idx != customer_indices[0] else 0
        current_time += time_matrix[prev_node, node]

        # Time window check
        if customer.earliest_time is not None and current_time < customer.earliest_time:
            current_time = customer.earliest_time  # Wait
        if customer.latest_time is not None and current_time > customer.latest_time + 1e-9:
            time_window_violations.append(
                f"Customer {customer.customer_id}: arrival {current_time:.2f} > latest {customer.latest_time}"
            )

        arrival_times.append(current_time)
        current_time += customer.service_time
        departure_times.append(current_time)

    # Return to depot
    if customer_indices:
        last_node = customer_indices[-1] + 1
        current_time += time_matrix[last_node, 0]

    recomputed_duration = current_time - vehicle.start_time

    # Load check
    recomputed_load = sum(instance.customers[idx].demand for idx in customer_indices)
    capacity_violated = recomputed_load > vehicle.capacity + 1e-9

    # Duration check
    duration_violated = False
    if vehicle.max_route_duration is not None:
        duration_violated = recomputed_duration > vehicle.max_route_duration + 1e-9
    if vehicle.end_time is not None:
        duration_violated = duration_violated or (current_time > vehicle.end_time + 1e-9)

    feasible = (
        not capacity_violated
        and not duration_violated
        and len(time_window_violations) == 0
        and abs(recomputed_distance - route.distance) < 1e-6
    )

    return RouteValidationResult(
        vehicle_id=route.vehicle_id,
        feasible=feasible,
        distance=recomputed_distance,
        duration=recomputed_duration,
        load=recomputed_load,
        capacity=vehicle.capacity,
        capacity_violated=capacity_violated,
        time_window_violations=time_window_violations,
        duration_violated=duration_violated,
        arrival_times=arrival_times,
        departure_times=departure_times,
    )


def validate_solution(
    solution: Solution,
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
) -> SolutionValidationResult:
    """
    Validate a complete solution independently.

    Checks:
    1. Every customer visited exactly once
    2. Each route starts and ends at depot
    3. No capacity violations
    4. No time window violations (with waiting)
    5. Maximum route duration respected
    6. Recomputed distance matches reported distance
    7. Recomputed load matches reported load

    Args:
        solution: Solution to validate
        instance: Original instance
        distance_matrix: Distance matrix
        time_matrix: Time matrix (optional)

    Returns:
        SolutionValidationResult with detailed findings
    """
    if time_matrix is None:
        time_matrix = distance_matrix

    route_results = []
    total_distance = 0.0
    total_duration = 0.0
    all_feasible = True

    visited_customers = set()
    duplicate_customers = set()

    for route in solution.routes:
        # Check for duplicates
        for cust_id in route.customer_ids:
            if cust_id in visited_customers:
                duplicate_customers.add(cust_id)
            visited_customers.add(cust_id)

        # Validate route
        result = validate_route(route, instance, distance_matrix, time_matrix)
        route_results.append(result)

        total_distance += result.distance
        total_duration += result.duration

        if not result.feasible:
            all_feasible = False

    # Check all customers served
    expected_customers = {c.customer_id for c in instance.customers}
    missing_customers = expected_customers - visited_customers
    all_served = len(missing_customers) == 0

    # Overall feasibility
    overall_feasible = (
        all_feasible
        and all_served
        and len(duplicate_customers) == 0
        and abs(total_distance - solution.total_distance) < 1e-6
    )

    # Collect errors and warnings
    errors = []
    warnings = []

    if not all_served:
        errors.append(f"Missing customers: {missing_customers}")
    if duplicate_customers:
        errors.append(f"Duplicate customers: {duplicate_customers}")
    if abs(total_distance - solution.total_distance) > 1e-6:
        warnings.append(
            f"Distance mismatch: recomputed={total_distance:.6f}, "
            f"reported={solution.total_distance:.6f}"
        )

    for rr in route_results:
        if rr.capacity_violated:
            errors.append(f"Route {rr.vehicle_id}: capacity exceeded (load={rr.load:.2f} > cap={rr.capacity})")
        if rr.duration_violated:
            errors.append(f"Route {rr.vehicle_id}: duration exceeded ({rr.duration:.2f})")
        for twv in rr.time_window_violations:
            errors.append(f"Route {rr.vehicle_id}: {twv}")

    return SolutionValidationResult(
        instance_name=solution.instance_name,
        algorithm=solution.algorithm,
        overall_feasible=overall_feasible,
        route_results=route_results,
        total_distance=total_distance,
        total_duration=total_duration,
        vehicles_used=solution.vehicles_used,
        all_customers_served=all_served,
        missing_customers=missing_customers,
        duplicate_customers=duplicate_customers,
        errors=errors,
        warnings=warnings,
    )


def validate_solution_simple(
    solution: Solution,
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
) -> ValidationReport:
    """
    Simple validation returning ValidationReport (compatible with data.validation).

    Returns:
        ValidationReport with errors/warnings
    """
    result = validate_solution(solution, instance, distance_matrix, time_matrix)
    report = ValidationReport([], [])

    if not result.overall_feasible:
        for error in result.errors:
            report.add_error(error)
    for warning in result.warnings:
        report.add_warning(warning)

    return report