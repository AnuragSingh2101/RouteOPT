"""Benchmark runner for VRP algorithms."""

from __future__ import annotations
import time
import json
from dataclasses import dataclass, asdict
from typing import Optional, Callable
from pathlib import Path
import numpy as np
import pandas as pd

from ..data import load_instance, load_cvrplib_instance, load_solomon_instance
from ..data.schema import Instance
from ..algorithms import (
    nearest_neighbor,
    clarke_wright_savings,
    solve_with_local_search,
)
from ..optimization import (
    solve_cvrp_ortools,
    solve_vrptw_ortools,
    solve_cvrp_exact_mtz,
    ORToolsSolverConfig,
)
from ..evaluation import (
    compute_metrics,
    validate_solution,
    SolutionMetrics,
    SolutionValidationResult,
    compare_solutions_lexicographic,
    wilcoxon_signed_rank_test,
    paired_t_test,
    summarize_benchmark_results,
)


@dataclass
class BenchmarkResult:
    """Result of a single algorithm on a single instance."""
    instance_name: str
    instance_source: str
    num_customers: int
    algorithm: str
    total_distance: float
    total_duration: float
    vehicles_used: int
    capacity_utilization: float
    avg_route_duration: float
    max_route_duration: float
    runtime_seconds: float
    feasible: bool
    status: str
    reference_distance: Optional[float] = None
    gap_percent: Optional[float] = None
    gap_vehicles: Optional[int] = None
    validation_errors: int = 0
    validation_warnings: int = 0


class BenchmarkRunner:
    """Run benchmarks across instances and algorithms."""

    def __init__(
        self,
        output_dir: Path = Path("reports"),
        time_limits: Optional[list[int]] = None,
        ortools_strategies: Optional[list[str]] = None,
        ortools_metaheuristics: Optional[list[str]] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.time_limits = time_limits or [10, 30, 60]
        self.ortools_strategies = ortools_strategies or ["PATH_CHEAPEST_ARC", "SAVINGS"]
        self.ortools_metaheuristics = ortools_metaheuristics or ["GUIDED_LOCAL_SEARCH", "TABU_SEARCH"]

        self.results: list[BenchmarkResult] = []

    def run_cvrp_benchmark(
        self,
        instance: Instance,
        distance_matrix: np.ndarray,
        reference_distance: Optional[float] = None,
        reference_vehicles: Optional[int] = None,
    ) -> list[BenchmarkResult]:
        """Run all CVRP algorithms on an instance."""
        results = []

        # 1. Nearest Neighbor
        start = time.time()
        nn_sol = nearest_neighbor(instance, distance_matrix)
        nn_time = time.time() - start
        nn_val = validate_solution(nn_sol, instance, distance_matrix)
        nn_metrics = compute_metrics(nn_sol, instance, distance_matrix, reference_distance=reference_distance)
        results.append(BenchmarkResult(
            instance_name=instance.metadata.name,
            instance_source=instance.metadata.source,
            num_customers=instance.num_customers,
            algorithm="Nearest Neighbor",
            total_distance=nn_sol.total_distance,
            total_duration=nn_sol.total_duration,
            vehicles_used=nn_sol.vehicles_used,
            capacity_utilization=nn_metrics.capacity_utilization,
            avg_route_duration=nn_metrics.avg_route_duration,
            max_route_duration=nn_metrics.max_route_duration,
            runtime_seconds=nn_time,
            feasible=nn_val.overall_feasible,
            status=nn_sol.status,
            reference_distance=reference_distance,
            gap_percent=nn_metrics.gap_percent,
            gap_vehicles=nn_metrics.gap_vehicles,
            validation_errors=len(nn_val.errors),
            validation_warnings=len(nn_val.warnings),
        ))

        # 2. Clarke-Wright Savings
        start = time.time()
        cw_sol = clarke_wright_savings(instance, distance_matrix)
        cw_time = time.time() - start
        cw_val = validate_solution(cw_sol, instance, distance_matrix)
        cw_metrics = compute_metrics(cw_sol, instance, distance_matrix, reference_distance=reference_distance)
        results.append(BenchmarkResult(
            instance_name=instance.metadata.name,
            instance_source=instance.metadata.source,
            num_customers=instance.num_customers,
            algorithm="Clarke-Wright Savings",
            total_distance=cw_sol.total_distance,
            total_duration=cw_sol.total_duration,
            vehicles_used=cw_sol.vehicles_used,
            capacity_utilization=cw_metrics.capacity_utilization,
            avg_route_duration=cw_metrics.avg_route_duration,
            max_route_duration=cw_metrics.max_route_duration,
            runtime_seconds=cw_time,
            feasible=cw_val.overall_feasible,
            status=cw_sol.status,
            reference_distance=reference_distance,
            gap_percent=cw_metrics.gap_percent,
            gap_vehicles=cw_metrics.gap_vehicles,
            validation_errors=len(cw_val.errors),
            validation_warnings=len(cw_val.warnings),
        ))

        # 3. Savings + Local Search
        start = time.time()
        ls_sol = solve_with_local_search(
            instance, distance_matrix,
            initial_heuristic="savings",
        )
        ls_time = time.time() - start
        ls_val = validate_solution(ls_sol, instance, distance_matrix)
        ls_metrics = compute_metrics(ls_sol, instance, distance_matrix, reference_distance=reference_distance)
        results.append(BenchmarkResult(
            instance_name=instance.metadata.name,
            instance_source=instance.metadata.source,
            num_customers=instance.num_customers,
            algorithm="Savings + Local Search",
            total_distance=ls_sol.total_distance,
            total_duration=ls_sol.total_duration,
            vehicles_used=ls_sol.vehicles_used,
            capacity_utilization=ls_metrics.capacity_utilization,
            avg_route_duration=ls_metrics.avg_route_duration,
            max_route_duration=ls_metrics.max_route_duration,
            runtime_seconds=ls_time,
            feasible=ls_val.overall_feasible,
            status=ls_sol.status,
            reference_distance=reference_distance,
            gap_percent=ls_metrics.gap_percent,
            gap_vehicles=ls_metrics.gap_vehicles,
            validation_errors=len(ls_val.errors),
            validation_warnings=len(ls_val.warnings),
        ))

        # 4. OR-Tools with different time limits
        for tl in self.time_limits:
            for strat in self.ortools_strategies:
                for meta in self.ortools_metaheuristics:
                    config = ORToolsSolverConfig(
                        time_limit_seconds=tl,
                        first_solution_strategy=strat,
                        local_search_metaheuristic=meta,
                        scale_factor=1,
                    )
                    start = time.time()
                    ort_sol = solve_cvrp_ortools(
                        instance, distance_matrix,
                        time_limit_seconds=tl,
                        scale_factor=1,
                        strategy=strat,
                        metaheuristic=meta,
                    )
                    ort_time = time.time() - start
                    ort_val = validate_solution(ort_sol, instance, distance_matrix)
                    ort_metrics = compute_metrics(ort_sol, instance, distance_matrix, reference_distance=reference_distance)
                    results.append(BenchmarkResult(
                        instance_name=instance.metadata.name,
                        instance_source=instance.metadata.source,
                        num_customers=instance.num_customers,
                        algorithm=f"OR-Tools ({strat}+{meta}, {tl}s)",
                        total_distance=ort_sol.total_distance,
                        total_duration=ort_sol.total_duration,
                        vehicles_used=ort_sol.vehicles_used,
                        capacity_utilization=ort_metrics.capacity_utilization,
                        avg_route_duration=ort_metrics.avg_route_duration,
                        max_route_duration=ort_metrics.max_route_duration,
                        runtime_seconds=ort_time,
                        feasible=ort_val.overall_feasible,
                        status=ort_sol.status,
                        reference_distance=reference_distance,
                        gap_percent=ort_metrics.gap_percent,
                        gap_vehicles=ort_metrics.gap_vehicles,
                        validation_errors=len(ort_val.errors),
                        validation_warnings=len(ort_val.warnings),
                    ))

        # 5. Exact MILP (only for tiny instances)
        if instance.num_customers <= 12:
            try:
                start = time.time()
                exact_sol = solve_cvrp_exact_mtz(
                    instance, distance_matrix,
                    time_limit_seconds=60,
                    solver="scipy",
                )
                exact_time = time.time() - start
                exact_val = validate_solution(exact_sol, instance, distance_matrix)
                exact_metrics = compute_metrics(exact_sol, instance, distance_matrix, reference_distance=reference_distance)
                results.append(BenchmarkResult(
                    instance_name=instance.metadata.name,
                    instance_source=instance.metadata.source,
                    num_customers=instance.num_customers,
                    algorithm="Exact MILP (MTZ)",
                    total_distance=exact_sol.total_distance,
                    total_duration=exact_sol.total_duration,
                    vehicles_used=exact_sol.vehicles_used,
                    capacity_utilization=exact_metrics.capacity_utilization,
                    avg_route_duration=exact_metrics.avg_route_duration,
                    max_route_duration=exact_metrics.max_route_duration,
                    runtime_seconds=exact_time,
                    feasible=exact_val.overall_feasible,
                    status=exact_sol.status,
                    reference_distance=reference_distance,
                    gap_percent=exact_metrics.gap_percent,
                    gap_vehicles=exact_metrics.gap_vehicles,
                    validation_errors=len(exact_val.errors),
                    validation_warnings=len(exact_val.warnings),
                ))
            except Exception as e:
                print(f"Exact MILP failed for {instance.metadata.name}: {e}")

        self.results.extend(results)
        return results

    def run_vrptw_benchmark(
        self,
        instance: Instance,
        distance_matrix: np.ndarray,
        time_matrix: np.ndarray,
        reference_distance: Optional[float] = None,
        reference_vehicles: Optional[int] = None,
    ) -> list[BenchmarkResult]:
        """Run all VRPTW algorithms on an instance."""
        results = []

        # 1. Nearest Neighbor (with time windows)
        start = time.time()
        nn_sol = nearest_neighbor(instance, distance_matrix, time_matrix, consider_time_windows=True)
        nn_time = time.time() - start
        nn_val = validate_solution(nn_sol, instance, distance_matrix, time_matrix)
        nn_metrics = compute_metrics(nn_sol, instance, distance_matrix, time_matrix,
                                     reference_distance=reference_distance, reference_vehicles=reference_vehicles)
        results.append(BenchmarkResult(
            instance_name=instance.metadata.name,
            instance_source=instance.metadata.source,
            num_customers=instance.num_customers,
            algorithm="Nearest Neighbor (TW)",
            total_distance=nn_sol.total_distance,
            total_duration=nn_sol.total_duration,
            vehicles_used=nn_sol.vehicles_used,
            capacity_utilization=nn_metrics.capacity_utilization,
            avg_route_duration=nn_metrics.avg_route_duration,
            max_route_duration=nn_metrics.max_route_duration,
            runtime_seconds=nn_time,
            feasible=nn_val.overall_feasible,
            status=nn_sol.status,
            reference_distance=reference_distance,
            gap_percent=nn_metrics.gap_percent,
            gap_vehicles=nn_metrics.gap_vehicles,
            validation_errors=len(nn_val.errors),
            validation_warnings=len(nn_val.warnings),
        ))

        # 2. Clarke-Wright Savings (with time windows)
        start = time.time()
        cw_sol = clarke_wright_savings(instance, distance_matrix, time_matrix, consider_time_windows=True)
        cw_time = time.time() - start
        cw_val = validate_solution(cw_sol, instance, distance_matrix, time_matrix)
        cw_metrics = compute_metrics(cw_sol, instance, distance_matrix, time_matrix,
                                     reference_distance=reference_distance, reference_vehicles=reference_vehicles)
        results.append(BenchmarkResult(
            instance_name=instance.metadata.name,
            instance_source=instance.metadata.source,
            num_customers=instance.num_customers,
            algorithm="Clarke-Wright Savings (TW)",
            total_distance=cw_sol.total_distance,
            total_duration=cw_sol.total_duration,
            vehicles_used=cw_sol.vehicles_used,
            capacity_utilization=cw_metrics.capacity_utilization,
            avg_route_duration=cw_metrics.avg_route_duration,
            max_route_duration=cw_metrics.max_route_duration,
            runtime_seconds=cw_time,
            feasible=cw_val.overall_feasible,
            status=cw_sol.status,
            reference_distance=reference_distance,
            gap_percent=cw_metrics.gap_percent,
            gap_vehicles=cw_metrics.gap_vehicles,
            validation_errors=len(cw_val.errors),
            validation_warnings=len(cw_val.warnings),
        ))

        # 3. OR-Tools VRPTW with different time limits
        for tl in self.time_limits:
            for strat in self.ortools_strategies:
                for meta in self.ortools_metaheuristics:
                    start = time.time()
                    ort_sol = solve_vrptw_ortools(
                        instance, distance_matrix, time_matrix,
                        time_limit_seconds=tl,
                        scale_factor=100,
                        strategy=strat,
                        metaheuristic=meta,
                        use_lexicographic=True,
                    )
                    ort_time = time.time() - start
                    ort_val = validate_solution(ort_sol, instance, distance_matrix, time_matrix)
                    ort_metrics = compute_metrics(ort_sol, instance, distance_matrix, time_matrix,
                                                 reference_distance=reference_distance, reference_vehicles=reference_vehicles)
                    results.append(BenchmarkResult(
                        instance_name=instance.metadata.name,
                        instance_source=instance.metadata.source,
                        num_customers=instance.num_customers,
                        algorithm=f"OR-Tools VRPTW ({strat}+{meta}, {tl}s)",
                        total_distance=ort_sol.total_distance,
                        total_duration=ort_sol.total_duration,
                        vehicles_used=ort_sol.vehicles_used,
                        capacity_utilization=ort_metrics.capacity_utilization,
                        avg_route_duration=ort_metrics.avg_route_duration,
                        max_route_duration=ort_metrics.max_route_duration,
                        runtime_seconds=ort_time,
                        feasible=ort_val.overall_feasible,
                        status=ort_sol.status,
                        reference_distance=reference_distance,
                        gap_percent=ort_metrics.gap_percent,
                        gap_vehicles=ort_metrics.gap_vehicles,
                        validation_errors=len(ort_val.errors),
                        validation_warnings=len(ort_val.warnings),
                    ))

        self.results.extend(results)
        return results

    def save_results(self, filename: str = "benchmark_results.json") -> None:
        """Save results to JSON file."""
        output_path = self.output_dir / filename
        data = [asdict(r) for r in self.results]
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    def save_results_csv(self, filename: str = "benchmark_results.csv") -> None:
        """Save results to CSV file."""
        output_path = self.output_dir / filename
        df = pd.DataFrame([asdict(r) for r in self.results])
        df.to_csv(output_path, index=False)

    def generate_report(self, filename: str = "benchmark_results.md") -> str:
        """Generate markdown report with tables and honest results section."""
        output_path = self.output_dir / filename

        df = pd.DataFrame([asdict(r) for r in self.results])

        lines = []
        lines.append("# RouteOpt Benchmark Results\n")
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"Total runs: {len(self.results)}\n")
        lines.append(f"Instances tested: {df['instance_name'].nunique()}\n")
        lines.append(f"Algorithms tested: {df['algorithm'].nunique()}\n\n")

        # Per-instance summary
        lines.append("## Per-Instance Results\n")
        for inst_name in sorted(df['instance_name'].unique()):
            inst_df = df[df['instance_name'] == inst_name]
            lines.append(f"### {inst_name}\n")
            lines.append("| Algorithm | Distance | Duration | Vehicles | Feasible | Gap% | Runtime |\n")
            lines.append("|-----------|----------|----------|----------|----------|------|---------|\n")
            for _, row in inst_df.iterrows():
                gap = f"{row['gap_percent']:.2f}%" if row['gap_percent'] is not None else "N/A"
                lines.append(f"| {row['algorithm']} | {row['total_distance']:.2f} | {row['total_duration']:.2f} | "
                           f"{row['vehicles_used']} | {row['feasible']} | {gap} | {row['runtime_seconds']:.2f}s |\n")
            lines.append("")

        # Algorithm summary
        lines.append("## Algorithm Summary (Feasible Solutions Only)\n")
        feasible_df = df[df['feasible'] == True]
        if len(feasible_df) > 0:
            summary = feasible_df.groupby('algorithm').agg({
                'total_distance': ['mean', 'std'],
                'total_duration': ['mean', 'std'],
                'vehicles_used': ['mean', 'std'],
                'runtime_seconds': ['mean', 'std'],
                'gap_percent': ['mean', 'std'],
            }).round(2)
            lines.append(summary.to_markdown())
            lines.append("")

        # Honest Results Section
        lines.append("## Honest Results\n")
        lines.append("This section highlights cases where simple heuristics matched or beat OR-Tools, ")
        lines.append("and where OR-Tools failed to reach feasibility.\n\n")

        # Compare heuristics vs OR-Tools on same instances
        for inst_name in sorted(df['instance_name'].unique()):
            inst_df = df[df['instance_name'] == inst_name]
            ortools_df = inst_df[inst_df['algorithm'].str.startswith('OR-Tools')]
            heuristic_df = inst_df[~inst_df['algorithm'].str.startswith('OR-Tools') &
                                   ~inst_df['algorithm'].str.startswith('Exact')]

            if len(ortools_df) > 0 and len(heuristic_df) > 0:
                best_ortools = ortools_df[ortools_df['feasible']].nsmallest(1, 'total_distance')
                best_heuristic = heuristic_df[heuristic_df['feasible']].nsmallest(1, 'total_distance')

                if len(best_ortools) > 0 and len(best_heuristic) > 0:
                    ort_dist = best_ortools.iloc[0]['total_distance']
                    heur_dist = best_heuristic.iloc[0]['total_distance']
                    ort_alg = best_ortools.iloc[0]['algorithm']
                    heur_alg = best_heuristic.iloc[0]['algorithm']

                    if heur_dist <= ort_dist + 1e-6:
                        lines.append(f"- **{inst_name}**: Heuristic **{heur_alg}** ({heur_dist:.2f}) "
                                   f"matched or beat OR-Tools **{ort_alg}** ({ort_dist:.2f})\n")

        # OR-Tools failures
        ortools_infeasible = df[df['algorithm'].str.startswith('OR-Tools') & (df['feasible'] == False)]
        if len(ortools_infeasible) > 0:
            lines.append("\n### OR-Tools Feasibility Failures\n")
            for _, row in ortools_infeasible.iterrows():
                lines.append(f"- **{row['instance_name']}**: {row['algorithm']} - {row['status']} "
                           f"(validation errors: {row['validation_errors']})\n")

        lines.append("\n---\n")
        lines.append("*All solutions validated by independent route_validator.py. ")
        lines.append("Labels: 'feasible' = all constraints satisfied, 'best_found' = feasible but not proven optimal, ")
        lines.append("'proven_optimal' = exact MILP with optimality proof.*\n")

        report = "\n".join(lines)
        with open(output_path, 'w') as f:
            f.write(report)

        return report


def run_standard_benchmarks(
    cvrplib_dir: Path = Path("data/raw/benchmark/cvrplib"),
    solomon_dir: Path = Path("data/raw/benchmark/solomon"),
    output_dir: Path = Path("reports"),
) -> BenchmarkRunner:
    """Run standard benchmarks on CVRPLIB and Solomon instances."""
    runner = BenchmarkRunner(output_dir=output_dir)

    # CVRPLIB instances (small ones first)
    cvrp_instances = []
    for vrp_file in sorted(cvrplib_dir.glob("*.vrp")):
        sol_file = vrp_file.with_suffix(".sol")
        if sol_file.exists():
            inst = load_cvrplib_instance(vrp_file, sol_file)
            cvrp_instances.append(inst)

    print(f"Found {len(cvrp_instances)} CVRPLIB instances with solutions")

    # Run CVRP benchmarks (small instances first)
    cvrp_instances.sort(key=lambda x: x.num_customers)
    for inst in cvrp_instances[:5]:  # Limit for testing
        print(f"Running CVRP benchmark on {inst.metadata.name}...")
        runner.run_cvrp_benchmark(
            inst, inst.distance_matrix,
            reference_distance=inst.metadata.reference_value,
        )

    # Solomon instances
    solomon_instances = []
    for txt_file in sorted(solomon_dir.glob("*.txt")):
        inst = load_solomon_instance(txt_file)
        solomon_instances.append(inst)

    print(f"Found {len(solomon_instances)} Solomon instances")

    for inst in solomon_instances[:3]:  # Limit for testing
        print(f"Running VRPTW benchmark on {inst.metadata.name}...")
        runner.run_vrptw_benchmark(
            inst, inst.distance_matrix, inst.distance_matrix,
            reference_distance=inst.metadata.reference_value,
        )

    # Save results
    runner.save_results()
    runner.save_results_csv()
    runner.generate_report()

    return runner