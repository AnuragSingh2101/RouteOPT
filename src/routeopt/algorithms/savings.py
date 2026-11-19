"""Clarke-Wright Savings algorithm for VRP."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

from ..data.schema import Instance, Route, Solution, Vehicle, Customer


@dataclass
class SavingsEntry:
    """Represents a savings opportunity between two routes."""
    i: int          # Customer index (0-based in customers list)
    j: int          # Customer index
    savings: float  # S[i,j] = d(i,0) + d(0,j) - d(i,j)
    i_node: int     # Node index in distance matrix (i+1)
    j_node: int     # Node index in distance matrix (j+1)


def clarke_wright_savings(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    consider_time_windows: bool = False,
    parallel_routes: bool = True,
) -> Solution:
    """
    Clarke-Wright Savings algorithm for VRP.

    Algorithm:
    1. Start with each customer on its own route: 0 -> i -> 0
    2. Compute savings S[i,j] = d(i,0) + d(0,j) - d(i,j) for all pairs
    3. Sort savings in descending order
    4. For each saving (i,j):
       - Find routes containing i (as end) and j (as start)
       - If they're different routes and merge is feasible:
         * Capacity constraint satisfied
         * Route continuity preserved (i at end of route A, j at start of route B)
         * Time windows satisfied (if enabled)
       - Merge routes: routeA + routeB
    5. Continue until no more merges possible

    The savings formula works because:
    - Original cost: d(i,0) + d(0,j) (two separate trips to depot)
    - Merged cost: d(i,j) (direct connection)
    - Savings = original - merged = d(i,0) + d(0,j) - d(i,j)

    Args:
        instance: VRP instance
        distance_matrix: n x n distance matrix (depot at index 0)
        time_matrix: n x n time matrix (optional)
        consider_time_windows: If True, respect time windows
        parallel_routes: If True, only merge end-to-start (parallel routes).
                        If False, also allows sequential merging (more complex).

    Returns:
        Solution object with routes
    """
    if time_matrix is None:
        time_matrix = distance_matrix

    n_customers = instance.num_customers
    if n_customers == 0:
        return Solution(
            instance_name=instance.metadata.name,
            algorithm="Clarke-Wright Savings",
            routes=[],
            total_distance=0.0,
            total_duration=0.0,
            vehicles_used=0,
            runtime_seconds=0.0,
            status="feasible",
            objective_value=0.0,
        )

    # Initialize: each customer on its own route
    routes = []  # List of lists of customer indices (0-based in customers array)
    route_loads = []  # Total demand per route

    for i in range(n_customers):
        customer = instance.customers[i]
        routes.append([i])
        route_loads.append(customer.demand)

    # Compute savings for all pairs
    savings_list = []
    for i in range(n_customers):
        for j in range(i + 1, n_customers):
            i_node = i + 1  # Distance matrix index (depot is 0)
            j_node = j + 1
            s = distance_matrix[i_node, 0] + distance_matrix[0, j_node] - distance_matrix[i_node, j_node]
            if s > 0:  # Only positive savings worth considering
                savings_list.append(SavingsEntry(
                    i=i, j=j, savings=s, i_node=i_node, j_node=j_node
                ))

    # Sort by savings descending
    savings_list.sort(key=lambda x: x.savings, reverse=True)

    # Vehicle capacities
    vehicle_capacities = [v.capacity for v in instance.vehicles]

    # Process savings in order
    for entry in savings_list:
        i, j = entry.i, entry.j

        # Find routes containing i and j
        route_i_idx = None
        route_j_idx = None
        pos_i = None  # 'start' or 'end' position in route
        pos_j = None

        for r_idx, route in enumerate(routes):
            if i in route:
                route_i_idx = r_idx
                if route[0] == i:
                    pos_i = 'start'
                if route[-1] == i:
                    pos_i = 'end' if pos_i is None else 'both'
            if j in route:
                route_j_idx = r_idx
                if route[0] == j:
                    pos_j = 'start'
                if route[-1] == j:
                    pos_j = 'end' if pos_j is None else 'both'

        # Skip if either not found (already merged and internal)
        if route_i_idx is None or route_j_idx is None:
            continue

        # Skip if same route
        if route_i_idx == route_j_idx:
            continue

        # For parallel routes, we need i at end of route_i and j at start of route_j
        # 'both' means single-customer route which can be treated as either
        def is_end(pos):
            return pos == 'end' or pos == 'both'
        def is_start(pos):
            return pos == 'start' or pos == 'both'

        if parallel_routes:
            if not is_end(pos_i) or not is_start(pos_j):
                continue
        else:
            # Sequential routes - more flexible but complex
            if not ((is_end(pos_i) and is_start(pos_j)) or (is_start(pos_i) and is_end(pos_j))):
                continue

        # Check combined capacity
        combined_load = route_loads[route_i_idx] + route_loads[route_j_idx]
        # Find a vehicle that can handle this load
        feasible_vehicle = None
        for v_idx, cap in enumerate(vehicle_capacities):
            if combined_load <= cap + 1e-9:
                feasible_vehicle = v_idx
                break

        if feasible_vehicle is None:
            continue  # No vehicle can handle combined load

        # Check time windows if enabled
        if consider_time_windows:
            # Build merged route and check feasibility
            route_i = routes[route_i_idx]
            route_j = routes[route_j_idx]

            if pos_i == 'end' and pos_j == 'start':
                merged = route_i + route_j
            elif pos_i == 'start' and pos_j == 'end':
                merged = route_j + route_i
            else:
                continue

            if not _check_route_time_feasibility(
                merged, instance, distance_matrix, time_matrix, vehicle_capacities[feasible_vehicle]
            ):
                continue

        # Perform merge
        route_i = routes[route_i_idx]
        route_j = routes[route_j_idx]

        # Determine merge order based on positions
        # For parallel routes: route_i must end with i, route_j must start with j
        # For 'both' (single customer), we can treat as either
        if (is_end(pos_i) and is_start(pos_j)):
            merged_route = route_i + route_j
        elif (is_start(pos_i) and is_end(pos_j)):
            merged_route = route_j + route_i
        else:
            continue

        # Update routes - replace route_i with merged, remove route_j
        routes[route_i_idx] = merged_route
        route_loads[route_i_idx] = combined_load

        # Remove route_j (adjust index if route_j_idx > route_i_idx)
        if route_j_idx > route_i_idx:
            routes.pop(route_j_idx)
            route_loads.pop(route_j_idx)
        else:
            routes.pop(route_j_idx)
            route_loads.pop(route_j_idx)

    # Now assign vehicles to all routes
    # Sort routes by load descending, assign largest vehicles first
    route_order = sorted(range(len(routes)), key=lambda r: route_loads[r], reverse=True)
    vehicle_order = sorted(range(len(vehicle_capacities)), key=lambda v: vehicle_capacities[v], reverse=True)

    assigned_vehicles = [-1] * len(routes)
    vehicle_used = [False] * len(vehicle_capacities)

    for r_idx in route_order:
        for v_idx in vehicle_order:
            if not vehicle_used[v_idx] and route_loads[r_idx] <= vehicle_capacities[v_idx] + 1e-9:
                assigned_vehicles[r_idx] = v_idx
                vehicle_used[v_idx] = True
                break

    # Check for unassigned routes (infeasible)
    unassigned = [r for r, v in enumerate(assigned_vehicles) if v == -1]
    if unassigned:
        status = "infeasible"
    else:
        status = "feasible"

    # Build Solution object - include ALL routes, even unassigned ones
    solution_routes = []
    total_distance = 0.0
    total_duration = 0.0

    for r_idx, route in enumerate(routes):
        if not route:
            continue

        v_idx = assigned_vehicles[r_idx]
        if v_idx == -1:
            # No vehicle available - create a dummy vehicle marker
            # Use first vehicle type for distance calculation
            vehicle = instance.vehicles[0]
            vehicle_id = f"UNUSED_ROUTE_{r_idx}"
        else:
            vehicle = instance.vehicles[v_idx]
            vehicle_id = vehicle.vehicle_id

        # Compute route distance
        route_distance = distance_matrix[0, route[0] + 1]
        for k in range(1, len(route)):
            route_distance += distance_matrix[route[k-1] + 1, route[k] + 1]
        route_distance += distance_matrix[route[-1] + 1, 0]

        # Compute route duration and times
        current_time = vehicle.start_time
        arrival_times = []
        departure_times = []
        route_load = 0.0

        # First customer
        first_cust = instance.customers[route[0]]
        travel_time = time_matrix[0, route[0] + 1]
        current_time += travel_time
        if consider_time_windows and first_cust.earliest_time is not None:
            current_time = max(current_time, first_cust.earliest_time)
        arrival_times.append(current_time)
        departure_time = current_time + first_cust.service_time
        departure_times.append(departure_time)
        current_time = departure_time
        route_load += first_cust.demand

        # Middle customers
        for k in range(1, len(route)):
            cust = instance.customers[route[k]]
            prev_node = route[k-1] + 1
            curr_node = route[k] + 1
            travel_time = time_matrix[prev_node, curr_node]
            current_time += travel_time
            if consider_time_windows and cust.earliest_time is not None:
                current_time = max(current_time, cust.earliest_time)
            arrival_times.append(current_time)
            departure_time = current_time + cust.service_time
            departure_times.append(departure_time)
            current_time = departure_time
            route_load += cust.demand

        # Return to depot
        return_time = time_matrix[route[-1] + 1, 0]
        route_duration = current_time - vehicle.start_time + return_time

        solution_routes.append(Route(
            vehicle_id=vehicle.vehicle_id,
            customer_ids=[instance.customers[i].customer_id for i in route],
            distance=route_distance,
            duration=route_duration,
            load=route_load,
            arrival_times=arrival_times,
            departure_times=departure_times,
        ))

        total_distance += route_distance
        total_duration += route_duration

    return Solution(
        instance_name=instance.metadata.name,
        algorithm="Clarke-Wright Savings",
        routes=solution_routes,
        total_distance=total_distance,
        total_duration=total_duration,
        vehicles_used=len(solution_routes),
        runtime_seconds=0.0,
        status=status,
        objective_value=total_distance,
    )


def _check_route_time_feasibility(
    route: list[int],
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: np.ndarray,
    vehicle_capacity: float,
) -> bool:
    """Check if a route satisfies time windows and capacity."""
    # Check capacity
    total_demand = sum(instance.customers[i].demand for i in route)
    if total_demand > vehicle_capacity + 1e-9:
        return False

    # Check time windows
    current_time = 0  # Start at depot time 0
    prev_node = 0

    for cust_idx in route:
        customer = instance.customers[cust_idx]
        node_idx = cust_idx + 1

        # Travel time
        current_time += time_matrix[prev_node, node_idx]

        # Check time window
        if customer.earliest_time is not None:
            current_time = max(current_time, customer.earliest_time)
        if customer.latest_time is not None:
            if current_time > customer.latest_time + 1e-9:
                return False

        # Service time
        current_time += customer.service_time
        prev_node = node_idx

    # Return to depot
    current_time += time_matrix[prev_node, 0]

    return True


def clarke_wright_savings_time_windows(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
) -> Solution:
    """
    Time-window-aware Clarke-Wright Savings.

    This variant computes savings considering time window feasibility.
    More complex - for now, delegate to main function with flag.
    """
    return clarke_wright_savings(
        instance, distance_matrix, time_matrix,
        consider_time_windows=True, parallel_routes=True
    )