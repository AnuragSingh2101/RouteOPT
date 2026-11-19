"""Local search operators for VRP route improvement."""

from __future__ import annotations
from typing import Optional, Callable
import copy
import numpy as np

from ..data.schema import Instance, Route, Solution
from .nearest_neighbor import nearest_neighbor
from .savings import clarke_wright_savings


def compute_route_distance(route: list[int], distance_matrix: np.ndarray) -> float:
    """Compute total distance of a route (list of customer indices, 0-based)."""
    if not route:
        return 0.0
    dist = distance_matrix[0, route[0] + 1]
    for i in range(1, len(route)):
        dist += distance_matrix[route[i-1] + 1, route[i] + 1]
    dist += distance_matrix[route[-1] + 1, 0]
    return dist


def compute_route_load(route: list[int], instance: Instance) -> float:
    """Compute total demand of a route."""
    return sum(instance.customers[i].demand for i in route)


def check_route_feasible(
    route: list[int],
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: np.ndarray,
    vehicle_capacity: float,
    vehicle_start_time: float = 0,
    vehicle_end_time: float = float('inf'),
    consider_time_windows: bool = False,
) -> tuple[bool, float, list[float], list[float]]:
    """
    Check if a route is feasible.

    Returns:
        (feasible, duration, arrival_times, departure_times)
    """
    if not route:
        return True, 0.0, [], []

    current_time = vehicle_start_time
    prev_node = 0
    arrival_times = []
    departure_times = []
    load = 0.0

    for cust_idx in route:
        customer = instance.customers[cust_idx]
        node_idx = cust_idx + 1

        # Travel
        current_time += time_matrix[prev_node, node_idx]

        # Time window
        if consider_time_windows:
            if customer.earliest_time is not None:
                current_time = max(current_time, customer.earliest_time)
            if customer.latest_time is not None and current_time > customer.latest_time + 1e-9:
                return False, 0.0, [], []

        arrival_times.append(current_time)

        # Service
        current_time += customer.service_time
        departure_times.append(current_time)

        # Load
        load += customer.demand
        if load > vehicle_capacity + 1e-9:
            return False, 0.0, [], []

        prev_node = node_idx

    # Return to depot
    current_time += time_matrix[prev_node, 0]

    if current_time > vehicle_end_time + 1e-9:
        return False, 0.0, [], []

    duration = current_time - vehicle_start_time
    return True, duration, arrival_times, departure_times


def two_opt(route: list[int], distance_matrix: np.ndarray) -> list[tuple[int, int, float]]:
    """
    Generate 2-opt moves for a single route.

    2-opt: Reverse a segment of the route.
    For route [a, b, c, d, e], reversing segment b..d gives [a, d, c, b, e].

    Returns:
        List of (i, j, delta_distance) where reversing segment i..j gives delta
    """
    moves = []
    n = len(route)
    if n < 2:
        return moves

    for i in range(n):
        for j in range(i + 1, n):
            if i == 0 and j == n - 1:
                continue  # Full reversal = same route

            # Current edges: (i-1, i) and (j, j+1)
            # New edges: (i-1, j) and (i, j+1)
            a = route[i-1] if i > 0 else -1  # -1 = depot
            b = route[i]
            c = route[j]
            d = route[j+1] if j+1 < n else -1

            current = 0.0
            new = 0.0

            if a == -1:
                current += distance_matrix[0, b + 1]
                new += distance_matrix[0, c + 1]
            else:
                current += distance_matrix[a + 1, b + 1]
                new += distance_matrix[a + 1, c + 1]

            if d == -1:
                current += distance_matrix[c + 1, 0]
                new += distance_matrix[b + 1, 0]
            else:
                current += distance_matrix[c + 1, d + 1]
                new += distance_matrix[b + 1, d + 1]

            delta = new - current
            if delta < -1e-9:  # Improvement
                moves.append((i, j, delta))

    return moves


def apply_two_opt(route: list[int], i: int, j: int) -> list[int]:
    """Apply 2-opt move by reversing segment i..j."""
    new_route = route[:]
    new_route[i:j+1] = reversed(new_route[i:j+1])
    return new_route


def relocate_moves(
    routes: list[list[int]],
    distance_matrix: np.ndarray,
    instance: Instance,
) -> list[tuple[int, int, int, float]]:
    """
    Generate relocate moves (move customer from one route to another).

    Returns:
        List of (source_route, customer_pos, target_route, insert_pos, delta_distance)
    """
    moves = []

    for src_idx, src_route in enumerate(routes):
        if not src_route:
            continue

        for cust_pos, customer in enumerate(src_route):
            # Try removing from src_route and inserting into each other route
            for tgt_idx, tgt_route in enumerate(routes):
                if src_idx == tgt_idx:
                    continue

                # Try all insertion positions in target route
                for insert_pos in range(len(tgt_route) + 1):
                    # Compute delta distance
                    # Removal from src
                    a = src_route[cust_pos - 1] if cust_pos > 0 else -1
                    b = customer
                    c = src_route[cust_pos + 1] if cust_pos + 1 < len(src_route) else -1

                    remove_current = 0.0
                    remove_new = 0.0
                    if a == -1:
                        remove_current += distance_matrix[0, b + 1]
                        remove_new += distance_matrix[0, c + 1] if c != -1 else 0
                    else:
                        remove_current += distance_matrix[a + 1, b + 1]
                        remove_new += distance_matrix[a + 1, c + 1] if c != -1 else 0

                    if c == -1:
                        remove_current += distance_matrix[b + 1, 0]
                    else:
                        remove_current += distance_matrix[b + 1, c + 1]

                    # Insertion into tgt
                    p = tgt_route[insert_pos - 1] if insert_pos > 0 else -1
                    q = tgt_route[insert_pos] if insert_pos < len(tgt_route) else -1

                    insert_current = 0.0
                    insert_new = 0.0
                    if p == -1 and q == -1:
                        # Empty target route
                        insert_new = distance_matrix[0, b + 1] + distance_matrix[b + 1, 0]
                    elif p == -1:
                        insert_current += distance_matrix[0, q + 1]
                        insert_new += distance_matrix[0, b + 1] + distance_matrix[b + 1, q + 1]
                    elif q == -1:
                        insert_current += distance_matrix[p + 1, 0]
                        insert_new += distance_matrix[p + 1, b + 1] + distance_matrix[b + 1, 0]
                    else:
                        insert_current += distance_matrix[p + 1, q + 1]
                        insert_new += distance_matrix[p + 1, b + 1] + distance_matrix[b + 1, q + 1]

                    delta = (remove_new - remove_current) + (insert_new - insert_current)

                    if delta < -1e-9:
                        moves.append((src_idx, cust_pos, tgt_idx, insert_pos, delta))

    return moves


def apply_relocate(
    routes: list[list[int]],
    src_idx: int,
    cust_pos: int,
    tgt_idx: int,
    insert_pos: int,
) -> list[list[int]]:
    """Apply relocate move."""
    new_routes = [r[:] for r in routes]
    customer = new_routes[src_idx].pop(cust_pos)
    new_routes[tgt_idx].insert(insert_pos, customer)
    return new_routes


def swap_moves(
    routes: list[list[int]],
    distance_matrix: np.ndarray,
) -> list[tuple[int, int, int, int, float]]:
    """
    Generate swap moves (swap two customers between routes or within route).

    Returns:
        List of (route1, pos1, route2, pos2, delta_distance)
    """
    moves = []

    for r1_idx, route1 in enumerate(routes):
        if not route1:
            continue
        for r2_idx, route2 in enumerate(routes):
            if r2_idx < r1_idx:
                continue
            if not route2:
                continue

            for p1, c1 in enumerate(route1):
                for p2, c2 in enumerate(route2):
                    if r1_idx == r2_idx and p2 <= p1:
                        continue

                    # Compute delta
                    # For c1 at p1 in route1
                    a1 = route1[p1 - 1] if p1 > 0 else -1
                    b1 = c1
                    c1_next = route1[p1 + 1] if p1 + 1 < len(route1) else -1

                    # For c2 at p2 in route2
                    a2 = route2[p2 - 1] if p2 > 0 else -1
                    b2 = c2
                    c2_next = route2[p2 + 1] if p2 + 1 < len(route2) else -1

                    current = 0.0
                    new = 0.0

                    # Edges around c1
                    if a1 == -1:
                        current += distance_matrix[0, b1 + 1]
                        new += distance_matrix[0, b2 + 1]
                    else:
                        current += distance_matrix[a1 + 1, b1 + 1]
                        new += distance_matrix[a1 + 1, b2 + 1]

                    if c1_next == -1:
                        current += distance_matrix[b1 + 1, 0]
                        new += distance_matrix[b2 + 1, 0]
                    else:
                        current += distance_matrix[b1 + 1, c1_next + 1]
                        new += distance_matrix[b2 + 1, c1_next + 1]

                    # Edges around c2
                    if a2 == -1:
                        current += distance_matrix[0, b2 + 1]
                        new += distance_matrix[0, b1 + 1]
                    else:
                        current += distance_matrix[a2 + 1, b2 + 1]
                        new += distance_matrix[a2 + 1, b1 + 1]

                    if c2_next == -1:
                        current += distance_matrix[b2 + 1, 0]
                        new += distance_matrix[b1 + 1, 0]
                    else:
                        current += distance_matrix[b2 + 1, c2_next + 1]
                        new += distance_matrix[b1 + 1, c2_next + 1]

                    delta = new - current
                    if delta < -1e-9:
                        moves.append((r1_idx, p1, r2_idx, p2, delta))

    return moves


def apply_swap(
    routes: list[list[int]],
    r1_idx: int, p1: int, r2_idx: int, p2: int,
) -> list[list[int]]:
    """Apply swap move."""
    new_routes = [r[:] for r in routes]
    new_routes[r1_idx][p1], new_routes[r2_idx][p2] = new_routes[r2_idx][p2], new_routes[r1_idx][p1]
    return new_routes


def or_opt_moves(
    routes: list[list[int]],
    distance_matrix: np.ndarray,
    max_segment: int = 3,
) -> list[tuple[int, int, int, int, int, float]]:
    """
    Generate Or-opt moves (relocate a segment of 1-3 consecutive customers).

    Returns:
        List of (src_route, start_pos, end_pos, tgt_route, insert_pos, delta_distance)
    """
    moves = []

    for src_idx, src_route in enumerate(routes):
        if len(src_route) < 2:
            continue

        for seg_len in range(1, min(max_segment + 1, len(src_route))):
            for start_pos in range(len(src_route) - seg_len + 1):
                end_pos = start_pos + seg_len - 1
                segment = src_route[start_pos:end_pos + 1]

                # Try inserting into each other route
                for tgt_idx, tgt_route in enumerate(routes):
                    if src_idx == tgt_idx:
                        continue

                    for insert_pos in range(len(tgt_route) + 1):
                        # Compute delta similar to relocate but for segment
                        # Simplified - just check if it's an improvement
                        # Full implementation would compute exact delta
                        pass  # Placeholder for full implementation

    return moves


def local_search(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    initial_solution: Optional[Solution] = None,
    consider_time_windows: bool = False,
    max_iterations: int = 1000,
    operators: Optional[list[str]] = None,
) -> Solution:
    """
    Local search improvement for VRP solutions.

    Applies 2-opt, relocate, and swap moves iteratively until no improvement.

    Args:
        instance: VRP instance
        distance_matrix: Distance matrix
        time_matrix: Time matrix (optional)
        initial_solution: Starting solution (if None, uses Clarke-Wright)
        consider_time_windows: If True, respect time windows
        max_iterations: Maximum iterations
        operators: List of operators to use ('two_opt', 'relocate', 'swap')

    Returns:
        Improved Solution
    """
    if time_matrix is None:
        time_matrix = distance_matrix

    if operators is None:
        operators = ['two_opt', 'relocate', 'swap']

    # Get initial solution
    if initial_solution is None:
        initial_solution = clarke_wright_savings(
            instance, distance_matrix, time_matrix, consider_time_windows
        )

    # Convert solution to route format (list of customer indices)
    routes = []
    for route in initial_solution.routes:
        cust_indices = []
        for cust_id in route.customer_ids:
            # Find index in instance.customers
            for idx, c in enumerate(instance.customers):
                if c.customer_id == cust_id:
                    cust_indices.append(idx)
                    break
        routes.append(cust_indices)

    # Vehicle assignments
    vehicle_assignments = [r.vehicle_id for r in initial_solution.routes]

    best_routes = [r[:] for r in routes]
    best_distance = initial_solution.total_distance
    improved = True
    iteration = 0

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1

        # Try 2-opt on each route
        if 'two_opt' in operators:
            for r_idx, route in enumerate(best_routes):
                if len(route) < 4:
                    continue

                moves = two_opt(route, distance_matrix)
                if moves:
                    # Take best move
                    moves.sort(key=lambda x: x[2])  # Sort by delta (most negative first)
                    i, j, delta = moves[0]

                    # Check feasibility
                    vehicle = next(v for v in instance.vehicles if v.vehicle_id == vehicle_assignments[r_idx])
                    feasible, duration, arrivals, departures = check_route_feasible(
                        apply_two_opt(route, i, j),
                        instance, distance_matrix, time_matrix,
                        vehicle.capacity, vehicle.start_time, vehicle.end_time,
                        consider_time_windows
                    )

                    if feasible:
                        best_routes[r_idx] = apply_two_opt(route, i, j)
                        improved = True
                        break  # Restart scan

        if improved:
            continue

        # Try relocate
        if 'relocate' in operators:
            moves = relocate_moves(best_routes, distance_matrix, instance)
            if moves:
                moves.sort(key=lambda x: x[4])
                src_idx, cust_pos, tgt_idx, insert_pos, delta = moves[0]

                # Check feasibility for both routes
                new_routes = apply_relocate(best_routes, src_idx, cust_pos, tgt_idx, insert_pos)

                vehicle_src = next(v for v in instance.vehicles if v.vehicle_id == vehicle_assignments[src_idx])
                vehicle_tgt = next(v for v in instance.vehicles if v.vehicle_id == vehicle_assignments[tgt_idx])

                feasible_src, _, _, _ = check_route_feasible(
                    new_routes[src_idx], instance, distance_matrix, time_matrix,
                    vehicle_src.capacity, vehicle_src.start_time, vehicle_src.end_time,
                    consider_time_windows
                )
                feasible_tgt, _, _, _ = check_route_feasible(
                    new_routes[tgt_idx], instance, distance_matrix, time_matrix,
                    vehicle_tgt.capacity, vehicle_tgt.start_time, vehicle_tgt.end_time,
                    consider_time_windows
                )

                if feasible_src and feasible_tgt:
                    best_routes = new_routes
                    improved = True
                    continue

        # Try swap
        if 'swap' in operators:
            moves = swap_moves(best_routes, distance_matrix)
            if moves:
                moves.sort(key=lambda x: x[4])
                r1, p1, r2, p2, delta = moves[0]

                new_routes = apply_swap(best_routes, r1, p1, r2, p2)

                vehicle_r1 = next(v for v in instance.vehicles if v.vehicle_id == vehicle_assignments[r1])
                vehicle_r2 = next(v for v in instance.vehicles if v.vehicle_id == vehicle_assignments[r2])

                feasible_r1, _, _, _ = check_route_feasible(
                    new_routes[r1], instance, distance_matrix, time_matrix,
                    vehicle_r1.capacity, vehicle_r1.start_time, vehicle_r1.end_time,
                    consider_time_windows
                )
                feasible_r2, _, _, _ = check_route_feasible(
                    new_routes[r2], instance, distance_matrix, time_matrix,
                    vehicle_r2.capacity, vehicle_r2.start_time, vehicle_r2.end_time,
                    consider_time_windows
                )

                if feasible_r1 and feasible_r2:
                    best_routes = new_routes
                    improved = True
                    continue

    # Build final solution
    solution_routes = []
    total_distance = 0.0
    total_duration = 0.0

    for r_idx, route in enumerate(best_routes):
        if not route:
            continue

        vehicle = next(v for v in instance.vehicles if v.vehicle_id == vehicle_assignments[r_idx])

        route_distance = compute_route_distance(route, distance_matrix)
        feasible, duration, arrivals, departures = check_route_feasible(
            route, instance, distance_matrix, time_matrix,
            vehicle.capacity, vehicle.start_time, vehicle.end_time,
            consider_time_windows
        )

        route_load = compute_route_load(route, instance)

        solution_routes.append(Route(
            vehicle_id=vehicle.vehicle_id,
            customer_ids=[instance.customers[i].customer_id for i in route],
            distance=route_distance,
            duration=duration,
            load=route_load,
            arrival_times=arrivals,
            departure_times=departures,
        ))

        total_distance += route_distance
        total_duration += duration

    status = "feasible" if len(solution_routes) == len(initial_solution.routes) else "infeasible"

    return Solution(
        instance_name=instance.metadata.name,
        algorithm=f"Local Search ({'+'.join(operators)})",
        routes=solution_routes,
        total_distance=total_distance,
        total_duration=total_duration,
        vehicles_used=len(solution_routes),
        runtime_seconds=0.0,
        status=status,
        objective_value=total_distance,
    )


def solve_with_local_search(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    consider_time_windows: bool = False,
    initial_heuristic: str = "savings",  # "savings" or "nearest_neighbor"
) -> Solution:
    """
    Convenience function: run initial heuristic then local search.

    Args:
        instance: VRP instance
        distance_matrix: Distance matrix
        time_matrix: Time matrix
        consider_time_windows: If True, respect time windows
        initial_heuristic: Starting heuristic

    Returns:
        Solution after local search
    """
    if initial_heuristic == "savings":
        initial = clarke_wright_savings(instance, distance_matrix, time_matrix, consider_time_windows)
    elif initial_heuristic == "nearest_neighbor":
        initial = nearest_neighbor(instance, distance_matrix, time_matrix, consider_time_windows)
    else:
        raise ValueError(f"Unknown initial heuristic: {initial_heuristic}")

    return local_search(
        instance, distance_matrix, time_matrix,
        initial_solution=initial,
        consider_time_windows=consider_time_windows,
        operators=['two_opt', 'relocate', 'swap']
    )