from decimal import Decimal
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the src directory to the path so we can import handlers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from handlers.geocode_service import handler, reverse_geocode

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


class TestReverseGeocode:
    pass


class TestHandler:

    @patch("handlers.geocode_service.reverse_geocode")
    def test_handler_success(self, mock_reverse_geocode):
        """Test successful handler execution"""
        # Mock successful geocoding
        mock_reverse_geocode.return_value = {
            "display_name": "Test Address",
            "lat": "52.52",
            "lon": "13.405",
        }

        event = {"queryStringParameters": {"lat": "52.52", "lon": "13.405"}}

        response = handler(event, {})

        assert response["statusCode"] == 200
        # Geocode service doesn't set CORS headers (handled by API Gateway)
        assert "Content-Type" in response["headers"]

        body = json.loads(response["body"])
        assert body["display_name"] == "Test Address"

    def test_handler_missing_parameters(self):
        """Test handler with missing parameters"""
        event = {
            "queryStringParameters": {
                "lat": "52.52"
                # Missing 'lon'
            }
        }

        response = handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_handler_no_query_parameters(self):
        """Test handler with no query parameters"""
        event = {"queryStringParameters": None}

        response = handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_handler_invalid_coordinates(self):
        """Test handler with invalid coordinates"""
        event = {"queryStringParameters": {"lat": "invalid", "lon": "13.405"}}

        response = handler(event, {})

        assert (
            response["statusCode"] == 500
        )  # Invalid coordinates cause ValueError exception
        body = json.loads(response["body"])
        assert "error" in body

    @patch("handlers.geocode_service.reverse_geocode")
    def test_handler_geocoding_error(self, mock_reverse_geocode):
        """Test handler when geocoding returns error"""
        # Mock geocoding error
        mock_reverse_geocode.return_value = {
            "error": "Failed to get address",
            "status_code": 500,
        }

        event = {"queryStringParameters": {"lat": "52.52", "lon": "13.405"}}

        response = handler(event, {})

        assert (
            response["statusCode"] == 200
        )  # Handler doesn't check for error in geocode result
        body = json.loads(response["body"])
        assert "error" in body  # Error is in the returned data

    def test_handler_exception(self):
        """Test handler with unexpected exception"""
        event = {"queryStringParameters": {"lat": "52.52", "lon": "13.405"}}

        with patch("handlers.geocode_service.reverse_geocode") as mock_reverse:
            mock_reverse.side_effect = Exception("Unexpected error")

            response = handler(event, {})

            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert "error" in body

    @patch("handlers.geocode_service.reverse_geocode")
    def test_handler_coordinate_edge_cases(self, mock_reverse_geocode):
        """Test handler with coordinate edge cases"""
        mock_reverse_geocode.return_value = {"display_name": "Test Address"}

        edge_cases = [
            # Extreme coordinates
            {"lat": "90.0", "lon": "180.0"},  # North pole, date line
            {"lat": "-90.0", "lon": "-180.0"},  # South pole, opposite date line
            {
                "lat": "0.1",
                "lon": "0.1",
            },  # Near equator, near prime meridian (not exactly 0)
            # High precision coordinates
            {"lat": "52.123456789", "lon": "13.987654321"},
        ]

        for params in edge_cases:
            event = {"queryStringParameters": params}
            response = handler(event, {})

            # Should handle all edge cases
            assert response["statusCode"] == 200

    @patch("handlers.geocode_service.reverse_geocode")
    def test_handler_decimal_serialization(self, mock_reverse_geocode):
        """Test handler properly serializes Decimal values"""
        # Mock geocoding with Decimal values
        mock_reverse_geocode.return_value = {
            "display_name": "Test Address",
            "lat": Decimal("52.52"),
            "lon": Decimal("13.405"),
        }

        event = {"queryStringParameters": {"lat": "52.52", "lon": "13.405"}}

        response = handler(event, {})

        assert response["statusCode"] == 200

        # Should be able to parse JSON without Decimal serialization errors
        body = json.loads(response["body"])
        assert isinstance(body["lat"], float)
        assert isinstance(body["lon"], float)
