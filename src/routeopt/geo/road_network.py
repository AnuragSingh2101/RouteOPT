"""Road network processing with OSMnx and OSRM integration."""

from __future__ import annotations
import math
import pickle
from pathlib import Path
from typing import Optional, Literal
import numpy as np
import networkx as nx

try:
    import osmnx as ox
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False

from .coordinates import haversine_distance_meters


def download_road_network(
    place_name: str,
    network_type: Literal["drive", "walk", "bike", "all"] = "drive",
    cache_dir: Optional[Path] = None,
) -> nx.MultiDiGraph:
    """
    Download road network from OpenStreetMap using OSMnx.

    Args:
        place_name: Place name (e.g., "San Francisco, California, USA")
        network_type: Type of network to download
        cache_dir: Optional directory to cache the graph

    Returns:
        NetworkX MultiDiGraph with road network
    """
    if not OSMNX_AVAILABLE:
        raise ImportError("osmnx not installed. Install with: pip install osmnx")

    if cache_dir:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{place_name.replace(', ', '_').replace(' ', '_')}_{network_type}.graphml"
        if cache_file.exists():
            return ox.load_graphml(cache_file)

    graph = ox.graph_from_place(place_name, network_type=network_type, simplify=True)

    if cache_dir:
        ox.save_graphml(graph, cache_file)

    return graph


def download_road_network_bbox(
    north: float, south: float, east: float, west: float,
    network_type: Literal["drive", "walk", "bike", "all"] = "drive",
    cache_dir: Optional[Path] = None,
) -> nx.MultiDiGraph:
    """Download road network for a bounding box."""
    if not OSMNX_AVAILABLE:
        raise ImportError("osmnx not installed. Install with: pip install osmnx")

    if cache_dir:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"bbox_{north}_{south}_{east}_{west}_{network_type}.graphml"
        if cache_file.exists():
            return ox.load_graphml(cache_file)

    graph = ox.graph_from_bbox(north, south, east, west, network_type=network_type, simplify=True)

    if cache_dir:
        ox.save_graphml(graph, cache_file)

    return graph


def snap_points_to_network(
    graph: nx.MultiDiGraph,
    points: list[tuple[float, float]],  # (lat, lon)
) -> list[int]:
    """
    Snap GPS points to nearest network nodes.

    Args:
        graph: OSMnx road network graph
        points: List of (lat, lon) tuples

    Returns:
        List of nearest node IDs
    """
    if not OSMNX_AVAILABLE:
        raise ImportError("osmnx not installed")

    # OSMnx uses (lat, lon) for points
    node_ids = ox.distance.nearest_nodes(graph, [p[1] for p in points], [p[0] for p in points])
    return node_ids.tolist()


def compute_network_distance_matrix(
    graph: nx.MultiDiGraph,
    node_ids: list[int],
    weight: str = "length",
) -> np.ndarray:
    """
    Compute shortest path distances between nodes on the network.

    Args:
        graph: OSMnx road network graph
        node_ids: List of node IDs to compute distances between
        weight: Edge weight attribute ("length" for distance, "travel_time" for time)

    Returns:
        Distance matrix of shape (n, n)
    """
    n = len(node_ids)
    matrix = np.full((n, n), np.inf)

    # Compute all-pairs shortest paths for the subset of nodes
    # Use Dijkstra from each source node
    for i, source in enumerate(node_ids):
        try:
            lengths = nx.single_source_dijkstra_path_length(graph, source, weight=weight)
            for j, target in enumerate(node_ids):
                if target in lengths:
                    matrix[i, j] = lengths[target]
                elif i == j:
                    matrix[i, j] = 0
        except nx.NetworkXNoPath:
            # No path from source to any target
            matrix[i, i] = 0

    # Replace inf with NaN for unreachable pairs
    matrix[matrix == np.inf] = np.nan

    return matrix


def get_route_geometry(
    graph: nx.MultiDiGraph,
    source_node: int,
    target_node: int,
    weight: str = "length",
) -> Optional[list[tuple[float, float]]]:
    """
    Get route geometry as list of (lon, lat) coordinates.

    Returns:
        List of (lon, lat) coordinates for the route, or None if no path
    """
    try:
        path = nx.shortest_path(graph, source_node, target_node, weight=weight)
        # Extract geometry from edges
        coords = []
        for u, v in zip(path[:-1], path[1:]):
            edge_data = graph.get_edge_data(u, v)
            if edge_data:
                # MultiDiGraph - get first edge
                edge = next(iter(edge_data.values()))
                if "geometry" in edge:
                    # Geometry is a LineString
                    geom = edge["geometry"]
                    coords.extend(list(geom.coords))
                else:
                    # Straight line between nodes
                    u_data = graph.nodes[u]
                    v_data = graph.nodes[v]
                    coords.append((u_data["x"], u_data["y"]))
                    coords.append((v_data["x"], v_data["y"]))
        return coords
    except nx.NetworkXNoPath:
        return None


def sample_customer_locations(
    graph: nx.MultiDiGraph,
    n_customers: int,
    depot_coord: Optional[tuple[float, float]] = None,
    seed: int = 42,
) -> list[tuple[float, float]]:
    """
    Sample random customer locations from the road network.

    Args:
        graph: OSMnx road network graph
        n_customers: Number of customers to sample
        depot_coord: Optional (lat, lon) for depot - customers sampled nearby
        seed: Random seed

    Returns:
        List of (lat, lon) tuples for customer locations
    """
    import random
    random.seed(seed)
    np.random.seed(seed)

    nodes = list(graph.nodes())
    node_coords = [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in nodes]  # (lat, lon)

    if depot_coord:
        # Sample within radius of depot
        depot_lat, depot_lon = depot_coord
        # Filter nodes within ~10km
        nearby_nodes = []
        nearby_coords = []
        for node, (lat, lon) in zip(nodes, node_coords):
            dist = haversine_distance_meters(depot_lat, depot_lon, lat, lon)
            if dist <= 10000:  # 10 km
                nearby_nodes.append(node)
                nearby_coords.append((lat, lon))

        if len(nearby_nodes) < n_customers:
            # Fall back to all nodes
            sampled_indices = random.sample(range(len(nodes)), n_customers)
            return [node_coords[i] for i in sampled_indices]

        sampled_indices = random.sample(range(len(nearby_nodes)), n_customers)
        return [nearby_coords[i] for i in sampled_indices]
    else:
        # Sample from all nodes
        sampled_indices = random.sample(range(len(nodes)), n_customers)
        return [node_coords[i] for i in sampled_indices]


def estimate_travel_time_from_distance(
    distance_meters: float,
    speed_kmh: float = 30.0,
) -> float:
    """
    Estimate travel time from distance assuming constant speed.

    Args:
        distance_meters: Distance in meters
        speed_kmh: Average speed in km/h

    Returns:
        Travel time in seconds
    """
    speed_ms = speed_kmh * 1000 / 3600
    return distance_meters / speed_ms


class OSRMClient:
    """Client for interacting with local OSRM server."""

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        profile: str = "driving",
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.profile = profile
        self.timeout = timeout
        self._session = None

    @property
    def session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def table(
        self,
        coordinates: list[tuple[float, float]],  # (lon, lat)
        sources: Optional[list[int]] = None,
        destinations: Optional[list[int]] = None,
        annotations: str = "distance,duration",
    ) -> dict:
        """Request distance/duration table from OSRM."""
        coord_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
        url = f"{self.base_url}/table/v1/{self.profile}/{coord_str}"

        params = {"annotations": annotations}
        if sources is not None:
            params["sources"] = ";".join(str(s) for s in sources)
        if destinations is not None:
            params["destinations"] = ";".join(str(d) for d in destinations)

        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def route(
        self,
        coordinates: list[tuple[float, float]],  # (lon, lat)
        steps: bool = True,
        geometries: str = "geojson",
        overview: str = "full",
    ) -> dict:
        """Request route geometry from OSRM."""
        coord_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
        url = f"{self.base_url}/route/v1/{self.profile}/{coord_str}"

        params = {
            "steps": "true" if steps else "false",
            "geometries": geometries,
            "overview": overview,
        }

        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def nearest(
        self,
        coordinates: list[tuple[float, float]],  # (lon, lat)
        number: int = 1,
    ) -> dict:
        """Snap coordinates to road network."""
        coord_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
        url = f"{self.base_url}/nearest/v1/{self.profile}/{coord_str}"

        params = {"number": number}
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def health_check(self) -> bool:
        """Check if OSRM server is running."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


def build_osrm_matrix_chunked(
    client: OSRMClient,
    coordinates: list[tuple[float, float]],
    chunk_size: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build distance and duration matrices using chunked OSRM requests.

    Args:
        client: OSRMClient instance
        coordinates: List of (lon, lat) tuples
        chunk_size: Max coordinates per request

    Returns:
        Tuple of (distance_matrix_meters, duration_matrix_seconds)
    """
    n = len(coordinates)
    distance_matrix = np.full((n, n), np.nan)
    duration_matrix = np.full((n, n), np.nan)

    for i in range(0, n, chunk_size):
        src_indices = list(range(i, min(i + chunk_size, n)))
        src_coords = [coordinates[idx] for idx in src_indices]

        # Request distances from src_indices to all destinations
        result = client.table(
            coordinates,
            sources=src_indices,
            destinations=list(range(n)),
        )

        if result["code"] != "Ok":
            raise RuntimeError(f"OSRM table error: {result.get('message', 'Unknown')}")

        dist_chunk = np.array(result["distances"])
        dur_chunk = np.array(result["durations"])

        for row_idx, src in enumerate(src_indices):
            distance_matrix[src, :] = dist_chunk[row_idx]
            duration_matrix[src, :] = dur_chunk[row_idx]

    return distance_matrix, duration_matrix