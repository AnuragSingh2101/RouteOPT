"""VRP model builder for OR-Tools."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal
import numpy as np

from ..data.schema import Instance, Vehicle


@dataclass
class ORToolsModel:
    """Container for OR-Tools routing model components."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    manager: 'pywrapcp.RoutingIndexManager'
    routing: 'pywrapcp.RoutingModel'
    distance_callback_index: int
    time_callback_index: Optional[int] = None
    capacity_dimension_name: str = "Capacity"
    time_dimension_name: str = "Time"


def create_routing_model(
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    scale_factor: int = 1,
    use_fixed_vehicle_cost: bool = False,
    fixed_vehicle_cost: int = 1000000,
    add_time_dimension_flag: bool = False,
) -> ORToolsModel:
    """
    Create OR-Tools routing model from instance.

    Args:
        instance: VRP instance
        distance_matrix: n x n distance matrix (depot at 0)
        time_matrix: n x n time matrix (optional, defaults to distance)
        scale_factor: Multiply distances by this for integer API
        use_fixed_vehicle_cost: If True, add large fixed cost per vehicle (for lexicographic vehicle minimization)
        fixed_vehicle_cost: Fixed cost per vehicle used
        add_time_dimension_flag: If True, register time callback and prepare for time dimension

    Returns:
        ORToolsModel with manager, routing model, and callback indices
    """
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    n_nodes = instance.num_nodes
    num_vehicles = len(instance.vehicles)

    # Create index manager
    manager = pywrapcp.RoutingIndexManager(
        n_nodes,
        num_vehicles,
        0,  # depot index
    )

    # Create routing model
    routing = pywrapcp.RoutingModel(manager)

    # Scale distance matrix for integer API
    dist_int = np.round(distance_matrix * scale_factor).astype(np.int64)
    if time_matrix is not None:
        time_int = np.round(time_matrix * scale_factor).astype(np.int64)
    else:
        time_int = dist_int.copy()

    # Distance callback
    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(dist_int[from_node, to_node])

    distance_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

    # Add fixed vehicle cost if requested (for lexicographic vehicle minimization)
    if use_fixed_vehicle_cost:
        for v in range(num_vehicles):
            routing.SetFixedCostOfVehicle(fixed_vehicle_cost, v)

    # Time callback - only register if explicitly requested
    time_callback_index = None
    if add_time_dimension_flag:
        def time_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(time_int[from_node, to_node])

        time_callback_index = routing.RegisterTransitCallback(time_callback)

    return ORToolsModel(
        manager=manager,
        routing=routing,
        distance_callback_index=distance_callback_index,
        time_callback_index=time_callback_index,
    )


def add_capacity_dimension(
    model: ORToolsModel,
    instance: Instance,
    distance_matrix: np.ndarray,
    scale_factor: int = 1,
) -> None:
    """Add capacity dimension to routing model."""
    from ortools.constraint_solver import pywrapcp

    demands = np.zeros(instance.num_nodes, dtype=int)
    demands[0] = 0  # depot
    for i, customer in enumerate(instance.customers):
        demands[i + 1] = int(round(customer.demand * scale_factor))

    def demand_callback(from_index: int) -> int:
        from_node = model.manager.IndexToNode(from_index)
        return int(demands[from_node])

    demand_callback_index = model.routing.RegisterUnaryTransitCallback(demand_callback)

    # Vehicle capacities
    vehicle_capacities = [int(round(v.capacity * scale_factor)) for v in instance.vehicles]

    model.routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        vehicle_capacities,  # vehicle maximum capacities
        True,  # start cumul to zero
        model.capacity_dimension_name,
    )


def add_time_dimension(
    model: ORToolsModel,
    instance: Instance,
    time_matrix: np.ndarray,
    scale_factor: int = 1,
    service_time_factor: float = 1.0,
) -> None:
    """Add time dimension with time windows to routing model."""
    from ortools.constraint_solver import pywrapcp

    # Time callback already registered during model creation
    if model.time_callback_index is None:
        raise ValueError("Time callback not registered in model")

    # Service times
    service_times = np.zeros(instance.num_nodes, dtype=int)
    service_times[0] = 0  # depot
    for i, customer in enumerate(instance.customers):
        service_times[i + 1] = int(round(customer.service_time * scale_factor * service_time_factor))

    def service_time_callback(from_index: int) -> int:
        from_node = model.manager.IndexToNode(from_index)
        return int(service_times[from_node])

    service_callback_index = model.routing.RegisterUnaryTransitCallback(service_time_callback)

    # Time windows
    time_windows = []
    for i in range(instance.num_nodes):
        if i == 0:
            # Depot time window
            earliest = instance.depot.earliest_time if instance.depot.earliest_time is not None else 0
            latest = instance.depot.latest_time if instance.depot.latest_time is not None else 10**9
        else:
            customer = instance.customers[i - 1]
            earliest = customer.earliest_time if customer.earliest_time is not None else 0
            latest = customer.latest_time if customer.latest_time is not None else 10**9
        time_windows.append((int(round(earliest * scale_factor)), int(round(latest * scale_factor))))

    # Vehicle time windows
    vehicle_time_windows = []
    for v in instance.vehicles:
        start = int(round((v.start_time if v.start_time is not None else 0) * scale_factor))
        end = int(round((v.end_time if v.end_time is not None else 10**9) * scale_factor))
        vehicle_time_windows.append((start, end))

    # Horizon - maximum possible time
    max_time = max(w[1] for w in time_windows)
    for vtw in vehicle_time_windows:
        max_time = max(max_time, vtw[1])

    model.routing.AddDimension(
        model.time_callback_index,
        max_time,  # waiting time allowed
        max_time,  # maximum time per vehicle
        False,  # don't force start cumul to zero
        model.time_dimension_name,
    )

    time_dimension = model.routing.GetDimensionOrDie(model.time_dimension_name)

    # Set time window constraints for locations (including depot)
    for i in range(instance.num_nodes):
        index = model.manager.NodeToIndex(i)
        time_dimension.CumulVar(index).SetRange(time_windows[i][0], time_windows[i][1])

    # Set time window constraints for vehicle start/end
    for v in range(len(instance.vehicles)):
        start_index = model.routing.Start(v)
        end_index = model.routing.End(v)
        time_dimension.CumulVar(start_index).SetRange(vehicle_time_windows[v][0], vehicle_time_windows[v][1])
        time_dimension.CumulVar(end_index).SetRange(vehicle_time_windows[v][0], vehicle_time_windows[v][1])

    # Add service times
    for i in range(instance.num_nodes):
        index = model.manager.NodeToIndex(i)
        time_dimension.SetCumulVarSoftUpperBound(index, time_windows[i][1], 0)
        if service_times[i] > 0:
            # Service time is handled by transit callback in AddDimension
            pass

    # Set span cost coefficient for workload balancing (optional)
    # time_dimension.SetSpanCostCoefficientForAllVehicles(100)


def add_max_route_duration(
    model: ORToolsModel,
    instance: Instance,
    scale_factor: int = 1,
) -> None:
    """Add maximum route duration constraint."""
    from ortools.constraint_solver import pywrapcp

    if model.time_callback_index is None:
        raise ValueError("Time callback required for max route duration")

    time_dimension = model.routing.GetDimensionOrDie(model.time_dimension_name)

    for v, vehicle in enumerate(instance.vehicles):
        if vehicle.max_route_duration is not None:
            max_duration = int(round(vehicle.max_route_duration * scale_factor))
            time_dimension.CumulVar(model.routing.End(v)).SetMax(max_duration)


def configure_search_parameters(
    time_limit_seconds: int = 30,
    first_solution_strategy: str = "PATH_CHEAPEST_ARC",
    local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH",
    log_search: bool = False,
) -> 'pywrapcp.DefaultRoutingSearchParameters':
    """Configure OR-Tools search parameters."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.time_limit.seconds = time_limit_seconds

    # First solution strategy
    strategy_map = {
        "PATH_CHEAPEST_ARC": routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        "SAVINGS": routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
        "SWEEP": routing_enums_pb2.FirstSolutionStrategy.SWEEP,
        "CHRISTOFIDES": routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES,
        "ALL_UNPERFORMED": routing_enums_pb2.FirstSolutionStrategy.ALL_UNPERFORMED,
        "BEST_INSERTION": routing_enums_pb2.FirstSolutionStrategy.BEST_INSERTION,
        "PARALLEL_CHEAPEST_INSERTION": routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
        "LOCAL_CHEAPEST_INSERTION": routing_enums_pb2.FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION,
        "GLOBAL_CHEAPEST_ARC": routing_enums_pb2.FirstSolutionStrategy.GLOBAL_CHEAPEST_ARC,
    }
    search_params.first_solution_strategy = strategy_map.get(
        first_solution_strategy,
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    # Local search metaheuristic
    metaheuristic_map = {
        "GUIDED_LOCAL_SEARCH": routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
        "TABU_SEARCH": routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
        "SIMULATED_ANNEALING": routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
        "GENERIC_TABU_SEARCH": routing_enums_pb2.LocalSearchMetaheuristic.GENERIC_TABU_SEARCH,
    }
    search_params.local_search_metaheuristic = metaheuristic_map.get(
        local_search_metaheuristic,
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )

    search_params.log_search = log_search

    return search_params


def solve_with_parameters(
    model: ORToolsModel,
    search_params: 'pywrapcp.DefaultRoutingSearchParameters',
) -> Optional['pywrapcp.Assignment']:
    """Solve the routing model with given search parameters."""
    return model.routing.SolveWithParameters(search_params)


def extract_solution(
    model: ORToolsModel,
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    assignment: Optional['pywrapcp.Assignment'] = None,
    scale_factor: int = 1,
) -> dict:
    """
    Extract solution from OR-Tools assignment.

    Returns:
        Dictionary with routes, total_distance, total_duration, vehicles_used, etc.
    """
    from ..data.schema import Route

    if assignment is None:
        return {
            "routes": [],
            "total_distance": 0.0,
            "total_duration": 0.0,
            "vehicles_used": 0,
            "status": "infeasible",
        }

    routes = []
    total_distance = 0.0
    total_duration = 0.0
    vehicles_used = 0

    for v in range(len(instance.vehicles)):
        index = model.routing.Start(v)
        route_customers = []
        route_distance = 0
        route_load = 0

        if assignment.Value(model.routing.NextVar(index)) == model.routing.End(v):
            # Empty route
            continue

        vehicles_used += 1
        vehicle = instance.vehicles[v]

        # Get time dimension if available (only if time callback was registered)
        time_dim = None
        if model.time_callback_index is not None:
            try:
                time_dim = model.routing.GetDimensionOrDie(model.time_dimension_name)
            except:
                pass

        while not model.routing.IsEnd(index):
            node = model.manager.IndexToNode(index)
            if node != 0:  # Skip depot
                route_customers.append(instance.customers[node - 1].customer_id)
                route_load += instance.customers[node - 1].demand

            next_index = assignment.Value(model.routing.NextVar(index))
            next_node = model.manager.IndexToNode(next_index)

            if not model.routing.IsEnd(next_index) and node != 0:
                route_distance += distance_matrix[node, next_node]

            index = next_index

        # Return to depot distance
        if route_customers:
            last_customer_node = model.manager.IndexToNode(index)  # This is depot (0)
            # Actually, index is now at End(v), we need the last customer
            # Let's reconstruct from route
            pass

        # Better: reconstruct route from nodes visited
        # Re-traverse to get proper distances
        index = model.routing.Start(v)
        prev_node = 0
        arrival_times = []
        departure_times = []

        while not model.routing.IsEnd(index):
            node = model.manager.IndexToNode(index)
            if node != 0:
                # Distance from prev
                route_distance += distance_matrix[prev_node, node]

                # Time
                if time_dim:
                    arrival = assignment.Value(time_dim.CumulVar(index))
                    arrival_times.append(arrival / scale_factor)
                    departure = arrival + instance.customers[node - 1].service_time
                    departure_times.append(departure / scale_factor)

            next_index = assignment.Value(model.routing.NextVar(index))
            if model.routing.IsEnd(next_index):
                # Return to depot
                route_distance += distance_matrix[node, 0]
            prev_node = node
            index = next_index

        route_duration = route_distance / scale_factor if time_matrix is None else route_distance / scale_factor

        total_distance += route_distance / scale_factor
        total_duration += route_duration

        routes.append(Route(
            vehicle_id=vehicle.vehicle_id,
            customer_ids=route_customers,
            distance=route_distance / scale_factor,
            duration=route_duration,
            load=route_load,
            arrival_times=arrival_times,
            departure_times=departure_times,
        ))

    return {
        "routes": routes,
        "total_distance": total_distance,
        "total_duration": total_duration,
        "vehicles_used": vehicles_used,
        "status": "feasible",
        "objective_value": assignment.ObjectiveValue() / scale_factor if assignment else 0,
    }