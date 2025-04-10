import json
import boto3
import os
from decimal import Decimal
import traceback
from boto3.dynamodb.conditions import Key

# Configure DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get("DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations")
logs_table = dynamodb.Table(table_name + "-logs")  # Use the logs table
locations_table = dynamodb.Table(table_name)  # Main locations table


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def fetch_locations_by_time_range(vehicle_id, start_time, end_time):
    """
    Fetch locations from the locations table within a given time range for a vehicle
    
    Args:
        vehicle_id (str): The ID of the vehicle
        start_time (str): ISO format start timestamp
        end_time (str): ISO format end timestamp
        
    Returns:
        list: List of location data points
    """
    try:
        print(f"Fetching locations for vehicle {vehicle_id} from {start_time} to {end_time}")
        
        # Query the locations table with the time range condition
        response = locations_table.query(
            KeyConditionExpression=
                Key('id').eq(vehicle_id) & 
                Key('timestamp').between(start_time, end_time)
        )
        
        locations = response.get('Items', [])
        print(f"Found {len(locations)} location points in the time range")
        
        # Handle pagination if there are more results
        while 'LastEvaluatedKey' in response:
            response = locations_table.query(
                KeyConditionExpression=
                    Key('id').eq(vehicle_id) & 
                    Key('timestamp').between(start_time, end_time),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            locations.extend(response.get('Items', []))
            print(f"Added {len(response.get('Items', []))} more location points")
        
        return locations
    except Exception as e:
        print(f"Error fetching locations: {str(e)}")
        print(traceback.format_exc())
        return []


def handler(event, context):
    # Print event for debugging
    print("Event received:", json.dumps(event))
    
    # Common headers for all responses
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET"
    }
    
    # For HTTP API direct invocations
    if 'requestContext' in event and 'http' in event.get('requestContext', {}):
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET').upper()
    else:
        # For REST API or other invocations
        http_method = event.get('httpMethod', 'GET').upper()
    
    print(f"HTTP Method identified: {http_method}")
    print(f"DynamoDB Table: {logs_table.name}")
    
    # Handle OPTIONS requests
    if http_method == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }
    
    # Check if we're looking for a specific log (by ID)
    query_parameters = event.get('queryStringParameters', {}) or {}
    log_id = query_parameters.get('id')
    include_route = query_parameters.get('route') == 'true'
    
    try:
        # If log_id is provided, get that specific log entry
        if log_id:
            print(f"Fetching log with ID: {log_id}")
            response = logs_table.query(
                KeyConditionExpression=Key('id').eq(log_id)
            )
            items = response.get('Items', [])
            
            if not items:
                return {
                    "statusCode": 404,
                    "headers": headers,
                    "body": json.dumps({"message": "Log entry not found"})
                }
            
            # Get the first (and should be only) item
            log_entry = items[0]
            
            # If route is requested but we want to limit the size of the response
            if include_route:
                log_entry['route'] = get_route_for_log(log_entry)
            
            # By default, don't include full locations array for individual log fetches
            # unless explicitly requested with include_route=true
            elif 'locations' in log_entry and not include_route:
                del log_entry['locations']
            
            response_body = json.dumps(log_entry, default=decimal_default)
            
            return {
                "statusCode": 200,
                "headers": headers,
                "body": response_body
            }
        
        # Get all log entries if no ID is provided
        print("Scanning logs table")
        response = logs_table.scan()
        items = response.get('Items', [])
        print(f"Found {len(items)} items in the table")
        
        # If no items, return empty array
        if not items:
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({"logs": []})
            }
        
        # Sort by timestamp descending (newest first)
        sorted_items = sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Process items for response
        logs = []
        for item in sorted_items:
            # Remove the full locations array to reduce response size
            processed_item = dict(item)  # Create a copy to avoid modifying the original
            if 'locations' in processed_item:
                del processed_item['locations']
            logs.append(processed_item)
        
        response_body = json.dumps({"logs": logs}, default=decimal_default)
        print(f"Returning response with {len(logs)} logs")
        print(f"Response body sample: {response_body[:200]}...")
        
        return {
            "statusCode": 200,
            "headers": headers,
            "body": response_body
        }
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        print(traceback.format_exc())
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)})
        }


def get_route_for_log(log_entry):
    """Extract route points from a log entry based on start/end time"""
    # Get the relevant fields
    start_time = log_entry.get('startTime')
    end_time = log_entry.get('endTime')
    vehicle_id = log_entry.get('vehicleId', 'vehicle_01')  # Default to vehicle_01 if not specified
    start_address = log_entry.get('startAddress')
    end_address = log_entry.get('endAddress')
    
    # Fetch locations directly from the locations table
    locations = fetch_locations_by_time_range(vehicle_id, start_time, end_time)
    
    if not locations:
        # Fall back to locations in the log entry if available
        locations = log_entry.get('locations', [])
        if not locations:
            return []

    # Filter and prepare route points
    route = []
    
    # Sort locations by timestamp
    sorted_locations = sorted(locations, key=lambda x: x.get('timestamp', ''))
    
    # Extract the route points
    for loc in sorted_locations:
        # Include only necessary fields to minimize payload size
        route_point = {
            'lat': loc.get('latitude'),
            'lng': loc.get('longitude'),
            'timestamp': loc.get('timestamp'),
            'altitude': loc.get('altitude'),
            'cog': loc.get('cog'),
            'sog': loc.get('sog'),
            'quality': loc.get('quality'),
            'satellites_used': loc.get('satellites_used'),
            'processed_at': loc.get('processed_at'),
            'segment_type': loc.get('segment_type', 'moving'),
            'stop_duration_seconds': loc.get('stop_duration_seconds'),
            'address': loc.get('address')
        }
        route.append(route_point)
    
    # If we have route points and we also have address info, update the first/last points
    if route and (start_address or end_address):
        if start_address:
            route[0]['address'] = start_address
        
        if end_address:
            route[-1]['address'] = end_address
    
    return route