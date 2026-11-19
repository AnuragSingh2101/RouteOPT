"""Baseline routing algorithms module."""

from .nearest_neighbor import nearest_neighbor, nearest_neighbor_parallel
from .savings import clarke_wright_savings, clarke_wright_savings_time_windows
from .local_search import (
    local_search,
    solve_with_local_search,
    two_opt,
    relocate_moves,
    swap_moves,
    compute_route_distance,
    compute_route_load,
    check_route_feasible,
)

__all__ = [
    "nearest_neighbor",
    "nearest_neighbor_parallel",
    "clarke_wright_savings",
    "clarke_wright_savings_time_windows",
    "local_search",
    "solve_with_local_search",
    "two_opt",
    "relocate_moves",
    "swap_moves",
    "compute_route_distance",
    "compute_route_load",
    "check_route_feasible",
]