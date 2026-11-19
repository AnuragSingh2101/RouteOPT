# Business Assumptions

This document records the key business assumptions underlying RouteOpt models and their implications.

---

## 1. Problem Domain Assumptions

### Last-Mile Delivery Context
- **Single depot**: All routes start and end at the same location
- **Known demand**: Customer demands known in advance (deterministic)
- **Homogeneous fleet**: All vehicles identical (capacity, cost, speed)
- **No split deliveries**: Each customer served by exactly one vehicle
- **No pickup/delivery pairs**: Pure delivery (not pickup-and-delivery)

### Operational Constraints
| Constraint | Assumption | Relaxation |
|------------|------------|------------|
| Vehicle capacity | Hard limit | None (infeasible if exceeded) |
| Time windows | Hard with waiting | Early arrival → wait |
| Service time | Fixed per customer | Included in duration |
| Max route duration | Hard limit | None |
| Working hours | Per vehicle | Depot window applies |
| Split deliveries | Not allowed | Would require reformulation |
| Multiple depots | Not supported | Would require multi-depot model |

---

## 2. Cost Structure Assumptions

### Cost Components
1. **Variable cost per distance**: $c_{dist}$ per unit (default 1.0)
2. **Variable cost per time**: $c_{time}$ per unit (default 0.0)
3. **Fixed vehicle cost**: $c_{fixed}$ per vehicle used (default 0, or large for lexicographic)
4. **Penalty costs**: Drop penalty, tardiness penalty (configurable)

### Default Values
| Parameter | Default | Unit |
|-----------|---------|------|
| Distance cost | 1.0 | per distance unit |
| Time cost | 0.0 | per time unit |
| Fixed vehicle cost | 0 | per vehicle |
| Drop penalty | None | per dropped customer |

### Lexicographic Vehicle Minimization
When `use_fixed_vehicle_cost=True`:
- Fixed cost = 1,000,000 × scale_factor
- Effectively forces vehicle minimization as primary objective
- Matches Solomon VRPTW literature convention

---

## 3. Distance and Time Assumptions

### Benchmark Mode (CVRPLIB/Solomon)
| Metric | Assumption |
|--------|------------|
| Distance | Euclidean (planar) |
| Travel time | = Distance |
| Speed | Implicit (1 distance unit = 1 time unit) |
| Waiting | Allowed at no cost |
| Detours | None (straight-line) |

### City Demo Mode (OSM/OSRM)
| Metric | Assumption |
|--------|------------|
| Distance | Road network (meters) |
| Travel time | OSRM duration (seconds) |
| Speed | OSRM profile-based (default: car) |
| Traffic | Static (no real-time) |
| Turn penalties | OSRM default |

### Haversine Fallback
- Straight-line (great circle) distance
- Used when OSRM unavailable
- **Always labeled** as "schematic, not road-following"

---

## 4. Demand and Supply Assumptions

### Customer Demand
- **Known in advance**: Static, deterministic
- **Non-negative**: No returns/pickups in base model
- **Single product**: No multi-commodity
- **No stochasticity**: No demand uncertainty modeled

### Vehicle Capacity
- **Homogeneous**: All vehicles same capacity
- **Hard limit**: No overloading (infeasible if violated)
- **No soft capacity**: No penalty for near-capacity

### Fleet Size
- **CVRPLIB**: Fixed (given in instance name)
- **Solomon**: Upper bound (not fixed)
- **Custom**: Configurable

---

## 5. Time Window Assumptions

### Solomon Format
- **Ready Time** = Earliest arrival
- **Due Date** = Latest arrival
- **Service Time** = Time at customer
- **Waiting**: Allowed (vehicle waits if early)
- **Late arrival**: Infeasible (hard constraint)

### Depot Window
- **Start**: Vehicle availability (default 0)
- **End**: Latest return (default ∞ or 1236 for Solomon)

### Service Time
- Per-customer (default 0 for CVRPLIB, 10 for Solomon)
- Added to arrival time → departure time
- Included in route duration

### Waiting Time
- **Allowed**: Vehicle waits until window opens
- **Cost**: No explicit waiting cost (included in duration)
- **Implication**: Tight windows may force detours/waiting

---

## 6. Objective Function Assumptions

### Default: Minimize Total Distance
```
min Σ distance(route)
```
- Simple, interpretable
- Ignores vehicle count (may use more vehicles than needed)

### Lexicographic (Solomon Style)
```
Phase 1: min vehicles
Phase 2: min distance (s.t. optimal vehicles)
```
Or single objective with large fixed vehicle cost.

### Workload Balancing
- **Span cost**: Penalize max-min route duration difference
- **Max duration minimization**: Direct constraint or soft penalty
- **Not standard**: Must be explicitly enabled

### Multi-Objective Trade-offs
- Weighted sum: `w1×dist + w2×vehicles + w3×time`
- **Limitation**: Cannot find non-convex Pareto points
- **Alternative**: ε-constraint method (not implemented)

---

## 7. Modeling Limitations

### Not Modeled
| Feature | Status | Workaround |
|---------|--------|------------|
| Heterogeneous fleet | Constraints only | Not in solver |
| Multiple depots | Not supported | Run separately |
| Pickup & delivery | Not supported | Reformulate |
| Stochastic demand | Not supported | Scenario analysis |
| Real-time traffic | Not supported | OSRM static only |
| Driver breaks | Constraint stub only | Not in solver |
| Vehicle compatibility | Constraint stub only | Not in solver |
| Multi-period | Not supported | Run per period |
| Emissions/CO₂ | Not modeled | Proxy via distance |

### Simplifications
| Simplification | Impact |
|----------------|--------|
| Euclidean distance | Underestimates real distance |
| Constant speed | Ignores traffic patterns |
| No loading/unloading sequence | May affect feasibility |
| Deterministic times | No robustness to variability |
| No break constraints | May violate labor rules |

---

## 8. Data Quality Assumptions

### Input Data
- Coordinates accurate (no GPS noise)
- Demands exact (no forecasting error)
- Time windows correct (no customer preference changes)
- Road network complete (OSM coverage)

### Synthetic Data (Demo Mode)
- **All labeled "SYNTHETIC"**
- Not historical performance
- Statistical validity via multiple seeds
- Directional insights only

---

## 8. Solver Behavior Assumptions

### OR-Tools
- **No optimality proof**: Best-found within time limit
- **Non-deterministic**: Results vary by run/platform
- **Time-limited**: Quality improves with time
- **No lower bound**: Cannot prove optimality gap

### Exact MILP
- **Proven optimal**: Only when solver returns optimal status
- **Time-limited**: May return best-found or timeout
- **Small instances only**: n ≤ 12 practical

### Heuristics
- **No guarantee**: Feasible, not optimal
- **Deterministic**: Same input → same output (fixed seed)
- **Fast**: Milliseconds for n≤100

---

## 9. Validation Assumptions

### Independent Validator
- Recomputes from raw data only
- Checks: capacity, time windows, distance, continuity
- **No trust in solver output**

### Feasibility Labels
| Label | Meaning |
|-------|---------|
| feasible | All constraints satisfied, validated |
| best_found | Feasible but not proven optimal (OR-Tools) |
| proven_optimal | Exact MILP optimal status |
| infeasible | Constraints violated |

---

## 10. Reporting Assumptions

### Gap Calculation
```
gap% = (solution_distance - reference_distance) / reference_distance × 100
```
- Only computed when reference exists AND conventions match
- Solomon: vehicle count gap reported first, then distance gap

### Aggregation
- Mean gap reported for multiple instances
- Wilcoxon signed-rank test for paired comparison
- Individual instance results always shown

### Status Reporting
- Always include: algorithm, time limit, seed, platform
- Always label: feasible / best_found / proven_optimal
- Never claim "optimal" without proof