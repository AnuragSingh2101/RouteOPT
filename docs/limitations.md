# RouteOpt Limitations and Future Work

This document lists the known limitations of the current RouteOpt implementation and outlines future work.

---

## 1. ETA Prediction Model (Phase 7 - Gated)

### Current State
The ETA prediction module (`src/routeopt/prediction/eta_model.py`) is implemented as a **documented stub** that raises `ETAModelError` when used.

### Reason
**No real observed travel-time labels are available.** The project uses:
- OpenStreetMap (OSM) road network geometry
- OSRM routing engine estimates

**Neither of these constitutes observed ground truth labels:**
- OSM geometry is map data, not travel time observations
- OSRM estimates are model predictions based on heuristics and speed profiles
- Using OSRM estimates as "labels" to train a model would be circular

### Requirements for Real ETA Model
To implement a real ETA model, the following would be needed:
1. **GPS trace data** from actual delivery vehicles with timestamps
2. **Observed travel times** for road segments (not estimated)
3. **Sufficient volume** of observations across different times of day, days of week, weather conditions
4. **Time-based validation** (not random split) to avoid data leakage

### Current Workaround
For planning purposes, RouteOpt uses OSRM duration estimates directly:
```python
from routeopt.prediction import get_osrm_duration_estimate
duration_seconds = get_osrm_duration_estimate(distance_meters, speed_kmh=30.0)
```

### Future Work
If real GPS trace data becomes available:
1. Replace stub with `RealETAModel` implementation (see `eta_model.py` for template)
2. Use time-based train/test split (e.g., first 80% of time periods for training)
3. Report MAE, RMSE, and residual analysis
4. Compare against OSRM baseline (simple physics-based estimate)
5. Feature engineering: time of day, day of week, road class, historical congestion

---

## 2. Exact MILP Solver Scalability

### Current State
The exact MILP solver (`src/routeopt/optimization/exact_milp.py`) uses MTZ formulation with SciPy/PuLP.

### Limitation
- **Only works for tiny instances (n ≤ 12 customers)**
- Number of variables: O(n²K) where K = number of vehicles
- MTZ formulation has weak LP relaxation
- Solving time grows exponentially

### Future Work
- Implement lazy constraint callbacks (branch-and-cut) for subtour elimination
- Use two-index formulation with stronger cuts
- Integrate with commercial solvers (Gurobi, CPLEX) for better performance
- Add constraint generation for capacity cuts

---

## 3. OR-Tools Search Variability

### Current State
OR-Tools solver uses metaheuristics (Guided Local Search, Tabu Search) with time limits.

### Limitation
- **Results vary between runs** due to randomized search
- **Platform-dependent** results (Windows vs Linux may differ)
- No optimality guarantee or lower bound
- Solution quality depends heavily on time limit

### Mitigation
- Run multiple times with different seeds and take best
- Document time limit and platform for reproducibility
- Compare against exact solver on tiny instances for validation

### Future Work
- Implement solution pooling to collect diverse solutions
- Add support for OR-Tools' solution callbacks for custom heuristics
- Experiment with CP-SAT for exact solving on larger instances

---

## 4. Benchmark Comparability

### Current State
RouteOpt loads CVRPLIB and Solomon instances and compares against published BKS.

### Limitations
1. **CVRPLIB**: Uses Euclidean rounded distances; BKS assumes this convention
2. **Solomon**: Uses exact Euclidean; literature varies on rounding (some truncate to 1 decimal)
3. **Fleet size in CVRPLIB X instances**: The 'k' in instance name is a minimum, not fixed limit
4. **Objective definition**: Solomon uses lexicographic (vehicles first, then distance)

### Mitigation
- Record distance convention, rounding rule, objective definition with every result
- Use scale_factor=1 for CVRPLIB, scale_factor=100 for Solomon
- Label all solutions as "feasible", "best_found", or "proven_optimal"

### Future Work
- Add more instance sets (Homberger, Cordeau, etc.)
- Implement Solomon 100-customer instances
- Validate against multiple reference sources

---

## 5. Road Network Integration

### Current State
- OSMnx integration for graph download and node snapping
- OSRM integration for distance/duration matrices and route geometries
- OSRM runs as local Docker container

### Limitations
1. **OSRM setup complexity**: Requires Docker, data extraction, partition, customize steps
2. **OSRM table size limit**: Large matrices require chunking
3. **No traffic data**: Uses static speeds, not real-time or historical traffic
4. **Geographic scope**: Limited to small regions for performance

### Future Work
- Add support for traffic-aware routing (e.g., OpenTraffic, TomTom)
- Implement contraction hierarchies for faster matrix computation
- Add fallback to Haversine when OSRM unavailable
- Support multi-region / country-scale routing

---

## 6. Streamlit Dashboard

### Current State
Dashboard structure defined in `app/` with 6 pages but not fully implemented.

### Planned Features
1. **Overview**: KPIs, fleet utilization, solver status
2. **Delivery Data**: CSV upload, validation, depot/fleet configuration
3. **Route Optimization**: Algorithm selection, parameters, run button, results
4. **Route Map**: Interactive map with routes, sequence numbers, details
5. **Model Comparison**: Side-by-side algorithm comparison
6. **Scenario Analysis**: Parameter sweeps, sensitivity plots

### Limitations
- No real-time solving for large instances (UI would block)
- Map rendering limited to small instance sizes
- No export to PDF/Excel yet

---

## 7. Scenario Generation

### Current State
Scenario generator implemented in `src/routeopt/scenarios/generator.py`.

### Planned Features
- Synthetic instance generator with configurable:
  - Customer count, demand distribution
  - Fleet size, vehicle capacities
  - Time window width and density
  - Spatial distributions (uniform, clustered, Solomon R/C/RC styles)
- Reproducible with seeds
- Multiple seeds per setting for statistical validity

---

## 8. Evaluation and Validation

### Current State
- Independent route validator (`src/routeopt/evaluation/route_validator.py`)
- Benchmark runner with multiple algorithms
- Statistical comparison (Wilcoxon signed-rank) implemented

### Limitations
- No automated benchmark result tables yet
- No "Honest results" section documenting where heuristics beat OR-Tools

---

## 9. Reproducibility

### Current State
- Fixed seeds in config.yaml
- Central config for all parameters
- uv.lock for dependency locking

### Limitations
- OR-Tools results vary by platform and run
- No MLflow integration (optional)
- No automated `run_all.ps1` script yet

### Future Work
- Create `scripts/run_all.ps1` for full pipeline
- Add git commit hash and config hash to results
- Document platform-dependent variability

---

## 10. Heterogeneous Fleet and Advanced Constraints

### Current State
Basic support in constraint helpers (`src/routeopt/optimization/constraints.py`) but not integrated into main solver.

### Missing Features
- Vehicle-specific capacities, costs, speeds
- Pickup and delivery pairs
- Driver breaks and working hour rules
- Skill-based assignment
- Zone restrictions
- Precedence constraints

---

## 11. Multi-Objective Optimization

### Current State
Weighted combination and lexicographic objectives implemented.

### Limitations
- Weighted sum can miss parts of Pareto front
- No automatic Pareto frontier generation
- Weight selection is manual

### Future Work
- Implement epsilon-constraint method
- Add Pareto frontier visualization
- Support for decision-maker preference elicitation

---

## 12. Testing Coverage

### Current State
81 tests passing across all modules.

### Gaps
- No integration tests for full pipeline
- No OSRM-dependent tests (requires Docker)
- No benchmark regression tests
- No UI tests for Streamlit

### Future Work
- Add GitHub Actions CI with OSRM mock
- Add benchmark regression tests
- Add property-based testing for validators

---

## Summary of Priority Future Work

| Priority | Item | Phase |
|----------|------|-------|
| High | Complete Streamlit Dashboard | 10 |
| High | Benchmarking & Evaluation module | 8 |
| High | Scenario Generation | 9 |
| High | Reproducibility scripts | 12 |
| Medium | Complete Documentation | 13 |
| Medium | Heterogeneous fleet integration | 5/6 |
| Low | Real ETA model (when data available) | 7 |
| Low | Traffic-aware routing | 4 |
| Low | Pareto frontier tools | 6 |