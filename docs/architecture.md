# RouteOpt Architecture

## Overview

RouteOpt follows a modular, layered architecture designed for testability, extensibility, and clear separation of concerns.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit Dashboard                         │
│  Overview │ Delivery Data │ Route Opt │ Route Map │ Comparison  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
│  Loaders │ Solvers │ Evaluator │ Scenario Gen │ Dashboard API   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Domain Layer                               │
│  Instance │ Route │ Solution │ Vehicle │ Customer │ Depot        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                          │
│  Geo (OSRM, OSMnx) │ Config │ Logging │ Cache │ File I/O        │
└─────────────────────────────────────────────────────────────────┘
```

## Module Dependencies

```
routeopt/
├── data/              # ← No internal deps (schema, loaders, validation)
├── geo/               # ← data (for coordinates)
├── algorithms/        # ← data, geo (distance matrices)
├── optimization/      # ← data, geo, algorithms
│   ├── vrp_model      # OR-Tools model builder
│   ├── ortools_solver # OR-Tools wrapper
│   ├── exact_milp     # SciPy/PuLP exact solver
│   ├── objectives     # Objective variants
│   └── constraints    # Advanced constraints
├── prediction/        # ← data (stub only)
├── evaluation/        # ← data, algorithms, optimization
│   ├── metrics
│   ├── route_validator
│   └── benchmark
├── scenarios/         # ← data, geo
└── utils/             # ← No internal deps (config, logging)
```

**Key Principle**: Lower layers never depend on higher layers. Validation, algorithms, and optimization all share only the domain schema (`data.schema`).

## Data Flow

### 1. Instance Loading
```
CSV/VRP/TXT file → Loader → Schema Validation → Instance (dataclass)
                                    ↓
                            Distance Matrix (geo)
```

### 2. Solving
```
Instance + Distance Matrix → Algorithm/Solver → Solution
                                    ↓
                            Independent Validator → ValidationResult
```

### 3. Evaluation
```
Solution + Instance + Distance Matrix → Metrics + Validation → Report
```

## Key Design Decisions

### 1. Dataclasses over Classes
All domain objects use `@dataclass` for immutability, serialization, and type safety.

### 2. Independent Validator
`route_validator.py` recomputes everything from raw instance data. No solver internals accessed.

### 3. Central Configuration
Single `config.yaml` with `Config` singleton. All parameters configurable.

### 4. Distance Matrix Abstraction
`geo.get_distance_matrix()` handles Euclidean, Haversine, OSRM with caching. Solvers only see `np.ndarray`.

### 5. Scale Factor for OR-Tools
OR-Tools requires integer costs. Scale factor applied at boundary, divided back for reporting.

### 6. Benchmark vs Demo Separation
- **Benchmark mode**: CVRPLIB/Solomon, exact conventions, BKS comparison
- **Demo mode**: OSM data, synthetic orders, road networks
- Never mixed in same comparison table

## Solver Architecture

### Heuristic Algorithms (`algorithms/`)
```
Nearest Neighbor → Sequential route construction
Clarke-Wright Savings → Parallel route merging
Local Search (2-opt, Relocate, Swap) → Iterative improvement
```

### Exact MILP (`optimization/exact_milp.py`)
```
MTZ Formulation → SciPy milp (HiGHS) / PuLP (HiGHS)
Variables: x[i,j,k] ∈ {0,1}, u[i] ≥ 0
Constraints: Visit once, Flow, Capacity, MTZ
Only for n ≤ 12
```

### OR-Tools (`optimization/ortools_solver.py`)
```
RoutingIndexManager + RoutingModel
├── Distance callback (arc cost)
├── Capacity dimension
├── Time dimension (windows, service, duration)
├── Fixed vehicle cost (lexicographic)
└── Disjunctions (drop penalties)
Search: First-solution + Metaheuristic + Time limit
```

## Caching Strategy

```
Distance Matrix Cache (disk)
├── Key: SHA256(coords + method + profile)
├── Value: .npz (compressed matrix) + .meta.json
└── TTL: None (explicit invalidation)

OSRM Results
├── Table requests chunked (max 100)
├── Route geometries cached per route
└── Nearest snapping cached
```

## Testing Strategy

```
tests/
├── test_loaders.py       # Parsing, validation, schema
├── test_geo.py           # Coordinates, matrices, OSRM
├── test_algorithms.py    # NN, Savings, Local Search
├── test_exact_milp.py    # MILP vs heuristic comparison
├── test_ortools_solver.py # CVRP, VRPTW, config, benchmark
├── test_evaluation.py    # Metrics, validator, benchmark
├── test_objectives.py    # Objective variants
├── test_scenarios.py     # Generation, sensitivity
└── conftest.py           # Shared fixtures
```

**Rules**:
- Every solution must pass `validate_solution()`
- Numerical correctness tested (not just "returns something")
- Edge cases: empty, single customer, infeasible, duplicates
- CI runs on tiny fixtures only (no OSRM, no downloads)

## Extensibility Points

1. **New Algorithm**: Add to `algorithms/`, implement solver interface
2. **New Objective**: Add to `optimization/objectives.py`
3. **New Constraint**: Add to `optimization/constraints.py`
4. **New Loader**: Add to `data/loaders.py`, return `Instance`
5. **New Distance Method**: Add to `geo/distance_matrix.py`
6. **New Dashboard Page**: Add to `app/pages/`, use `st.session_state`