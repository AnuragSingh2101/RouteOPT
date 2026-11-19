"""Tests for geospatial processing."""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from routeopt.geo import (
    haversine_distance_meters,
    euclidean_distance,
    euclidean_distance_rounded,
    DistanceMatrixCache,
    compute_distance_matrix,
    get_distance_matrix,
    validate_distance_matrix,
)


class TestCoordinates:
    """Test coordinate distance functions."""

    def test_haversine_known_distance(self):
        # New York to Los Angeles (approximate)
        # NYC: 40.7128° N, 74.0060° W
        # LA: 34.0522° N, 118.2437° W
        dist = haversine_distance_meters(40.7128, -74.0060, 34.0522, -118.2437)
        # Expected ~3940 km
        assert 3900000 < dist < 4000000

    def test_haversine_same_point(self):
        dist = haversine_distance_meters(40.7128, -74.0060, 40.7128, -74.0060)
        assert dist == 0

    def test_haversine_symmetry(self):
        d1 = haversine_distance_meters(40.7128, -74.0060, 34.0522, -118.2437)
        d2 = haversine_distance_meters(34.0522, -118.2437, 40.7128, -74.0060)
        assert abs(d1 - d2) < 1e-6

    def test_euclidean_exact(self):
        assert abs(euclidean_distance(0, 0, 3, 4) - 5.0) < 1e-9
        assert abs(euclidean_distance(1, 1, 4, 5) - 5.0) < 1e-9

    def test_euclidean_rounded(self):
        assert euclidean_distance_rounded(0, 0, 3, 4) == 5
        assert euclidean_distance_rounded(0, 0, 1, 1) == 1  # sqrt(2) ≈ 1.414
        assert euclidean_distance_rounded(0, 0, 2, 2) == 3  # sqrt(8) ≈ 2.828


class TestDistanceMatrix:
    """Test distance matrix computation."""

    def test_euclidean_exact_matrix(self):
        coords = np.array([[0, 0], [3, 4], [6, 8]])
        matrix = compute_distance_matrix(coords, "euclidean_exact")

        assert matrix.shape == (3, 3)
        assert matrix[0, 0] == 0
        assert matrix[0, 1] == 5
        assert matrix[0, 2] == 10
        assert matrix[1, 2] == 5
        assert np.allclose(matrix, matrix.T)  # Symmetric

    def test_euclidean_rounded_matrix(self):
        coords = np.array([[0, 0], [1, 1], [2, 2]])
        matrix = compute_distance_matrix(coords, "euclidean_rounded")

        assert matrix[0, 1] == 1  # sqrt(2) -> 1
        assert matrix[0, 2] == 3  # sqrt(8) -> 3
        assert matrix[1, 2] == 1  # sqrt(2) -> 1

    def test_haversine_matrix(self):
        # NYC, LA, Chicago
        coords = np.array([
            [-74.0060, 40.7128],   # NYC (lon, lat)
            [-118.2437, 34.0522],  # LA
            [-87.6298, 41.8781],   # Chicago
        ])
        matrix = compute_distance_matrix(coords, "haversine")

        assert matrix.shape == (3, 3)
        assert matrix[0, 0] == 0
        # NYC to LA ~3940 km
        assert 3900000 < matrix[0, 1] < 4000000
        assert np.allclose(matrix, matrix.T)

    def test_scale_factor(self):
        coords = np.array([[0, 0], [3, 4]])
        matrix = compute_distance_matrix(coords, "euclidean_exact", scale_factor=100)
        assert matrix[0, 1] == 500  # 5 * 100

    def test_get_distance_matrix_with_cache(self):
        # Use project cache directory instead of temp
        cache_dir = Path("data/cache/test_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = DistanceMatrixCache(cache_dir)
        coords = np.array([[0, 0], [3, 4], [6, 8]])

        # First call - computes and caches
        matrix1, _ = get_distance_matrix(coords, "euclidean_exact", cache=cache)
        assert matrix1[0, 1] == 5

        # Second call - uses cache
        matrix2, _ = get_distance_matrix(coords, "euclidean_exact", cache=cache)
        assert np.allclose(matrix1, matrix2)

        # Clean up
        import shutil
        shutil.rmtree(cache_dir, ignore_errors=True)

    def test_validate_distance_matrix(self):
        # Valid matrix
        matrix = np.array([[0, 5, 10], [5, 0, 5], [10, 5, 0]])
        issues = validate_distance_matrix(matrix, "euclidean_exact")
        assert len(issues) == 0

        # Non-zero diagonal
        matrix_bad = np.array([[1, 5], [5, 0]])
        issues = validate_distance_matrix(matrix_bad, "euclidean_exact")
        assert any("diagonal" in i for i in issues)

        # Negative distances
        matrix_bad = np.array([[0, -5], [-5, 0]])
        issues = validate_distance_matrix(matrix_bad, "euclidean_exact")
        assert any("Negative" in i for i in issues)

        # NaN
        matrix_bad = np.array([[0, np.nan], [np.nan, 0]])
        issues = validate_distance_matrix(matrix_bad, "euclidean_exact")
        assert any("NaN" in i for i in issues)

        # Asymmetric
        matrix_bad = np.array([[0, 5], [6, 0]])
        issues = validate_distance_matrix(matrix_bad, "euclidean_exact")
        assert any("symmetric" in i for i in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])