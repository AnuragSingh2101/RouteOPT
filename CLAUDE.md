# RouteOpt - Standing Rules (Phase 0)

These rules are copied from the Master Implementation Prompt Section 2 and must be obeyed in every phase.

## Core Principles

**No fabrication.** Never invent benchmark scores, optimality claims, traffic data, delivery records, ETA predictions, or improvement figures. Report only numbers produced by runs you executed.

**Never claim a solution is optimal unless it is proven.** Label every solution as one of: feasible, best-found, or proven optimal. Proven optimal is allowed only when the exact MILP finishes with an optimality proof, or when the benchmark library itself marks the reference as optimal (and then only for that reference).

**Compare only like with like.** Two results are comparable only if they share the same instance, distance convention, rounding rule, and objective definition. Record these four things with every result.

**Never apply Haversine to x/y benchmark coordinates.** Never mix Haversine and road-network values in one comparison. Never silently fall back from road distances to Haversine; if a fallback happens, label it in the output and the UI.

**Independent validation.** Every solution from every algorithm must pass route_validator.py, which recomputes cost, load, and timing from the raw instance data without using solver internals. A solver returning a route proves nothing.

**Keep two evaluation modes apart:** benchmark evaluation (CVRPLIB, Solomon) and city demonstration (OSM geography, synthetic orders). Never merge their results into one table. Label generated orders as synthetic everywhere.

**Evidence before assumptions.** Inspect file formats, conventions, and documentation before writing parsers or comparing against reference values.

**Windows first.** All commands must work in PowerShell.

**Continuity.** Read docs/IMPLEMENTATION_STATUS.md before starting work if it exists. Update it after every phase. Do not redo finished work or overwrite working files blindly.

**Execute and verify.** Run what you write, read the outputs, run the tests, and fix failures before moving on.

**Stay free and CPU-only.** No paid APIs, no cloud requirement, no GPU algorithms, no unnecessary technologies. The core benchmark pipeline must run offline once the instances are downloaded.