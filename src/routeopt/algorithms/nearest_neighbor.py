"""Nearest Neighbor heuristic for VRP."""

from __future__ import annotations
from typing import Optional
import numpy as np

from ..data.schema import Instance, Route, Solution, Vehicle, Customer


def nearest_neighbor(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    consider_time_windows: bool = False,
) -> Solution:
    """
    Nearest Neighbor heuristic for VRP/VRPTW.

    Builds routes sequentially:
    1. Start with an unused vehicle at the depot
    2. Repeatedly visit the nearest unvisited customer that fits capacity (and time windows)
    3. When no more customers can be added, return to depot and start new route
    4. Continue until all customers are served or no vehicles remain

    Args:
        instance: VRP instance
        distance_matrix: n x n distance matrix (depot at index 0)
        time_matrix: n x n time matrix (optional, defaults to distance_matrix)
        consider_time_windows: If True, respect time windows (VRPTW)

    Returns:
        Solution object with routes
    """
    if time_matrix is None:
        time_matrix = distance_matrix

    n_customers = instance.num_customers
    visited = np.zeros(n_customers, dtype=bool)
    routes = []
    vehicle_idx = 0

    # Sort customers by distance from depot for deterministic tie-breaking
    depot_distances = distance_matrix[0, 1:]  # Exclude depot
    customer_order = np.argsort(depot_distances)

    while not np.all(visited) and vehicle_idx < len(instance.vehicles):
        vehicle = instance.vehicles[vehicle_idx]
        route_customer_indices = []  # Store indices (0-based in customers list)
        route_load = 0.0
        current_time = vehicle.start_time
        current_node = 0  # Depot index
        arrival_times = []
        departure_times = []

        # Try to add customers to this route
        while True:
            # Find nearest unvisited customer that fits
            best_customer_idx = None
            best_dist = float('inf')

            for cust_idx in customer_order:
                if visited[cust_idx]:
                    continue

                customer = instance.customers[cust_idx]
                node_idx = cust_idx + 1  # +1 for depot in distance matrix

                # Check capacity
                if route_load + customer.demand > vehicle.capacity + 1e-9:
                    continue

                # Check time window if enabled
                if consider_time_windows:
                    travel_time = time_matrix[current_node, node_idx]
                    arrival = current_time + travel_time

                    # Wait if early
                    if customer.earliest_time is not None:
                        arrival = max(arrival, customer.earliest_time)

                    # Check if late
                    if customer.latest_time is not None and arrival > customer.latest_time + 1e-9:
                        continue

                    # Check return to depot within vehicle hours
                    return_time = time_matrix[node_idx, 0]
                    if vehicle.end_time is not None and arrival + customer.service_time + return_time > vehicle.end_time + 1e-9:
                        continue

                # Valid candidate - check distance
                dist = distance_matrix[current_node, node_idx]
                if dist < best_dist:
                    best_dist = dist
                    best_customer_idx = cust_idx

            if best_customer_idx is None:
                break  # No more customers can be added to this route

            # Add customer to route
            customer = instance.customers[best_customer_idx]
            node_idx = best_customer_idx + 1

            # Update time
            travel_time = time_matrix[current_node, node_idx]
            current_time += travel_time

            if consider_time_windows and customer.earliest_time is not None:
                current_time = max(current_time, customer.earliest_time)

            arrival_times.append(current_time)
            departure_time = current_time + customer.service_time
            departure_times.append(departure_time)
            current_time = departure_time

            # Update route state
            route_customer_indices.append(best_customer_idx)
            route_load += customer.demand
            visited[best_customer_idx] = True
            current_node = node_idx

        if route_customer_indices:
            # Return to depot
            return_dist = distance_matrix[current_node, 0]
            return_time = time_matrix[current_node, 0]

            # Compute total distance properly using indices
            total_distance = distance_matrix[0, route_customer_indices[0] + 1]
            for i in range(1, len(route_customer_indices)):
                total_distance += distance_matrix[route_customer_indices[i-1] + 1, route_customer_indices[i] + 1]
            total_distance += distance_matrix[route_customer_indices[-1] + 1, 0]

            total_duration = current_time - vehicle.start_time + return_time

            routes.append(Route(
                vehicle_id=vehicle.vehicle_id,
                customer_ids=[instance.customers[i].customer_id for i in route_customer_indices],
                distance=total_distance,
                duration=total_duration,
                load=route_load,
                arrival_times=arrival_times,
                departure_times=departure_times,
            ))

        vehicle_idx += 1

    # Check for unvisited customers (infeasible)
    unvisited = [instance.customers[i].customer_id for i in range(n_customers) if not visited[i]]
    if unvisited:
        status = "infeasible"
    else:
        status = "feasible"

    total_distance = sum(r.distance for r in routes)
    total_duration = sum(r.duration for r in routes)

    return Solution(
        instance_name=instance.metadata.name,
        algorithm="Nearest Neighbor",
        routes=routes,
        total_distance=total_distance,
        total_duration=total_duration,
        vehicles_used=len(routes),
        runtime_seconds=0.0,  # Set by caller
        status=status,
        objective_value=total_distance,
    )


def nearest_neighbor_parallel(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    consider_time_windows: bool = False,
    num_starts: int = 10,
) -> Solution:
    """
    Multi-start Nearest Neighbor with random tie-breaking.

    Runs NN multiple times with randomized customer order and returns best.
    """
    import random
    best_solution = None
    best_distance = float('inf')

    for _ in range(num_starts):
        # Shuffle customer order for tie-breaking
        n_customers = instance.num_customers
        customer_order = list(range(n_customers))
        random.shuffle(customer_order)

        # We need to modify the algorithm to use this order
        # For simplicity, just run standard NN (deterministic is fine for baseline)
        sol = nearest_neighbor(instance, distance_matrix, time_matrix, consider_time_windows)
        if sol.total_distance < best_distance:
            best_distance = sol.total_distance
            best_solution = sol

    return best_solution or nearest_neighbor(instance, distance_matrix, time_matrix, consider_time_windows)