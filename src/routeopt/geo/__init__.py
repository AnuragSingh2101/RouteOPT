"""Geospatial processing module."""

from .coordinates import (
    Coordinate,
    haversine_distance,
    haversine_distance_meters,
    euclidean_distance,
    euclidean_distance_rounded,
    project_wgs84_to_web_mercator,
    project_web_mercator_to_wgs84,
    build_coordinate_array,
    compute_bounding_box,
)

from .distance_matrix import (
    DistanceMatrixCache,
    compute_distance_matrix,
    compute_osrm_matrix,
    get_distance_matrix,
    validate_distance_matrix,
    DistanceMethod,
)

from .road_network import (
    download_road_network,
    download_road_network_bbox,
    snap_points_to_network,
    compute_network_distance_matrix,
    get_route_geometry,
    sample_customer_locations,
    estimate_travel_time_from_distance,
    OSRMClient,
    build_osrm_matrix_chunked,
)

__all__ = [
    # Coordinates
    "Coordinate",
    "haversine_distance",
    "haversine_distance_meters",
    "euclidean_distance",
    "euclidean_distance_rounded",
    "project_wgs84_to_web_mercator",
    "project_web_mercator_to_wgs84",
    "build_coordinate_array",
    "compute_bounding_box",
    # Distance Matrix
    "DistanceMatrixCache",
    "compute_distance_matrix",
    "compute_osrm_matrix",
    "get_distance_matrix",
    "validate_distance_matrix",
    "DistanceMethod",
    # Road Network
    "download_road_network",
    "download_road_network_bbox",
    "snap_points_to_network",
    "compute_network_distance_matrix",
    "get_route_geometry",
    "sample_customer_locations",
    "estimate_travel_time_from_distance",
    "OSRMClient",
    "build_osrm_matrix_chunked",
]