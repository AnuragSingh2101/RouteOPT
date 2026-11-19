"""CLI entry point for RouteOpt."""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="routeopt",
        description="RouteOpt: Last-Mile Delivery Route Optimization CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run benchmark suite")
    bench_parser.add_argument(
        "--cvrplib-dir",
        type=Path,
        default=Path("data/raw/benchmark/cvrplib"),
        help="Path to CVRPLIB instances directory"
    )
    bench_parser.add_argument(
        "--solomon-dir",
        type=Path,
        default=Path("data/raw/benchmark/solomon"),
        help="Path to Solomon instances directory"
    )
    bench_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Directory to save benchmark reports"
    )

    args = parser.parse_args()

    if args.command == "benchmark":
        from routeopt.evaluation.benchmark import run_standard_benchmarks
        print("Starting RouteOpt Benchmark Suite...")
        runner = run_standard_benchmarks(
            cvrplib_dir=args.cvrplib_dir,
            solomon_dir=args.solomon_dir,
            output_dir=args.output_dir
        )
        print(f"Benchmarks completed! Results saved to {args.output_dir}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
