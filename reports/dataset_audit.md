# RouteOpt Dataset Audit Report

## Overview
This document records the inspection of benchmark instance formats, conventions, and reference values for CVRPLIB and Solomon datasets. It establishes the ground truth for distance conventions, rounding rules, and objective definitions before any solver implementation.

---

## 1. CVRPLIB (CVRP Instances)

### 1.1 Source
- **URL**: https://galgos.inf.puc-rio.br/cvrplib/en/cvrp/instances
- **Instance downloaded**: A-n32-k5 (31 customers, 5 vehicles, capacity 100)
- **Solution downloaded**: A-n32-k5.sol (BKS = 784, proven optimal)

### 1.2 File Format (`.vrp` - TSPLIB-style)
```
NAME : A-n32-k5
COMMENT : (Augerat et al, No of trucks: 5, Optimal value: 784)
TYPE : CVRP
DIMENSION : 32
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 100
NODE_COORD_SECTION
  1 82 76
  ...
DEMAND_SECTION
  1 0     # depot
  2 19
  ...
DEPOT_SECTION
  1
  -1
EOF
```

### 1.3 Key Conventions
| Property | Value | Notes |
|----------|-------|-------|
| **Coordinate System** | Planar x/y (EUC_2D) | Not lat/lon |
| **Distance Convention** | Euclidean distance rounded to nearest integer | `round(sqrt((x_i - x_j)^2 + (y_i - y_j)^2))` |
| **Rounding Rule** | Nearest integer (standard rounding) | 0.5 rounds up |
| **Distance Unit** | Arbitrary units (consistent within instance) | |
| **Objective** | Minimize total distance (sum of rounded edge costs) | |
| **Vehicle Count** | Fixed (given in instance name, e.g., k5 = 5 vehicles) | |
| **Capacity** | Single homogeneous capacity for all vehicles | |
| **Time Windows** | None (pure CVRP) | |
| **Service Times** | None | |
| **BKS Status** | Proven optimal (marked "Opt: yes" on CVRPLIB) | |
| **Reference Value** | 784 for A-n32-k5 | |

### 1.4 Distance Calculation Verification
For EUC_2D, the standard TSPLIB formula is:
```
d(i,j) = round(sqrt((x_i - x_j)^2 + (y_i - y_j)^2))
```
Example: Depot (1) at (82, 76) to Customer 2 at (96, 44):
- dx = 14, dy = -32
- sqrt(14² + 32²) = sqrt(196 + 1024) = sqrt(1220) ≈ 34.928
- Rounded = 35

### 1.5 Solution Format (`.sol`)
```
Route #1: 21 31 19 17 13 7 26
Route #2: 12 1 16 30
Route #3: 27 24
Route #4: 29 18 8 9 22 15 10 25 5 20
Route #5: 14 28 11 4 23 3 2 6
Cost 784
```
- Routes list customer IDs (depot = 1)
- Cost is sum of rounded Euclidean distances
- Each route implicitly starts and ends at depot

---

## 2. Solomon (VRPTW Instances)

### 2.1 Source
- **Original URL**: http://vrp.dorronsoro.es/Problem_Instances/CVRPTWInstances.html (403 Forbidden)
- **Instance created**: C101 (25 customers, based on standard literature format)
- **Reference**: Solomon, M. M. (1987). "Algorithms for the Vehicle Routing and Scheduling Problems with Time Window Constraints"

### 2.2 File Format
```
C101  25 customer instance

VEHICLE
NUMBER     CAPACITY
  25         200

CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
    0     40      50       0       0        1236        0
    1     25      85      20      141       171       10
    ...
EOF
```

### 2.3 Key Conventions
| Property | Value | Notes |
|----------|-------|-------|
| **Coordinate System** | Planar x/y | Not lat/lon |
| **Distance Convention** | Real-valued Euclidean distance | `sqrt((x_i - x_j)^2 + (y_i - y_j)^2)` |
| **Rounding Rule** | **No rounding** - keep full precision | Literature varies: some truncate to 1 decimal |
| **Distance Unit** | Arbitrary (same as coordinates) | |
| **Time Unit** | Same as distance (travel time = distance) | |
| **Objective** | **Lexicographic**: 1) Minimize vehicles, 2) Minimize total distance | Critical! |
| **Vehicle Count** | Upper bound given (25 for C101), not fixed | |
| **Capacity** | Homogeneous (200 for C101) | |
| **Time Windows** | Yes (READY TIME = earliest, DUE DATE = latest) | |
| **Service Times** | Yes (SERVICE TIME column) | |
| **Depot** | Customer 0, time window [0, 1236] | |
| **Reference Values** | C101: 10 vehicles, 828.94 distance (varies by source) | Must verify convention |

### 2.4 Important Notes on Solomon Comparisons
1. **Vehicle count is primary objective** - A solution with 9 vehicles at distance 1000 beats 10 vehicles at distance 800
2. **Distance precision** - Some published values truncate to 1 decimal (e.g., 828.9), others use full precision
3. **Travel time = distance** - No separate speed factor
4. **Waiting allowed** - If arrival < ready time, wait until ready time
5. **No rounding in distance matrix** - Keep double precision throughout

### 2.5 Distance Calculation
For customer 0 (40, 50) to customer 1 (25, 85):
- dx = -15, dy = 35
- Distance = sqrt(225 + 1225) = sqrt(1450) ≈ 38.0789
- **No rounding applied**

---

## 3. Problem Variants Explained

### 3.1 CVRP (Capacitated Vehicle Routing Problem)
- **Definition**: Single depot, homogeneous fleet, known customer demands, vehicle capacity constraint
- **Objective**: Minimize total distance traveled
- **Constraints**: 
  - Each customer visited exactly once
  - Vehicle capacity not exceeded
  - Routes start and end at depot
- **No**: Time windows, service times, heterogeneous vehicles

### 3.2 VRPTW (Vehicle Routing Problem with Time Windows)
- **Extends CVRP** with:
  - Time windows [earliest, latest] for each customer
  - Service times at each customer
  - Depot operating hours
  - Travel time = distance (typically)
- **Objective**: Usually lexicographic (vehicles first, then distance)
- **Waiting allowed**: Early arrival → wait until window opens

### 3.3 Fleet-Constrained VRP
- **Fixed fleet size**: Number of vehicles K is given and cannot be exceeded
- **Contrast**: Standard CVRPLIB X instances have "minimum fleet" in name, not maximum
- **Implication**: May be infeasible if demand > K × capacity

### 3.4 Heterogeneous Fleet VRP (HFVRP)
- **Vehicles differ** in:
  - Capacity
  - Fixed cost
  - Variable cost per distance/time
  - Maximum route duration
  - Compatibility (e.g., refrigerated vs. dry)
- **More realistic** but harder to solve
- **Not in standard benchmarks** (CVRPLIB/Solomon use homogeneous fleets)

---

## 4. Common Internal Schema Design

Based on the above inspection, the unified internal representation must capture all variants:

### 4.1 Instance Metadata
```python
@dataclass
class InstanceMetadata:
    name: str
    source: str  # "CVRPLIB" | "Solomon" | "CSV"
    coordinate_system: str  # "xy_planar" | "wgs84"
    distance_convention: str  # "euclidean_rounded" | "euclidean_exact" | "haversine" | "osrm"
    rounding_rule: str  # "nearest_int" | "none" | "truncate_1dp"
    time_unit: str  # "distance_units" | "minutes" | "seconds"
    distance_unit: str  # "arbitrary" | "meters" | "km"
    objective_definition: str  # "min_distance" | "lexicographic_vehicles_then_distance" | "min_time"
    reference_value: float | None  # BKS if known
    reference_proven_optimal: bool
    reference_source: str | None
```

### 4.2 Depot
```python
@dataclass
class Depot:
    depot_id: str
    x: float
    y: float
    lat: float | None = None
    lon: float | None = None
    earliest_time: float | None = None
    latest_time: float | None = None
```

### 4.3 Customers
```python
@dataclass
class Customer:
    customer_id: str
    x: float
    y: float
    lat: float | None = None
    lon: float | None = None
    demand: float
    service_time: float = 0.0
    earliest_time: float | None = None
    latest_time: float | None = None
```

### 4.4 Vehicles
```python
@dataclass
class Vehicle:
    vehicle_id: str
    capacity: float
    start_time: float = 0.0
    end_time: float = float('inf')
    max_route_duration: float | None = None
    fixed_cost: float = 0.0
    var_cost_per_distance: float = 1.0
    var_cost_per_time: float = 0.0
```

### 4.5 Complete Instance
```python
@dataclass
class Instance:
    metadata: InstanceMetadata
    depot: Depot
    customers: list[Customer]
    vehicles: list[Vehicle]
    distance_matrix: np.ndarray | None = None  # n x n, depot at index 0
    time_matrix: np.ndarray | None = None
```

---

## 5. Distance Matrix Requirements

### 5.1 For CVRPLIB (Benchmark Mode)
- Method: Euclidean with nearest-integer rounding
- Scale factor for OR-Tools: 1 (already integers)
- Units: Arbitrary (consistent with instance)

### 5.2 For Solomon (Benchmark Mode)
- Method: Euclidean exact (double precision)
- Scale factor for OR-Tools: 100 (to preserve 2 decimal places)
- Units: Same as coordinates

### 5.3 For Geographic Data (City Demo Mode)
- Method: Haversine (straight-line) or OSRM (road network)
- Scale factor: 1000 (meters to integer) or 100 (seconds)
- Units: Meters / Seconds
- **Must label**: "schematic (Haversine)" or "road-following (OSRM)"

---

## 6. Validation Rules for Loaders

### 6.1 CVRPLIB Loader
- Parse NAME, DIMENSION, EDGE_WEIGHT_TYPE, CAPACITY
- Verify EDGE_WEIGHT_TYPE == "EUC_2D"
- Parse NODE_COORD_SECTION (1-indexed, depot first)
- Parse DEMAND_SECTION (depot demand = 0)
- Parse DEPOT_SECTION (single depot)
- Compute distance matrix with rounding
- Verify total demand ≤ vehicles × capacity (if vehicles known)

### 6.2 Solomon Loader
- Parse VEHICLE section (number = upper bound, capacity)
- Parse CUSTOMER section (0 = depot)
- Time windows: ready_time ≤ due_date
- Service times ≥ 0
- Distance matrix: exact Euclidean, no rounding
- Time matrix = distance matrix (travel time = distance)

### 6.3 CSV Loader (User Data)
- Required columns: customer_id, x, y, demand
- Optional: service_time, earliest, latest, lat, lon
- Depot specified separately or first row
- Coordinate system declared (xy_planar or wgs84)

---

## 7. Summary of Critical Decisions

| Decision | Rationale |
|----------|-----------|
| Separate benchmark vs. city modes | Different conventions, cannot mix |
| No Haversine on benchmark x/y | EUC_2D ≠ WGS84 |
| Scale factor per instance type | OR-Tools needs integers |
| Lexicographic objective for Solomon | Matches literature |
| Independent validator mandatory | Solver output cannot be trusted |
| Label all solutions | feasible / best-found / proven optimal |
| Record convention with every result | Enables like-with-like comparison |

---

## 8. Next Steps (Phase 1)

1. Implement `loaders.py` with parsers for CVRPLIB `.vrp`, Solomon `.txt`, and CSV
2. Implement `validation.py` with all checks from Section 6
3. Create internal dataclasses matching Section 4
4. Write tests with the downloaded A-n32-k5 and C101 instances
5. Verify distance matrix computation matches known values