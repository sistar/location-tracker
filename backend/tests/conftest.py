"""Shared pytest configuration and fixtures for all tests."""

import pytest
import boto3
from moto import mock_aws
from decimal import Decimal


@pytest.fixture
def mock_dynamodb_tables():
    """Create mock DynamoDB tables for unit testing."""
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create locations table
        locations_table = dynamodb.create_table(
            TableName="gps-tracking-service-dev-locations-v2",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create logs table with GSI
        logs_table = dynamodb.create_table(
            TableName="gps-tracking-service-dev-locations-logs-v2",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "N"},
                {"AttributeName": "vehicleId", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "VehicleTimestampIndex",
                    "KeySchema": [
                        {"AttributeName": "vehicleId", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                }
            ],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )

        # Create geocode cache table
        geocode_table = dynamodb.create_table(
            TableName="gps-tracking-service-dev-geocode-cache",
            KeySchema=[{"AttributeName": "query", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "query", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        yield {
            "locations_table": locations_table,
            "logs_table": logs_table,
            "geocode_table": geocode_table,
            "dynamodb": dynamodb,
        }


@pytest.fixture
def sample_location_data():
    """Sample location data for testing."""
    return {
        "id": "vehicle_01",
        "timestamp": 1681430400,
        "lat": Decimal("52.5200"),
        "lon": Decimal("13.4050"),
        "ele": Decimal("100.5"),
        "cog": Decimal("45.0"),
        "sog": Decimal("50.0"),
        "quality": 1,
        "satellites_used": 8,
    }


@pytest.fixture
def sample_log_entry():
    """Sample log entry for testing."""
    return {
        "id": "test-session-001",
        "timestamp": 1681430400,
        "vehicleId": "vehicle_01",
        "startTime": "2023-04-14T12:00:00",
        "endTime": "2023-04-14T13:00:00",
        "distance": Decimal("25.5"),
        "duration": 3600,
        "purpose": "Business",
        "notes": "Test trip",
        "startAddress": "Berlin, Germany",
        "endAddress": "Hamburg, Germany",
    }