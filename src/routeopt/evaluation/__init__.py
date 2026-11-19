"""Evaluation and benchmarking module."""

from .metrics import (
    SolutionMetrics,
    compute_metrics,
    compute_optimality_gap,
    compare_solutions_lexicographic,
    wilcoxon_signed_rank_test,
    paired_t_test,
    summarize_benchmark_results,
)

from .route_validator import (
    RouteValidationResult,
    SolutionValidationResult,
    validate_route,
    validate_solution,
    validate_solution_simple,
)

from .benchmark import (
    BenchmarkResult,
    BenchmarkRunner,
    run_standard_benchmarks,
)

__all__ = [
    # Metrics
    "SolutionMetrics",
    "compute_metrics",
    "compute_optimality_gap",
    "compare_solutions_lexicographic",
    "wilcoxon_signed_rank_test",
    "paired_t_test",
    "summarize_benchmark_results",
    # Route Validator
    "RouteValidationResult",
    "SolutionValidationResult",
    "validate_route",
    "validate_solution",
    "validate_solution_simple",
    # Benchmark
    "BenchmarkResult",
    "BenchmarkRunner",
    "run_standard_benchmarks",
]