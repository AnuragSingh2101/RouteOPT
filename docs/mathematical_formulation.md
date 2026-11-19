# Mathematical Formulation for VRP Variants

This document describes the mathematical formulations for the Vehicle Routing Problem (VRP) variants implemented in RouteOpt.

---

## 1. Capacitated Vehicle Routing Problem (CVRP)

### 1.1 Problem Definition
- **Graph**: Complete directed graph G = (V, A) where V = {0, 1, ..., n}
  - Node 0 = depot
  - Nodes 1..n = customers
- **Demand**: q_i ≥ 0 for each customer i ∈ {1..n}, q_0 = 0
- **Fleet**: K identical vehicles, each with capacity Q
- **Cost**: c_{ij} = distance from i to j (symmetric, triangle inequality)
- **Objective**: Minimize total distance traveled

### 1.2 Three-Index Vehicle Flow Formulation

**Decision Variables**:
- x_{ijk} ∈ {0,1} = 1 if vehicle k travels from i to j, 0 otherwise
- u_i ≥ 0 = auxiliary variable for subtour elimination (MTZ)

**Objective**:
```
minimize ∑_{k=1}^K ∑_{i∈V} ∑_{j∈V} c_{ij} x_{ijk}
```

**Constraints**:

1. **Each customer visited exactly once**:
```
∑_{k=1}^K ∑_{j∈V} x_{ijk} = 1  ∀i ∈ {1..n}
```

2. **Flow conservation at each node for each vehicle**:
```
∑_{j∈V} x_{ijk} - ∑_{j∈V} x_{jik} = 0  ∀i ∈ V, ∀k ∈ {1..K}
```

3. **Vehicle capacity**:
```
∑_{i∈{1..n}} ∑_{j∈V} q_i x_{ijk} ≤ Q  ∀k ∈ {1..K}
```

4. **Depot departure/return** (each vehicle used at most once):
```
∑_{j∈{1..n}} x_{0jk} ≤ 1  ∀k ∈ {1..K}
∑_{i∈{1..n}} x_{i0k} ≤ 1  ∀k ∈ {1..K}
```

5. **Subtour Elimination (MTZ)**:
```
u_i - u_j + Q x_{ijk} ≤ Q - q_j  ∀i,j ∈ {1..n}, i≠j, ∀k
1 ≤ u_i ≤ Q  ∀i ∈ {1..n}
```
*Note: MTZ uses n×K additional variables and n²×K constraints. For large instances, lazy constraint callbacks (adding subtour elimination cuts only when violated) are more efficient but require solver support.*

6. **Binary/Non-negativity**:
```
x_{ijk} ∈ {0,1}
u_i ≥ 0
```

---

### 1.3 Two-Index Formulation (for homogeneous fleet)

When all vehicles are identical, we can aggregate over vehicles:

**Variables**:
- x_{ij} ∈ {0,1,...,K} = number of vehicles traveling from i to j
- u_i ≥ 0 = MTZ variables

**Objective**:
```
minimize ∑_{i∈V} ∑_{j∈V} c_{ij} x_{ij}
```

**Constraints**:
1. **Customer degree**: ∑_{j∈V} x_{ij} = 1  ∀i ∈ {1..n}
2. **Flow conservation**: ∑_{j∈V} x_{ij} = ∑_{j∈V} x_{ji}  ∀i ∈ V
3. **Capacity**: ∑_{i∈{1..n}} ∑_{j∈V} q_i x_{ij} ≤ K·Q
4. **Depot**: ∑_{j∈{1..n}} x_{0j} ≤ K, ∑_{i∈{1..n}} x_{i0} ≤ K
5. **MTZ**: u_i - u_j + Q x_{ij} ≤ Q - q_j  ∀i,j ∈ {1..n}, i≠j

*Trade-off: Two-index has fewer variables (no K dimension) but weaker LP relaxation. Three-index is tighter but larger.*

---

## 2. Vehicle Routing Problem with Time Windows (VRPTW)

### 2.1 Additional Elements
- **Time windows**: [e_i, l_i] for each node i ∈ V (e_0, l_0 = depot hours)
- **Service time**: s_i ≥ 0 for each node i ∈ V (s_0 = 0)
- **Travel time**: t_{ij} (typically = c_{ij} for Euclidean)
- **Arrival time variables**: T_i ≥ 0

### 2.2 Three-Index VRPTW Formulation

**Additional Variables**:
- T_{ik} ≥ 0 = arrival time of vehicle k at node i

**Additional Constraints**:

1. **Time window satisfaction**:
```
e_i ≤ T_{ik} ≤ l_i  ∀i ∈ V, ∀k
```

2. **Time consistency** (big-M formulation):
```
T_{ik} + t_{ij} + s_i - T_{jk} ≤ M(1 - x_{ijk})  ∀i,j ∈ V, ∀k
```
where M is a large constant (e.g., l_i + t_{ij} + s_i - e_j)

3. **Waiting allowed**: If vehicle arrives before e_i, it waits until e_i. The constraint above allows this because T_{jk} ≥ T_{ik} + t_{ij} + s_i when x_{ijk}=1, but T_{ik} can be > e_i.

### 2.3 Practical Considerations
- **Big-M value**: Tight bounds improve solver performance. Use M_{ij} = l_i + t_{ij} + s_i - e_j
- **Time window tightening**: Preprocess to reduce [e_i, l_i] based on travel times
- **Vehicle working hours**: Captured by depot time window [e_0, l_0]

---

## 3. Fleet Size Variants

### 3.1 Fixed Fleet Size (CVRPLIB standard)
- Number of vehicles K is given and fixed
- Some vehicles may be unused (x_{0jk} = 0 for some k)

### 3.2 Minimum Fleet Size (CVRPLIB X instances)
- Instance name "X-n100-k10" means *at least* 10 vehicles available
- Actual number used is decision variable
- Model: upper bound on K, minimize vehicles first (lexicographic) or use fixed cost per vehicle

### 3.3 Unlimited Fleet
- No upper bound on vehicles (or K = n)
- Each customer could get dedicated vehicle
- Objective naturally limits vehicles through distance minimization

---

## 4. Heterogeneous Fleet VRP (HFVRP)

### 4.1 Additional Parameters per Vehicle k
- Capacity Q_k
- Fixed cost f_k
- Variable cost per distance c_k
- Maximum route duration D_k
- Compatibility constraints (e.g., refrigerated vs. dry)

### 4.2 Formulation Changes
- Capacity constraint: ∑ q_i x_{ijk} ≤ Q_k
- Duration constraint: route duration_k ≤ D_k
- Objective: minimize ∑_k (f_k · used_k + ∑_{i,j} c_k c_{ij} x_{ijk})
- Requires three-index formulation (vehicle-specific parameters)

---

## 5. Objective Variants

### 5.1 Standard: Minimize Total Distance
```
min ∑ c_{ij} x_{ij}
```

### 5.2 Minimize Number of Vehicles (Lexicographic)
Two-phase:
1. Minimize ∑_{j} x_{0j} (vehicles used)
2. Fix optimal vehicle count, minimize distance

Or single objective with large fixed cost:
```
min ∑ c_{ij} x_{ij} + M ∑_j x_{0j}  where M >> max possible distance
```

### 5.3 Minimize Total Duration
```
min ∑ (t_{ij} + s_i) x_{ij}
```

### 5.4 Workload Balancing
- **Min-max route duration**: minimize max_k duration_k
- **Span cost**: add penalty for route duration exceeding average
- **Variance minimization**: quadratic objective (requires MIQP solver)

---

## 6. Subtour Elimination: MTZ vs Lazy Cuts

### 6.1 Miller-Tucker-Zemlin (MTZ)
**Pros**:
- Compact formulation (polynomial constraints)
- Works with any MILP solver
- Easy to implement

**Cons**:
- Weak LP relaxation (large integrality gap)
- Numerical issues with large Q
- O(n²) constraints

**Best for**: Small instances (n ≤ 50), exact verification, solvers without callback support

### 6.2 Lazy Constraint Callbacks (Branch-and-Cut)
**Pros**:
- Much tighter LP relaxation
- Only adds violated constraints
- Scales to larger instances
- Standard in commercial solvers (Gurobi, CPLEX)

**Cons**:
- Requires solver with callback API
- More complex implementation
- Not available in all open-source solvers (HiGHS has limited support)

**Best for**: Production solvers, larger instances

### 6.3 RouteOpt Approach
- **Exact MILP verification**: MTZ formulation (works with SciPy/PuLP/HiGHS)
- **OR-Tools**: Uses its own internal branch-and-cut with constraint callbacks
- **Comparison**: On tiny instances (n≤12), both should find proven optimum

---

## 7. Implementation Notes for Exact MILP (Phase 4)

### 7.1 SciPy/PuLP with HiGHS
```python
from scipy.optimize import milp
# or
import pulp
```

### 7.2 MTZ Implementation for CVRP
```python
# Variables
x = {(i,j,k): binary for i in V for j in V for k in K if i != j}
u = {i: continuous for i in 1..n}

# MTZ constraints
for k in K:
    for i in 1..n:
        for j in 1..n:
            if i != j:
                prob += u[i] - u[j] + Q * x[i,j,k] <= Q - q[j]
```

### 7.3 Time Limit and Status Handling
- Set time limit (e.g., 60 seconds for tiny instances)
- Check solver status: optimal, feasible, infeasible, time_limit
- Only claim "proven optimal" if status = optimal

---

## 8. References

1. Toth, P., & Vigo, D. (2014). *Vehicle Routing: Problems, Methods, and Applications*. SIAM.
2. Laporte, G. (2009). Fifty years of vehicle routing. *Transportation Science*, 43(4), 408-416.
3. Desrochers, M., & Laporte, G. (1991). Improvements and extensions to the Miller-Tucker-Zemlin subtour elimination constraints. *Operations Research Letters*, 10(1), 27-36.
4. Solomon, M. M. (1987). Algorithms for the vehicle routing and scheduling problems with time window constraints. *Operations Research*, 35(2), 254-265.
5. CVRPLIB documentation: https://galgos.inf.puc-rio.br/cvrplib/en/