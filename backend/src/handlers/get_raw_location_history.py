import json
import boto3
import os
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timedelta

# IMPORTANT: DynamoDB timestamp schema
# The 'timestamp' field is a Number (representing UTC epoch timestamp in seconds)
# This is used as the sort key in DynamoDB tables


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def create_api_response(status_code, body, error=False):
    """Create a standardized API Gateway response"""
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        },
        "body": json.dumps(body if not error else {"error": str(body)}, default=decimal_default)
    }


# Database setup
dynamodb = boto3.resource("dynamodb")

# Get table name from environment variables or use default
locations_table_name = os.environ.get("DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations-v2")

# Create table resource
locations_table = dynamodb.Table(locations_table_name)


def handler(event, context):
    """Get raw location history for the past 7 days with no filtering"""
    try:
        # Extract parameters from query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        vehicle_id = query_params.get('vehicle_id', 'vehicle_01')
        days = int(query_params.get('days', '7'))  # Default to 7 days if not specified

        # Calculate the timestamp for 'days' days ago
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Convert to epoch timestamps
        end_timestamp = int(end_time.timestamp())
        start_timestamp = int(start_time.timestamp())
        
        print(f"Fetching raw location data for {vehicle_id} from {start_time} to {end_time}")
        print(f"Epoch timestamps: start={start_timestamp}, end={end_timestamp}")

        # Query for all location points in the time range, with no filtering or processing
        items = []
        exclusive_start_key = None
        
        # Paginate through results since we might have a lot of data
        while True:
            query_params = {
                "KeyConditionExpression": Key('id').eq(vehicle_id) & Key('timestamp').between(start_timestamp, end_timestamp),
                "ScanIndexForward": False  # Newest first for better user experience
            }
            
            if exclusive_start_key:
                query_params["ExclusiveStartKey"] = exclusive_start_key
                
            response = locations_table.query(**query_params)
            
            # Add items from this page
            items.extend(response.get('Items', []))
            
            # Check if there are more items to fetch
            exclusive_start_key = response.get('LastEvaluatedKey')
            if not exclusive_start_key:
                break
        
        print(f"Retrieved {len(items)} raw location points")
        
        # Add a human-readable timestamp for each point for frontend display
        for point in items:
            if 'timestamp' in point:
                try:
                    if isinstance(point['timestamp'], (int, float, Decimal)):
                        epoch_ts = float(point['timestamp'])
                        point['timestamp_str'] = datetime.fromtimestamp(epoch_ts).isoformat()
                except Exception as e:
                    print(f"Error converting timestamp to string: {str(e)}")
                    point['timestamp_str'] = str(point['timestamp'])
        
        return create_api_response(200, items)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_api_response(500, str(e), error=True)