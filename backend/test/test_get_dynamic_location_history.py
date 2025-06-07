import json
import math
import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest

from handlers.get_dynamic_location_history import (
    calculate_median_position,
    calculate_time_window,
    clean_phantom_locations,
    create_api_response,
    decimal_default,
    extend_session_points,
    handler,
    haversine,
    parse_timestamp_safely,
    query_location_range,
)


class TestUtilityFunctions:

    def test_decimal_default(self):
        """Test Decimal to float conversion"""
        assert decimal_default(Decimal("123.45")) == 123.45

        with pytest.raises(TypeError):
            decimal_default("not a decimal")

    def test_parse_timestamp_safely_numeric(self):
        """Test parsing numeric timestamps"""
        epoch = 1681430400  # 2023-04-14

        # Test int
        result = parse_timestamp_safely(1681430400)
        assert isinstance(result, datetime)

        # Test float
        result = parse_timestamp_safely(1681430400.0)
        assert isinstance(result, datetime)

        # Test Decimal
        result = parse_timestamp_safely(Decimal("1681430400"))
        assert isinstance(result, datetime)

    def test_parse_timestamp_safely_string_digit(self):
        """Test parsing string digit timestamps"""
        result = parse_timestamp_safely("1681430400")
        assert isinstance(result, datetime)

    def test_parse_timestamp_safely_iso_format(self):
        """Test parsing ISO format timestamps"""
        iso_timestamp = "2023-04-14T12:00:00"
        result = parse_timestamp_safely(iso_timestamp)
        assert isinstance(result, datetime)

    def test_parse_timestamp_safely_with_timezone(self):
        """Test parsing timestamps with timezone"""
        timestamp_with_tz = "2025-04-14T02:26:59 MESZ"
        result = parse_timestamp_safely(timestamp_with_tz)
        assert isinstance(result, datetime)

    def test_parse_timestamp_safely_various_formats(self):
        """Test parsing various timestamp formats"""
        formats = ["2023-04-14 12:00:00", "2023/04/14 12:00:00", "14.04.2023 12:00:00"]

        for timestamp in formats:
            result = parse_timestamp_safely(timestamp)
            assert isinstance(result, datetime)

    def test_parse_timestamp_safely_invalid(self):
        """Test parsing invalid timestamp raises error"""
        with pytest.raises(ValueError):
            parse_timestamp_safely("invalid-timestamp")

    def test_haversine(self):
        """Test haversine distance calculation"""
        # Test distance between two known points
        lat1, lon1 = 52.5200, 13.4050  # Berlin
        lat2, lon2 = 48.8566, 2.3522  # Paris

        distance = haversine(lat1, lon1, lat2, lon2)
        # Approximate distance Berlin-Paris is around 878km
        assert 870000 < distance < 890000

        # Test same point (should be 0)
        distance = haversine(lat1, lon1, lat1, lon1)
        assert distance == 0

    def test_calculate_median_position_empty(self):
        """Test median position calculation with empty list"""
        result = calculate_median_position([])
        assert result == (0.0, 0.0)

    def test_calculate_median_position_single(self):
        """Test median position calculation with single location"""
        locations = [{"lat": 52.5200, "lon": 13.4050}]
        result = calculate_median_position(locations)
        assert result == (52.5200, 13.4050)

    def test_calculate_median_position_multiple(self):
        """Test median position calculation with multiple locations"""
        locations = [
            {"lat": 52.5200, "lon": 13.4050},
            {"lat": 52.5300, "lon": 13.4150},
            {"lat": 52.5100, "lon": 13.3950},
        ]
        result = calculate_median_position(locations)
        expected_lat = statistics.median([52.5200, 52.5300, 52.5100])
        expected_lon = statistics.median([13.4050, 13.4150, 13.3950])
        assert result == (expected_lat, expected_lon)

    def test_create_api_response_success(self):
        """Test API response creation for success"""
        body = {"data": "test"}
        response = create_api_response(200, body)

        assert response["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in response["headers"]
        assert json.loads(response["body"]) == body

    def test_create_api_response_error(self):
        """Test API response creation for error"""
        error_msg = "Test error"
        response = create_api_response(500, error_msg, error=True)

        assert response["statusCode"] == 500
        assert json.loads(response["body"]) == {"error": error_msg}


class TestCleanPhantomLocations:

    def test_clean_phantom_locations_empty(self):
        """Test cleaning with empty list"""
        result = clean_phantom_locations([])
        assert result == []

    def test_clean_phantom_locations_insufficient_data(self):
        """Test cleaning with insufficient data points"""
        locations = [
            {"lat": 52.5200, "lon": 13.4050, "timestamp": 1681430400},
            {"lat": 52.5201, "lon": 13.4051, "timestamp": 1681430460},
        ]
        result = clean_phantom_locations(locations)
        assert len(result) == 2

    def test_clean_phantom_locations_moving_points(self):
        """Test cleaning with moving points (should mark as moving)"""
        locations = []
        base_timestamp = 1681430400
        base_lat, base_lon = 52.5200, 13.4050

        # Create points that are far apart (movement)
        for i in range(5):
            locations.append(
                {
                    "lat": base_lat + (i * 0.01),  # Move significantly each time
                    "lon": base_lon + (i * 0.01),
                    "timestamp": base_timestamp + (i * 60),
                }
            )

        result = clean_phantom_locations(locations)
        assert len(result) >= 3
        # Check that points are marked as moving
        for point in result:
            if "segment_type" in point:
                assert point["segment_type"] == "moving"

    def test_clean_phantom_locations_stopped_points(self):
        """Test cleaning with stopped points"""
        locations = []
        base_timestamp = 1681430400
        base_lat, base_lon = 52.5200, 13.4050

        # Create points that are close together (stopped)
        for i in range(20):  # Need enough points for median calculation
            locations.append(
                {
                    "lat": base_lat + (i * 0.0001),  # Very small movement
                    "lon": base_lon + (i * 0.0001),
                    "timestamp": base_timestamp + (i * 60),  # 1 minute intervals
                }
            )

        result = clean_phantom_locations(locations)
        assert len(result) > 0


class TestDatabaseOperations:

    @patch("handlers.get_dynamic_location_history.parse_timestamp_safely")
    def test_query_location_range_success(self, mock_parse):
        """Test successful location range query"""
        mock_table = Mock()
        mock_table.name = "test-table"
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

        # Mock timestamp parsing to return epoch values
        mock_parse.side_effect = lambda x: (
            datetime.fromtimestamp(x)
            if isinstance(x, (int, float))
            else datetime.fromisoformat(x)
        )

        items, error = query_location_range(
            mock_table, "vehicle_01", 1681430400, 1681434000
        )

        assert error is None
        assert len(items) == 1
        assert items[0]["id"] == "vehicle_01"

    def test_query_location_range_error(self):
        """Test location range query with error"""
        mock_table = Mock()
        mock_table.query.side_effect = Exception("Database error")

        items, error = query_location_range(
            mock_table, "vehicle_01", 1681430400, 1681434000
        )

        assert items == []
        assert "Database error" in error

    def test_calculate_time_window_both_timestamps(self):
        """Test time window calculation with both timestamps provided"""
        start_ts = "2023-04-14T12:00:00"
        end_ts = "2023-04-14T18:00:00"

        calc_start, calc_end, error = calculate_time_window(start_ts, end_ts, 6)

        assert error is None
        assert calc_start is None  # No calculation needed
        assert calc_end is None

    def test_calculate_time_window_start_only(self):
        """Test time window calculation with start timestamp only"""
        start_ts = "2023-04-14T12:00:00"

        calc_start, calc_end, error = calculate_time_window(start_ts, None, 6)

        assert error is None
        assert calc_start is None
        assert calc_end is not None

    def test_calculate_time_window_end_only(self):
        """Test time window calculation with end timestamp only"""
        end_ts = "2023-04-14T18:00:00"

        calc_start, calc_end, error = calculate_time_window(None, end_ts, 6)

        assert error is None
        assert calc_start is not None
        assert calc_end is None

    def test_calculate_time_window_neither(self):
        """Test time window calculation with no timestamps"""
        calc_start, calc_end, error = calculate_time_window(None, None, 6)

        assert error is None
        assert calc_start is not None
        assert calc_end is not None
        assert calc_end > calc_start


class TestExtendSessionPoints:

    @patch("handlers.get_dynamic_location_history.parse_timestamp_safely")
    def test_extend_session_points_backward(self, mock_parse):
        """Test extending session points backward"""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "id": "vehicle_01",
                    "timestamp": 1681430100,
                    "lat": 52.5200,
                    "lon": 13.4050,
                }
            ]
        }

        boundary_time = datetime.fromtimestamp(1681430400)
        mock_parse.return_value = boundary_time

        points, new_boundary, error = extend_session_points(
            mock_table, "vehicle_01", 1681430400, "backward", 50
        )

        assert error is None
        assert len(points) == 1
        assert new_boundary == 1681430100

    @patch("handlers.get_dynamic_location_history.parse_timestamp_safely")
    def test_extend_session_points_forward(self, mock_parse):
        """Test extending session points forward"""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "id": "vehicle_01",
                    "timestamp": 1681430700,
                    "lat": 52.5200,
                    "lon": 13.4050,
                }
            ]
        }

        boundary_time = datetime.fromtimestamp(1681430400)
        mock_parse.return_value = boundary_time

        points, new_boundary, error = extend_session_points(
            mock_table, "vehicle_01", 1681430400, "forward", 50
        )

        assert error is None
        assert len(points) == 1
        assert new_boundary == 1681430700

    def test_extend_session_points_no_points(self):
        """Test extending session points when no points found"""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}

        with patch(
            "handlers.get_dynamic_location_history.parse_timestamp_safely"
        ) as mock_parse:
            mock_parse.return_value = datetime.fromtimestamp(1681430400)

            points, new_boundary, error = extend_session_points(
                mock_table, "vehicle_01", 1681430400, "backward", 50
            )

            assert points == []
            assert error == "No points found"

    def test_extend_session_points_error(self):
        """Test extending session points with error"""
        mock_table = Mock()
        mock_table.query.side_effect = Exception("Database error")

        with patch(
            "handlers.get_dynamic_location_history.parse_timestamp_safely"
        ) as mock_parse:
            mock_parse.return_value = datetime.fromtimestamp(1681430400)

            points, new_boundary, error = extend_session_points(
                mock_table, "vehicle_01", 1681430400, "backward", 50
            )

            assert points == []
            assert "Database error" in error


class TestHandler:

    @patch("handlers.get_dynamic_location_history.query_location_range")
    @patch("handlers.get_dynamic_location_history.extend_session_points")
    @patch("handlers.get_dynamic_location_history.clean_phantom_locations")
    def test_handler_success(self, mock_clean, mock_extend, mock_query):
        """Test successful handler execution"""
        # Mock the query response
        mock_query.return_value = (
            [
                {
                    "id": "vehicle_01",
                    "timestamp": 1681430400,
                    "lat": 52.5200,
                    "lon": 13.4050,
                }
            ],
            None,
        )

        # Mock extension (no additional points)
        mock_extend.return_value = ([], 1681430400, "No points found")

        # Mock cleaning
        mock_clean.return_value = [
            {
                "id": "vehicle_01",
                "timestamp": 1681430400,
                "lat": 52.5200,
                "lon": 13.4050,
                "segment_type": "moving",
            }
        ]

        event = {
            "queryStringParameters": {
                "vehicle_id": "vehicle_01",
                "start_timestamp": "1681430400",
                "end_timestamp": "1681434000",
            }
        }

        response = handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body) == 1
        assert "timestamp_str" in body[0]

    def test_handler_no_query_params(self):
        """Test handler with no query parameters"""
        event = {"queryStringParameters": None}

        with patch(
            "handlers.get_dynamic_location_history.query_location_range"
        ) as mock_query:
            mock_query.return_value = ([], "No data found")
            response = handler(event, {})

            assert response["statusCode"] == 500

    def test_handler_invalid_time_window(self):
        """Test handler with invalid time window parameter"""
        event = {
            "queryStringParameters": {
                "time_window": "invalid",
                "vehicle_id": "vehicle_01",
            }
        }

        with patch(
            "handlers.get_dynamic_location_history.query_location_range"
        ) as mock_query:
            mock_query.return_value = ([], "No data found")
            response = handler(event, {})

            # Should handle invalid time_window gracefully and use default
            assert response["statusCode"] == 500  # Due to no data found

    @patch("handlers.get_dynamic_location_history.query_location_range")
    def test_handler_no_data_found(self, mock_query):
        """Test handler when no data is found"""
        mock_query.return_value = ([], None)

        event = {
            "queryStringParameters": {
                "vehicle_id": "vehicle_01",
                "start_timestamp": "1681430400",
                "end_timestamp": "1681434000",
            }
        }

        response = handler(event, {})

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "No location data found" in body["message"]

    def test_handler_query_error(self):
        """Test handler when query returns error"""
        with patch(
            "handlers.get_dynamic_location_history.query_location_range"
        ) as mock_query:
            mock_query.return_value = ([], "Database connection error")

            event = {
                "queryStringParameters": {
                    "vehicle_id": "vehicle_01",
                    "start_timestamp": "1681430400",
                    "end_timestamp": "1681434000",
                }
            }

            response = handler(event, {})

            assert response["statusCode"] == 500

    def test_handler_exception(self):
        """Test handler with general exception"""
        event = {"queryStringParameters": {"vehicle_id": "vehicle_01"}}

        with patch(
            "handlers.get_dynamic_location_history.calculate_time_window"
        ) as mock_calc:
            mock_calc.side_effect = Exception("Unexpected error")

            response = handler(event, {})

            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert "error" in body


# Legacy tests from original file
def test_parse_timestamp_safely_iso_format():
    timestamp = "2023-03-15T12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromisoformat(timestamp)
    assert result == expected


def test_parse_timestamp_safely_iso_format_with_timezone():
    timestamp = "2023-03-15T12:34:56+00:00"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromisoformat(timestamp)
    assert result == expected


def test_parse_timestamp_safely_standard_format():
    timestamp = "2023-03-15T12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    assert result == expected


def test_parse_timestamp_safely_space_separated_format():
    timestamp = "2023-03-15 12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    assert result == expected


def test_parse_timestamp_safely_slash_separated_format():
    timestamp = "2023/03/15 12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.strptime(timestamp, "%Y/%m/%d %H:%M:%S")
    assert result == expected


def test_parse_timestamp_safely_dot_separated_format():
    timestamp = "15.03.2023 12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.strptime(timestamp, "%d.%m.%Y %H:%M:%S")
    assert result == expected


def test_parse_timestamp_safely_unparsable_format():
    timestamp = "invalid-timestamp"
    with pytest.raises(ValueError):
        parse_timestamp_safely(timestamp)


def test_parse_timestamp_safely_with_timezone_info():
    timestamp = "2023-03-15T12:34:56 MESZ"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromisoformat("2023-03-15T12:34:56")
    assert result == expected


def test_parse_timestamp_safely_empty_string():
    timestamp = ""
    with pytest.raises(ValueError):
        parse_timestamp_safely(timestamp)


# New tests for epoch timestamp handling


def test_parse_timestamp_safely_epoch_int():
    timestamp = 1678885200  # 2023-03-15T12:00:00 UTC
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromtimestamp(timestamp)
    assert result == expected


def test_parse_timestamp_safely_epoch_float():
    timestamp = 1678885200.5  # 2023-03-15T12:00:00.5 UTC
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromtimestamp(timestamp)
    assert result == expected


def test_parse_timestamp_safely_epoch_decimal():
    timestamp = Decimal("1678885200.5")  # 2023-03-15T12:00:00.5 UTC
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromtimestamp(float(timestamp))
    assert result == expected


def test_parse_timestamp_safely_epoch_string():
    timestamp = "1678885200"  # 2023-03-15T12:00:00 UTC as string
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromtimestamp(float(timestamp))
    assert result == expected
