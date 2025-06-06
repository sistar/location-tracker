import pytest
import json
import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, call
import math

# Import the module being tested
import handlers.processor as processor


class TestProcessorUtilityFunctions:
    """Test utility functions in processor.py"""
    
    def test_parse_timestamp_iso_format(self):
        """Test parsing ISO format timestamps"""
        timestamp_str = "2023-03-15T12:34:56"
        result = processor.parse_timestamp(timestamp_str)
        expected = datetime.datetime.fromisoformat(timestamp_str)
        assert result == expected
    
    def test_parse_timestamp_with_timezone(self):
        """Test parsing timestamps with timezone"""
        timestamp_str = "2023-03-15T12:34:56+02:00"
        result = processor.parse_timestamp(timestamp_str)
        expected = datetime.datetime.fromisoformat("2023-03-15T12:34:56")
        assert result == expected
    
    def test_parse_timestamp_with_z_suffix(self):
        """Test parsing timestamps with Z suffix"""
        timestamp_str = "2023-03-15T12:34:56Z"
        result = processor.parse_timestamp(timestamp_str)
        expected = datetime.datetime.fromisoformat("2023-03-15T12:34:56")
        assert result == expected
    
    def test_haversine_distance_same_point(self):
        """Test haversine distance calculation for same point"""
        lat, lon = 52.5200, 13.4050
        distance = processor.haversine_distance(lat, lon, lat, lon)
        assert distance == 0.0
    
    def test_haversine_distance_known_points(self):
        """Test haversine distance calculation for known points"""
        # Berlin to Munich (approximate distance ~504 km)
        berlin_lat, berlin_lon = 52.5200, 13.4050
        munich_lat, munich_lon = 48.1351, 11.5820
        
        distance = processor.haversine_distance(berlin_lat, berlin_lon, munich_lat, munich_lon)
        
        # Allow for some tolerance in the calculation
        assert 500000 < distance < 510000  # approximately 504 km
    
    def test_calculate_speed_kmh_normal(self):
        """Test speed calculation with normal values"""
        distance_meters = 1000  # 1 km
        time_diff_seconds = 3600  # 1 hour
        
        speed = processor.calculate_speed_kmh(distance_meters, time_diff_seconds)
        assert speed == 1.0  # 1 km/h
    
    def test_calculate_speed_kmh_zero_time(self):
        """Test speed calculation with zero time difference"""
        distance_meters = 1000
        time_diff_seconds = 0
        
        speed = processor.calculate_speed_kmh(distance_meters, time_diff_seconds)
        assert speed == float('inf')
    
    def test_calculate_speed_kmh_negative_time(self):
        """Test speed calculation with negative time difference"""
        distance_meters = 1000
        time_diff_seconds = -3600
        
        speed = processor.calculate_speed_kmh(distance_meters, time_diff_seconds)
        assert speed == float('inf')
    
    def test_is_significant_movement_first_location(self):
        """Test significant movement with no previous location"""
        new_loc = {"lat": 52.5200, "lon": 13.4050}
        result = processor.is_significant_movement(new_loc, None)
        assert result is True
    
    def test_is_significant_movement_above_threshold(self):
        """Test significant movement above threshold"""
        previous_loc = {"lat": 52.5200, "lon": 13.4050}
        new_loc = {"lat": 52.5201, "lon": 13.4051}  # About 11 meters away
        
        result = processor.is_significant_movement(new_loc, previous_loc, min_distance=10)
        assert result is True
    
    def test_is_significant_movement_below_threshold(self):
        """Test significant movement below threshold"""
        previous_loc = {"lat": 52.5200, "lon": 13.4050}
        new_loc = {"lat": 52.52001, "lon": 13.40501}  # About 1 meter away
        
        result = processor.is_significant_movement(new_loc, previous_loc, min_distance=10)
        assert result is False


class TestLocationHistory:
    """Test location history management"""
    
    def setup_method(self):
        """Reset location history before each test"""
        processor.reset_location_history()
    
    def test_add_to_location_history_empty(self):
        """Test adding first location to empty history"""
        location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(location)
        
        history = processor.get_location_history()
        assert len(history) == 1
        assert history[0] == location
    
    def test_add_to_location_history_max_size(self):
        """Test that history maintains maximum size"""
        # Add more locations than max_history (default 10)
        for i in range(15):
            location = {"lat": 52.5200 + i*0.001, "lon": 13.4050 + i*0.001, "timestamp": 1678885200 + i}
            processor.add_to_location_history(location, max_history=10)
        
        history = processor.get_location_history()
        assert len(history) == 10
        # Check that the oldest locations were removed
        assert history[0]["lat"] == 52.5200 + 5*0.001  # Should be the 6th location added
    
    def test_reset_location_history(self):
        """Test resetting location history"""
        location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(location)
        
        processor.reset_location_history()
        history = processor.get_location_history()
        assert len(history) == 0


class TestOutlierDetection:
    """Test outlier detection logic"""
    
    def setup_method(self):
        """Reset location history before each test"""
        processor.reset_location_history()
    
    def test_is_outlier_temporal_no_history(self):
        """Test outlier detection with no history"""
        location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        is_outlier, reason = processor.is_outlier_temporal(location)
        
        assert is_outlier is False
        assert "Insufficient history" in reason
    
    def test_is_outlier_temporal_reasonable_speed(self):
        """Test outlier detection with reasonable speed"""
        # Add a location to history
        prev_location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(prev_location)
        
        # New location 1 km away, 1 hour later (1 km/h speed)
        new_location = {"lat": 52.5290, "lon": 13.4050, "timestamp": 1678885200 + 3600}
        
        is_outlier, reason = processor.is_outlier_temporal(new_location, max_speed_kmh=150)
        assert is_outlier is False
        assert "Reasonable movement" in reason
    
    def test_is_outlier_temporal_unrealistic_speed(self):
        """Test outlier detection with unrealistic speed"""
        # Add a location to history
        prev_location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(prev_location)
        
        # New location 100 km away, 1 minute later (6000 km/h speed)
        new_location = {"lat": 53.4200, "lon": 13.4050, "timestamp": 1678885200 + 60}
        
        is_outlier, reason = processor.is_outlier_temporal(new_location, max_speed_kmh=150)
        assert is_outlier is True
        assert "Unrealistic speed" in reason
    
    def test_is_outlier_temporal_large_distance_short_time(self):
        """Test outlier detection with large distance in short time"""
        prev_location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(prev_location)
        
        # New location 200m away, 5 seconds later
        new_location = {"lat": 52.5218, "lon": 13.4050, "timestamp": 1678885200 + 5}
        
        is_outlier, reason = processor.is_outlier_temporal(new_location, threshold_meters=100)
        assert is_outlier is True
        assert "Large distance in short time" in reason
    
    def test_is_outlier_temporal_same_timestamp(self):
        """Test outlier detection with same timestamp"""
        prev_location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(prev_location)
        
        # Same timestamp, large distance
        new_location = {"lat": 52.6200, "lon": 13.4050, "timestamp": 1678885200}
        
        is_outlier, reason = processor.is_outlier_temporal(new_location, threshold_meters=100)
        assert is_outlier is True
        assert "Distance threshold exceeded" in reason and "same timestamp" in reason
    
    def test_is_outlier_temporal_missing_timestamps(self):
        """Test outlier detection with missing timestamps"""
        prev_location = {"lat": 52.5200, "lon": 13.4050}  # No timestamp
        processor.add_to_location_history(prev_location)
        
        new_location = {"lat": 52.6200, "lon": 13.4050}  # No timestamp
        
        is_outlier, reason = processor.is_outlier_temporal(new_location, threshold_meters=100)
        assert is_outlier is True
        assert "missing timestamp" in reason


class TestPrepareProcessedItem:
    """Test preparation of items for DynamoDB storage"""
    
    def test_prepare_processed_item_basic(self):
        """Test basic item preparation"""
        location_data = {
            "lat": 52.5200,
            "lon": 13.4050,
            "timestamp": 1678885200,
            "device_id": "vehicle_01"
        }
        
        result = processor.prepare_processed_item(location_data)
        
        assert result["id"] == "vehicle_01"
        assert result["timestamp"] == 1678885200
        assert result["lat"] == 52.5200
        assert result["lon"] == 13.4050
        assert "timestamp_iso" in result
        assert "processed_at" in result
    
    def test_prepare_processed_item_default_device_id(self):
        """Test item preparation with default device_id"""
        location_data = {
            "lat": 52.5200,
            "lon": 13.4050,
            "timestamp": 1678885200
        }
        
        result = processor.prepare_processed_item(location_data)
        assert result["id"] == "vehicle_01"
    
    @patch('handlers.processor.datetime')
    def test_prepare_processed_item_default_timestamp(self, mock_datetime):
        """Test item preparation with default timestamp"""
        mock_datetime.datetime.utcnow.return_value.timestamp.return_value = 1678885200
        mock_datetime.datetime.fromtimestamp.return_value.isoformat.return_value = "2023-03-15T12:00:00"
        
        location_data = {
            "lat": 52.5200,
            "lon": 13.4050,
            "device_id": "vehicle_01"
        }
        
        result = processor.prepare_processed_item(location_data)
        assert result["timestamp"] == 1678885200
    
    def test_prepare_processed_item_elevation_with_suffix(self):
        """Test item preparation with elevation having 'M' suffix"""
        location_data = {
            "lat": 52.5200,
            "lon": 13.4050,
            "timestamp": 1678885200,
            "ele": "123.5M"
        }
        
        result = processor.prepare_processed_item(location_data)
        assert result["ele"] == 123.5
    
    def test_prepare_processed_item_elevation_without_suffix(self):
        """Test item preparation with numeric elevation"""
        location_data = {
            "lat": 52.5200,
            "lon": 13.4050,
            "timestamp": 1678885200,
            "ele": 123.5
        }
        
        result = processor.prepare_processed_item(location_data)
        assert result["ele"] == 123.5


class TestProcessSingleLocation:
    """Test single location processing"""
    
    def setup_method(self):
        """Reset location history and set up mocks before each test"""
        processor.reset_location_history()
    
    @patch('handlers.processor.table')
    def test_process_single_location_success(self, mock_table):
        """Test successful processing of a single location"""
        location_data = {
            "lat": 52.5200,
            "lon": 13.4050,
            "timestamp": 1678885200,
            "device_id": "vehicle_01"
        }
        
        result = processor.process_single_location(location_data, skip_outlier_detection=True)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "Location processed and stored"
        
        # Verify DynamoDB put_item was called
        mock_table.put_item.assert_called_once()
    
    @patch('handlers.processor.table')
    def test_process_single_location_outlier_detected(self, mock_table):
        """Test processing when outlier is detected"""
        # Add a location to history
        prev_location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(prev_location)
        
        # Try to add an outlier location (very far away, short time)
        outlier_location = {
            "lat": 53.5200,  # About 111 km away
            "lon": 13.4050,
            "timestamp": 1678885200 + 60  # 1 minute later
        }
        
        result = processor.process_single_location(outlier_location)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "Unrealistic speed" in body["status"]
        
        # Verify DynamoDB put_item was NOT called
        mock_table.put_item.assert_not_called()
    
    @patch('handlers.processor.table')
    def test_process_single_location_insufficient_movement(self, mock_table):
        """Test processing when movement is insufficient"""
        # Add a location to history
        prev_location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(prev_location)
        
        # Try to add a location very close to the previous one
        close_location = {
            "lat": 52.52001,  # About 1 meter away
            "lon": 13.40501,
            "timestamp": 1678885200 + 60
        }
        
        result = processor.process_single_location(close_location)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "Insufficient movement"
        
        # Verify DynamoDB put_item was NOT called
        mock_table.put_item.assert_not_called()
    
    @patch('handlers.processor.table')
    def test_process_single_location_skip_outlier_detection(self, mock_table):
        """Test processing with outlier detection skipped"""
        # Add a location to history that would normally trigger outlier detection
        prev_location = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        processor.add_to_location_history(prev_location)
        
        outlier_location = {
            "lat": 53.5200,  # Far away
            "lon": 13.4050,
            "timestamp": 1678885200 + 60  # Short time
        }
        
        result = processor.process_single_location(outlier_location, skip_outlier_detection=True)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "Location processed and stored"
        
        # Verify DynamoDB put_item was called
        mock_table.put_item.assert_called_once()
    
    @patch('handlers.processor.table')
    def test_process_single_location_error_handling(self, mock_table):
        """Test error handling in single location processing"""
        # Configure mock to raise an exception
        mock_table.put_item.side_effect = Exception("DynamoDB error")
        
        location_data = {
            "lat": 52.5200,
            "lon": 13.4050,
            "timestamp": 1678885200
        }
        
        result = processor.process_single_location(location_data, skip_outlier_detection=True)
        
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body
        assert "DynamoDB error" in body["error"]


class TestProcessLocation:
    """Test main process_location handler"""
    
    def setup_method(self):
        """Reset location history before each test"""
        processor.reset_location_history()
    
    @patch('handlers.processor.process_single_location')
    def test_process_location_http_api_gateway(self, mock_process_single):
        """Test processing HTTP API Gateway event"""
        mock_process_single.return_value = {
            "statusCode": 200,
            "body": json.dumps({"status": "success"})
        }
        
        event = {
            "body": json.dumps({
                "lat": 52.5200,
                "lon": 13.4050,
                "timestamp": 1678885200
            })
        }
        
        result = processor.process_location(event, None)
        
        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]
        mock_process_single.assert_called_once()
    
    @patch('handlers.processor.process_single_location')
    def test_process_location_http_with_skip_outlier_detection(self, mock_process_single):
        """Test processing HTTP event with skip_outlier_detection parameter"""
        mock_process_single.return_value = {
            "statusCode": 200,
            "body": json.dumps({"status": "success"})
        }
        
        event = {
            "body": json.dumps({
                "lat": 52.5200,
                "lon": 13.4050,
                "timestamp": 1678885200,
                "skip_outlier_detection": True
            })
        }
        
        result = processor.process_location(event, None)
        
        assert result["statusCode"] == 200
        # Verify skip_outlier_detection was passed correctly
        call_args = mock_process_single.call_args
        assert call_args[1]["skip_outlier_detection"] is True
        # Verify skip_outlier_detection was removed from location data
        location_data = call_args[0][0]
        assert "skip_outlier_detection" not in location_data
    
    @patch('handlers.processor.process_single_location')
    def test_process_location_batch_processing(self, mock_process_single):
        """Test processing batch of locations"""
        mock_process_single.return_value = {
            "statusCode": 200,
            "body": json.dumps({"status": "success"})
        }
        
        event = [
            {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200},
            {"lat": 52.5201, "lon": 13.4051, "timestamp": 1678885260}
        ]
        
        result = processor.process_location(event, None)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "Processed 2 locations" in body["status"]
        assert mock_process_single.call_count == 2
    
    @patch('handlers.processor.process_single_location')
    def test_process_location_single_iot_event(self, mock_process_single):
        """Test processing single IoT event"""
        mock_process_single.return_value = {
            "statusCode": 200,
            "body": json.dumps({"status": "success"})
        }
        
        event = {"lat": 52.5200, "lon": 13.4050, "timestamp": 1678885200}
        
        result = processor.process_location(event, None)
        
        assert result["statusCode"] == 200
        mock_process_single.assert_called_once_with(event)
    
    def test_process_location_error_handling_http(self):
        """Test error handling for HTTP events"""
        # Invalid JSON in body
        event = {
            "body": "invalid json"
        }
        
        result = processor.process_location(event, None)
        
        assert result["statusCode"] == 500
        assert "Access-Control-Allow-Origin" in result["headers"]
        body = json.loads(result["body"])
        assert "error" in body
    
    @patch('handlers.processor.process_single_location')
    def test_process_location_error_handling_iot(self, mock_process_single):
        """Test error handling for IoT events"""
        mock_process_single.side_effect = Exception("Processing error")
        
        event = {"lat": 52.5200, "lon": 13.4050}
        
        result = processor.process_location(event, None)
        
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body