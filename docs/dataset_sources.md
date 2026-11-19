# Dataset Sources and Conventions

## CVRPLIB (Capacitated Vehicle Routing Problem Library)

### Source
- **URL**: https://galgos.inf.puc-rio.br/cvrplib/
- **Maintainers**: GALGOS Lab, PUC-Rio
- **License**: Academic use permitted

### Instance Families
| Family | Reference | Customers | Vehicles | Status |
|--------|-----------|-----------|----------|--------|
| A | Augerat et al. (1995) | 31-79 | 5-10 | Proven optimal |
| B | Augerat et al. (1995) | 30-50 | 5-7 | Proven optimal |
| P | Augerat et al. (1995) | 16-70 | 4-8 | Proven optimal |
| E | Christofides & Eilon (1969) | 13-100 | 5-18 | Some optimal |
| M | Christofides et al. (1979) | 50-199 | 5-17 | Some optimal |
| X | Uchoa et al. (2017) | 100-1000 | Min fleet | BKS only |

### File Format (.vrp)
TSPLIB-style format:
```
NAME : A-n32-k5
COMMENT : (Augerat et al, No of trucks: 5, Optimal value: 784)
TYPE : CVRP
DIMENSION : 32
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 100
NODE_COORD_SECTION
 1 82 76
 2 96 44
 ...
DEMAND_SECTION
 1 0
 2 19
 ...
DEPOT_SECTION
 1
 -1
EOF
```

### Conventions
| Property | Value |
|----------|-------|
| Coordinate System | Planar x/y (EUC_2D) |
| Distance | Euclidean rounded to nearest integer |
| Rounding | Standard (0.5 rounds up) |
| Objective | Minimize total distance |
| Fleet | Fixed (given in name, e.g., k5 = 5 vehicles) |
| BKS Status | Proven optimal for A, B, P, E families |

### Solution File (.sol)
```
Route #1: 21 31 19 17 13 7 26
Route #2: 12 1 16 30
Route #3: 27 24
Route #4: 29 18 8 9 22 15 10 25 5 20
Route #5: 14 28 11 4 23 3 2 6
Cost 784
```

### Distance Calculation
```
d(i,j) = round( sqrt( (x_i - x_j)² + (y_i - y_j)² ) )
```
Example: Depot (82,76) to Customer 2 (96,44):
- dx = 14, dy = -32
- sqrt(196 + 1024) = sqrt(1220) ≈ 34.93
- Rounded = 35

### Scale Factor for OR-Tools
- **Scale = 1** (distances already integers)

---

## Solomon VRPTW (Vehicle Routing Problem with Time Windows)

### Source
- **Original**: Solomon, M. M. (1987). "Algorithms for the Vehicle Routing and Scheduling Problems with Time Window Constraints". Operations Research, 35(2), 254-265.
- **Repository**: http://vrp.dorronsoro.es/Problem_Instances/CVRPTWInstances.html (may be unavailable)

### Instance Format
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

### Instance Classes
| Class | Distribution | Time Windows | Customers |
|-------|--------------|--------------|-----------|
| C1 | Clustered | Tight | 25, 50, 100 |
| C2 | Clustered | Wide | 25, 50, 100 |
| R1 | Random | Tight | 25, 50, 100 |
| R2 | Random | Wide | 25, 50, 100 |
| RC1 | Mixed | Tight | 25, 50, 100 |
| RC2 | Mixed | Wide | 25, 50, 100 |

### Conventions
| Property | Value |
|----------|-------|
| Coordinates | Planar x/y (same as CVRPLIB) |
| Distance | Exact Euclidean (no rounding) |
| Travel Time | = Distance |
| Time Windows | [Ready Time, Due Date] |
| Service Time | Given per customer |
| Depot | Customer 0, window [0, 1236] |
| Objective | **Lexicographic**: 1) Minimize vehicles, 2) Minimize distance |

### Distance Calculation
```
d(i,j) = sqrt( (x_i - x_j)² + (y_i - y_j)² )
```
**No rounding** - keep full double precision.

### Scale Factor for OR-Tools
- **Scale = 100** (preserves 2 decimal places)

### Reference Values
From Solomon (1987) and subsequent literature:
- C101 (25 cust): 10 vehicles, ~828.94 distance
- R101 (25 cust): ~19 vehicles, ~1650 distance
- RC101 (25 cust): ~14 vehicles, ~1500 distance

*Note: Some published values truncate to 1 decimal. RouteOpt uses full precision.*

### Fleet Size
The "NUMBER" in VEHICLE section is an **upper bound**, not fixed fleet.
- Instance name "C101" doesn't indicate vehicle count
- Optimal typically uses fewer than maximum

---

## Comparison: CVRPLIB vs Solomon

| Aspect | CVRPLIB | Solomon |
|--------|---------|---------|
| Problem | CVRP | VRPTW |
| Distance | Rounded integer | Exact double |
| Time Windows | None | Yes |
| Service Time | None | Yes |
| Objective | Min distance | Lexicographic (vehicles, then distance) |
| Scale Factor | 1 | 100 |
| Fleet | Fixed (k in name) | Upper bound |
| BKS Status | Proven optimal (small) | Heuristic best-known |

---

## Critical Rules for Comparison

### NEVER DO
- ❌ Apply Haversine to CVRPLIB/Solomon x/y coordinates
- ❌ Mix rounded and exact distances in one comparison
- ❌ Use different scale factors for same instance
- ❌ Compare distance-only objective with lexicographic objective
- ❌ Assume fleet size is fixed in Solomon (it's an upper bound)

### ALWAYS DO
- ✅ Record: instance, distance convention, rounding rule, objective definition
- ✅ Use scale_factor=1 for CVRPLIB, 100 for Solomon
- ✅ For Solomon: report vehicles first, then distance
- ✅ Validate every solution with independent validator
- ✅ Label solutions: feasible / best_found / proven_optimal

---

## OSM / OSRM Data (City Demo Mode)

### Source
- **OpenStreetMap**: https://www.openstreetmap.org/
- **Geofabrik Extracts**: https://download.geofabrik.de/
- **OSRM**: http://project-osrm.org/

### Coordinate System
- **WGS84** (latitude/longitude)
- **Distance**: Road network (OSRM) or Haversine (straight-line)

### Conventions
| Property | Value |
|----------|-------|
| Distance | Meters (OSRM) or km (Haversine) |
| Time | Seconds (OSRM duration) |
| Scale Factor | 1000 (meters → integer) or 100 (seconds) |
| Objective | Minimize distance/time |
| Orders | **Synthetic** (generated, labeled everywhere) |

### Synthetic Order Generation
- Customer locations: Sampled from OSM road network nodes (OSMnx)
- Demands: Configurable distribution
- Time windows: Configurable width/density
- Service times: Configurable
- **All labels**: "SYNTHETIC" in UI and reports

---

## Summary: Distance Conventions by Source

| Source | Coordinates | Distance Formula | Rounding | Scale Factor |
|--------|-------------|------------------|----------|--------------|
| CVRPLIB | x,y (planar) | round(√(dx²+dy²)) | Nearest int | 1 |
| Solomon | x,y (planar) | √(dx²+dy²) | None (exact) | 100 |
| OSM Haversine | lat,lon | Haversine formula | None | 1000 (meters) |
| OSRM Road | lat,lon | Road network | None | 1000 (meters) |