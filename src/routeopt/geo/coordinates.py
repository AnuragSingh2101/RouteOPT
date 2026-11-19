"""Coordinate handling and transformations for RouteOpt."""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class Coordinate:
    """A geographic or planar coordinate."""
    x: float
    y: float
    lat: Optional[float] = None
    lon: Optional[float] = None

    @property
    def is_geographic(self) -> bool:
        return self.lat is not None and self.lon is not None


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float,
    radius_km: float = 6371.0088
) -> float:
    """
    Calculate Haversine distance between two WGS84 coordinates.

    Args:
        lat1, lon1: First point latitude/longitude in degrees
        lat2, lon2: Second point latitude/longitude in degrees
        radius_km: Earth radius in km (default: WGS84 mean radius)

    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)

    # Haversine formula
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(min(1, math.sqrt(a)))

    return radius_km * c


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters."""
    return haversine_distance(lat1, lon1, lat2, lon2) * 1000


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Exact Euclidean distance."""
    return math.hypot(x1 - x2, y1 - y2)


def euclidean_distance_rounded(x1: float, y1: float, x2: float, y2: float) -> int:
    """Euclidean distance rounded to nearest integer (CVRPLIB convention)."""
    return int(round(math.hypot(x1 - x2, y1 - y2)))


def project_wgs84_to_web_mercator(lat: float, lon: float) -> tuple[float, float]:
    """
    Project WGS84 (lat/lon) to Web Mercator (EPSG:3857) in meters.

    This is a simple projection suitable for local areas.
    For precise work, use pyproj.
    """
    # Web Mercator projection
    x = lon * 20037508.34 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
    y = y * 20037508.34 / 180
    return x, y


def project_web_mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Inverse Web Mercator projection."""
    lon = x * 180 / 20037508.34
    lat = 180 / math.pi * (2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon


def build_coordinate_array(
    coords: list[Coordinate],
    use_geographic: bool = False
) -> np.ndarray:
    """
    Build coordinate array for distance matrix computation.

    Args:
        coords: List of Coordinate objects
        use_geographic: If True, use (lon, lat) for geographic; else (x, y)

    Returns:
        Array of shape (n, 2)
    """
    if use_geographic:
        return np.array([[c.lon or c.x, c.lat or c.y] for c in coords])
    else:
        return np.array([[c.x, c.y] for c in coords])


def compute_bounding_box(coords: list[Coordinate]) -> tuple[float, float, float, float]:
    """Compute bounding box (min_x, min_y, max_x, max_y) of coordinates."""
    xs = [c.x for c in coords]
    ys = [c.y for c in coords]
    return min(xs), min(ys), max(xs), max(ys)