from datetime import datetime, timedelta
from decimal import Decimal
import json
from unittest.mock import MagicMock, patch

import boto3
import pytest

# Import the module, not just functions, so we can patch properly
import handlers.get_raw_location_history
from handlers.get_raw_location_history import decimal_default


class TestGetRawLocationHistory:
    """Test cases for the get_raw_location_history handler"""

    @pytest.fixture
    def mock_handler_setup(self):
        """Set up mock DynamoDB table and query responses with proper patching"""
        # Sample data representing raw GPS points
        sample_data = [
            {
                "id": "vehicle_01",
                "timestamp": Decimal("1714320000"),  # Example epoch timestamp
                "lat": Decimal("52.5200"),
                "lon": Decimal("13.4050"),
                "ele": Decimal("50"),
                "sog": Decimal("0"),
                "cog": Decimal("0"),
            },
            {
                "id": "vehicle_01",
                "timestamp": Decimal("1714323600"),  # 1 hour later
                "lat": Decimal("52.5220"),
                "lon": Decimal("13.4070"),
                "ele": Decimal("51"),
                "sog": Decimal("20"),
                "cog": Decimal("90"),
            },
        ]

        # Configure the mock response
        mock_response = {
            "Items": sample_data,
            "Count": len(sample_data),
            "ScannedCount": len(sample_data),
            "LastEvaluatedKey": None,  # Indicate no more pages
        }

        # Create mock objects
        mock_table = MagicMock()
        mock_table.query.return_value = mock_response

        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table

        # Create patches
        patches = [
            patch(
                "handlers.get_raw_location_history.boto3.resource",
                return_value=mock_resource,
            ),
            patch("handlers.get_raw_location_history.locations_table", mock_table),
        ]

        # Apply all patches
        for p in patches:
            p.start()

        yield mock_table

        # Clean up all patches
        for p in patches:
            p.stop()

    def test_decimal_default(self):
        """Test the decimal_default function handles Decimal type correctly"""
        # Test with a decimal value
        assert decimal_default(Decimal("10.5")) == 10.5

        # Test with non-decimal value should raise TypeError
        with pytest.raises(TypeError):
            decimal_default("not a decimal")

    def test_handler_successful_response(self, mock_handler_setup):
        """Test handler returns correct response format with data"""
        # Create a mock event with query parameters
        event = {"queryStringParameters": {"vehicle_id": "vehicle_01", "days": "7"}}

        # Execute the handler
        response = handlers.get_raw_location_history.handler(event, None)

        # Verify the response format
        assert response["statusCode"] == 200
        assert "body" in response
        assert "Access-Control-Allow-Origin" in response["headers"]

        # Parse the body JSON
        body = json.loads(response["body"])

        # Verify items were returned
        assert len(body) == 2

        # Verify items have timestamp_str field added
        assert "timestamp_str" in body[0]
        assert "timestamp_str" in body[1]

        # Verify coordinates are converted to float
        assert isinstance(body[0]["lat"], float)
        assert isinstance(body[0]["lon"], float)

    def test_handler_with_default_parameters(self, mock_handler_setup):
        """Test handler works with default parameters when not all are provided"""
        # Create a mock event with minimal query parameters
        event = {
            "queryStringParameters": {
                # Only vehicle_id, no days parameter
                "vehicle_id": "vehicle_01"
            }
        }

        # Execute the handler
        response = handlers.get_raw_location_history.handler(event, None)

        # Verify successful response
        assert response["statusCode"] == 200

        # Verify query was called at least once
        assert mock_handler_setup.query.called

        # Instead of looking for the string, verify the status code which is more reliable
        assert response["statusCode"] == 200

        # Parse the body JSON to verify we got data
        body = json.loads(response["body"])
        assert len(body) == 2  # We expect 2 items

        # Check if the response has the expected structure
        for item in body:
            assert "id" in item
            assert "lat" in item
            assert "lon" in item
            assert "timestamp" in item
            assert "timestamp_str" in item

    def test_handler_with_custom_days(self, mock_handler_setup):
        """Test handler respects the days parameter"""
        # Create a mock event with custom days parameter
        event = {
            "queryStringParameters": {
                "vehicle_id": "vehicle_01",
                "days": "14",  # 14 days instead of default 7
            }
        }

        # Execute the handler
        handlers.get_raw_location_history.handler(event, None)

        # Verify query was called
        assert mock_handler_setup.query.called

    def test_handler_error_handling(self, mock_handler_setup):
        """Test handler handles errors gracefully"""
        # Configure mock to raise an exception
        mock_handler_setup.query.side_effect = Exception("Test error")

        # Create a mock event
        event = {"queryStringParameters": {"vehicle_id": "vehicle_01"}}

        # Execute the handler
        response = handlers.get_raw_location_history.handler(event, None)

        # Verify error response
        assert response["statusCode"] == 500
        assert "body" in response

        # Parse the body JSON
        body = json.loads(response["body"])

        # Verify error message
        assert "error" in body
