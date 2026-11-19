"""Constraint helpers for OR-Tools VRP models."""

from __future__ import annotations
from typing import Optional
import numpy as np

from ..data.schema import Instance


def add_break_constraints(
    model,
    manager,
    routing,
    time_dimension,
    instance: Instance,
    break_duration: int,
    break_time_windows: list[tuple[int, int]],
    scale_factor: int = 1,
) -> None:
    """
    Add break constraints (e.g., driver breaks, lunch).

    Args:
        model: OR-Tools routing model
        manager: RoutingIndexManager
        routing: RoutingModel
        time_dimension: Time dimension
        instance: VRP instance
        break_duration: Duration of break in time units
        break_time_windows: List of (start, end) for break windows
        scale_factor: Time scaling factor
    """
    # This is a placeholder - full implementation would add break nodes
    # and constrain them to specific time windows
    pass


def add_vehicle_compatibility(
    model,
    manager,
    routing,
    instance: Instance,
    vehicle_types: list[str],
    customer_requirements: list[Optional[str]],
) -> None:
    """
    Add vehicle-customer compatibility constraints.

    Args:
        vehicle_types: Type of each vehicle (e.g., "refrigerated", "standard")
        customer_requirements: Required vehicle type for each customer (None = any)
    """
    for v, v_type in enumerate(vehicle_types):
        for c, req in enumerate(customer_requirements):
            if req is not None and req != v_type:
                # This vehicle cannot serve this customer
                index = manager.NodeToIndex(c + 1)  # +1 for depot
                routing.VehicleVar(index).RemoveValue(v)


def add_load_balance_penalty(
    model,
    manager,
    routing,
    capacity_dimension,
    target_load: float,
    penalty_coefficient: float,
) -> None:
    """
    Add soft constraint to balance load across vehicles.

    Args:
        capacity_dimension: Capacity dimension
        target_load: Target load per vehicle
        penalty_coefficient: Penalty per unit deviation from target
    """
    # This would add soft bounds on vehicle loads
    pass


def add_route_duration_balance(
    model,
    manager,
    routing,
    time_dimension,
    target_duration: float,
    penalty_coefficient: float,
) -> None:
    """
    Add soft constraint to balance route durations.

    Args:
        time_dimension: Time dimension
        target_duration: Target duration per vehicle
        penalty_coefficient: Penalty per unit deviation from target
    """
    # This would add soft bounds on route durations
    pass


def add_precedence_constraints(
    model,
    manager,
    routing,
    precedence_pairs: list[tuple[int, int]],
) -> None:
    """
    Add precedence constraints (customer A must be visited before customer B).

    Args:
        precedence_pairs: List of (before_customer, after_customer) 0-based indices
    """
    for before, after in precedence_pairs:
        routing.AddVariableMinimizedByFinalizer(
            routing.VehicleVar(manager.NodeToIndex(before + 1))
        )
        routing.solver().Add(
            routing.VehicleVar(manager.NodeToIndex(before + 1))
            == routing.VehicleVar(manager.NodeToIndex(after + 1))
        )
        # Time constraint would also be needed
        # time_dimension.CumulVar(manager.NodeToIndex(before + 1)) <=
        # time_dimension.CumulVar(manager.NodeToIndex(after + 1))


def add_pickup_delivery_pairs(
    model,
    manager,
    routing,
    pickup_delivery_pairs: list[tuple[int, int]],
) -> None:
    """
    Add pickup and delivery pairs (customer A is pickup, customer B is delivery).

    Args:
        pickup_delivery_pairs: List of (pickup_customer, delivery_customer) 0-based indices
    """
    for pickup, delivery in pickup_delivery_pairs:
        pickup_index = manager.NodeToIndex(pickup + 1)
        delivery_index = manager.NodeToIndex(delivery + 1)
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        # Same vehicle constraint
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
        )
        # Pickup before delivery in time
        # time_dimension.CumulVar(pickup_index) <= time_dimension.CumulVar(delivery_index)


def add_skill_constraints(
    model,
    manager,
    routing,
    instance: Instance,
    vehicle_skills: list[set[str]],
    customer_skills: list[set[str]],
) -> None:
    """
    Add skill-based assignment constraints.

    Args:
        vehicle_skills: Set of skills for each vehicle
        customer_skills: Set of required skills for each customer
    """
    for v, v_skills in enumerate(vehicle_skills):
        for c, c_skills in enumerate(customer_skills):
            if c_skills and not c_skills.issubset(v_skills):
                index = manager.NodeToIndex(c + 1)
                routing.VehicleVar(index).RemoveValue(v)


def add_zone_restrictions(
    model,
    manager,
    routing,
    instance: Instance,
    vehicle_zones: list[set[int]],
    customer_zones: list[int],
) -> None:
    """
    Add zone-based restrictions (vehicles can only serve certain zones).

    Args:
        vehicle_zones: Set of allowed zones for each vehicle
        customer_zones: Zone index for each customer
    """
    for v, v_zones in enumerate(vehicle_zones):
        for c, c_zone in enumerate(customer_zones):
            if c_zone not in v_zones:
                index = manager.NodeToIndex(c + 1)
                routing.VehicleVar(index).RemoveValue(v)


def add_consecutive_visit_constraint(
    model,
    manager,
    routing,
    time_dimension,
    max_gap: int,
    scale_factor: int = 1,
) -> None:
    """
    Add constraint on maximum time gap between consecutive visits.

    Args:
        time_dimension: Time dimension
        max_gap: Maximum allowed time gap between consecutive visits
        scale_factor: Time scaling factor
    """
    # This would constrain time between consecutive customers
    pass