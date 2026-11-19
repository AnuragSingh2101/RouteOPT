"""Distance matrix computation and caching for RouteOpt."""

from __future__ import annotations
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Optional, Literal
import numpy as np
import requests

from .coordinates import (
    haversine_distance_meters,
    euclidean_distance,
    euclidean_distance_rounded,
    build_coordinate_array,
)

DistanceMethod = Literal["euclidean_rounded", "euclidean_exact", "haversine", "osrm"]


class DistanceMatrixCache:
    """Cache for distance matrices keyed by coordinates + method + profile."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, coords: np.ndarray, method: str, profile: str = "driving") -> str:
        """Create cache key from coordinates, method, and profile."""
        # Round coordinates to 6 decimal places for stable hashing
        coord_str = json.dumps(coords.round(6).tolist(), sort_keys=True)
        content = f"{coord_str}|{method}|{profile}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.npz"

    def _meta_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.meta.json"

    def get(self, coords: np.ndarray, method: str, profile: str = "driving") -> Optional[np.ndarray]:
        """Retrieve cached matrix if exists."""
        key = self._make_key(coords, method, profile)
        cache_file = self._cache_path(key)
        if cache_file.exists():
            try:
                data = np.load(cache_file)
                matrix = data["matrix"]
                # Verify shape matches
                if matrix.shape == (len(coords), len(coords)):
                    return matrix
            except Exception:
                pass
        return None

    def set(self, coords: np.ndarray, method: str, matrix: np.ndarray, profile: str = "driving") -> None:
        """Store matrix in cache."""
        key = self._make_key(coords, method, profile)
        cache_file = self._cache_path(key)
        meta_file = self._meta_path(key)

        np.savez_compressed(cache_file, matrix=matrix)

        meta = {
            "key": key,
            "method": method,
            "profile": profile,
            "n_points": len(coords),
            "shape": list(matrix.shape),
            "created": time.time(),
        }
        with open(meta_file, "w") as f:
            json.dump(meta, f)

    def has(self, coords: np.ndarray, method: str, profile: str = "driving") -> bool:
        """Check if matrix is cached."""
        key = self._make_key(coords, method, profile)
        return self._cache_path(key).exists()


def compute_distance_matrix(
    coords: np.ndarray,
    method: DistanceMethod = "euclidean_exact",
    scale_factor: float = 1.0,
) -> np.ndarray:
    """
    Compute distance matrix from coordinates.

    Args:
        coords: Array of shape (n, 2) with (x, y) or (lon, lat)
        method: Distance computation method
        scale_factor: Multiply distances by this factor (for OR-Tools integer API)

    Returns:
        Distance matrix of shape (n, n)
    """
    n = len(coords)
    matrix = np.zeros((n, n), dtype=float)

    if method == "euclidean_rounded":
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i, j] = euclidean_distance_rounded(
                        coords[i, 0], coords[i, 1], coords[j, 0], coords[j, 1]
                    ) * scale_factor

    elif method == "euclidean_exact":
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i, j] = euclidean_distance(
                        coords[i, 0], coords[i, 1], coords[j, 0], coords[j, 1]
                    ) * scale_factor

    elif method == "haversine":
        # coords are (lon, lat)
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i, j] = haversine_distance_meters(
                        coords[i, 1], coords[i, 0],  # lat, lon
                        coords[j, 1], coords[j, 0]
                    ) * scale_factor

    elif method == "osrm":
        # Will be filled by OSRM caller
        raise NotImplementedError("OSRM matrix requires network call - use compute_osrm_matrix")

    else:
        raise ValueError(f"Unknown method: {method}")

    return matrix


def compute_osrm_matrix(
    coords: np.ndarray,
    osrm_url: str = "http://localhost:5000",
    profile: str = "driving",
    chunk_size: int = 100,
    timeout: int = 60,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute distance and duration matrices using OSRM table service.

    Args:
        coords: Array of shape (n, 2) with (lon, lat) in WGS84
        osrm_url: Base URL of OSRM server
        profile: Routing profile (driving, cycling, walking)
        chunk_size: Maximum locations per request (OSRM limit)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (distance_matrix_meters, duration_matrix_seconds)
    """
    n = len(coords)
    distance_matrix = np.full((n, n), np.nan)
    duration_matrix = np.full((n, n), np.nan)

    # OSRM table endpoint: /table/v1/{profile}/{coordinates}
    # coordinates format: lon1,lat1;lon2,lat2;...
    # We need to chunk for large matrices

    def make_request(indices: list[int]) -> tuple[np.ndarray, np.ndarray]:
        """Make OSRM table request for a subset of coordinates."""
        coord_str = ";".join(f"{coords[i, 0]},{coords[i, 1]}" for i in indices)
        url = f"{osrm_url}/table/v1/{profile}/{coord_str}"
        params = {
            "annotations": "distance,duration",
            "sources": ";".join(str(i) for i in range(len(indices))),
            "destinations": ";".join(str(i) for i in range(len(indices))),
        }

        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        if data["code"] != "Ok":
            raise RuntimeError(f"OSRM error: {data.get('message', 'Unknown error')}")

        distances = np.array(data["distances"])  # meters
        durations = np.array(data["durations"])   # seconds

        return distances, durations

    # Process in chunks
    for i in range(0, n, chunk_size):
        chunk_indices = list(range(i, min(i + chunk_size, n)))
        try:
            dist_chunk, dur_chunk = make_request(chunk_indices)
            # Fill the corresponding block in the full matrix
            for row_idx, src in enumerate(chunk_indices):
                for col_idx, dst in enumerate(chunk_indices):
                    distance_matrix[src, dst] = dist_chunk[row_idx, col_idx]
                    duration_matrix[src, dst] = dur_chunk[row_idx, col_idx]
        except Exception as e:
            raise RuntimeError(f"OSRM request failed for chunk {chunk_indices}: {e}")

    # Check for unreachable pairs (NaN)
    unreachable = np.isnan(distance_matrix)
    if np.any(unreachable):
        # Don't silently replace - let caller handle
        pass

    return distance_matrix, duration_matrix


def get_distance_matrix(
    coords: np.ndarray,
    method: DistanceMethod = "euclidean_exact",
    cache: Optional[DistanceMatrixCache] = None,
    osrm_url: str = "http://localhost:5000",
    osrm_profile: str = "driving",
    scale_factor: float = 1.0,
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Get distance matrix with caching support.

    Args:
        coords: Coordinates array (n, 2)
        method: Distance computation method
        cache: Optional cache instance
        osrm_url: OSRM server URL (for OSRM method)
        osrm_profile: OSRM profile
        scale_factor: Scaling factor for integer API

    Returns:
        Tuple of (distance_matrix, time_matrix_or_None)
    """
    # Try cache first
    if cache is not None:
        cached = cache.get(coords, method, osrm_profile)
        if cached is not None:
            return cached, None  # Time matrix not cached separately

    if method == "osrm":
        dist_matrix, time_matrix = compute_osrm_matrix(
            coords, osrm_url, osrm_profile
        )
        dist_matrix = dist_matrix * scale_factor
        time_matrix = time_matrix * scale_factor
    else:
        dist_matrix = compute_distance_matrix(coords, method, scale_factor)
        time_matrix = dist_matrix.copy()  # For Euclidean, time = distance

    # Cache the result
    if cache is not None:
        cache.set(coords, method, dist_matrix, osrm_profile)

    return dist_matrix, time_matrix


def validate_distance_matrix(matrix: np.ndarray, method: str) -> list[str]:
    """
    Validate distance matrix properties.

    Returns:
        List of warning/error messages (empty if valid)
    """
    issues = []
    n = matrix.shape[0]

    if matrix.shape != (n, n):
        issues.append(f"Matrix not square: {matrix.shape}")

    # Check diagonal
    diag = np.diag(matrix)
    if not np.allclose(diag, 0):
        issues.append(f"Non-zero diagonal: {diag[diag != 0]}")

    # Check for negative distances
    if np.any(matrix < 0):
        neg_count = np.sum(matrix < 0)
        issues.append(f"Negative distances found: {neg_count} entries")

    # Check for NaN
    if np.any(np.isnan(matrix)):
        nan_count = np.sum(np.isnan(matrix))
        issues.append(f"NaN distances found: {nan_count} entries")

    # Check symmetry for Euclidean/Haversine
    if method in ("euclidean_rounded", "euclidean_exact", "haversine"):
        diff = np.abs(matrix - matrix.T)
        max_diff = np.max(diff)
        if max_diff > 1e-9:
            issues.append(f"Matrix not symmetric (max diff: {max_diff})")

    return issues