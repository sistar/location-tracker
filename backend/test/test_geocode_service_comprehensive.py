import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
import boto3
from moto import mock_aws
import requests

from handlers.geocode_service import (
    decimal_default,
    haversine,
    throttle_requests,
    get_address_from_cache,
    save_address_to_cache,
    reverse_geocode,
    handler
)


class TestUtilityFunctions:
    
    def test_decimal_default(self):
        """Test Decimal to float conversion"""
        assert decimal_default(Decimal('123.45')) == 123.45
        
        with pytest.raises(TypeError):
            decimal_default("not a decimal")
    
    def test_haversine(self):
        """Test haversine distance calculation"""
        # Test distance between two known points
        lat1, lon1 = 52.5200, 13.4050  # Berlin
        lat2, lon2 = 48.8566, 2.3522   # Paris
        
        distance = haversine(lat1, lon1, lat2, lon2)
        # Approximate distance Berlin-Paris is around 878km
        assert 870000 < distance < 890000
        
        # Test same point (should be 0)
        distance = haversine(lat1, lon1, lat1, lon1)
        assert distance == 0
    
    def test_haversine_close_points(self):
        """Test haversine with very close points"""
        lat1, lon1 = 52.5200, 13.4050
        lat2, lon2 = 52.5201, 13.4051  # Very close points
        
        distance = haversine(lat1, lon1, lat2, lon2)
        # Should be a small distance
        assert 0 < distance < 200  # Less than 200 meters


class TestRateLimiting:
    
    def setup_method(self):
        """Setup method called before each test"""
        # Reset the global rate limiting state
        from handlers import geocode_service
        geocode_service.last_request_time = 0
    
    def test_throttle_requests_first_call(self):
        """Test throttle_requests on first call"""
        start_time = time.time()
        throttle_requests()
        end_time = time.time()
        
        # First call should not add significant delay
        assert (end_time - start_time) < 0.1
    
    def test_throttle_requests_rate_limiting(self):
        """Test throttle_requests enforces rate limiting"""
        from handlers import geocode_service
        
        # Simulate a recent request
        geocode_service.last_request_time = time.time()
        
        start_time = time.time()
        throttle_requests()
        end_time = time.time()
        
        # Should have added delay close to RATE_LIMIT_DELAY (1.1 seconds)
        assert (end_time - start_time) >= 1.0  # At least 1 second delay
    
    def test_throttle_requests_no_delay_needed(self):
        """Test throttle_requests when no delay is needed"""
        from handlers import geocode_service
        
        # Simulate an old request (more than rate limit delay ago)
        geocode_service.last_request_time = time.time() - 2.0
        
        start_time = time.time()
        throttle_requests()
        end_time = time.time()
        
        # Should not add significant delay
        assert (end_time - start_time) < 0.1


class TestCaching:
    
    @mock_aws
    def test_get_address_from_cache_hit(self):
        """Test getting address from cache - cache hit"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-geocode-cache-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'cache_key', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'cache_key', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test data
        cache_key = "test_key"
        cache_data = {
            'cache_key': cache_key,
            'address': 'Test Address',
            'timestamp': datetime.now().isoformat()
        }
        table.put_item(Item=cache_data)
        
        # Mock the table in the module
        with patch('handlers.geocode_service.geocode_cache_table', table):
            result = get_address_from_cache(cache_key)
            
            assert result is not None
            assert result['address'] == 'Test Address'
    
    @mock_aws
    def test_get_address_from_cache_miss(self):
        """Test getting address from cache - cache miss"""
        # Create empty mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-geocode-cache-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'cache_key', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'cache_key', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        with patch('handlers.geocode_service.geocode_cache_table', table):
            result = get_address_from_cache("nonexistent_key")
            
            assert result is None
    
    @mock_aws
    def test_get_address_from_cache_expired(self):
        """Test getting address from cache - expired entry"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-geocode-cache-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'cache_key', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'cache_key', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add expired test data (35 days old)
        cache_key = "expired_key"
        old_timestamp = (datetime.now() - timedelta(days=35)).isoformat()
        cache_data = {
            'cache_key': cache_key,
            'address': 'Expired Address',
            'timestamp': old_timestamp
        }
        table.put_item(Item=cache_data)
        
        with patch('handlers.geocode_service.geocode_cache_table', table):
            result = get_address_from_cache(cache_key)
            
            # Should return None for expired entries
            assert result is None
    
    def test_get_address_from_cache_error(self):
        """Test getting address from cache with error"""
        mock_table = Mock()
        mock_table.get_item.side_effect = Exception("Database error")
        
        with patch('handlers.geocode_service.geocode_cache_table', mock_table):
            result = get_address_from_cache("test_key")
            
            # Should handle error gracefully and return None
            assert result is None
    
    @mock_aws
    def test_save_address_to_cache_success(self):
        """Test saving address to cache"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-geocode-cache-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'cache_key', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'cache_key', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        cache_key = "test_save_key"
        address_data = {'address': 'Test Save Address'}
        
        with patch('handlers.geocode_service.geocode_cache_table', table):
            save_address_to_cache(cache_key, address_data)
            
            # Verify it was saved
            response = table.get_item(Key={'cache_key': cache_key})
            assert 'Item' in response
            assert response['Item']['address'] == 'Test Save Address'
            assert 'timestamp' in response['Item']
    
    def test_save_address_to_cache_error(self):
        """Test saving address to cache with error"""
        mock_table = Mock()
        mock_table.put_item.side_effect = Exception("Database error")
        
        cache_key = "test_key"
        address_data = {'address': 'Test Address'}
        
        with patch('handlers.geocode_service.geocode_cache_table', mock_table):
            # Should handle error gracefully without raising exception
            save_address_to_cache(cache_key, address_data)
            
            # Should have attempted to save
            mock_table.put_item.assert_called_once()


class TestReverseGeocode:
    
    @patch('handlers.geocode_service.requests.get')
    @patch('handlers.geocode_service.get_address_from_cache')
    @patch('handlers.geocode_service.save_address_to_cache')
    def test_reverse_geocode_cache_hit(self, mock_save_cache, mock_get_cache, mock_requests):
        """Test reverse geocode with cache hit"""
        # Mock cache hit
        cached_data = {
            'cache_key': 'rev_52.520000_13.405000',
            'address': 'Cached Address',
            'timestamp': datetime.now().isoformat()
        }
        mock_get_cache.return_value = cached_data
        
        result = reverse_geocode(52.52, 13.405)
        
        assert result == cached_data
        # Should not make API request
        mock_requests.assert_not_called()
        # Should not save to cache (already cached)
        mock_save_cache.assert_not_called()
    
    @patch('handlers.geocode_service.requests.get')
    @patch('handlers.geocode_service.get_address_from_cache')
    @patch('handlers.geocode_service.save_address_to_cache')
    @patch('handlers.geocode_service.throttle_requests')
    def test_reverse_geocode_api_success(self, mock_throttle, mock_save_cache, mock_get_cache, mock_requests):
        """Test reverse geocode with successful API call"""
        # Mock cache miss
        mock_get_cache.return_value = None
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'display_name': 'API Address',
            'lat': '52.52',
            'lon': '13.405'
        }
        mock_requests.return_value = mock_response
        
        result = reverse_geocode(52.52, 13.405)
        
        # Should throttle requests
        mock_throttle.assert_called_once()
        
        # Should make API request
        mock_requests.assert_called_once()
        
        # Should save to cache
        mock_save_cache.assert_called_once()
        
        # Check result format
        assert 'display_name' in result
        assert result['display_name'] == 'API Address'
    
    @patch('handlers.geocode_service.requests.get')
    @patch('handlers.geocode_service.get_address_from_cache')
    @patch('handlers.geocode_service.save_address_to_cache')
    @patch('handlers.geocode_service.throttle_requests')
    def test_reverse_geocode_api_error(self, mock_throttle, mock_save_cache, mock_get_cache, mock_requests):
        """Test reverse geocode with API error"""
        # Mock cache miss
        mock_get_cache.return_value = None
        
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.return_value = mock_response
        
        result = reverse_geocode(52.52, 13.405)
        
        # Should return error result
        assert result['error'] == 'Failed to get address'
        assert result['status_code'] == 500
        
        # Should not save error to cache
        mock_save_cache.assert_not_called()
    
    @patch('handlers.geocode_service.requests.get')
    @patch('handlers.geocode_service.get_address_from_cache')
    @patch('handlers.geocode_service.save_address_to_cache')
    @patch('handlers.geocode_service.throttle_requests')
    def test_reverse_geocode_request_exception(self, mock_throttle, mock_save_cache, mock_get_cache, mock_requests):
        """Test reverse geocode with request exception"""
        # Mock cache miss
        mock_get_cache.return_value = None
        
        # Mock request exception
        mock_requests.side_effect = requests.RequestException("Network error")
        
        result = reverse_geocode(52.52, 13.405)
        
        # Should return error result
        assert result['error'] == 'Request failed'
        assert 'Network error' in result['details']
        
        # Should not save error to cache
        mock_save_cache.assert_not_called()
    
    @patch('handlers.geocode_service.requests.get')
    @patch('handlers.geocode_service.get_address_from_cache')
    @patch('handlers.geocode_service.save_address_to_cache')
    @patch('handlers.geocode_service.throttle_requests')
    def test_reverse_geocode_json_decode_error(self, mock_throttle, mock_save_cache, mock_get_cache, mock_requests):
        """Test reverse geocode with JSON decode error"""
        # Mock cache miss
        mock_get_cache.return_value = None
        
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_requests.return_value = mock_response
        
        result = reverse_geocode(52.52, 13.405)
        
        # Should return error result
        assert result['error'] == 'Failed to parse response'
        
        # Should not save error to cache
        mock_save_cache.assert_not_called()


class TestHandler:
    
    @patch('handlers.geocode_service.reverse_geocode')
    def test_handler_success(self, mock_reverse_geocode):
        """Test successful handler execution"""
        # Mock successful geocoding
        mock_reverse_geocode.return_value = {
            'display_name': 'Test Address',
            'lat': '52.52',
            'lon': '13.405'
        }
        
        event = {
            'queryStringParameters': {
                'lat': '52.52',
                'lon': '13.405'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['display_name'] == 'Test Address'
    
    def test_handler_missing_parameters(self):
        """Test handler with missing parameters"""
        event = {
            'queryStringParameters': {
                'lat': '52.52'
                # Missing 'lon'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_handler_no_query_parameters(self):
        """Test handler with no query parameters"""
        event = {'queryStringParameters': None}
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_handler_invalid_coordinates(self):
        """Test handler with invalid coordinates"""
        event = {
            'queryStringParameters': {
                'lat': 'invalid',
                'lon': '13.405'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    @patch('handlers.geocode_service.reverse_geocode')
    def test_handler_geocoding_error(self, mock_reverse_geocode):
        """Test handler when geocoding returns error"""
        # Mock geocoding error
        mock_reverse_geocode.return_value = {
            'error': 'Failed to get address',
            'status_code': 500
        }
        
        event = {
            'queryStringParameters': {
                'lat': '52.52',
                'lon': '13.405'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_handler_exception(self):
        """Test handler with unexpected exception"""
        event = {
            'queryStringParameters': {
                'lat': '52.52',
                'lon': '13.405'
            }
        }
        
        with patch('handlers.geocode_service.reverse_geocode') as mock_reverse:
            mock_reverse.side_effect = Exception("Unexpected error")
            
            response = handler(event, {})
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert 'error' in body
    
    @patch('handlers.geocode_service.reverse_geocode')
    def test_handler_coordinate_edge_cases(self, mock_reverse_geocode):
        """Test handler with coordinate edge cases"""
        mock_reverse_geocode.return_value = {'display_name': 'Test Address'}
        
        edge_cases = [
            # Extreme coordinates
            {'lat': '90.0', 'lon': '180.0'},      # North pole, date line
            {'lat': '-90.0', 'lon': '-180.0'},    # South pole, opposite date line
            {'lat': '0.0', 'lon': '0.0'},         # Equator, prime meridian
            # High precision coordinates
            {'lat': '52.123456789', 'lon': '13.987654321'},
        ]
        
        for params in edge_cases:
            event = {'queryStringParameters': params}
            response = handler(event, {})
            
            # Should handle all edge cases
            assert response['statusCode'] == 200
    
    @patch('handlers.geocode_service.reverse_geocode')
    def test_handler_decimal_serialization(self, mock_reverse_geocode):
        """Test handler properly serializes Decimal values"""
        # Mock geocoding with Decimal values
        mock_reverse_geocode.return_value = {
            'display_name': 'Test Address',
            'lat': Decimal('52.52'),
            'lon': Decimal('13.405')
        }
        
        event = {
            'queryStringParameters': {
                'lat': '52.52',
                'lon': '13.405'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 200
        
        # Should be able to parse JSON without Decimal serialization errors
        body = json.loads(response['body'])
        assert isinstance(body['lat'], float)
        assert isinstance(body['lon'], float)


class TestIntegrationScenarios:
    
    @patch('handlers.geocode_service.requests.get')
    @mock_aws
    def test_full_caching_workflow(self, mock_requests):
        """Test complete caching workflow"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'test-geocode-cache-table'
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'cache_key', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'cache_key', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'display_name': 'Full Workflow Address',
            'lat': '52.52',
            'lon': '13.405'
        }
        mock_requests.return_value = mock_response
        
        with patch('handlers.geocode_service.geocode_cache_table', table):
            # First call - should hit API and cache result
            result1 = reverse_geocode(52.52, 13.405)
            
            # Second call - should hit cache
            result2 = reverse_geocode(52.52, 13.405)
            
            # Both results should be the same
            assert result1['display_name'] == result2['display_name']
            
            # API should only be called once
            assert mock_requests.call_count == 1
            
            # Check cache contains the entry
            cache_key = "rev_52.520000_13.405000"
            response = table.get_item(Key={'cache_key': cache_key})
            assert 'Item' in response
    
    def test_rate_limiting_compliance(self):
        """Test that rate limiting is properly enforced"""
        from handlers import geocode_service
        
        # Reset rate limiting state
        geocode_service.last_request_time = 0
        
        # Make rapid calls
        start_time = time.time()
        
        throttle_requests()  # First call
        throttle_requests()  # Second call - should be throttled
        
        end_time = time.time()
        
        # Should take at least the rate limit delay
        assert (end_time - start_time) >= 1.0
    
    @patch('handlers.geocode_service.requests.get')
    @patch('handlers.geocode_service.get_address_from_cache')
    @patch('handlers.geocode_service.save_address_to_cache')
    def test_error_handling_chain(self, mock_save_cache, mock_get_cache, mock_requests):
        """Test error handling throughout the chain"""
        # Mock cache error
        mock_get_cache.side_effect = Exception("Cache error")
        
        # Mock API error
        mock_requests.side_effect = requests.RequestException("API error")
        
        # Mock save error
        mock_save_cache.side_effect = Exception("Save error")
        
        result = reverse_geocode(52.52, 13.405)
        
        # Should handle all errors gracefully
        assert 'error' in result
        assert result['error'] == 'Request failed'
        assert 'API error' in result['details']