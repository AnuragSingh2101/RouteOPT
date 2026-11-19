"""Metrics computation for VRP solutions."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

from ..data.schema import Instance, Solution, Route


@dataclass
class SolutionMetrics:
    """Comprehensive metrics for a VRP solution."""
    # Basic metrics
    total_distance: float
    total_duration: float
    vehicles_used: int
    
    # Capacity utilization
    total_capacity: float
    used_capacity: float
    capacity_utilization: float  # used / total on active vehicles
    
    # Route-level metrics
    avg_route_distance: float
    max_route_distance: float
    min_route_distance: float
    avg_route_duration: float
    max_route_duration: float
    min_route_duration: float
    avg_route_load: float
    max_route_load: float
    
    # Workload balance
    duration_cv: float  # coefficient of variation of route durations
    distance_cv: float
    load_cv: float
    
    # Feasibility
    feasible: bool
    capacity_violations: int
    time_window_violations: int
    duration_violations: int
    
    # Comparison metrics (when reference available)
    reference_distance: Optional[float] = None
    gap_percent: Optional[float] = None
    gap_vehicles: Optional[int] = None


def compute_metrics(
    solution: Solution,
    instance: Instance,
    distance_matrix: np.ndarray,
    time_matrix: Optional[np.ndarray] = None,
    reference_distance: Optional[float] = None,
    reference_vehicles: Optional[int] = None,
) -> SolutionMetrics:
    """
    Compute comprehensive metrics for a solution.

    Args:
        solution: Solution to evaluate
        instance: Original instance
        distance_matrix: Distance matrix
        time_matrix: Time matrix (optional)
        reference_distance: BKS or reference distance (optional)
        reference_vehicles: Reference vehicle count (optional)

    Returns:
        SolutionMetrics with all computed values
    """
    routes = solution.routes
    n_routes = len(routes)

    if n_routes == 0:
        return SolutionMetrics(
            total_distance=0.0,
            total_duration=0.0,
            vehicles_used=0,
            total_capacity=sum(v.capacity for v in instance.vehicles),
            used_capacity=0.0,
            capacity_utilization=0.0,
            avg_route_distance=0.0,
            max_route_distance=0.0,
            min_route_distance=0.0,
            avg_route_duration=0.0,
            max_route_duration=0.0,
            min_route_duration=0.0,
            avg_route_load=0.0,
            max_route_load=0.0,
            duration_cv=0.0,
            distance_cv=0.0,
            load_cv=0.0,
            feasible=solution.status == "feasible",
            capacity_violations=0,
            time_window_violations=0,
            duration_violations=0,
        )

    # Basic totals
    total_distance = solution.total_distance
    total_duration = solution.total_duration
    vehicles_used = solution.vehicles_used

    # Capacity
    total_capacity = sum(v.capacity for v in instance.vehicles)
    used_capacity = sum(r.load for r in routes)
    active_capacity = sum(
        next(v.capacity for v in instance.vehicles if v.vehicle_id == r.vehicle_id)
        for r in routes
    )
    capacity_utilization = used_capacity / active_capacity if active_capacity > 0 else 0.0

    # Route-level metrics
    route_distances = [r.distance for r in routes]
    route_durations = [r.duration for r in routes]
    route_loads = [r.load for r in routes]

    avg_route_distance = np.mean(route_distances)
    max_route_distance = np.max(route_distances)
    min_route_distance = np.min(route_distances)

    avg_route_duration = np.mean(route_durations)
    max_route_duration = np.max(route_durations)
    min_route_duration = np.min(route_durations)

    avg_route_load = np.mean(route_loads)
    max_route_load = np.max(route_loads)

    # Coefficient of variation (workload balance)
    def cv(values):
        mean = np.mean(values)
        return np.std(values) / mean if mean > 0 else 0.0

    duration_cv = cv(route_durations)
    distance_cv = cv(route_distances)
    load_cv = cv(route_loads)

    # Feasibility checks (use validator for detailed checks)
    feasible = solution.status == "feasible"

    # Reference comparison
    gap_percent = None
    if reference_distance is not None and reference_distance > 0:
        gap_percent = ((total_distance - reference_distance) / reference_distance) * 100

    gap_vehicles = None
    if reference_vehicles is not None:
        gap_vehicles = vehicles_used - reference_vehicles

    return SolutionMetrics(
        total_distance=total_distance,
        total_duration=total_duration,
        vehicles_used=vehicles_used,
        total_capacity=total_capacity,
        used_capacity=used_capacity,
        capacity_utilization=capacity_utilization,
        avg_route_distance=avg_route_distance,
        max_route_distance=max_route_distance,
        min_route_distance=min_route_distance,
        avg_route_duration=avg_route_duration,
        max_route_duration=max_route_duration,
        min_route_duration=min_route_duration,
        avg_route_load=avg_route_load,
        max_route_load=max_route_load,
        duration_cv=duration_cv,
        distance_cv=distance_cv,
        load_cv=load_cv,
        feasible=feasible,
        capacity_violations=0,  # Detailed check in validator
        time_window_violations=0,
        duration_violations=0,
        reference_distance=reference_distance,
        gap_percent=gap_percent,
        gap_vehicles=gap_vehicles,
    )


def compute_optimality_gap(
    solution_distance: float,
    reference_distance: float,
) -> float:
    """Compute optimality gap as percentage."""
    if reference_distance <= 0:
        return float('inf')
    return ((solution_distance - reference_distance) / reference_distance) * 100


def compare_solutions_lexicographic(
    sol1: Solution,
    sol2: Solution,
) -> int:
    """
    Compare two solutions lexicographically (vehicles first, then distance).
    Returns: -1 if sol1 better, 1 if sol2 better, 0 if equal.
    """
    if sol1.vehicles_used < sol2.vehicles_used:
        return -1
    elif sol1.vehicles_used > sol2.vehicles_used:
        return 1
    else:
        # Same vehicles, compare distance
        if sol1.total_distance < sol2.total_distance:
            return -1
        elif sol1.total_distance > sol2.total_distance:
            return 1
        return 0


def wilcoxon_signed_rank_test(
    gaps1: list[float],
    gaps2: list[float],
) -> tuple[float, float]:
    """
    Perform Wilcoxon signed-rank test on paired gap differences.

    Returns:
        (statistic, p-value)
    """
    try:
        from scipy.stats import wilcoxon
        stat, pval = wilcoxon(gaps1, gaps2)
        return float(stat), float(pval)
    except ImportError:
        return float('nan'), float('nan')
    except ValueError:
        # Not enough data or all differences zero
        return float('nan'), float('nan')


def paired_t_test(
    gaps1: list[float],
    gaps2: list[float],
) -> tuple[float, float]:
    """
    Perform paired t-test on gap differences.

    Returns:
        (t-statistic, p-value)
    """
    try:
        from scipy.stats import ttest_rel
        stat, pval = ttest_rel(gaps1, gaps2)
        return float(stat), float(pval)
    except ImportError:
        return float('nan'), float('nan')
    except ValueError:
        return float('nan'), float('nan')


def summarize_benchmark_results(
    results: list[dict],
) -> dict:
    """
    Summarize benchmark results across instances and algorithms.

    Args:
        results: List of result dicts with keys:
            instance_name, algorithm, total_distance, vehicles_used,
            reference_distance, gap_percent, status, runtime

    Returns:
        Summary dict with mean/std per algorithm, pairwise comparisons
    """
    import pandas as pd

    df = pd.DataFrame(results)

    # Per-algorithm summary
    summary = {}
    for alg in df['algorithm'].unique():
        alg_df = df[df['algorithm'] == alg]
        feasible = alg_df[alg_df['status'] == 'feasible']

        summary[alg] = {
            'n_instances': len(alg_df),
            'n_feasible': len(feasible),
            'feasibility_rate': len(feasible) / len(alg_df) if len(alg_df) > 0 else 0,
            'mean_distance': feasible['total_distance'].mean() if len(feasible) > 0 else None,
            'std_distance': feasible['total_distance'].std() if len(feasible) > 0 else None,
            'mean_gap_percent': feasible['gap_percent'].mean() if len(feasible) > 0 and 'gap_percent' in feasible.columns else None,
            'std_gap_percent': feasible['gap_percent'].std() if len(feasible) > 0 and 'gap_percent' in feasible.columns else None,
            'mean_vehicles': feasible['vehicles_used'].mean() if len(feasible) > 0 else None,
            'mean_runtime': alg_df['runtime_seconds'].mean() if len(alg_df) > 0 else None,
        }

    return summary