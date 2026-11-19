"""Tests for data loaders and validation."""

import pytest
import numpy as np
from pathlib import Path

from routeopt.data import (
    load_cvrplib_instance,
    load_solomon_instance,
    validate_instance,
    euclidean_distance_rounded,
    euclidean_distance_exact,
    build_distance_matrix,
    Instance,
)


class TestDistanceFunctions:
    """Test distance calculation functions."""

    def test_euclidean_rounded(self):
        # Simple 3-4-5 triangle
        assert euclidean_distance_rounded(0, 0, 3, 4) == 5
        assert euclidean_distance_rounded(0, 0, 1, 1) == 1  # sqrt(2) ≈ 1.414 -> 1
        assert euclidean_distance_rounded(0, 0, 2, 2) == 3  # sqrt(8) ≈ 2.828 -> 3

    def test_euclidean_exact(self):
        assert abs(euclidean_distance_exact(0, 0, 3, 4) - 5.0) < 1e-9
        assert abs(euclidean_distance_exact(0, 0, 1, 1) - 1.41421356237) < 1e-9

    def test_build_distance_matrix(self):
        coords = [(0, 0), (3, 4), (6, 8)]
        matrix = build_distance_matrix(coords, "euclidean_rounded")
        assert matrix.shape == (3, 3)
        assert matrix[0, 1] == 5
        assert matrix[0, 2] == 10
        assert matrix[1, 2] == 5
        # Symmetric
        assert np.allclose(matrix, matrix.T)
        # Diagonal zeros
        assert np.all(np.diag(matrix) == 0)


class TestCVRPLIBLoader:
    """Test CVRPLIB instance loading."""

    @pytest.fixture
    def cvrplib_instance(self) -> Instance:
        path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
        sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
        return load_cvrplib_instance(path, sol_path)

    def test_instance_loaded(self, cvrplib_instance: Instance):
        assert cvrplib_instance is not None
        assert cvrplib_instance.metadata.name == "A-n32-k5"
        assert cvrplib_instance.metadata.source == "CVRPLIB"

    def test_depot_and_customers(self, cvrplib_instance: Instance):
        assert cvrplib_instance.depot.depot_id == "1"
        assert cvrplib_instance.num_customers == 31
        assert cvrplib_instance.num_nodes == 32

    def test_distance_matrix(self, cvrplib_instance: Instance):
        matrix = cvrplib_instance.distance_matrix
        assert matrix is not None
        assert matrix.shape == (32, 32)
        # Depot (0) to customer 2 (index 1)
        # Depot at (82, 76), customer 2 at (96, 44)
        # sqrt(14^2 + 32^2) = sqrt(196 + 1024) = sqrt(1220) ≈ 34.93 -> 35
        assert matrix[0, 1] == 35

    def test_vehicles(self, cvrplib_instance: Instance):
        assert len(cvrplib_instance.vehicles) == 5
        for v in cvrplib_instance.vehicles:
            assert v.capacity == 100

    def test_reference_value(self, cvrplib_instance: Instance):
        assert cvrplib_instance.metadata.reference_value == 784
        assert cvrplib_instance.metadata.reference_proven_optimal is True

    def test_validation_passes(self, cvrplib_instance: Instance):
        report = validate_instance(cvrplib_instance)
        assert report.is_valid, f"Validation failed: {report}"


class TestSolomonLoader:
    """Test Solomon instance loading."""

    @pytest.fixture
    def solomon_instance(self) -> Instance:
        path = Path("data/raw/benchmark/solomon/C101.txt")
        return load_solomon_instance(path)

    def test_instance_loaded(self, solomon_instance: Instance):
        assert solomon_instance is not None
        assert solomon_instance.metadata.name == "C101"
        assert solomon_instance.metadata.source == "Solomon"

    def test_depot_and_customers(self, solomon_instance: Instance):
        assert solomon_instance.depot.depot_id == "0"
        assert solomon_instance.num_customers == 25
        assert solomon_instance.num_nodes == 26

    def test_distance_matrix_exact(self, solomon_instance: Instance):
        matrix = solomon_instance.distance_matrix
        assert matrix is not None
        assert matrix.shape == (26, 26)
        # Depot (40, 50) to customer 1 (25, 85)
        # sqrt(15^2 + 35^2) = sqrt(1450) ≈ 38.0789
        assert abs(matrix[0, 1] - 38.07886552931954) < 1e-9

    def test_time_windows(self, solomon_instance: Instance):
        depot = solomon_instance.depot
        assert depot.earliest_time == 0
        assert depot.latest_time == 1236

        cust1 = solomon_instance.customers[0]
        assert cust1.customer_id == "1"
        assert cust1.earliest_time == 141
        assert cust1.latest_time == 171
        assert cust1.service_time == 10

    def test_objective_definition(self, solomon_instance: Instance):
        assert solomon_instance.metadata.objective_definition == "lexicographic_vehicles_then_distance"

    def test_validation_passes(self, solomon_instance: Instance):
        report = validate_instance(solomon_instance)
        assert report.is_valid, f"Validation failed: {report}"


class TestValidation:
    """Test validation functions."""

    def test_duplicate_customer_ids(self):
        # Create instance with duplicate IDs
        from routeopt.data.schema import InstanceMetadata, Depot, Customer, Vehicle
        metadata = InstanceMetadata(
            name="test", source="Test", coordinate_system="xy_planar",
            distance_convention="euclidean_exact", rounding_rule="none",
            time_unit="distance_units", distance_unit="arbitrary",
            objective_definition="min_distance"
        )
        depot = Depot(depot_id="0", x=0, y=0)
        customers = [
            Customer(customer_id="1", x=1, y=1, demand=10),
            Customer(customer_id="1", x=2, y=2, demand=10),  # Duplicate
        ]
        vehicles = [Vehicle(vehicle_id="V1", capacity=100)]
        instance = Instance(metadata=metadata, depot=depot, customers=customers, vehicles=vehicles)

        report = validate_instance(instance)
        assert not report.is_valid
        assert any("Duplicate customer IDs" in e for e in report.errors)

    def test_negative_demand(self):
        from routeopt.data.schema import InstanceMetadata, Depot, Customer, Vehicle
        metadata = InstanceMetadata(
            name="test", source="Test", coordinate_system="xy_planar",
            distance_convention="euclidean_exact", rounding_rule="none",
            time_unit="distance_units", distance_unit="arbitrary",
            objective_definition="min_distance"
        )
        depot = Depot(depot_id="0", x=0, y=0)
        customers = [Customer(customer_id="1", x=1, y=1, demand=-5)]
        vehicles = [Vehicle(vehicle_id="V1", capacity=100)]
        instance = Instance(metadata=metadata, depot=depot, customers=customers, vehicles=vehicles)

        report = validate_instance(instance)
        assert not report.is_valid
        assert any("negative demand" in e for e in report.errors)

    def test_demand_exceeds_capacity(self):
        from routeopt.data.schema import InstanceMetadata, Depot, Customer, Vehicle
        metadata = InstanceMetadata(
            name="test", source="Test", coordinate_system="xy_planar",
            distance_convention="euclidean_exact", rounding_rule="none",
            time_unit="distance_units", distance_unit="arbitrary",
            objective_definition="min_distance"
        )
        depot = Depot(depot_id="0", x=0, y=0)
        customers = [Customer(customer_id="1", x=1, y=1, demand=150)]
        vehicles = [Vehicle(vehicle_id="V1", capacity=100)]
        instance = Instance(metadata=metadata, depot=depot, customers=customers, vehicles=vehicles)

        report = validate_instance(instance)
        assert not report.is_valid
        assert any("exceeds maximum vehicle capacity" in e for e in report.errors)

    def test_inverted_time_window(self):
        from routeopt.data.schema import InstanceMetadata, Depot, Customer, Vehicle
        metadata = InstanceMetadata(
            name="test", source="Test", coordinate_system="xy_planar",
            distance_convention="euclidean_exact", rounding_rule="none",
            time_unit="distance_units", distance_unit="arbitrary",
            objective_definition="min_distance"
        )
        depot = Depot(depot_id="0", x=0, y=0, earliest_time=100, latest_time=50)
        customers = []
        vehicles = [Vehicle(vehicle_id="V1", capacity=100)]
        instance = Instance(metadata=metadata, depot=depot, customers=customers, vehicles=vehicles)

        report = validate_instance(instance)
        assert not report.is_valid
        assert any("inverted" in e for e in report.errors)

    def test_total_demand_exceeds_fleet(self):
        from routeopt.data.schema import InstanceMetadata, Depot, Customer, Vehicle
        metadata = InstanceMetadata(
            name="test", source="Test", coordinate_system="xy_planar",
            distance_convention="euclidean_exact", rounding_rule="none",
            time_unit="distance_units", distance_unit="arbitrary",
            objective_definition="min_distance"
        )
        depot = Depot(depot_id="0", x=0, y=0)
        customers = [Customer(customer_id=str(i), x=i, y=i, demand=60) for i in range(1, 4)]
        vehicles = [Vehicle(vehicle_id="V1", capacity=100), Vehicle(vehicle_id="V2", capacity=50)]
        instance = Instance(metadata=metadata, depot=depot, customers=customers, vehicles=vehicles)

        report = validate_instance(instance)
        assert not report.is_valid
        assert any("exceeds total fleet capacity" in e for e in report.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])