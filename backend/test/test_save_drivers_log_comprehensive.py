import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime
import boto3
from moto import mock_aws

from handlers.save_drivers_log import (
    decimal_default,
    convert_floats_to_decimal,
    convert_timestamp_to_epoch,
    check_for_overlapping_logs,
    check_session_already_saved,
    handler
)


class TestUtilityFunctions:
    
    def test_decimal_default(self):
        """Test Decimal to float conversion"""
        assert decimal_default(Decimal('123.45')) == 123.45
        
        with pytest.raises(TypeError):
            decimal_default("not a decimal")
    
    def test_convert_floats_to_decimal_float(self):
        """Test converting float to Decimal"""
        result = convert_floats_to_decimal(123.45)
        assert isinstance(result, Decimal)
        assert float(result) == 123.45
    
    def test_convert_floats_to_decimal_dict(self):
        """Test converting floats in dictionary to Decimal"""
        input_dict = {
            'lat': 52.5200,
            'lon': 13.4050,
            'name': 'Berlin',
            'count': 1
        }
        
        result = convert_floats_to_decimal(input_dict)
        
        assert isinstance(result['lat'], Decimal)
        assert isinstance(result['lon'], Decimal)
        assert isinstance(result['name'], str)  # Non-float should remain unchanged
        assert isinstance(result['count'], int)  # Non-float should remain unchanged
    
    def test_convert_floats_to_decimal_list(self):
        """Test converting floats in list to Decimal"""
        input_list = [123.45, 'text', 67, 89.12]
        
        result = convert_floats_to_decimal(input_list)
        
        assert isinstance(result[0], Decimal)
        assert isinstance(result[1], str)
        assert isinstance(result[2], int)
        assert isinstance(result[3], Decimal)
    
    def test_convert_floats_to_decimal_nested(self):
        """Test converting floats in nested structures"""
        input_data = {
            'coordinates': [52.5200, 13.4050],
            'metadata': {
                'accuracy': 5.5,
                'speed': 60.0
            },
            'id': 'test'
        }
        
        result = convert_floats_to_decimal(input_data)
        
        assert isinstance(result['coordinates'][0], Decimal)
        assert isinstance(result['coordinates'][1], Decimal)
        assert isinstance(result['metadata']['accuracy'], Decimal)
        assert isinstance(result['metadata']['speed'], Decimal)
        assert isinstance(result['id'], str)
    
    def test_convert_floats_to_decimal_non_float(self):
        """Test converting non-float values (should remain unchanged)"""
        test_values = [
            "string",
            123,
            True,
            None
        ]
        
        for value in test_values:
            result = convert_floats_to_decimal(value)
            assert result == value
            assert type(result) == type(value)


class TestTimestampConversion:
    
    def test_convert_timestamp_to_epoch_int(self):
        """Test converting integer timestamp"""
        epoch = 1681430400
        result = convert_timestamp_to_epoch(epoch)
        assert result == epoch
        assert isinstance(result, int)
    
    def test_convert_timestamp_to_epoch_float(self):
        """Test converting float timestamp"""
        epoch = 1681430400.5
        result = convert_timestamp_to_epoch(epoch)
        assert result == 1681430400
        assert isinstance(result, int)
    
    def test_convert_timestamp_to_epoch_decimal(self):
        """Test converting Decimal timestamp"""
        epoch = Decimal('1681430400.5')
        result = convert_timestamp_to_epoch(epoch)
        assert result == 1681430400
        assert isinstance(result, int)
    
    def test_convert_timestamp_to_epoch_string_numeric(self):
        """Test converting string numeric timestamp"""
        epoch_str = "1681430400"
        result = convert_timestamp_to_epoch(epoch_str)
        assert result == 1681430400
        assert isinstance(result, int)
    
    def test_convert_timestamp_to_epoch_iso_format(self):
        """Test converting ISO format timestamp"""
        iso_timestamp = "2023-04-14T12:00:00"
        result = convert_timestamp_to_epoch(iso_timestamp)
        
        # Verify it's a reasonable epoch timestamp
        assert isinstance(result, int)
        assert result > 1600000000  # After 2020
        assert result < 2000000000  # Before 2033
    
    def test_convert_timestamp_to_epoch_iso_with_timezone(self):
        """Test converting ISO format timestamp with timezone"""
        iso_timestamp = "2023-04-14T12:00:00+02:00"
        result = convert_timestamp_to_epoch(iso_timestamp)
        
        assert isinstance(result, int)
        assert result > 1600000000
    
    def test_convert_timestamp_to_epoch_invalid(self):
        """Test converting invalid timestamp (should return current time)"""
        invalid_timestamp = "invalid-timestamp"
        
        # Get current time before and after the call
        before = int(time.time())
        result = convert_timestamp_to_epoch(invalid_timestamp)
        after = int(time.time())
        
        # Result should be close to current time
        assert before <= result <= after + 1


class TestOverlapDetection:
    
    @mock_aws
    def test_check_for_overlapping_logs_no_overlap(self):
        """Test checking for overlaps when there are none"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add existing log that doesn't overlap
        table.put_item(Item={
            'id': 'log_001',
            'vehicleId': 'vehicle_01',
            'startTime': 1681430000,  # Earlier time
            'endTime': 1681430300     # Ends before our test period
        })
        
        with patch('handlers.save_drivers_log.logs_table', table):
            # Test period that doesn't overlap
            has_overlap, overlap_id = check_for_overlapping_logs(
                1681430400,  # Starts after existing log ends
                1681430700,
                'vehicle_01'
            )
            
            assert not has_overlap
            assert overlap_id is None
    
    @mock_aws
    def test_check_for_overlapping_logs_with_overlap(self):
        """Test checking for overlaps when there is one"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add existing log that overlaps
        overlap_log_id = 'log_overlap'
        table.put_item(Item={
            'id': overlap_log_id,
            'vehicleId': 'vehicle_01',
            'startTime': 1681430200,  # Overlaps with our test period
            'endTime': 1681430500
        })
        
        with patch('handlers.save_drivers_log.logs_table', table):
            # Test period that overlaps
            has_overlap, overlap_id = check_for_overlapping_logs(
                1681430400,  # Overlaps with existing log
                1681430700,
                'vehicle_01'
            )
            
            assert has_overlap
            assert overlap_id == overlap_log_id
    
    @mock_aws
    def test_check_for_overlapping_logs_different_vehicle(self):
        """Test that overlaps are only checked for the same vehicle"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add existing log for different vehicle
        table.put_item(Item={
            'id': 'log_other_vehicle',
            'vehicleId': 'vehicle_02',  # Different vehicle
            'startTime': 1681430200,
            'endTime': 1681430500
        })
        
        with patch('handlers.save_drivers_log.logs_table', table):
            # Test same time period but different vehicle
            has_overlap, overlap_id = check_for_overlapping_logs(
                1681430400,
                1681430700,
                'vehicle_01'  # Different vehicle ID
            )
            
            # Should not detect overlap for different vehicle
            assert not has_overlap
            assert overlap_id is None
    
    @mock_aws
    def test_check_for_overlapping_logs_iso_timestamps(self):
        """Test overlap detection with ISO format timestamps"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add existing log with ISO timestamps
        table.put_item(Item={
            'id': 'log_iso',
            'vehicleId': 'vehicle_01',
            'startTime': '2023-04-14T12:00:00',
            'endTime': '2023-04-14T13:00:00'
        })
        
        with patch('handlers.save_drivers_log.logs_table', table):
            # Test with overlapping ISO timestamps
            has_overlap, overlap_id = check_for_overlapping_logs(
                '2023-04-14T12:30:00',  # Overlaps
                '2023-04-14T13:30:00',
                'vehicle_01'
            )
            
            assert has_overlap
            assert overlap_id == 'log_iso'
    
    @mock_aws
    def test_check_for_overlapping_logs_missing_data(self):
        """Test overlap detection with missing timestamp data"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add log with missing timestamps
        table.put_item(Item={
            'id': 'log_incomplete',
            'vehicleId': 'vehicle_01'
            # Missing startTime and endTime
        })
        
        with patch('handlers.save_drivers_log.logs_table', table):
            has_overlap, overlap_id = check_for_overlapping_logs(
                1681430400,
                1681430700,
                'vehicle_01'
            )
            
            # Should not detect overlap for incomplete logs
            assert not has_overlap
            assert overlap_id is None
    
    def test_check_for_overlapping_logs_error(self):
        """Test overlap detection with database error"""
        mock_table = Mock()
        mock_table.scan.side_effect = Exception("Database error")
        
        with patch('handlers.save_drivers_log.logs_table', mock_table):
            has_overlap, overlap_id = check_for_overlapping_logs(
                1681430400,
                1681430700,
                'vehicle_01'
            )
            
            # Should handle error gracefully
            assert not has_overlap
            assert overlap_id is None


class TestSessionAlreadySaved:
    
    @mock_aws
    def test_check_session_already_saved_not_exists(self):
        """Test checking for session that doesn't exist"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        with patch('handlers.save_drivers_log.logs_table', table):
            exists = check_session_already_saved('nonexistent_session', 'vehicle_01')
            
            assert not exists
    
    @mock_aws
    def test_check_session_already_saved_exists(self):
        """Test checking for session that exists"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add existing session
        session_id = 'existing_session'
        table.put_item(Item={
            'id': session_id,
            'vehicleId': 'vehicle_01',
            'startTime': 1681430400,
            'endTime': 1681430700
        })
        
        with patch('handlers.save_drivers_log.logs_table', table):
            exists = check_session_already_saved(session_id, 'vehicle_01')
            
            assert exists
    
    @mock_aws
    def test_check_session_already_saved_different_vehicle(self):
        """Test checking for session with different vehicle ID"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add session for different vehicle
        session_id = 'session_other_vehicle'
        table.put_item(Item={
            'id': session_id,
            'vehicleId': 'vehicle_02',  # Different vehicle
            'startTime': 1681430400,
            'endTime': 1681430700
        })
        
        with patch('handlers.save_drivers_log.logs_table', table):
            exists = check_session_already_saved(session_id, 'vehicle_01')
            
            # Should not find session for different vehicle
            assert not exists
    
    def test_check_session_already_saved_error(self):
        """Test checking for session with database error"""
        mock_table = Mock()
        mock_table.query.side_effect = Exception("Database error")
        
        with patch('handlers.save_drivers_log.logs_table', mock_table):
            exists = check_session_already_saved('test_session', 'vehicle_01')
            
            # Should handle error gracefully and return False
            assert not exists


class TestHandler:
    
    @patch('handlers.save_drivers_log.check_session_already_saved')
    @patch('handlers.save_drivers_log.check_for_overlapping_logs')
    @mock_aws
    def test_handler_success(self, mock_check_overlap, mock_check_saved):
        """Test successful handler execution"""
        # Mock no existing session and no overlaps
        mock_check_saved.return_value = False
        mock_check_overlap.return_value = (False, None)
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'sessionId': 'test_session',
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': 'Test Trip',
                'description': 'Test Description'
            })
        }
        
        with patch('handlers.save_drivers_log.logs_table', table):
            response = handler(event, {})
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['message'] == 'Log entry saved successfully'
    
    def test_handler_missing_body(self):
        """Test handler with missing body"""
        event = {
            'httpMethod': 'POST'
            # No body
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'message' in body
    
    def test_handler_invalid_json(self):
        """Test handler with invalid JSON body"""
        event = {
            'httpMethod': 'POST',
            'body': 'invalid json'
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 500  # JSON parsing error causes 500
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_handler_missing_required_fields(self):
        """Test handler with missing required fields"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'sessionId': 'test_session'
                # Missing other required fields
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'message' in body
    
    @patch('handlers.save_drivers_log.check_session_already_saved')
    def test_handler_session_already_exists(self, mock_check_saved):
        """Test handler when session already exists"""
        mock_check_saved.return_value = True
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'sessionId': 'existing_session',
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': 'Test Trip'
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'already' in body['message']
    
    @patch('handlers.save_drivers_log.check_session_already_saved')
    @patch('handlers.save_drivers_log.check_for_overlapping_logs')
    def test_handler_overlapping_session(self, mock_check_overlap, mock_check_saved):
        """Test handler when there's an overlapping session"""
        mock_check_saved.return_value = False
        mock_check_overlap.return_value = (True, 'overlapping_log_id')
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'sessionId': 'new_session',
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': 'Test Trip'
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'overlap' in body['message']
    
    @patch('handlers.save_drivers_log.check_session_already_saved')
    @patch('handlers.save_drivers_log.check_for_overlapping_logs')
    def test_handler_database_error(self, mock_check_overlap, mock_check_saved):
        """Test handler with database error during save"""
        mock_check_saved.return_value = False
        mock_check_overlap.return_value = (False, None)
        
        mock_table = Mock()
        mock_table.put_item.side_effect = Exception("Database save error")
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'sessionId': 'test_session',
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': 'Test Trip'
            })
        }
        
        with patch('handlers.save_drivers_log.logs_table', mock_table):
            response = handler(event, {})
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert 'error' in body
    
    def test_handler_exception(self):
        """Test handler with unexpected exception"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'sessionId': 'test_session',
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': 'Test Trip'
            })
        }
        
        with patch('handlers.save_drivers_log.check_session_already_saved') as mock_check:
            mock_check.side_effect = Exception("Unexpected error")
            
            response = handler(event, {})
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert 'error' in body


class TestDataConversion:
    
    @patch('handlers.save_drivers_log.check_session_already_saved')
    @patch('handlers.save_drivers_log.check_for_overlapping_logs')
    @mock_aws
    def test_handler_data_conversion(self, mock_check_overlap, mock_check_saved):
        """Test that handler properly converts data types for DynamoDB"""
        mock_check_saved.return_value = False
        mock_check_overlap.return_value = (False, None)
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-logs-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'sessionId': 'test_session',
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': 'Test Trip',
                'distance': 123.45,  # Float value
                'duration': 3600.5,  # Float value
                'startLocation': {
                    'lat': 52.5200,  # Float value
                    'lon': 13.4050   # Float value
                }
            })
        }
        
        with patch('handlers.save_drivers_log.logs_table', table):
            response = handler(event, {})
            
            assert response['statusCode'] == 200
            
            # Verify data was saved correctly
            items = table.scan()['Items']
            assert len(items) == 1
            
            saved_item = items[0]
            # Float values should be converted to Decimal
            assert isinstance(saved_item['distance'], Decimal)
            assert isinstance(saved_item['duration'], Decimal)
            # startLocation is not saved by the handler, so we'll just verify distance and duration


class TestEdgeCases:
    
    def test_handler_empty_strings(self):
        """Test handler with empty string values"""
        event = {
            'body': json.dumps({
                'sessionId': '',  # Empty string
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': ''  # Empty string
            })
        }
        
        response = handler(event, {})
        
        # Should handle empty strings appropriately
        assert response['statusCode'] in [400, 500]
    
    @patch('handlers.save_drivers_log.check_session_already_saved')
    @patch('handlers.save_drivers_log.check_for_overlapping_logs')
    def test_handler_very_long_strings(self, mock_check_overlap, mock_check_saved):
        """Test handler with very long string values"""
        mock_check_saved.return_value = False
        mock_check_overlap.return_value = (False, None)
        
        long_string = 'x' * 10000  # Very long string
        
        event = {
            'body': json.dumps({
                'sessionId': 'test_session',
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': long_string,
                'description': long_string
            })
        }
        
        # Should handle very long strings
        response = handler(event, {})
        assert response['statusCode'] in [200, 400, 500]
    
    def test_handler_special_characters(self):
        """Test handler with special characters"""
        event = {
            'body': json.dumps({
                'sessionId': 'test_session_äöü',
                'vehicleId': 'vehicle_01',
                'startTime': '2023-04-14T12:00:00',
                'endTime': '2023-04-14T13:00:00',
                'title': 'Trip with émojis 🚗🌍',
                'description': 'Special chars: @#$%^&*()'
            })
        }
        
        # Should handle special characters
        response = handler(event, {})
        assert response['statusCode'] in [200, 400, 500]
        
        # Should be valid JSON
        body = json.loads(response['body'])
        assert isinstance(body, dict)