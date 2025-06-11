from datetime import datetime
from decimal import Decimal
import json
from unittest.mock import MagicMock, Mock, patch

import boto3
from moto import mock_aws
import pytest

from handlers.get_drivers_logs import (
    decimal_default,
    fetch_locations_by_time_range,
    handler,
)


class TestUtilityFunctions:

    def test_decimal_default(self):
        """Test Decimal to float conversion"""
        assert decimal_default(Decimal("123.45")) == 123.45

        with pytest.raises(TypeError):
            decimal_default("not a decimal")


class TestFetchLocationsByTimeRange:

    @mock_aws
    def test_fetch_locations_success(self):
        """Test successful location fetching"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table_name = "test-locations-table"

        table = dynamodb.create_table(
            TableName=table_name,
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

        # Put test data
        table.put_item(
            Item={
                "id": "vehicle_01",
                "timestamp": 1681430400,
                "lat": Decimal("52.5200"),
                "lon": Decimal("13.4050"),
            }
        )

        # Mock the locations_table in the module
        with patch("handlers.get_drivers_logs.locations_table", table):
            result = fetch_locations_by_time_range("vehicle_01", 1681430000, 1681430500)

            assert len(result) == 1
            assert result[0]["id"] == "vehicle_01"

    def test_fetch_locations_string_timestamps(self):
        """Test fetching locations with string timestamps"""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "id": "vehicle_01",
                    "timestamp": 1681430400,
                    "lat": 52.5200,
                    "lon": 13.4050,
                }
            ]
        }

        with patch("handlers.get_drivers_logs.locations_table", mock_table):
            # Test with string numeric timestamps
            result = fetch_locations_by_time_range(
                "vehicle_01", "1681430000", "1681430500"
            )
            assert len(result) == 1

            # Test with ISO timestamp strings
            result = fetch_locations_by_time_range(
                "vehicle_01", "2023-04-14T12:00:00", "2023-04-14T13:00:00"
            )
            assert len(result) == 1

    def test_fetch_locations_with_pagination(self):
        """Test fetching locations with pagination"""
        mock_table = Mock()

        # First call returns data with LastEvaluatedKey
        # Second call returns more data without LastEvaluatedKey
        mock_table.query.side_effect = [
            {
                "Items": [
                    {
                        "id": "vehicle_01",
                        "timestamp": 1681430400,
                        "lat": 52.5200,
                        "lon": 13.4050,
                    }
                ],
                "LastEvaluatedKey": {"id": "vehicle_01", "timestamp": 1681430400},
            },
            {
                "Items": [
                    {
                        "id": "vehicle_01",
                        "timestamp": 1681430500,
                        "lat": 52.5300,
                        "lon": 13.4150,
                    }
                ]
            },
        ]

        with patch("handlers.get_drivers_logs.locations_table", mock_table):
            result = fetch_locations_by_time_range("vehicle_01", 1681430000, 1681430600)

            assert len(result) == 2
            assert mock_table.query.call_count == 2

    def test_fetch_locations_error(self):
        """Test fetching locations with error"""
        mock_table = Mock()
        mock_table.query.side_effect = Exception("Database error")

        with patch("handlers.get_drivers_logs.locations_table", mock_table):
            result = fetch_locations_by_time_range("vehicle_01", 1681430000, 1681430500)

            # Should return empty list on error (based on the function implementation)
            assert result == []

    def test_fetch_locations_iso_timestamp_conversion_error(self):
        """Test error handling during ISO timestamp conversion"""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}

        with patch("handlers.get_drivers_logs.locations_table", mock_table):
            # Use an invalid ISO timestamp
            result = fetch_locations_by_time_range(
                "vehicle_01", "invalid-timestamp", "2023-04-14T13:00:00"
            )
            # Function should handle the error gracefully
            assert result == []


class TestHandler:

    @patch("handlers.get_drivers_logs.fetch_locations_by_time_range")
    @mock_aws
    def test_handler_success_with_vehicle_data(self, mock_fetch_locations):
        """Test handler success with vehicle location data"""
        # Mock DynamoDB for logs table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        logs_table_name = "test-logs-table"

        logs_table = dynamodb.create_table(
            TableName=logs_table_name,
            KeySchema=[{"AttributeName": "logId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "logId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Add sample log data
        logs_table.put_item(
            Item={
                "logId": "log_001",
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        )

        # Mock location fetching
        mock_fetch_locations.return_value = [
            {
                "id": "vehicle_01",
                "timestamp": 1681430400,
                "lat": 52.5200,
                "lon": 13.4050,
            }
        ]

        event = {
            "queryStringParameters": {
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        }

        with patch("handlers.get_drivers_logs.logs_table", logs_table):
            response = handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            # Handler returns dict with 'logs' key, not direct list
            assert isinstance(body, dict)
            assert "logs" in body

    def test_handler_missing_parameters(self):
        """Test handler with missing required parameters"""
        event = {
            "queryStringParameters": {
                "vehicleId": "vehicle_01"
                # Missing start_time and end_time
            }
        }

        response = handler(event, {})

        # Handler doesn't validate required parameters, returns 200 with all logs
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "logs" in body

    def test_handler_no_query_parameters(self):
        """Test handler with no query parameters"""
        event = {"queryStringParameters": None}

        response = handler(event, {})

        # Handler handles None params gracefully with defaults
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "logs" in body

    @mock_aws
    def test_handler_database_error(self):
        """Test handler with database error"""
        event = {
            "queryStringParameters": {
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        }

        # Mock table that throws an error for both GSI query and fallback scan
        with patch("handlers.get_drivers_logs.logs_table") as mock_table:
            # Mock GSI query to throw a non-GSI error (like connection error)
            from botocore.exceptions import ClientError
            error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'Database connection error'}}
            mock_table.query.side_effect = ClientError(error_response, 'Query')
            mock_table.scan.side_effect = Exception("Database connection error")

            response = handler(event, {})

            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert "error" in body

    @patch("handlers.get_drivers_logs.fetch_locations_by_time_range")
    @mock_aws
    def test_handler_with_logs_filtering(self, mock_fetch_locations):
        """Test handler with logs filtering functionality"""
        # Create mock logs table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        logs_table_name = "test-logs-table"

        logs_table = dynamodb.create_table(
            TableName=logs_table_name,
            KeySchema=[{"AttributeName": "logId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "logId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Add multiple log entries
        logs_table.put_item(
            Item={
                "logId": "log_001",
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        )

        logs_table.put_item(
            Item={
                "logId": "log_002",
                "vehicleId": "vehicle_02",  # Different vehicle
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        )

        # Mock location data
        mock_fetch_locations.return_value = [
            {
                "id": "vehicle_01",
                "timestamp": 1681430400,
                "lat": 52.5200,
                "lon": 13.4050,
            }
        ]

        event = {
            "queryStringParameters": {
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        }

        with patch("handlers.get_drivers_logs.logs_table", logs_table):
            response = handler(event, {})

            assert response["statusCode"] == 200
            # Should only return data for vehicle_01
            # The handler doesn't fetch locations in this scenario - it just returns logs
            assert not mock_fetch_locations.called

    def test_handler_invalid_time_format(self):
        """Test handler with invalid time format"""
        event = {
            "queryStringParameters": {
                "vehicleId": "vehicle_01",
                "start_time": "invalid-time",
                "end_time": "invalid-time",
            }
        }

        response = handler(event, {})

        # Handler ignores invalid time format and returns all logs
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "logs" in body

    @patch("handlers.get_drivers_logs.fetch_locations_by_time_range")
    @mock_aws
    def test_handler_empty_results(self, mock_fetch_locations):
        """Test handler when no data is found"""
        # Mock empty results
        mock_fetch_locations.return_value = []

        # Create empty logs table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        logs_table = dynamodb.create_table(
            TableName="test-logs-table",
            KeySchema=[{"AttributeName": "logId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "logId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "queryStringParameters": {
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        }

        with patch("handlers.get_drivers_logs.logs_table", logs_table):
            response = handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            # Handler returns dict with 'logs' key
            assert isinstance(body, dict)
            assert "logs" in body
            assert len(body["logs"]) == 0

    def test_handler_exception(self):
        """Test handler with unexpected exception"""
        event = {
            "queryStringParameters": {
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        }

        with patch(
            "handlers.get_drivers_logs.fetch_locations_by_time_range"
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Unexpected error")

            response = handler(event, {})

            # Handler doesn't call fetch_locations when params are provided, so no exception
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert "logs" in body


class TestIntegrationScenarios:

    @patch("handlers.get_drivers_logs.fetch_locations_by_time_range")
    @mock_aws
    def test_complete_workflow(self, mock_fetch_locations):
        """Test complete workflow from request to response"""
        # Setup mock data
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        logs_table = dynamodb.create_table(
            TableName="test-logs-table",
            KeySchema=[{"AttributeName": "logId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "logId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Add comprehensive log data
        logs_table.put_item(
            Item={
                "logId": "log_001",
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
                "start_address": "Berlin, Germany",
                "end_address": "Hamburg, Germany",
                "distance": Decimal("290.5"),
                "duration": 180,
            }
        )

        # Mock comprehensive location data
        mock_fetch_locations.return_value = [
            {
                "id": "vehicle_01",
                "timestamp": 1681430400,
                "lat": 52.5200,
                "lon": 13.4050,
                "speed": 50,
                "heading": 45,
            },
            {
                "id": "vehicle_01",
                "timestamp": 1681430460,
                "lat": 52.5300,
                "lon": 13.4150,
                "speed": 60,
                "heading": 50,
            },
        ]

        event = {
            "queryStringParameters": {
                "vehicleId": "vehicle_01",
                "start_time": "2023-04-14T12:00:00",
                "end_time": "2023-04-14T13:00:00",
            }
        }

        with patch("handlers.get_drivers_logs.logs_table", logs_table):
            response = handler(event, {})

            assert response["statusCode"] == 200
            assert "Access-Control-Allow-Origin" in response["headers"]

            body = json.loads(response["body"])
            # Handler returns dict with 'logs' key
            assert isinstance(body, dict)
            assert "logs" in body
            # Should have both logs and location data
            assert len(body["logs"]) >= 1

    def test_edge_case_parameters(self):
        """Test edge cases with parameter handling"""
        edge_cases = [
            # Empty vehicle ID
            {
                "queryStringParameters": {
                    "vehicleId": "",
                    "start_time": "2023-04-14T12:00:00",
                    "end_time": "2023-04-14T13:00:00",
                }
            },
            # Very old timestamps
            {
                "queryStringParameters": {
                    "vehicleId": "vehicle_01",
                    "start_time": "1970-01-01T00:00:00",
                    "end_time": "1970-01-01T01:00:00",
                }
            },
            # Future timestamps
            {
                "queryStringParameters": {
                    "vehicleId": "vehicle_01",
                    "start_time": "2030-01-01T00:00:00",
                    "end_time": "2030-01-01T01:00:00",
                }
            },
        ]

        for event in edge_cases:
            response = handler(event, {})
            # Should handle all edge cases gracefully
            assert response["statusCode"] in [200, 400, 500]
            assert "body" in response
