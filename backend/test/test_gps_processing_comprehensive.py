import math
from datetime import datetime, timedelta
from typing import Any, Dict

import pytest

from handlers.gps_processing import (
    calculate_speed_kmh,
    get_location_history,
    haversine_distance,
    is_outlier_temporal,
    parse_timestamp,
    reset_location_history,
)


class TestLocationHistoryManagement:

    def test_reset_location_history(self):
        """Test resetting location history"""
        # First populate some history
        from handlers import gps_processing

        gps_processing.location_history = [
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"}
        ]

        reset_location_history()
        history = get_location_history()

        assert history == []
        assert len(history) == 0

    def test_get_location_history(self):
        """Test getting location history"""
        from handlers import gps_processing

        # Reset first
        reset_location_history()

        # Add some test data
        test_data = [
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"},
            {"lat": 52.5300, "lon": 13.4150, "time": "2023-04-14T12:01:00Z"},
        ]
        gps_processing.location_history = test_data

        history = get_location_history()

        assert len(history) == 2
        assert history == test_data

    def test_location_history_persistence(self):
        """Test that location history persists between function calls"""
        from handlers import gps_processing

        reset_location_history()

        # Add data directly to the global variable
        gps_processing.location_history.append(
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"}
        )

        history = get_location_history()
        assert len(history) == 1

        # Add more data
        gps_processing.location_history.append(
            {"lat": 52.5300, "lon": 13.4150, "time": "2023-04-14T12:01:00Z"}
        )

        history = get_location_history()
        assert len(history) == 2


class TestTimestampParsing:

    def test_parse_timestamp_iso_format(self):
        """Test parsing ISO format timestamp"""
        timestamp = "2023-04-14T12:34:56"
        result = parse_timestamp(timestamp)

        expected = datetime.fromisoformat(timestamp)
        assert result == expected

    def test_parse_timestamp_with_z_suffix(self):
        """Test parsing timestamp with Z suffix"""
        timestamp = "2023-04-14T12:34:56Z"
        result = parse_timestamp(timestamp)

        expected = datetime.fromisoformat("2023-04-14T12:34:56")
        assert result == expected

    def test_parse_timestamp_with_timezone_offset(self):
        """Test parsing timestamp with timezone offset"""
        timestamp = "2023-04-14T12:34:56+02:00"
        result = parse_timestamp(timestamp)

        # Should strip timezone and parse the base time
        expected = datetime.fromisoformat("2023-04-14T12:34:56")
        assert result == expected

    def test_parse_timestamp_with_negative_timezone(self):
        """Test parsing timestamp with negative timezone offset"""
        timestamp = "2023-04-14T12:34:56-05:00"
        result = parse_timestamp(timestamp)

        # The function keeps timezone info when parsing
        expected = datetime.fromisoformat("2023-04-14T12:34:56-05:00")
        assert result == expected

    def test_parse_timestamp_multiple_plus_signs(self):
        """Test parsing timestamp with multiple plus signs (edge case)"""
        # This tests the rsplit behavior
        timestamp = "2023-04-14T12:34:56+02:00+extra"
        result = parse_timestamp(timestamp)

        # Should split on the last + and parse the first part
        expected = datetime.fromisoformat("2023-04-14T12:34:56+02:00")
        assert result == expected

    def test_parse_timestamp_invalid_format(self):
        """Test parsing invalid timestamp format"""
        timestamp = "invalid-timestamp"

        with pytest.raises(ValueError):
            parse_timestamp(timestamp)


class TestHaversineDistance:

    def test_haversine_distance_same_point(self):
        """Test distance calculation for same point"""
        lat, lon = 52.5200, 13.4050
        distance = haversine_distance(lat, lon, lat, lon)

        assert distance == 0.0

    def test_haversine_distance_known_points(self):
        """Test distance calculation between known points"""
        # Berlin to Paris (approximate)
        berlin_lat, berlin_lon = 52.5200, 13.4050
        paris_lat, paris_lon = 48.8566, 2.3522

        distance = haversine_distance(berlin_lat, berlin_lon, paris_lat, paris_lon)

        # Approximate distance Berlin-Paris is around 878km
        assert 870000 < distance < 890000

    def test_haversine_distance_close_points(self):
        """Test distance calculation for very close points"""
        lat1, lon1 = 52.5200, 13.4050
        lat2, lon2 = 52.5201, 13.4051  # Very close points

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be a small distance (less than 200 meters)
        assert 0 < distance < 200

    def test_haversine_distance_negative_coordinates(self):
        """Test distance calculation with negative coordinates"""
        # Sydney (negative coordinates)
        lat1, lon1 = -33.8688, 151.2093
        # Close point
        lat2, lon2 = -33.8689, 151.2094

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should calculate a small distance
        assert 0 < distance < 50

    def test_haversine_distance_equator_crossing(self):
        """Test distance calculation crossing equator"""
        lat1, lon1 = 1.0, 0.0  # North of equator
        lat2, lon2 = -1.0, 0.0  # South of equator

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be approximately 222 km (2 degrees at equator)
        assert 220000 < distance < 225000


class TestSpeedCalculation:

    def test_calculate_speed_normal(self):
        """Test normal speed calculation"""
        distance_meters = 1000  # 1 km
        time_diff_seconds = 60  # 1 minute

        speed = calculate_speed_kmh(distance_meters, time_diff_seconds)

        # 1 km in 1 minute = 60 km/h
        assert abs(speed - 60.0) < 0.001  # Allow for floating point precision

    def test_calculate_speed_zero_time(self):
        """Test speed calculation with zero time difference"""
        distance_meters = 1000
        time_diff_seconds = 0

        speed = calculate_speed_kmh(distance_meters, time_diff_seconds)

        # Should return infinity
        assert speed == float("inf")

    def test_calculate_speed_negative_time(self):
        """Test speed calculation with negative time difference"""
        distance_meters = 1000
        time_diff_seconds = -60

        speed = calculate_speed_kmh(distance_meters, time_diff_seconds)

        # Should return infinity
        assert speed == float("inf")

    def test_calculate_speed_very_small_time(self):
        """Test speed calculation with very small time difference"""
        distance_meters = 1000
        time_diff_seconds = 0.001  # 1 millisecond

        speed = calculate_speed_kmh(distance_meters, time_diff_seconds)

        # Should return very high speed
        expected_speed = (1000 / 0.001) * 3.6  # 3,600,000 km/h
        assert speed == expected_speed

    def test_calculate_speed_zero_distance(self):
        """Test speed calculation with zero distance"""
        distance_meters = 0
        time_diff_seconds = 60

        speed = calculate_speed_kmh(distance_meters, time_diff_seconds)

        # Should return 0
        assert speed == 0.0

    def test_calculate_speed_realistic_scenarios(self):
        """Test realistic speed calculation scenarios"""
        scenarios = [
            # (distance_m, time_s, expected_kmh)
            (100, 10, 36.0),  # 100m in 10s = 36 km/h
            (500, 30, 60.0),  # 500m in 30s = 60 km/h
            (2000, 60, 120.0),  # 2km in 1min = 120 km/h
            (50, 5, 36.0),  # 50m in 5s = 36 km/h
        ]

        for distance, time_s, expected in scenarios:
            speed = calculate_speed_kmh(distance, time_s)
            assert abs(speed - expected) < 0.1  # Allow small floating point differences


class TestOutlierDetection:

    def setup_method(self):
        """Setup method called before each test"""
        reset_location_history()

    def test_is_outlier_temporal_insufficient_history(self):
        """Test outlier detection with insufficient history"""
        location = {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"}

        is_outlier, reason = is_outlier_temporal(location)

        assert not is_outlier
        assert reason == "Insufficient history"

    def test_is_outlier_temporal_normal_movement(self):
        """Test outlier detection with normal movement"""
        from handlers import gps_processing

        # Add history
        gps_processing.location_history = [
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"}
        ]

        # Normal movement (1 km in 1 minute = 60 km/h)
        new_location = {
            "lat": 52.5300,  # About 1 km north
            "lon": 13.4050,
            "time": "2023-04-14T12:01:00Z",
        }

        is_outlier, reason = is_outlier_temporal(new_location)

        assert not is_outlier
        # Should pass speed test

    def test_is_outlier_temporal_unrealistic_speed(self):
        """Test outlier detection with unrealistic speed"""
        from handlers import gps_processing

        # Add history
        gps_processing.location_history = [
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"}
        ]

        # Unrealistic movement (very far in short time)
        new_location = {
            "lat": 53.5200,  # About 111 km north
            "lon": 13.4050,
            "time": "2023-04-14T12:00:01Z",  # Only 1 second later
        }

        is_outlier, reason = is_outlier_temporal(new_location)

        assert is_outlier
        assert "speed" in reason.lower()

    def test_is_outlier_temporal_missing_timestamps(self):
        """Test outlier detection when timestamps are missing"""
        from handlers import gps_processing

        # Add history without time
        gps_processing.location_history = [
            {
                "lat": 52.5200,
                "lon": 13.4050,
                # No 'time' field
            }
        ]

        # New location without time
        new_location = {
            "lat": 52.5300,
            "lon": 13.4050,
            # No 'time' field
        }

        is_outlier, reason = is_outlier_temporal(new_location)

        # Should fall back to distance-only check or detect outlier due to algorithm specifics
        # The algorithm might detect this as an outlier based on distance alone
        assert is_outlier  # Distance-based detection

    def test_is_outlier_temporal_distance_threshold(self):
        """Test outlier detection using distance threshold fallback"""
        from handlers import gps_processing

        # Add history without time
        gps_processing.location_history = [{"lat": 52.5200, "lon": 13.4050}]

        # New location very far away (should trigger distance threshold)
        new_location = {"lat": 53.5200, "lon": 13.4050}  # Very far

        is_outlier, reason = is_outlier_temporal(new_location, threshold_meters=1000)

        assert is_outlier
        assert "distance" in reason.lower()

    def test_is_outlier_temporal_custom_thresholds(self):
        """Test outlier detection with custom thresholds"""
        from handlers import gps_processing

        # Add history
        gps_processing.location_history = [
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"}
        ]

        # Movement that would be OK with default speed limit but not with custom
        new_location = {
            "lat": 52.5250,  # About 500m north
            "lon": 13.4050,
            "time": "2023-04-14T12:00:30Z",  # 30 seconds later = 60 km/h
        }

        # With very low speed limit, this should be an outlier
        is_outlier, reason = is_outlier_temporal(new_location, max_speed_kmh=30)

        assert is_outlier
        assert "speed" in reason.lower()

    def test_is_outlier_temporal_edge_case_same_location(self):
        """Test outlier detection when location doesn't change"""
        from handlers import gps_processing

        # Add history
        gps_processing.location_history = [
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"}
        ]

        # Exact same location
        new_location = {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:01:00Z"}

        is_outlier, reason = is_outlier_temporal(new_location)

        # Zero distance should not be an outlier
        assert not is_outlier

    def test_is_outlier_temporal_timestamp_parsing_error(self):
        """Test outlier detection with timestamp parsing errors"""
        from handlers import gps_processing

        # Add history with invalid time format
        gps_processing.location_history = [
            {"lat": 52.5200, "lon": 13.4050, "time": "invalid-timestamp"}
        ]

        new_location = {"lat": 52.5300, "lon": 13.4050, "time": "also-invalid"}

        # Should handle parsing error gracefully and fall back to distance check
        is_outlier, reason = is_outlier_temporal(new_location)

        # Should not crash and should fall back to distance-based check
        assert isinstance(is_outlier, bool)
        assert isinstance(reason, str)


class TestIntegrationScenarios:

    def setup_method(self):
        """Setup method called before each test"""
        reset_location_history()

    def test_realistic_driving_scenario(self):
        """Test a realistic driving scenario"""
        from handlers import gps_processing

        # Simulate a realistic drive
        locations = [
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"},  # Start
            {
                "lat": 52.5250,
                "lon": 13.4100,
                "time": "2023-04-14T12:01:00Z",
            },  # 1 min later
            {
                "lat": 52.5300,
                "lon": 13.4150,
                "time": "2023-04-14T12:02:00Z",
            },  # 2 min later
            {
                "lat": 52.5350,
                "lon": 13.4200,
                "time": "2023-04-14T12:03:00Z",
            },  # 3 min later
        ]

        outliers = []

        # Process each location
        for i, location in enumerate(locations):
            if i == 0:
                gps_processing.location_history.append(location)
                continue

            is_outlier, reason = is_outlier_temporal(location)
            if is_outlier:
                outliers.append((location, reason))
            else:
                gps_processing.location_history.append(location)

        # Should not detect any outliers in this realistic scenario
        assert len(outliers) == 0
        assert len(get_location_history()) == 4

    def test_gps_glitch_scenario(self):
        """Test scenario with GPS glitch"""
        from handlers import gps_processing

        # Simulate GPS glitch
        locations = [
            {"lat": 52.5200, "lon": 13.4050, "time": "2023-04-14T12:00:00Z"},  # Start
            {"lat": 52.5250, "lon": 13.4100, "time": "2023-04-14T12:01:00Z"},  # Normal
            {
                "lat": 55.7558,
                "lon": 37.6176,
                "time": "2023-04-14T12:01:01Z",
            },  # Glitch: Moscow!
            {
                "lat": 52.5300,
                "lon": 13.4150,
                "time": "2023-04-14T12:02:00Z",
            },  # Back to normal
        ]

        outliers = []

        # Process each location
        for i, location in enumerate(locations):
            if i == 0:
                gps_processing.location_history.append(location)
                continue

            is_outlier, reason = is_outlier_temporal(location)
            if is_outlier:
                outliers.append((location, reason))
            else:
                gps_processing.location_history.append(location)

        # Should detect the Moscow location as an outlier
        assert len(outliers) == 1
        assert outliers[0][0]["lat"] == 55.7558  # The Moscow location

        # History should not include the outlier
        history = get_location_history()
        moscow_in_history = any(loc["lat"] == 55.7558 for loc in history)
        assert not moscow_in_history

    def test_stationary_vehicle_scenario(self):
        """Test scenario with stationary vehicle"""
        from handlers import gps_processing

        # Simulate parked vehicle with slight GPS variations
        base_lat, base_lon = 52.5200, 13.4050
        locations = []

        for i in range(5):
            # Small GPS variations while parked
            locations.append(
                {
                    "lat": base_lat + (i * 0.0001),  # Very small variations
                    "lon": base_lon + (i * 0.0001),
                    "time": f"2023-04-14T12:0{i}:00Z",
                }
            )

        outliers = []

        # Process each location
        for i, location in enumerate(locations):
            if i == 0:
                gps_processing.location_history.append(location)
                continue

            is_outlier, reason = is_outlier_temporal(location)
            if is_outlier:
                outliers.append((location, reason))
            else:
                gps_processing.location_history.append(location)

        # Should not detect outliers for small parking variations
        assert len(outliers) == 0
        assert len(get_location_history()) == 5

    def test_highway_driving_scenario(self):
        """Test scenario with highway driving (high but realistic speeds)"""
        from handlers import gps_processing

        # Simulate highway driving at 120 km/h
        base_lat = 52.5200
        base_lon = 13.4050
        locations = []

        # Calculate distance for 120 km/h in 1 minute intervals
        # 120 km/h = 2 km/min = 2000m/min
        lat_change_per_minute = 2000 / 111000  # Approximate: 1 degree lat ≈ 111km

        for i in range(4):
            locations.append(
                {
                    "lat": base_lat + (i * lat_change_per_minute),
                    "lon": base_lon,
                    "time": f"2023-04-14T12:0{i}:00Z",
                }
            )

        outliers = []

        # Process each location
        for i, location in enumerate(locations):
            if i == 0:
                gps_processing.location_history.append(location)
                continue

            # Use higher speed limit for highway scenario
            is_outlier, reason = is_outlier_temporal(location, max_speed_kmh=150)
            if is_outlier:
                outliers.append((location, reason))
            else:
                gps_processing.location_history.append(location)

        # Should not detect outliers for realistic highway speeds
        assert len(outliers) == 0
