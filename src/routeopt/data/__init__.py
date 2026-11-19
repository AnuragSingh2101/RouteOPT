"""Data loading and validation module."""

from .schema import (
    InstanceMetadata,
    Depot,
    Customer,
    Vehicle,
    Instance,
    Route,
    Solution,
    ValidationReport,
)

from .loaders import (
    load_cvrplib_instance,
    load_solomon_instance,
    load_delivery_csv,
    load_instance,
    euclidean_distance_rounded,
    euclidean_distance_exact,
    build_distance_matrix,
)

from .validation import (
    validate_instance,
    validate_solution_feasibility,
)

__all__ = [
    # Schema
    "InstanceMetadata",
    "Depot",
    "Customer",
    "Vehicle",
    "Instance",
    "Route",
    "Solution",
    "ValidationReport",
    # Loaders
    "load_cvrplib_instance",
    "load_solomon_instance",
    "load_delivery_csv",
    "load_instance",
    "euclidean_distance_rounded",
    "euclidean_distance_exact",
    "build_distance_matrix",
    # Validation
    "validate_instance",
    "validate_solution_feasibility",
]