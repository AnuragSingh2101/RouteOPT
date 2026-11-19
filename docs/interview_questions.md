# RouteOpt Interview Questions

This document contains questions you might face in Data Scientist and Operations Research interviews, based on the RouteOpt project.

---

## 1. Problem Formulation Questions

### Q1: Explain the difference between CVRP, VRPTW, and Fleet-Constrained VRP.
**Answer:**
- **CVRP**: Single depot, homogeneous fleet, capacity constraints, minimize total distance. No time windows.
- **VRPTW**: Adds time windows [earliest, latest] per customer, service times, depot hours. Travel time = distance. Objective usually lexicographic (vehicles first, then distance).
- **Fleet-Constrained VRP**: Fixed number of vehicles K that cannot be exceeded. May be infeasible if demand > K×capacity. CVRPLIB instances have fixed fleet; Solomon gives upper bound.

### Q2: What is the MTZ formulation for subtour elimination? When would you use it vs lazy constraints?
**Answer:**
MTZ adds variables u_i ≥ 0 and constraints: u_i - u_j + Q·x_{ijk} ≤ Q - q_j for all i≠j. Ensures no subtours by enforcing visit order.
- **Use MTZ**: Small instances (n≤50), any MILP solver, simple implementation.
- **Use Lazy Constraints**: Large instances, commercial solvers (Gurobi/CPLEX), stronger LP relaxation, add violated subtour cuts only when needed.

### Q3: What is the difference between two-index and three-index VRP formulations?
**Answer:**
- **Three-index**: x_{ijk} = vehicle k travels i→j. Explicit vehicle assignment. Tighter LP but O(n²K) variables.
- **Two-index**: x_{ij} = number of vehicles traveling i→j (aggregated). O(n²) variables. Weaker LP relaxation but smaller. Use when fleet homogeneous.

### Q4: How do you model time windows in VRPTW? What is the big-M formulation?
**Answer:**
Variables T_i = arrival time at node i. Constraints:
- e_i ≤ T_i ≤ l_i (time windows)
- T_i + t_{ij} + s_i - T_j ≤ M(1 - x_{ijk}) (time consistency)
Where M = l_i + t_{ij} + s_i - e_j (tight bound). Waiting allowed: if arrive early, wait until e_i.

---

## 2. Algorithm Questions

### Q5: Explain the Clarke-Wright Savings formula and why it works.
**Answer:**
S[i,j] = d(i,0) + d(0,j) - d(i,j).
- Original cost: d(i,0) + d(0,j) (two trips to depot)
- Merged cost: d(i,j) (direct connection)
- Savings = original - merged = distance saved by merging.
Algorithm: Start with n routes, compute all savings, sort descending, merge routes while feasible (capacity, continuity).

### Q6: How does 2-opt work? What about relocate and swap?
**Answer:**
- **2-opt (intra-route)**: Reverse segment b→...→c in route a→b→...→c→d. New edges: a-c, b-d. Accept if distance decreases and feasible.
- **Relocate (inter-route)**: Move customer from route A to route B. Remove from A, insert into B at best position.
- **Swap (inter-route)**: Exchange customer between routes A and B.
All check feasibility (capacity, time windows) and strict improvement.

### Q7: What are the trade-offs between different first-solution strategies in OR-Tools?
**Answer:**
| Strategy | Speed | Quality | Best For |
|----------|-------|---------|----------|
| PATH_CHEAPEST_ARC | Fast | Good | General purpose |
| SAVINGS | Medium | Good | CVRP, similar to Clarke-Wright |
| CHRISTOFIDES | Slow | Very good | TSP-based, metric distances |
| SWEEP | Fast | Medium | Geographically clustered |
| PARALLEL_CHEAPEST_INSERTION | Fast | Good | Large instances, parallel |

### Q7b: When would you use GUIDED_LOCAL_SEARCH vs TABU_SEARCH?
**Answer:**
- **GLS**: Better for escaping deep local optima, uses penalty weights on frequently used arcs. Good default.
- **Tabu Search**: Better for avoiding cycling, maintains tabu list. Can find better solutions with careful parameter tuning.
- **Simulated Annealing**: Good for very rugged landscapes, probabilistic.

---

## 3. Exact Methods & Verification

### Q8: How does the exact MILP verify the heuristic/OR-Tools solutions?
**Answer:**
1. Build MTZ formulation for tiny instance (n≤12)
2. Solve with SciPy milp (HiGHS) or PuLP (HiGHS) with time limit
3. If status = optimal → proven optimal value
4. Compare heuristic distance ≥ optimal distance (within tolerance)
5. If heuristic < optimal → bug in validator or formulation

### Q9: What does "proven optimal" mean vs "best found"?
**Answer:**
- **Proven optimal**: Solver returned optimal status with optimality proof (gap=0, dual bound = primal bound). Only exact MILP or benchmark library marking.
- **Best found**: Feasible solution, no optimality proof. OR-Tools always returns "best found" (metaheuristic, no lower bound).
- **Feasible**: Constraints satisfied, no optimality claim.

### Q10: Why can't OR-Tools provide optimality proofs?
**Answer:**
OR-Tools uses metaheuristics (GLS, Tabu Search) which are local search methods. They maintain a single incumbent solution, explore neighborhood, accept improving moves. No dual bound, no branch-and-bound tree. They can prove infeasibility but not optimality.

---

## 4. Benchmarking & Evaluation

### Q11: How do you ensure fair comparison between algorithms?
**Answer:**
1. **Same instance** (identical coordinates, demands, constraints)
2. **Same distance convention** (Euclidean rounded vs exact, scale factor)
3. **Same objective** (distance vs lexicographic)
4. **Same time budget** for time-limited solvers
5. **Independent validator** for all solutions
6. **Record**: instance, distance convention, rounding rule, objective definition

### Q12: Why is Solomon VRPTW objective lexicographic? How do you implement it?
**Answer:**
Literature convention: minimize vehicles first, then distance.
**Implementation**: Large fixed vehicle cost M >> max possible distance.
Objective: min Σ c_{ij}x_{ij} + M Σ_k y_k
Where y_k = 1 if vehicle k used. M = 10⁶ × scale_factor.

### Q13: How do you handle infeasible instances in benchmarking?
**Answer:**
- **Drop penalties**: Allow skipping customers with penalty cost
- **Label**: "infeasible" or "feasible_with_drops"
- **Report**: Which customers dropped, validation errors
- Never report dropped customers as served

### Q14: What statistical tests do you use for benchmark comparison?
**Answer:**
- **Wilcoxon signed-rank test**: Paired comparison of gaps on same instances (non-parametric)
- **Paired t-test**: If gaps approximately normal
- Report: mean gap, std gap, p-value, sample size
- **Critical**: Only compare feasible solutions on same instances

---

## 5. Geospatial & Distance

### Q15: When do you use Haversine vs Euclidean vs OSRM?
**Answer:**
| Source | Method | Why |
|--------|--------|-----|
| CVRPLIB/Solomon | Euclidean (planar) | Benchmark convention, coordinates are x/y not lat/lon |
| OSM demo | OSRM road | Real roads, traffic speeds |
| OSM demo (fallback) | Haversine | When OSRM unavailable, labeled "schematic" |

**Never**: Haversine on benchmark x/y coordinates!

### Q16: What scale factor do you use for OR-Tools and why?
**Answer:**
- **CVRPLIB**: scale=1 (distances already rounded integers)
- **Solomon**: scale=100 (exact Euclidean, preserves 2 decimals)
- **OSRM**: scale=1000 (meters → integer, seconds → integer)
OR-Tools requires integer costs. Scale applied at boundary, divided back for reporting.

### Q17: How do you handle OSRM failures in batch matrix computation?
**Answer:**
1. Chunk requests (max 100 locations per table request)
2. Raise --max-table-size or chunk
3. On failure: raise exception, don't silently fall back to Haversine
4. Cache successful matrices by coordinate hash
5. Label any fallback explicitly in output/UI

---

## 6. Architecture & Engineering

### Q18: How does the independent route validator work?
**Answer:**
Recomputes everything from raw instance data:
1. For each route: trace depot→customers→depot
2. Sum distances from distance matrix
3. Simulate time: travel + wait + service
4. Check: capacity, time windows, max duration
5. Verify: all customers visited exactly once
6. Compare: recomputed distance ≈ reported distance
**Never uses solver internals.**

### Q19: How do you ensure reproducibility?
**Answer:**
- Fixed seeds in config.yaml
- Central Config singleton
- uv.lock for dependency locking
- Record: git commit, config hash, package versions
- Document platform-dependent variability (OR-Tools)

### Q20: How do you handle the different coordinate systems?
**Answer:**
- **Benchmark (CVRPLIB/Solomon)**: xy_planar, Euclidean
- **City demo**: WGS84 (lat/lon), Haversine or OSRM
- **Schema**: InstanceMetadata.coordinate_system field
- **Distance matrix**: Abstracted via geo.get_distance_matrix()
- **Never mix** benchmark and demo results in same table

---

## 7. Scenario Generation & Sensitivity

### Q21: How do you generate synthetic but realistic instances?
**Answer:**
- **Coordinates**: Sample from OSM road network (OSMnx nodes) or distributions (uniform, clustered, Solomon R/C/RC)
- **Demands**: Configurable (uniform, normal, bimodal)
- **Time windows**: Width/density configurable
- **Seeds**: Multiple seeds per setting, report mean ± std
- **Label**: Always "synthetic" in UI and reports

### Q22: What is sensitivity analysis in RouteOpt?
**Answer:**
Vary one parameter (e.g., num_customers, vehicle_capacity) across values, run solver with multiple seeds per value, report mean ± std of distance, vehicles, duration, feasibility rate. Summarize with line plots and box plots.

---

## 8. Business & Practical Questions

### Q23: What would you need to deploy this in production?
**Answer:**
- Real GPS traces for ETA model
- Traffic data integration (historical + real-time)
- Heterogeneous fleet support
- Pickup/delivery pairs
- Driver break constraints
- Multi-depot support
- Robust optimization for demand uncertainty
- CI/CD pipeline with benchmark regression tests
- Docker container with OSRM pre-built

### Q24: How would you handle a customer requesting a specific delivery time?
**Answer:**
Add as hard time window constraint. If infeasible:
1. Report infeasibility
2. Offer drop penalty (serve other customers)
3. Suggest relaxing time window
4. Show alternative feasible windows

### Q25: What's your approach to handling a new constraint not in the model?
**Answer:**
1. Add to constraint helpers (`optimization/constraints.py`)
2. Integrate into OR-Tools model builder (`vrp_model.py`)
3. Add to validator (`evaluation/route_validator.py`)
4. Add tests for the new constraint
5. Document in business assumptions

---

## 9. Quick Reference: Key Numbers

| Metric | Value |
|--------|-------|
| Max exact MILP customers | 12 |
| OR-Tools typical time limit | 30s |
| CVRPLIB scale factor | 1 |
| Solomon scale factor | 100 |
| OSRM scale factor | 1000 |
| Fixed vehicle cost (lexicographic) | 10⁶ × scale |
| Default time limit (benchmark) | 30s |
| Benchmark instances tested | A-n32-k5, C101 |
| Total tests | 81 passing |

---

## 10. Questions to Ask the Interviewer

1. "What's the typical problem size (customers/vehicles) in your operations?"
2. "Do you have real GPS traces for ETA modeling?"
3. "Is the fleet homogeneous or heterogeneous?"
4. "Do you need multi-depot or pickup/delivery support?"
4. "What's the acceptable solve time for production use?"
5. "How do you currently handle infeasible days (too much demand)?"
6. "Do you have historical data for benchmarking new algorithms?"
7. "What's the current solution method (manual, heuristic, OR-Tools)?"