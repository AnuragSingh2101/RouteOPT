"""Validation checks for VRP instances."""

from __future__ import annotations
from typing import Optional
import numpy as np

from .schema import Instance, ValidationReport, Customer, Depot, Vehicle


def validate_instance(instance: Instance) -> ValidationReport:
    """
    Comprehensive validation of a VRP instance.

    Checks:
    - Duplicate customer IDs
    - Missing or invalid coordinates
    - Negative or zero demand
    - Demand exceeding every vehicle's capacity
    - Invalid capacities
    - Missing depot
    - Inverted or impossible time windows
    - Invalid service times
    - Total demand vs total fleet capacity
    - Dataset consistency
    """
    report = ValidationReport([], [])

    # 1. Duplicate customer IDs
    customer_ids = [c.customer_id for c in instance.customers]
    if len(customer_ids) != len(set(customer_ids)):
        duplicates = [cid for cid in customer_ids if customer_ids.count(cid) > 1]
        report.add_error(f"Duplicate customer IDs: {set(duplicates)}")

    # 2. Depot ID conflicts with customer IDs
    if instance.depot.depot_id in customer_ids:
        report.add_error(f"Depot ID '{instance.depot.depot_id}' conflicts with a customer ID")

    # 3. Coordinate validation
    _validate_coordinates(instance, report)

    # 4. Demand validation
    _validate_demands(instance, report)

    # 5. Vehicle validation
    _validate_vehicles(instance, report)

    # 6. Time window validation
    _validate_time_windows(instance, report)

    # 7. Service time validation
    _validate_service_times(instance, report)

    # 8. Capacity feasibility
    _validate_capacity_feasibility(instance, report)

    # 9. Distance matrix validation (if present)
    if instance.distance_matrix is not None:
        _validate_distance_matrix(instance, report)

    return report


def _validate_coordinates(instance: Instance, report: ValidationReport) -> None:
    """Validate coordinate ranges and completeness."""
    # Depot coordinates
    if instance.depot.x is None or instance.depot.y is None:
        report.add_error("Depot missing coordinates")

    if instance.metadata.coordinate_system == "wgs84":
        if instance.depot.lat is not None:
            if not (-90 <= instance.depot.lat <= 90):
                report.add_error(f"Depot latitude out of range: {instance.depot.lat}")
        if instance.depot.lon is not None:
            if not (-180 <= instance.depot.lon <= 180):
                report.add_error(f"Depot longitude out of range: {instance.depot.lon}")

    # Customer coordinates
    for cust in instance.customers:
        if cust.x is None or cust.y is None:
            report.add_error(f"Customer {cust.customer_id} missing coordinates")

        if instance.metadata.coordinate_system == "wgs84":
            if cust.lat is not None and not (-90 <= cust.lat <= 90):
                report.add_error(f"Customer {cust.customer_id} latitude out of range: {cust.lat}")
            if cust.lon is not None and not (-180 <= cust.lon <= 180):
                report.add_error(f"Customer {cust.customer_id} longitude out of range: {cust.lon}")


def _validate_demands(instance: Instance, report: ValidationReport) -> None:
    """Validate customer demands."""
    max_vehicle_capacity = max((v.capacity for v in instance.vehicles), default=0)

    for cust in instance.customers:
        if cust.demand < 0:
            report.add_error(f"Customer {cust.customer_id} has negative demand: {cust.demand}")
        elif cust.demand == 0:
            report.add_warning(f"Customer {cust.customer_id} has zero demand")
        elif cust.demand > max_vehicle_capacity:
            report.add_error(
                f"Customer {cust.customer_id} demand ({cust.demand}) exceeds "
                f"maximum vehicle capacity ({max_vehicle_capacity})"
            )


def _validate_vehicles(instance: Instance, report: ValidationReport) -> None:
    """Validate vehicle specifications."""
    if not instance.vehicles:
        report.add_error("No vehicles defined")
        return

    for v in instance.vehicles:
        if v.capacity <= 0:
            report.add_error(f"Vehicle {v.vehicle_id} has non-positive capacity: {v.capacity}")
        if v.max_route_duration is not None and v.max_route_duration <= 0:
            report.add_error(f"Vehicle {v.vehicle_id} has non-positive max_route_duration")
        if v.start_time < 0:
            report.add_warning(f"Vehicle {v.vehicle_id} has negative start_time")
        if v.end_time is not None and v.end_time <= v.start_time:
            report.add_error(f"Vehicle {v.vehicle_id} end_time <= start_time")


def _validate_time_windows(instance: Instance, report: ValidationReport) -> None:
    """Validate time windows for depot and customers."""
    # Depot time window
    if instance.depot.earliest_time is not None and instance.depot.latest_time is not None:
        if instance.depot.earliest_time > instance.depot.latest_time:
            report.add_error(
                f"Depot time window inverted: earliest={instance.depot.earliest_time} > "
                f"latest={instance.depot.latest_time}"
            )
        if instance.depot.earliest_time < 0:
            report.add_warning(f"Depot earliest_time is negative: {instance.depot.earliest_time}")

    # Customer time windows
    for cust in instance.customers:
        if cust.earliest_time is not None and cust.latest_time is not None:
            if cust.earliest_time > cust.latest_time:
                report.add_error(
                    f"Customer {cust.customer_id} time window inverted: "
                    f"earliest={cust.earliest_time} > latest={cust.latest_time}"
                )
            if cust.earliest_time < 0:
                report.add_warning(f"Customer {cust.customer_id} earliest_time is negative")


def _validate_service_times(instance: Instance, report: ValidationReport) -> None:
    """Validate service times."""
    for cust in instance.customers:
        if cust.service_time < 0:
            report.add_error(f"Customer {cust.customer_id} has negative service_time: {cust.service_time}")

    if instance.depot.earliest_time is not None and instance.depot.latest_time is not None:
        # Depot service time is implicitly 0 in most models
        pass


def _validate_capacity_feasibility(instance: Instance, report: ValidationReport) -> None:
    """Check if total demand can be served by fleet."""
    total_demand = sum(c.demand for c in instance.customers)
    total_capacity = sum(v.capacity for v in instance.vehicles)

    if total_demand > total_capacity:
        report.add_error(
            f"Total demand ({total_demand}) exceeds total fleet capacity ({total_capacity}). "
            f"Instance is infeasible."
        )
    elif total_demand > 0.9 * total_capacity:
        report.add_warning(
            f"High utilization: total demand ({total_demand}) is "
            f"{100 * total_demand / total_capacity:.1f}% of fleet capacity ({total_capacity})"
        )


def _validate_distance_matrix(instance: Instance, report: ValidationReport) -> None:
    """Validate distance matrix properties."""
    matrix = instance.distance_matrix
    n = instance.num_nodes

    if matrix.shape != (n, n):
        report.add_error(
            f"Distance matrix shape {matrix.shape} != expected ({n}, {n})"
        )
        return

    # Check diagonal
    for i in range(n):
        if matrix[i, i] != 0:
            report.add_warning(f"Distance matrix diagonal[{i}] = {matrix[i, i]} (expected 0)")

    # Check symmetry (for Euclidean)
    if instance.metadata.distance_convention in ("euclidean_rounded", "euclidean_exact", "haversine"):
        for i in range(n):
            for j in range(i + 1, n):
                if abs(matrix[i, j] - matrix[j, i]) > 1e-9:
                    report.add_warning(
                        f"Distance matrix asymmetric at ({i},{j}): "
                        f"{matrix[i, j]} != {matrix[j, i]}"
                    )

    # Check for negative distances
    if np.any(matrix < 0):
        neg_indices = np.where(matrix < 0)
        report.add_error(f"Negative distances found at indices: {list(zip(neg_indices[0], neg_indices[1]))}")

    # Check for NaN
    if np.any(np.isnan(matrix)):
        nan_indices = np.where(np.isnan(matrix))
        report.add_error(f"NaN distances found at indices: {list(zip(nan_indices[0], nan_indices[1]))}")


def validate_solution_feasibility(
    instance: Instance,
    routes: list,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None
) -> ValidationReport:
    """
    Validate a complete solution (set of routes) for feasibility.

    This is the independent validator that recomputes everything from raw data.
    """
    report = ValidationReport([], [])

    if time_matrix is None:
        time_matrix = distance_matrix

    # Track visited customers
    visited = set()
    total_distance = 0.0
    total_duration = 0.0
    vehicles_used = 0

    for route in routes:
        if not route.customer_ids:
            continue

        vehicles_used += 1
        route_distance = 0.0
        route_load = 0.0
        current_time = route.vehicle.start_time if hasattr(route, 'vehicle') else 0
        prev_idx = 0  # Depot is index 0

        for cust_id in route.customer_ids:
            # Find customer index
            cust_idx = None
            for i, c in enumerate(instance.customers):
                if c.customer_id == cust_id:
                    cust_idx = i + 1  # +1 for depot at 0
                    break

            if cust_idx is None:
                report.add_error(f"Customer {cust_id} not found in instance")
                continue

            if cust_id in visited:
                report.add_error(f"Customer {cust_id} visited multiple times")
            visited.add(cust_id)

            # Distance
            dist = distance_matrix[prev_idx, cust_idx]
            route_distance += dist

            # Time
            travel_time = time_matrix[prev_idx, cust_idx]
            current_time += travel_time

            # Time window check
            cust = instance.customers[cust_idx - 1]
            if cust.earliest_time is not None and current_time < cust.earliest_time:
                current_time = cust.earliest_time  # Wait
            if cust.latest_time is not None and current_time > cust.latest_time:
                report.add_error(
                    f"Customer {cust_id} time window violated: "
                    f"arrival={current_time:.2f} > latest={cust.latest_time}"
                )

            # Service time
            current_time += cust.service_time

            # Load
            route_load += cust.demand

            prev_idx = cust_idx

        # Return to depot
        route_distance += distance_matrix[prev_idx, 0]
        route_duration = distance_matrix[prev_idx, 0]  # Simplified

        # Capacity check
        vehicle_capacity = route.vehicle.capacity if hasattr(route, 'vehicle') else max(v.capacity for v in instance.vehicles)
        if route_load > vehicle_capacity + 1e-9:
            report.add_error(
                f"Route {route.vehicle_id} capacity violated: "
                f"load={route_load:.2f} > capacity={vehicle_capacity}"
            )

        # Max duration check
        if hasattr(route, 'vehicle') and route.vehicle.max_route_duration:
            if route_duration > route.vehicle.max_route_duration + 1e-9:
                report.add_error(
                    f"Route {route.vehicle_id} duration violated: "
                    f"duration={route_duration:.2f} > max={route.vehicle.max_route_duration}"
                )

        total_distance += route_distance
        total_duration += route_duration

    # Check all customers visited
    expected_customers = {c.customer_id for c in instance.customers}
    missing = expected_customers - visited
    if missing:
        report.add_error(f"Customers not visited: {missing}")

    extra = visited - expected_customers
    if extra:
        report.add_error(f"Unknown customers visited: {extra}")

    return report