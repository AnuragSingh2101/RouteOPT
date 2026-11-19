"""Internal data schema for RouteOpt instances."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class InstanceMetadata:
    """Metadata about the instance source and conventions."""
    name: str
    source: str  # "CVRPLIB", "Solomon", "CSV", "OSM"
    coordinate_system: str  # "xy_planar", "wgs84"
    distance_convention: str  # "euclidean_rounded", "euclidean_exact", "haversine", "osrm"
    rounding_rule: str  # "nearest_int", "none", "truncate_1dp"
    time_unit: str  # "distance_units", "minutes", "seconds"
    distance_unit: str  # "arbitrary", "meters", "km"
    objective_definition: str  # "min_distance", "lexicographic_vehicles_then_distance", "min_time"
    reference_value: Optional[float] = None
    reference_proven_optimal: bool = False
    reference_source: Optional[str] = None


@dataclass
class Depot:
    """Depot location and time window."""
    depot_id: str
    x: float
    y: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    earliest_time: Optional[float] = None
    latest_time: Optional[float] = None


@dataclass
class Customer:
    """Customer with demand, service time, and time window."""
    customer_id: str
    x: float
    y: float
    demand: float
    service_time: float = 0.0
    earliest_time: Optional[float] = None
    latest_time: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass
class Vehicle:
    """Vehicle specifications."""
    vehicle_id: str
    capacity: float
    start_time: float = 0.0
    end_time: float = float('inf')
    max_route_duration: Optional[float] = None
    fixed_cost: float = 0.0
    var_cost_per_distance: float = 1.0
    var_cost_per_time: float = 0.0


@dataclass
class Instance:
    """Complete VRP instance with all data."""
    metadata: InstanceMetadata
    depot: Depot
    customers: list[Customer]
    vehicles: list[Vehicle]
    distance_matrix: Optional[np.ndarray] = None  # n x n, depot at index 0
    time_matrix: Optional[np.ndarray] = None

    @property
    def num_customers(self) -> int:
        return len(self.customers)

    @property
    def num_nodes(self) -> int:
        return 1 + len(self.customers)  # depot + customers

    @property
    def total_demand(self) -> float:
        return sum(c.demand for c in self.customers)

    @property
    def total_capacity(self) -> float:
        return sum(v.capacity for v in self.vehicles)

    @property
    def has_time_windows(self) -> bool:
        """Check if any customer or depot has time windows."""
        if self.depot.earliest_time is not None or self.depot.latest_time is not None:
            return True
        for c in self.customers:
            if c.earliest_time is not None or c.latest_time is not None:
                return True
        return False


@dataclass
class Route:
    """A single vehicle route."""
    vehicle_id: str
    customer_ids: list[str]  # Ordered list of customer IDs (excludes depot)
    distance: float
    duration: float
    load: float
    arrival_times: list[float]  # Arrival time at each customer
    departure_times: list[float]  # Departure time from each customer (after service)


@dataclass
class Solution:
    """Complete solution with all routes."""
    instance_name: str
    algorithm: str
    routes: list[Route]
    total_distance: float
    total_duration: float
    vehicles_used: int
    runtime_seconds: float
    status: str  # "feasible", "best_found", "proven_optimal", "infeasible"
    objective_value: float
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "instance_name": self.instance_name,
            "algorithm": self.algorithm,
            "routes": [
                {
                    "vehicle_id": r.vehicle_id,
                    "customers": r.customer_ids,
                    "distance": r.distance,
                    "duration": r.duration,
                    "load": r.load,
                    "arrival_times": r.arrival_times,
                    "departure_times": r.departure_times,
                }
                for r in self.routes
            ],
            "total_distance": self.total_distance,
            "total_duration": self.total_duration,
            "vehicles_used": self.vehicles_used,
            "runtime_seconds": self.runtime_seconds,
            "status": self.status,
            "objective_value": self.objective_value,
            "metadata": self.metadata,
        }


@dataclass
class ValidationReport:
    """Validation report with errors and warnings."""
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def __str__(self) -> str:
        lines = []
        if self.errors:
            lines.append("ERRORS:")
            for e in self.errors:
                lines.append(f"  - {e}")
        if self.warnings:
            lines.append("WARNINGS:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if not lines:
            lines.append("Valid: No errors or warnings")
        return "\n".join(lines)