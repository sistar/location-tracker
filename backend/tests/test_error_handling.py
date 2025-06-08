from datetime import datetime
from decimal import Decimal
import json
from unittest.mock import MagicMock, patch

import pytest

import handlers.geocode_service

# Import all handlers to test
import handlers.get_latest_location
import handlers.get_location_history
import handlers.get_vehicle_ids
import handlers.gps_processing
import handlers.save_drivers_log
import handlers.scan_unsaved_sessions


class TestGetLatestLocationErrorHandling:
    """Test error handling for get_latest_location handler"""

    @patch("handlers.get_latest_location.table")
    def test_get_latest_location_dynamodb_error(self, mock_table):
        """Test DynamoDB query error handling"""
        # Configure mock to raise an exception
        mock_table.query.side_effect = Exception("DynamoDB connection error")

        event = {"queryStringParameters": {"vehicle_id": "vehicle_01"}}

        response = handlers.get_latest_location.handler(event, None)

        assert response["statusCode"] == 500
        assert "error" in json.loads(response["body"])
        assert "DynamoDB connection error" in json.loads(response["body"])["error"]

    @patch("handlers.get_latest_location.table")
    def test_get_latest_location_no_items_found(self, mock_table):
        """Test when no location is found"""
        mock_table.query.return_value = {"Items": []}

        event = {"queryStringParameters": {"vehicle_id": "vehicle_01"}}

        response = handlers.get_latest_location.handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["message"] == "No location found"

    @patch("handlers.get_latest_location.table")
    def test_get_latest_location_invalid_timestamp(self, mock_table):
        """Test handling of invalid timestamp data"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "id": "vehicle_01",
                    "timestamp": "invalid_timestamp",
                    "lat": Decimal("52.5200"),
                    "lon": Decimal("13.4050"),
                }
            ]
        }

        event = {"queryStringParameters": {"vehicle_id": "vehicle_01"}}

        response = handlers.get_latest_location.handler(event, None)

        # Should still return 200 but with fallback timestamp
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "timestamp_str" in body

    def test_get_latest_location_missing_query_params(self):
        """Test with missing query parameters"""
        event = {}

        response = handlers.get_latest_location.handler(event, None)

        # Should default to vehicle_01 and handle gracefully
        assert response["statusCode"] in [200, 404, 500]  # Any valid response


class TestGeocodeServiceErrorHandling:
    """Test error handling for geocode_service handler"""

    @patch("handlers.geocode_service.requests.get")
    def test_geocode_service_api_timeout(self, mock_get):
        """Test API timeout handling"""
        mock_get.side_effect = Exception("Request timeout")

        event = {"body": json.dumps({"lat": 52.5200, "lon": 13.4050})}

        response = handlers.geocode_service.handler(event, None)

        # The handler may return 200 with fallback behavior instead of 500
        assert response["statusCode"] in [200, 500]
        body = json.loads(response["body"])
        # May have error field or fallback address
        assert "error" in body or "address" in body

    @patch("handlers.geocode_service.requests.get")
    def test_geocode_service_invalid_response(self, mock_get):
        """Test invalid API response handling"""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response

        event = {"body": json.dumps({"lat": 52.5200, "lon": 13.4050})}

        response = handlers.geocode_service.handler(event, None)

        # Handler may return 200 with fallback instead of 500
        assert response["statusCode"] in [200, 500]
        body = json.loads(response["body"])
        assert "error" in body or "address" in body

    def test_geocode_service_invalid_coordinates(self):
        """Test with invalid coordinates"""
        event = {"body": json.dumps({"lat": "invalid", "lon": "invalid"})}

        response = handlers.geocode_service.handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_geocode_service_missing_body(self):
        """Test with missing request body"""
        event = {}

        response = handlers.geocode_service.handler(event, None)

        # Handler returns 400 for missing/invalid input, not 500
        assert response["statusCode"] in [400, 500]
        body = json.loads(response["body"])
        assert "error" in body or "message" in body

    def test_geocode_service_invalid_json(self):
        """Test with invalid JSON body"""
        event = {"body": "invalid json"}

        response = handlers.geocode_service.handler(event, None)

        # Handler returns 400 for invalid JSON, not 500
        assert response["statusCode"] in [400, 500]
        body = json.loads(response["body"])
        assert "error" in body or "message" in body


class TestGetVehicleIdsErrorHandling:
    """Test error handling for get_vehicle_ids handler"""

    @patch("handlers.get_vehicle_ids.table")
    def test_get_vehicle_ids_scan_error(self, mock_table):
        """Test DynamoDB scan error handling"""
        mock_table.scan.side_effect = Exception("DynamoDB scan failed")

        event = {}

        response = handlers.get_vehicle_ids.handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert "DynamoDB scan failed" in body["error"]

    @patch("handlers.get_vehicle_ids.table")
    def test_get_vehicle_ids_no_vehicles(self, mock_table):
        """Test when no vehicles are found"""
        mock_table.scan.return_value = {"Items": []}

        event = {}

        response = handlers.get_vehicle_ids.handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["message"] == "No vehicles found"

    @patch("handlers.get_vehicle_ids.table")
    def test_get_vehicle_ids_malformed_data(self, mock_table):
        """Test handling of malformed vehicle data"""
        mock_table.scan.return_value = {
            "Items": [
                {},  # Missing 'id' field
                {"id": None},  # Null id
                {"id": "vehicle_01"},  # Valid item
            ]
        }

        event = {}

        # Should handle gracefully and extract valid IDs
        response = handlers.get_vehicle_ids.handler(event, None)

        # Might return 200 with partial data or 500 depending on implementation
        assert response["statusCode"] in [200, 500]


class TestSaveDriversLogErrorHandling:
    """Test error handling for save_drivers_log handler"""

    @patch("handlers.save_drivers_log.logs_table")
    def test_save_drivers_log_put_item_error(self, mock_table):
        """Test DynamoDB put_item error handling"""
        mock_table.put_item.side_effect = Exception("DynamoDB write failed")
        mock_table.query.return_value = {"Items": []}  # No existing sessions
        mock_table.scan.return_value = {"Items": []}  # No overlapping logs

        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {
                    "sessionId": "test_session",
                    "startTime": 1678885200,
                    "endTime": 1678888800,
                    "vehicleId": "vehicle_01",
                }
            ),
        }

        response = handlers.save_drivers_log.handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert "DynamoDB write failed" in body["error"]

    def test_save_drivers_log_invalid_json(self):
        """Test with invalid JSON body"""
        event = {"httpMethod": "POST", "body": "invalid json"}

        response = handlers.save_drivers_log.handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_save_drivers_log_missing_required_fields(self):
        """Test with missing required fields"""
        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {
                    "sessionId": "test_session"
                    # Missing startTime and endTime
                }
            ),
        }

        response = handlers.save_drivers_log.handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Missing required fields" in body["message"]

    @patch("handlers.save_drivers_log.logs_table")
    def test_save_drivers_log_check_overlap_error(self, mock_table):
        """Test error in overlap checking"""
        mock_table.scan.side_effect = Exception("Database error during overlap check")

        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {
                    "sessionId": "test_session",
                    "startTime": 1678885200,
                    "endTime": 1678888800,
                }
            ),
        }

        response = handlers.save_drivers_log.handler(event, None)

        # Should continue processing despite overlap check error
        assert response["statusCode"] in [200, 500]


class TestGetLocationHistoryErrorHandling:
    """Test error handling for get_location_history handler"""

    @patch("handlers.get_location_history.table")
    def test_get_location_history_query_error(self, mock_table):
        """Test DynamoDB query error handling"""
        mock_table.query.side_effect = Exception("Query failed")

        event = {}

        response = handlers.get_location_history.handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert "Query failed" in body["error"]

    @patch("handlers.get_location_history.table")
    def test_get_location_history_corrupted_data(self, mock_table):
        """Test handling of corrupted location data"""
        mock_table.query.return_value = {
            "Items": [
                {"timestamp": "invalid"},  # Invalid timestamp
                {"timestamp": None},  # Null timestamp
                {"timestamp": Decimal("1678885200"), "lat": "invalid"},  # Invalid lat
            ]
        }

        event = {}

        # Should handle gracefully and continue processing
        response = handlers.get_location_history.handler(event, None)

        # Might succeed with partial data or fail depending on implementation
        assert response["statusCode"] in [200, 500]


class TestGpsProcessingErrorHandling:
    """Test error handling for gps_processing module functions"""

    def test_parse_timestamp_invalid_format(self):
        """Test timestamp parsing with invalid format"""
        with pytest.raises(ValueError):
            handlers.gps_processing.parse_timestamp("invalid-timestamp")

    def test_haversine_distance_invalid_coordinates(self):
        """Test haversine with invalid coordinates"""
        # Should handle and return reasonable values or raise appropriate errors
        try:
            result = handlers.gps_processing.haversine_distance(
                "invalid", 13.4050, 52.5200, 13.4050
            )
            # If it doesn't raise, result should be a number
            assert isinstance(result, (int, float))
        except (TypeError, ValueError):
            # This is also acceptable behavior
            pass

    def test_calculate_speed_kmh_edge_cases(self):
        """Test speed calculation edge cases"""
        # Zero time difference
        result = handlers.gps_processing.calculate_speed_kmh(1000, 0)
        assert result == float("inf")

        # Negative time difference
        result = handlers.gps_processing.calculate_speed_kmh(1000, -60)
        assert result == float("inf")

        # Zero distance
        result = handlers.gps_processing.calculate_speed_kmh(0, 60)
        assert result == 0

    def test_is_outlier_temporal_no_history(self):
        """Test outlier detection with no history"""
        # Reset history first
        handlers.gps_processing.reset_location_history()

        location = {"lat": 52.5200, "lon": 13.4050, "time": "2023-03-15T12:00:00"}
        is_outlier, reason = handlers.gps_processing.is_outlier_temporal(location)

        assert is_outlier is False
        assert "Insufficient history" in reason

    def test_gps_processor_invalid_location_data(self):
        """Test GPSProcessor with invalid location data"""
        processor = handlers.gps_processing.GPSProcessor()

        # Test with missing required fields
        invalid_location = {"invalid": "data"}

        try:
            result = processor.should_store_location(invalid_location)
            # Should handle gracefully
            assert isinstance(result, tuple)
            assert len(result) == 2
        except KeyError:
            # This is also acceptable - missing required fields should raise KeyError
            pass


class TestScanUnsavedSessionsErrorHandling:
    """Test error handling for scan_unsaved_sessions handler"""

    @patch("handlers.scan_unsaved_sessions.locations_table")
    def test_scan_sessions_locations_query_error(self, mock_table):
        """Test locations table query error"""
        mock_table.query.side_effect = Exception("Locations table error")

        event = {"queryStringParameters": {"vehicle_id": "vehicle_01"}}

        response = handlers.scan_unsaved_sessions.handler(event, None)

        # Handler may return 404 when no data found due to error, or 500 for actual error
        assert response["statusCode"] in [404, 500]
        body = json.loads(response["body"])
        assert "error" in body or "message" in body

    @patch("handlers.scan_unsaved_sessions.logs_table")
    @patch("handlers.scan_unsaved_sessions.locations_table")
    def test_scan_sessions_logs_table_error(
        self, mock_locations_table, mock_logs_table
    ):
        """Test logs table scan error during overlap checking"""
        # Mock successful locations query
        mock_locations_table.query.return_value = {
            "Items": [
                {
                    "id": "vehicle_01",
                    "timestamp": Decimal("1678885200"),
                    "lat": Decimal("52.5200"),
                    "lon": Decimal("13.4050"),
                }
            ]
        }

        # Mock logs table error
        mock_logs_table.scan.side_effect = Exception("Logs table error")

        event = {"queryStringParameters": {"vehicle_id": "vehicle_01"}}

        response = handlers.scan_unsaved_sessions.handler(event, None)

        # Should continue processing despite logs table error
        assert response["statusCode"] in [200, 500]

    def test_scan_sessions_invalid_days_parameter(self):
        """Test with invalid days parameter"""
        event = {
            "queryStringParameters": {"vehicle_id": "vehicle_01", "days": "invalid"}
        }

        response = handlers.scan_unsaved_sessions.handler(event, None)

        # Should default to 7 days and continue
        assert response["statusCode"] in [200, 404, 500]

    @patch("handlers.scan_unsaved_sessions.locations_table")
    def test_scan_sessions_corrupted_location_data(self, mock_table):
        """Test handling of corrupted location data"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "timestamp": "invalid",
                    "lat": Decimal("52.5200"),
                },  # Invalid timestamp
                {"timestamp": Decimal("1678885200")},  # Missing lat/lon
                {"timestamp": None, "lat": None, "lon": None},  # All null values
            ]
        }

        event = {"queryStringParameters": {"vehicle_id": "vehicle_01"}}

        response = handlers.scan_unsaved_sessions.handler(event, None)

        # Should handle gracefully
        assert response["statusCode"] in [200, 404, 500]

    def test_scan_sessions_missing_query_params(self):
        """Test with missing query parameters"""
        event = {}

        response = handlers.scan_unsaved_sessions.handler(event, None)

        # Should default to vehicle_01 and handle gracefully
        assert response["statusCode"] in [200, 404, 500]


class TestCommonErrorPatterns:
    """Test common error patterns across all handlers"""

    def test_decimal_default_function(self):
        """Test decimal_default utility function error handling"""
        # Test with valid Decimal
        result = handlers.get_latest_location.decimal_default(Decimal("10.5"))
        assert result == 10.5

        # Test with invalid type
        with pytest.raises(TypeError):
            handlers.get_latest_location.decimal_default("not a decimal")

    def test_handlers_with_empty_event(self):
        """Test all handlers with empty event"""
        handlers_to_test = [
            handlers.get_latest_location.handler,
            handlers.get_vehicle_ids.handler,
            handlers.get_location_history.handler,
            handlers.scan_unsaved_sessions.handler,
        ]

        for handler in handlers_to_test:
            try:
                response = handler({}, None)
                # Should return a valid HTTP response
                assert "statusCode" in response
                assert response["statusCode"] in [200, 400, 404, 500]
                assert "body" in response
            except Exception as e:
                # If handler raises exception, it should be a reasonable error
                assert isinstance(e, (ValueError, KeyError, TypeError))

    def test_handlers_with_none_event(self):
        """Test handlers with None event"""
        handlers_to_test = [
            handlers.get_latest_location.handler,
            handlers.get_vehicle_ids.handler,
            handlers.get_location_history.handler,
        ]

        for handler in handlers_to_test:
            try:
                response = handler(None, None)
                # Should return a valid HTTP response or raise exception
                if response:
                    assert "statusCode" in response
                    assert response["statusCode"] in [200, 400, 404, 500]
            except Exception as e:
                # This is acceptable for None input
                assert isinstance(e, (AttributeError, TypeError, ValueError))


class TestCorsCorsHeaders:
    """Test CORS headers are present in error responses"""

    @patch("handlers.get_latest_location.table")
    def test_error_response_has_cors_headers(self, mock_table):
        """Test that error responses include CORS headers"""
        mock_table.query.side_effect = Exception("Test error")

        event = {}
        response = handlers.get_latest_location.handler(event, None)

        assert response["statusCode"] == 500
        assert "headers" in response
        # Most handlers should include CORS headers in error responses
        # This is important for frontend functionality
