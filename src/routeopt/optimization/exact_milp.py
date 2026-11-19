"""Exact MILP solver for VRP using MTZ formulation with PuLP/HiGHS."""

from __future__ import annotations
import time
from typing import Optional, Literal
import numpy as np

from ..data.schema import Instance, Solution, Route, ValidationReport


def solve_cvrp_exact_mtz(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_limit_seconds: int = 60,
    solver: Literal["pulp", "scipy"] = "pulp",
    verbose: bool = False,
) -> Solution:
    """
    Solve CVRP exactly using MTZ formulation with PuLP (HiGHS) or SciPy.

    MTZ Formulation:
    - Variables: x[i,j,k] ∈ {0,1} = vehicle k travels i→j
                 u[i] ≥ 0 = MTZ subtour elimination vars
    - Objective: minimize sum of c[i,j] * x[i,j,k]
    - Constraints: customer visit, flow conservation, capacity, MTZ

    Only works for small instances (n ≤ ~12) due to O(n²K) variables.

    Args:
        instance: VRP instance (CVRP only, no time windows)
        distance_matrix: n×n matrix with depot at index 0
        time_limit_seconds: Solver time limit
        solver: "pulp" (uses HiGHS) or "scipy" (uses HiGHS via SciPy)
        verbose: Print solver output

    Returns:
        Solution with status "proven_optimal", "feasible", "time_limit", or "infeasible"
    """
    n_customers = instance.num_customers
    n_nodes = n_customers + 1  # +1 for depot
    num_vehicles = len(instance.vehicles)

    if n_customers > 12:
        raise ValueError(f"Exact MILP only for tiny instances (n≤12), got n={n_customers}")

    if instance.metadata.distance_convention != "euclidean_rounded":
        # Only CVRPLIB instances have proven optimal references
        pass

    # Scale distances to integers for MILP
    scale = 1
    dist_int = np.round(distance_matrix * scale).astype(int)

    start_time = time.time()

    if solver == "pulp":
        return _solve_with_pulp(instance, dist_int, n_nodes, num_vehicles, time_limit_seconds, verbose, start_time)
    else:
        return _solve_with_scipy(instance, dist_int, n_nodes, num_vehicles, time_limit_seconds, verbose, start_time)


def _solve_with_pulp(
    instance: Instance,
    dist: np.ndarray,
    n_nodes: int,
    num_vehicles: int,
    time_limit: int,
    verbose: bool,
    start_time: float,
) -> Solution:
    """Solve using PuLP with HiGHS (PuLP 4.x API)."""
    try:
        import pulp
    except ImportError:
        raise ImportError("PuLP not installed. Install with: pip install pulp")

    # Create problem
    prob = pulp.LpProblem("CVRP_MTZ", pulp.LpMinimize)

    # Variables - use prob.add_variable() for PuLP 4.x
    # x[i,j,k] for i,j in nodes, k in vehicles
    x = {}
    for k in range(num_vehicles):
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j:
                    x[(i, j, k)] = prob.add_variable(f"x_{i}_{j}_{k}", lowBound=0, upBound=1, cat="Binary")

    # MTZ variables u[i] for customers only (1..n)
    u = {}
    for i in range(1, n_nodes):
        u[i] = prob.add_variable(f"u_{i}", lowBound=0, upBound=instance.vehicles[0].capacity, cat="Continuous")

    # Objective
    prob.setObjective(pulp.lpSum(dist[i, j] * x[(i, j, k)] for (i, j, k) in x))

    # 1. Each customer visited exactly once
    for i in range(1, n_nodes):
        prob.addConstraint(
            pulp.lpSum(x[(i, j, k)] for j in range(n_nodes) if j != i
                       for k in range(num_vehicles)) == 1,
            name=f"visit_once_{i}"
        )

    # 2. Flow conservation at each node for each vehicle
    for k in range(num_vehicles):
        for i in range(n_nodes):
            prob.addConstraint(
                (pulp.lpSum(x[(i, j, k)] for j in range(n_nodes) if j != i)
                 - pulp.lpSum(x[(j, i, k)] for j in range(n_nodes) if j != i)) == 0,
                name=f"flow_cons_{k}_{i}"
            )

    # 3. Vehicle capacity
    for k in range(num_vehicles):
        prob.addConstraint(
            pulp.lpSum(instance.customers[i-1].demand * x[(i, j, k)]
                       for i in range(1, n_nodes)
                       for j in range(n_nodes) if j != i) <= instance.vehicles[k].capacity,
            name=f"capacity_{k}"
        )

    # 4. Depot: each vehicle leaves depot at most once, returns at most once
    for k in range(num_vehicles):
        prob.addConstraint(
            pulp.lpSum(x[(0, j, k)] for j in range(1, n_nodes)) <= 1,
            name=f"depot_leave_{k}"
        )
        prob.addConstraint(
            pulp.lpSum(x[(i, 0, k)] for i in range(1, n_nodes)) <= 1,
            name=f"depot_return_{k}"
        )

    # 5. MTZ subtour elimination
    Q = instance.vehicles[0].capacity
    for k in range(num_vehicles):
        for i in range(1, n_nodes):
            for j in range(1, n_nodes):
                if i != j:
                    prob.addConstraint(
                        u[i] - u[j] + Q * x[(i, j, k)] <= Q - instance.customers[j-1].demand,
                        name=f"mtz_{k}_{i}_{j}"
                    )

    # 6. MTZ bounds (already set in variable definition)

    # Solve
    solver = pulp.HiGHS_CMD(msg=verbose, timeLimit=time_limit)
    prob.solve(solver)

    runtime = time.time() - start_time
    status = pulp.LpStatus[prob.status]

    return _extract_solution_pulp(prob, instance, dist, x, n_nodes, num_vehicles, runtime, status)


def _solve_with_scipy(
    instance: Instance,
    dist: np.ndarray,
    n_nodes: int,
    num_vehicles: int,
    time_limit: int,
    verbose: bool,
    start_time: float,
) -> Solution:
    """Solve using SciPy's milp (HiGHS)."""
    try:
        from scipy.optimize import milp, LinearConstraint, Bounds
        import scipy.sparse as sp
    except ImportError:
        raise ImportError("SciPy with milp not available (need SciPy ≥1.11)")

    # Build variable indices
    # x variables first, then u variables
    # x[i,j,k] for i!=j, k in vehicles
    x_vars = []
    x_indices = {}  # (i,j,k) -> var_idx
    idx = 0
    for k in range(num_vehicles):
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j:
                    x_indices[(i, j, k)] = idx
                    x_vars.append((i, j, k))
                    idx += 1

    # u variables for customers 1..n
    u_vars = []
    u_indices = {}  # i -> var_idx
    for i in range(1, n_nodes):
        u_indices[i] = idx
        u_vars.append(i)
        idx += 1

    n_vars = idx

    # Objective
    c = np.zeros(n_vars)
    for (i, j, k), var_idx in x_indices.items():
        c[var_idx] = dist[i, j]

    # Bounds
    lb = np.zeros(n_vars)
    ub = np.ones(n_vars)
    # u variables have bounds [0, Q]
    for i in range(1, n_nodes):
        ub[u_indices[i]] = instance.vehicles[0].capacity
    bounds = Bounds(lb, ub)

    # Constraints - using sparse matrices
    # We'll build them incrementally
    A_rows = []
    b_lower = []
    b_upper = []

    # 1. Each customer visited exactly once: sum_{j,k} x[i,j,k] = 1
    for i in range(1, n_nodes):
        row = np.zeros(n_vars)
        for j in range(n_nodes):
            if j != i:
                for k in range(num_vehicles):
                    row[x_indices[(i, j, k)]] = 1
        A_rows.append(row)
        b_lower.append(1)
        b_upper.append(1)

    # 2. Flow conservation: sum_j x[i,j,k] - sum_j x[j,i,k] = 0
    for k in range(num_vehicles):
        for i in range(n_nodes):
            row = np.zeros(n_vars)
            for j in range(n_nodes):
                if j != i:
                    row[x_indices[(i, j, k)]] = 1
                    row[x_indices[(j, i, k)]] = -1
            A_rows.append(row)
            b_lower.append(0)
            b_upper.append(0)

    # 3. Vehicle capacity
    for k in range(num_vehicles):
        row = np.zeros(n_vars)
        for i in range(1, n_nodes):
            for j in range(n_nodes):
                if j != i:
                    row[x_indices[(i, j, k)]] = instance.customers[i-1].demand
        A_rows.append(row)
        b_lower.append(0)
        b_upper.append(instance.vehicles[k].capacity)

    # 4. Depot constraints
    for k in range(num_vehicles):
        # Leave depot at most once
        row = np.zeros(n_vars)
        for j in range(1, n_nodes):
            row[x_indices[(0, j, k)]] = 1
        A_rows.append(row)
        b_lower.append(0)
        b_upper.append(1)

        # Return to depot at most once
        row = np.zeros(n_vars)
        for i in range(1, n_nodes):
            row[x_indices[(i, 0, k)]] = 1
        A_rows.append(row)
        b_lower.append(0)
        b_upper.append(1)

    # 5. MTZ constraints: u_i - u_j + Q*x[i,j,k] ≤ Q - q_j
    Q = instance.vehicles[0].capacity
    for k in range(num_vehicles):
        for i in range(1, n_nodes):
            for j in range(1, n_nodes):
                if i != j:
                    row = np.zeros(n_vars)
                    row[u_indices[i]] = 1
                    row[u_indices[j]] = -1
                    row[x_indices[(i, j, k)]] = Q
                    A_rows.append(row)
                    b_lower.append(-np.inf)
                    b_upper.append(Q - instance.customers[j-1].demand)

    # Convert to sparse
    A = sp.csr_matrix(np.array(A_rows))
    constraints = LinearConstraint(A, np.array(b_lower), np.array(b_upper))

    # Integrality: x are binary, u are continuous
    integrality = np.zeros(n_vars, dtype=int)
    for var_idx in x_indices.values():
        integrality[var_idx] = 1  # binary

    # Solve
    result = milp(
        c=c,
        constraints=constraints,
        bounds=bounds,
        integrality=integrality,
        options={"time_limit": time_limit, "disp": verbose}
    )

    runtime = time.time() - start_time
    status = result.status  # 0=optimal, 1=infeasible, 2=unbounded, 3=time_limit, etc.

    return _extract_solution_scipy(result, instance, dist, x_indices, u_indices, n_nodes, num_vehicles, runtime, status)


def _extract_solution_pulp(
    prob, instance: Instance, dist: np.ndarray, x: dict, n_nodes: int, num_vehicles: int, runtime: float, status: str
) -> Solution:
    """Extract solution from PuLP problem."""
    routes = []
    total_distance = 0.0

    if status == "Optimal":
        sol_status = "proven_optimal"
    elif status == "Infeasible":
        sol_status = "infeasible"
        return Solution(
            instance_name=instance.metadata.name,
            algorithm="Exact MILP (MTZ)",
            routes=[],
            total_distance=0.0,
            total_duration=0.0,
            vehicles_used=0,
            runtime_seconds=runtime,
            status=sol_status,
            objective_value=float('inf'),
        )
    else:
        sol_status = "time_limit" if status == "Not Solved" else "feasible"

    # Extract routes for each vehicle
    for k in range(num_vehicles):
        # Find arcs used by this vehicle
        arcs = []
        for (i, j, vk), var in x.items():
            if vk == k and var.value() > 0.5:
                arcs.append((i, j))

        if not arcs:
            continue

        # Reconstruct route - track node indices (0-based in customers array)
        route_node_indices = []  # 0-based customer indices
        current = 0
        while True:
            next_arc = next((a for a in arcs if a[0] == current), None)
            if next_arc is None:
                break
            next_node = next_arc[1]
            if next_node == 0:
                break
            route_node_indices.append(next_node - 1)  # Convert to 0-based customer index
            current = next_node

        if route_node_indices:
            # Compute distance using node indices
            route_dist = dist[0, route_node_indices[0] + 1]
            for i in range(1, len(route_node_indices)):
                route_dist += dist[route_node_indices[i-1] + 1, route_node_indices[i] + 1]
            route_dist += dist[route_node_indices[-1] + 1, 0]

            total_distance += route_dist

            route_customer_ids = [instance.customers[idx].customer_id for idx in route_node_indices]

            routes.append(Route(
                vehicle_id=instance.vehicles[k].vehicle_id,
                customer_ids=route_customer_ids,
                distance=route_dist,
                duration=route_dist,  # time = distance for CVRP
                load=sum(instance.customers[idx].demand for idx in route_node_indices),
                arrival_times=[],
                departure_times=[],
            ))

    return Solution(
        instance_name=instance.metadata.name,
        algorithm="Exact MILP (MTZ)",
        routes=routes,
        total_distance=total_distance,
        total_duration=total_distance,
        vehicles_used=len(routes),
        runtime_seconds=runtime,
        status=sol_status,
        objective_value=total_distance,
        metadata={"solver_status": status, "solver": "pulp_highs"},
    )


def _extract_solution_scipy(
    result, instance: Instance, dist: np.ndarray, x_indices: dict, u_indices: dict,
    n_nodes: int, num_vehicles: int, runtime: float, status: int
) -> Solution:
    """Extract solution from SciPy milp result."""
    routes = []
    total_distance = 0.0

    # SciPy status codes: 0=optimal, 1=infeasible, 2=unbounded, 3=time_limit, 4=iteration_limit
    if status == 0:
        sol_status = "proven_optimal"
    elif status == 1:
        sol_status = "infeasible"
        return Solution(
            instance_name=instance.metadata.name,
            algorithm="Exact MILP (MTZ)",
            routes=[],
            total_distance=0.0,
            total_duration=0.0,
            vehicles_used=0,
            runtime_seconds=runtime,
            status=sol_status,
            objective_value=float('inf'),
        )
    elif status == 3:
        sol_status = "time_limit"
    else:
        sol_status = "feasible"

    if result.x is None:
        return Solution(
            instance_name=instance.metadata.name,
            algorithm="Exact MILP (MTZ)",
            routes=[],
            total_distance=0.0,
            total_duration=0.0,
            vehicles_used=0,
            runtime_seconds=runtime,
            status=sol_status,
            objective_value=float('inf') if sol_status == "infeasible" else 0.0,
        )

    x_vals = result.x

    # Extract routes for each vehicle
    for k in range(num_vehicles):
        arcs = []
        for (i, j, vk), var_idx in x_indices.items():
            if vk == k and x_vals[var_idx] > 0.5:
                arcs.append((i, j))

        if not arcs:
            continue

        # Reconstruct route - track node indices (0-based in customers array)
        route_node_indices = []  # 0-based customer indices
        current = 0
        while True:
            next_arc = next((a for a in arcs if a[0] == current), None)
            if next_arc is None:
                break
            next_node = next_arc[1]
            if next_node == 0:
                break
            route_node_indices.append(next_node - 1)  # Convert to 0-based customer index
            current = next_node

        if route_node_indices:
            # Compute distance using node indices
            route_dist = dist[0, route_node_indices[0] + 1]
            for i in range(1, len(route_node_indices)):
                route_dist += dist[route_node_indices[i-1] + 1, route_node_indices[i] + 1]
            route_dist += dist[route_node_indices[-1] + 1, 0]

            total_distance += route_dist

            route_customer_ids = [instance.customers[idx].customer_id for idx in route_node_indices]

            routes.append(Route(
                vehicle_id=instance.vehicles[k].vehicle_id,
                customer_ids=route_customer_ids,
                distance=route_dist,
                duration=route_dist,
                load=sum(instance.customers[idx].demand for idx in route_node_indices),
                arrival_times=[],
                departure_times=[],
            ))

    return Solution(
        instance_name=instance.metadata.name,
        algorithm="Exact MILP (MTZ)",
        routes=routes,
        total_distance=total_distance,
        total_duration=total_distance,
        vehicles_used=len(routes),
        runtime_seconds=runtime,
        status=sol_status,
        objective_value=total_distance,
        metadata={"solver_status": status, "solver": "scipy_highs"},
    )


def create_tiny_instance_for_testing(num_customers: int = 8) -> Instance:
    """Create a small test instance for exact MILP verification."""
    from ..data.schema import InstanceMetadata, Depot, Customer, Vehicle

    np.random.seed(42)
    # Depot at origin
    depot = Depot(depot_id="0", x=0.0, y=0.0)

    # Random customers in [0, 100]x[0, 100]
    customers = []
    for i in range(num_customers):
        customers.append(Customer(
            customer_id=str(i+1),
            x=float(np.random.randint(0, 100)),
            y=float(np.random.randint(0, 100)),
            demand=float(np.random.randint(1, 20)),
        ))

    # 3 vehicles with capacity 50
    vehicles = [
        Vehicle(vehicle_id=f"V{i}", capacity=50.0)
        for i in range(1, 4)
    ]

    metadata = InstanceMetadata(
        name=f"tiny_{num_customers}",
        source="Test",
        coordinate_system="xy_planar",
        distance_convention="euclidean_rounded",
        rounding_rule="nearest_int",
        time_unit="distance_units",
        distance_unit="arbitrary",
        objective_definition="min_distance",
    )

    instance = Instance(metadata=metadata, depot=depot, customers=customers, vehicles=vehicles)

    # Build distance matrix
    from ..geo import compute_distance_matrix
    coords = [(depot.x, depot.y)] + [(c.x, c.y) for c in customers]
    instance.distance_matrix = compute_distance_matrix(np.array(coords), "euclidean_rounded")

    return instance