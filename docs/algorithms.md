# RouteOpt Algorithms

## Overview

RouteOpt implements three categories of routing algorithms:
1. **Constructive Heuristics** - Build initial solutions
2. **Local Search** - Improve existing solutions
3. **Metaheuristics** - OR-Tools guided search
4. **Exact Methods** - MILP for verification

---

## 1. Nearest Neighbor (Constructive)

### Algorithm
```
1. Start with all customers unvisited
2. While unvisited customers exist and vehicles available:
   a. Start new route at depot with next vehicle
   b. While route can accept more customers:
      i. Find nearest unvisited customer that fits capacity (and time windows)
      ii. If found: add to route, mark visited
      iii. Else: break
   c. Return to depot
3. Return all routes
```

### Tie-Breaking
Customers sorted by distance from depot initially. Nearest unvisited customer chosen at each step.

### Complexity
- Time: O(n² × v) where n = customers, v = vehicles
- Space: O(n)

### Guarantees
- Always produces feasible solution if one exists (with sufficient vehicles)
- No optimality guarantee
- Quality depends on instance structure

### VRPTW Extension
- Checks time window feasibility before adding customer
- Waits if early arrival
- Checks return-to-depot within vehicle hours

---

## 2. Clarke-Wright Savings (Constructive)

### Savings Formula
For customers i and j:
```
S[i,j] = d(i,0) + d(0,j) - d(i,j)
```
Where 0 = depot.

### Intuition
- Original: Two separate trips 0→i→0 and 0→j→0 = d(i,0) + d(0,j)
- Merged: Single trip 0→i→j→0 = d(i,j) + d(j,0) + d(0,i) = d(i,j) + d(i,0) + d(0,j)
- Savings = Original - Merged = d(i,0) + d(0,j) - d(i,j)

### Algorithm (Parallel Routes)
```
1. Start with each customer on own route: 0→i→0
2. Compute savings S[i,j] for all pairs
3. Sort savings descending
4. For each pair (i,j) in sorted order:
   a. Find route A ending with i, route B starting with j
   b. If A ≠ B and merge feasible:
      - Merge A + B
      - Update route load
5. Assign vehicles to routes (largest loads → largest capacities)
```

### Feasibility Checks
- Combined load ≤ vehicle capacity
- Route continuity: i at end of A, j at start of B
- Time windows (if enabled): simulate merged route

### Complexity
- Time: O(n² log n) for sorting + O(n² × v) for merging
- Space: O(n²) for savings list

### VRPTW Extension
- Time window feasibility checked during merge
- Waiting time simulated
- Max duration respected

---

## 3. Local Search (Improvement)

### Operators

#### 2-opt (Intra-route)
Reverse a segment of a single route.
```
Before: 0 → ... → a → b → ... → c → d → ... → 0
After:  0 → ... → a → c → ... → b → d → ... → 0
```
Only accept if distance decreases and route remains feasible.

#### Relocate (Inter-route)
Move a customer from one route to another.
```
Route A: ... → a → b → c → ...
Route B: ... → x → y → ...

Move b from A to B:
Route A: ... → a → c → ...
Route B: ... → x → b → y → ...
```

#### Swap (Inter-route)
Exchange two customers between routes.
```
Route A: ... → a → ...
Route B: ... → b → ...

Swap a and b:
Route A: ... → b → ...
Route B: ... → a → ...
```

### Acceptance Criteria
- New solution must be feasible (capacity, time windows, duration)
- Objective must strictly improve (Δ < -1e-9)
- First-improvement strategy (restart scan after each move)

### Algorithm
```
1. Start with initial solution (Savings or NN)
2. Repeat until no improvement or max iterations:
   a. Try 2-opt on each route → apply best
   b. Try Relocate between routes → apply best
   c. Try Swap between routes → apply best
3. Return best solution
```

### Complexity
- 2-opt per route: O(k²) for route of length k
- Relocate: O(n²) total
- Swap: O(n²) total
- Typically 10-100 iterations to local optimum

---

## 4. OR-Tools Metaheuristics

### First Solution Strategies
| Strategy | Description |
|----------|-------------|
| PATH_CHEAPEST_ARC | Iteratively add cheapest arc |
| SAVINGS | Clarke-Wright savings heuristic |
| BEST_INSERTION | Best cost insertion |
| CHRISTOFIDES | Christofides algorithm (TSP-based) |
| SWEEP | Geometric sweep |
| PARALLEL_CHEAPEST_INSERTION | Parallel cheapest insertion |

### Local Search Metaheuristics
| Metaheuristic | Description |
|---------------|-------------|
| GUIDED_LOCAL_SEARCH | Escape local optima with penalty weights |
| TABU_SEARCH | Tabu list to avoid cycling |
| SIMULATED_ANNEALING | Probabilistic uphill moves |
| GENERIC_TABU_SEARCH | Enhanced tabu search |

### Search Parameters
- Time limit: Configurable (default 30s)
- Log search: Optional
- Solution callback: Optional for tracking

---

## 5. Exact MILP (MTZ Formulation)

### Three-Index CVRP Formulation

**Sets**
- V = {0, 1, ..., n} (0 = depot, 1..n = customers)
- K = {1, ..., m} (vehicles)

**Variables**
- x_{ijk} ∈ {0,1}: Vehicle k travels i→j
- u_i ≥ 0: MTZ subtour elimination variable

**Objective**
```
min Σ_{k∈K} Σ_{i∈V} Σ_{j∈V} c_{ij} x_{ijk}
```

**Constraints**
1. Visit once: Σ_k Σ_j x_{ijk} = 1  ∀i∈{1..n}
2. Flow: Σ_j x_{ijk} = Σ_j x_{jik}  ∀i∈V, ∀k
3. Capacity: Σ_{i,j} q_i x_{ijk} ≤ Q  ∀k
4. Depot: Σ_j x_{0jk} ≤ 1, Σ_i x_{i0k} ≤ 1  ∀k
5. MTZ: u_i - u_j + Q x_{ijk} ≤ Q - q_j  ∀i,j∈{1..n}, i≠j, ∀k
6. Bounds: 1 ≤ u_i ≤ Q  ∀i∈{1..n}

**Solver**: SciPy `milp` (HiGHS) or PuLP (HiGHS/CBC)

**Limitations**: Only practical for n ≤ 12 due to O(n²m) variables and constraints.

---

## 6. Objective Variants

### Minimize Distance (Default)
```
min Σ c_{ij} x_{ij}
```

### Minimize Vehicles (Lexicographic)
Two-phase or large fixed cost:
```
min Σ c_{ij} x_{ij} + M Σ_k y_k
```
Where y_k = 1 if vehicle k used, M >> max possible distance.

### Minimize Duration
```
min Σ (t_{ij} + s_i) x_{ij}
```
Where t = travel time, s = service time.

### Workload Balancing
Span cost on time dimension:
```
min Σ c_{ij} x_{ij} + α × (max_route_time - min_route_time)
```
Implemented via `SetGlobalSpanCostCoefficient` in OR-Tools.

### Weighted Combination
```
min w₁×distance + w₂×vehicles + w₃×duration + w₄×max_duration
```
Warning: Weighted sum can miss Pareto-optimal solutions.

---

## 7. Algorithm Selection Guide

| Scenario | Recommended |
|----------|-------------|
| Quick baseline, small n | Nearest Neighbor |
| Good baseline, no TW | Clarke-Wright Savings |
| Good baseline + improvement | Savings + Local Search |
| Production CVRP | OR-Tools (PATH_CHEAPEST_ARC + GLS) |
| VRPTW | OR-Tools VRPTW (lexicographic) |
| Verify optimality (n≤12) | Exact MILP |
| Benchmark comparison | All above + multiple time limits |

---

## 8. Performance Characteristics

| Algorithm | Time | Quality | Scalability |
|-----------|------|---------|-------------|
| Nearest Neighbor | O(n²) | Low | n ≤ 1000 |
| Clarke-Wright | O(n² log n) | Medium | n ≤ 500 |
| Savings + LS | O(n² log n + iter×n²) | Good | n ≤ 200 |
| OR-Tools CVRP | Time-limited | Excellent | n ≤ 500 |
| OR-Tools VRPTW | Time-limited | Excellent | n ≤ 200 |
| Exact MILP | Exponential | Optimal | n ≤ 12 |

**Note**: OR-Tools quality depends heavily on time limit. 30s typically finds near-optimal for n≤100.