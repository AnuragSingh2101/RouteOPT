"""Data loaders for CVRPLIB, Solomon, and CSV instances."""

from __future__ import annotations
import math
import re
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

from .schema import (
    Instance, InstanceMetadata, Depot, Customer, Vehicle,
    ValidationReport
)


def euclidean_distance_rounded(x1: float, y1: float, x2: float, y2: float) -> int:
    """Euclidean distance rounded to nearest integer (CVRPLIB convention)."""
    return int(round(math.hypot(x1 - x2, y1 - y2)))


def euclidean_distance_exact(x1: float, y1: float, x2: float, y2: float) -> float:
    """Exact Euclidean distance (Solomon convention)."""
    return math.hypot(x1 - x2, y1 - y2)


def build_distance_matrix(
    coords: list[tuple[float, float]],
    convention: str = "euclidean_rounded"
) -> np.ndarray:
    """Build distance matrix from coordinate list."""
    n = len(coords)
    matrix = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i, j] = 0.0
            else:
                x1, y1 = coords[i]
                x2, y2 = coords[j]
                if convention == "euclidean_rounded":
                    matrix[i, j] = euclidean_distance_rounded(x1, y1, x2, y2)
                elif convention == "euclidean_exact":
                    matrix[i, j] = euclidean_distance_exact(x1, y1, x2, y2)
                else:
                    raise ValueError(f"Unknown convention: {convention}")
    return matrix


def load_cvrplib_instance(
    instance_path: Path,
    solution_path: Optional[Path] = None
) -> Instance:
    """
    Load a CVRPLIB instance (.vrp file) and optionally its solution (.sol file).

    Format: TSPLIB-style with NODE_COORD_SECTION, DEMAND_SECTION, DEPOT_SECTION.
    Distance convention: EUC_2D (Euclidean rounded to nearest integer).
    """
    report = ValidationReport([], [])

    with open(instance_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    # Parse header
    name = ""
    dimension = 0
    capacity = 0
    edge_weight_type = ""
    coord_section = False
    demand_section = False
    depot_section = False

    coords = {}  # node_id -> (x, y)
    demands = {}  # node_id -> demand
    depot_id = None

    for line in lines:
        if line.startswith("NAME"):
            name = line.split(":")[1].strip()
        elif line.startswith("DIMENSION"):
            dimension = int(line.split(":")[1].strip())
        elif line.startswith("CAPACITY"):
            capacity = int(line.split(":")[1].strip())
        elif line.startswith("EDGE_WEIGHT_TYPE"):
            edge_weight_type = line.split(":")[1].strip()
        elif line == "NODE_COORD_SECTION":
            coord_section = True
            demand_section = False
            depot_section = False
        elif line == "DEMAND_SECTION":
            coord_section = False
            demand_section = True
            depot_section = False
        elif line == "DEPOT_SECTION":
            coord_section = False
            demand_section = False
            depot_section = True
        elif line == "EOF":
            break
        elif coord_section:
            parts = line.split()
            if len(parts) >= 3:
                node_id = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                coords[node_id] = (x, y)
        elif demand_section:
            parts = line.split()
            if len(parts) >= 2:
                node_id = int(parts[0])
                demand = float(parts[1])
                demands[node_id] = demand
        elif depot_section:
            parts = line.split()
            if parts and parts[0] != "-1":
                depot_id = int(parts[0])

    # Validate required fields
    if not name:
        report.add_error("Missing NAME in instance file")
    if dimension == 0:
        report.add_error("Missing DIMENSION in instance file")
    if capacity == 0:
        report.add_error("Missing CAPACITY in instance file")
    if edge_weight_type != "EUC_2D":
        report.add_warning(f"Unexpected EDGE_WEIGHT_TYPE: {edge_weight_type} (expected EUC_2D)")
    if depot_id is None:
        report.add_error("No depot found in DEPOT_SECTION")

    # Verify node count
    if len(coords) != dimension:
        report.add_error(f"Coordinate count ({len(coords)}) != DIMENSION ({dimension})")

    # Depot is node 1 in CVRPLIB (first in NODE_COORD_SECTION)
    if depot_id is None:
        depot_id = 1

    depot_coord = coords.get(depot_id)
    if depot_coord is None:
        report.add_error(f"Depot {depot_id} not found in coordinates")

    # Build customer list (excluding depot)
    customers = []
    for node_id in range(1, dimension + 1):
        if node_id == depot_id:
            continue
        coord = coords.get(node_id)
        demand = demands.get(node_id, 0)
        if coord is None:
            report.add_error(f"Missing coordinates for node {node_id}")
            continue
        customers.append(Customer(
            customer_id=str(node_id),
            x=coord[0],
            y=coord[1],
            demand=demand,
        ))

    # Depot
    depot = Depot(
        depot_id=str(depot_id),
        x=depot_coord[0] if depot_coord else 0,
        y=depot_coord[1] if depot_coord else 0,
    )

    # Vehicles - CVRPLIB gives fleet size in instance name (k5 = 5 vehicles)
    # Parse from name: A-n32-k5 -> 5 vehicles
    fleet_match = re.search(r'-k(\d+)', name)
    num_vehicles = int(fleet_match.group(1)) if fleet_match else len(customers)

    vehicles = [
        Vehicle(
            vehicle_id=f"V{i}",
            capacity=capacity,
        )
        for i in range(1, num_vehicles + 1)
    ]

    # Build coordinate list for distance matrix (depot first)
    all_coords = [coords[depot_id]] + [coords[i] for i in range(1, dimension + 1) if i != depot_id]
    distance_matrix = build_distance_matrix(all_coords, "euclidean_rounded")

    metadata = InstanceMetadata(
        name=name,
        source="CVRPLIB",
        coordinate_system="xy_planar",
        distance_convention="euclidean_rounded",
        rounding_rule="nearest_int",
        time_unit="distance_units",
        distance_unit="arbitrary",
        objective_definition="min_distance",
        reference_value=None,
        reference_proven_optimal=False,
        reference_source=None,
    )

    # Load solution if provided
    if solution_path and solution_path.exists():
        reference_value = _parse_cvrplib_solution(solution_path)
        if reference_value is not None:
            metadata.reference_value = reference_value
            metadata.reference_proven_optimal = True  # CVRPLIB small instances are proven optimal
            metadata.reference_source = str(solution_path)

    instance = Instance(
        metadata=metadata,
        depot=depot,
        customers=customers,
        vehicles=vehicles,
        distance_matrix=distance_matrix,
    )

    # Run validation
    validation_report = validate_instance(instance)
    if not validation_report.is_valid:
        for err in validation_report.errors:
            report.add_error(err)
    for warn in validation_report.warnings:
        report.add_warning(warn)

    if not report.is_valid:
        raise ValueError(f"Instance validation failed:\n{report}")

    return instance


def _parse_cvrplib_solution(solution_path: Path) -> Optional[float]:
    """Parse CVRPLIB solution file to extract cost."""
    with open(solution_path, "r") as f:
        content = f.read()

    # Look for "Cost XXX" pattern
    match = re.search(r'Cost\s+(\d+)', content)
    if match:
        return float(match.group(1))
    return None


def load_solomon_instance(instance_path: Path) -> Instance:
    """
    Load a Solomon VRPTW instance.

    Format:
    VEHICLE
    NUMBER     CAPACITY
      25         200

    CUSTOMER
    CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
        0     40      50       0       0        1236        0
        1     25      85      20      141       171       10

    Distance convention: Exact Euclidean (no rounding).
    Time = distance.
    Objective: Lexicographic (min vehicles, then min distance).
    """
    report = ValidationReport([], [])

    with open(instance_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    # Parse
    name = ""
    vehicle_count = 0
    vehicle_capacity = 0
    customers = []
    depot = None

    in_customer_section = False

    for line in lines:
        if line.startswith("VEHICLE"):
            continue
        elif "NUMBER" in line and "CAPACITY" in line:
            continue
        elif line.startswith("CUSTOMER"):
            in_customer_section = True
        elif in_customer_section:
            if line == "EOF":
                break
            if line.startswith("CUST NO"):
                # Skip header line
                continue
            parts = line.split()
            if len(parts) >= 7:
                cust_no = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                demand = float(parts[3])
                ready_time = float(parts[4])
                due_date = float(parts[5])
                service_time = float(parts[6])

                if cust_no == 0:
                    depot = Depot(
                        depot_id="0",
                        x=x,
                        y=y,
                        earliest_time=ready_time,
                        latest_time=due_date,
                    )
                else:
                    customers.append(Customer(
                        customer_id=str(cust_no),
                        x=x,
                        y=y,
                        demand=demand,
                        service_time=service_time,
                        earliest_time=ready_time,
                        latest_time=due_date,
                    ))
        elif not name and not line.startswith("VEHICLE"):
            # First non-empty line is instance name
            name = line.split()[0]

    # Parse vehicle info (line after VEHICLE header)
    for i, line in enumerate(lines):
        if line.startswith("VEHICLE") and i + 2 < len(lines):
            parts = lines[i + 2].split()
            if len(parts) >= 2:
                vehicle_count = int(parts[0])
                vehicle_capacity = float(parts[1])
            break

    if depot is None:
        report.add_error("No depot (customer 0) found")

    if not customers:
        report.add_error("No customers found")

    # Vehicles - use vehicle_count as upper bound
    vehicles = [
        Vehicle(
            vehicle_id=f"V{i}",
            capacity=vehicle_capacity,
            start_time=depot.earliest_time if depot else 0,
            end_time=depot.latest_time if depot else float('inf'),
        )
        for i in range(1, vehicle_count + 1)
    ]

    # Build coordinate list (depot first)
    all_coords = [(depot.x, depot.y)] + [(c.x, c.y) for c in customers]
    distance_matrix = build_distance_matrix(all_coords, "euclidean_exact")

    metadata = InstanceMetadata(
        name=name,
        source="Solomon",
        coordinate_system="xy_planar",
        distance_convention="euclidean_exact",
        rounding_rule="none",
        time_unit="distance_units",
        distance_unit="arbitrary",
        objective_definition="lexicographic_vehicles_then_distance",
        reference_value=None,
        reference_proven_optimal=False,
        reference_source=None,
    )

    instance = Instance(
        metadata=metadata,
        depot=depot,
        customers=customers,
        vehicles=vehicles,
        distance_matrix=distance_matrix,
    )

    validation_report = validate_instance(instance)
    if not validation_report.is_valid:
        for err in validation_report.errors:
            report.add_error(err)
    for warn in validation_report.warnings:
        report.add_warning(warn)

    if not report.is_valid:
        raise ValueError(f"Instance validation failed:\n{report}")

    return instance


def load_delivery_csv(
    csv_path: Path,
    depot_row: int = 0,
    coordinate_system: str = "xy_planar",
    distance_convention: str = "euclidean_exact",
) -> Instance:
    """
    Load a delivery instance from CSV.

    Expected columns:
    - customer_id (or index)
    - x, y (or lat, lon for wgs84)
    - demand
    - service_time (optional)
    - earliest_time, latest_time (optional)
    - vehicle_capacity (optional, single value or per vehicle)

    The depot is at depot_row (default 0).
    """
    report = ValidationReport([], [])

    df = pd.read_csv(csv_path)

    # Identify coordinate columns
    if coordinate_system == "wgs84":
        x_col = "lon" if "lon" in df.columns else "longitude"
        y_col = "lat" if "lat" in df.columns else "latitude"
    else:
        x_col = "x" if "x" in df.columns else "XCOORD"
        y_col = "y" if "y" in df.columns else "YCOORD"

    if x_col not in df.columns or y_col not in df.columns:
        report.add_error(f"Coordinate columns {x_col}, {y_col} not found in CSV")

    # Depot
    depot_row_data = df.iloc[depot_row]
    depot = Depot(
        depot_id=str(depot_row_data.get("customer_id", "depot")),
        x=float(depot_row_data[x_col]),
        y=float(depot_row_data[y_col]),
        lat=float(depot_row_data.get("lat", depot_row_data.get("latitude", 0))) if coordinate_system == "wgs84" else None,
        lon=float(depot_row_data.get("lon", depot_row_data.get("longitude", 0))) if coordinate_system == "wgs84" else None,
        earliest_time=float(depot_row_data["earliest_time"]) if "earliest_time" in df.columns and pd.notna(depot_row_data["earliest_time"]) else None,
        latest_time=float(depot_row_data["latest_time"]) if "latest_time" in df.columns and pd.notna(depot_row_data["latest_time"]) else None,
    )

    # Customers (exclude depot row)
    customers = []
    for idx, row in df.iterrows():
        if idx == depot_row:
            continue
        customers.append(Customer(
            customer_id=str(row.get("customer_id", idx)),
            x=float(row[x_col]),
            y=float(row[y_col]),
            demand=float(row["demand"]),
            service_time=float(row.get("service_time", 0)) if "service_time" in df.columns and pd.notna(row.get("service_time")) else 0.0,
            earliest_time=float(row["earliest_time"]) if "earliest_time" in df.columns and pd.notna(row.get("earliest_time")) else None,
            latest_time=float(row["latest_time"]) if "latest_time" in df.columns and pd.notna(row.get("latest_time")) else None,
            lat=float(row.get("lat", row.get("latitude", 0))) if coordinate_system == "wgs84" else None,
            lon=float(row.get("lon", row.get("longitude", 0))) if coordinate_system == "wgs84" else None,
        ))

    # Vehicles - infer from data or use default
    vehicle_capacity = 100.0
    if "vehicle_capacity" in df.columns:
        vehicle_capacity = float(df["vehicle_capacity"].iloc[0])
    elif "capacity" in df.columns:
        vehicle_capacity = float(df["capacity"].iloc[0])

    num_vehicles = max(1, int(math.ceil(sum(c.demand for c in customers) / vehicle_capacity)) + 2)

    vehicles = [
        Vehicle(
            vehicle_id=f"V{i}",
            capacity=vehicle_capacity,
            start_time=depot.earliest_time or 0,
            end_time=depot.latest_time or float('inf'),
        )
        for i in range(1, num_vehicles + 1)
    ]

    # Build distance matrix
    all_coords = [(depot.x, depot.y)] + [(c.x, c.y) for c in customers]
    conv = "euclidean_rounded" if distance_convention == "euclidean_rounded" else "euclidean_exact"
    distance_matrix = build_distance_matrix(all_coords, conv)

    metadata = InstanceMetadata(
        name=csv_path.stem,
        source="CSV",
        coordinate_system=coordinate_system,
        distance_convention=distance_convention,
        rounding_rule="nearest_int" if distance_convention == "euclidean_rounded" else "none",
        time_unit="distance_units",
        distance_unit="arbitrary" if coordinate_system == "xy_planar" else "degrees",
        objective_definition="min_distance",
        reference_value=None,
        reference_proven_optimal=False,
        reference_source=None,
    )

    instance = Instance(
        metadata=metadata,
        depot=depot,
        customers=customers,
        vehicles=vehicles,
        distance_matrix=distance_matrix,
    )

    validation_report = validate_instance(instance)
    if not validation_report.is_valid:
        for err in validation_report.errors:
            report.add_error(err)
    for warn in validation_report.warnings:
        report.add_warning(warn)

    if not report.is_valid:
        raise ValueError(f"Instance validation failed:\n{report}")

    return instance


def validate_instance(instance: Instance) -> ValidationReport:
    """Validate a loaded instance for consistency."""
    from .validation import validate_instance as _validate
    return _validate(instance)


# Convenience function for loading with auto-detection
def load_instance(path: Path) -> Instance:
    """Load instance based on file extension."""
    suffix = path.suffix.lower()
    if suffix == ".vrp":
        sol_path = path.with_suffix(".sol")
        return load_cvrplib_instance(path, sol_path if sol_path.exists() else None)
    elif suffix == ".txt":
        return load_solomon_instance(path)
    elif suffix == ".csv":
        return load_delivery_csv(path)
    else:
        raise ValueError(f"Unknown file format: {suffix}")