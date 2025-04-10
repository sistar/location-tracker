import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# Let API Gateway handle CORS

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get("DYNAMODB_LOCATIONS_TABLE", "LocationTable")
logs_table = dynamodb.Table(table_name + "-logs")  # Use a separate table for logs


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def convert_floats_to_decimal(obj):
    """Convert all float values in a dict/list to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(i) for i in obj]
    else:
        return obj


def check_for_overlapping_logs(start_time, end_time):
    """
    Check if a time period overlaps with any existing driver's log entries
    
    Returns:
        bool: True if there's an overlap, False if no overlap
    """
    try:
        # Scan the logs table for entries
        # In a production system, you would use a GSI or better query method
        response = logs_table.scan()
        items = response.get('Items', [])
        
        for item in items:
            log_start = item.get('startTime')
            log_end = item.get('endTime')
            
            if not log_start or not log_end:
                continue
                
            # Check for overlap: if the new period starts before an existing period ends
            # and ends after the existing period starts
            if start_time <= log_end and end_time >= log_start:
                return True, item.get('id')
                
        return False, None
    except Exception as e:
        print(f"Error checking for overlapping logs: {str(e)}")
        return False, None


def check_session_already_saved(session_id):
    """
    Check if a session has already been saved to a driver's log
    
    Returns:
        bool: True if the session exists, False otherwise
    """
    try:
        response = logs_table.query(
            KeyConditionExpression=Key('id').eq(session_id)
        )
        
        return len(response.get('Items', [])) > 0
    except Exception as e:
        print(f"Error checking for existing session: {str(e)}")
        return False


def handler(event, context):
    # Log the full event for debugging
    print("Full event received:", json.dumps(event, default=str))
    
    # Common headers for all responses
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST,HEAD"
    }
    
    # Handle different HTTP methods for both HTTP API and REST API
    # First try to detect method from standard HTTP API structure
    if 'requestContext' in event and 'http' in event.get('requestContext', {}):
        http_method = event.get('requestContext', {}).get('http', {}).get('method', '').upper()
        print(f"Method from requestContext.http.method: {http_method}")
    # Then try REST API format
    elif 'httpMethod' in event:
        http_method = event.get('httpMethod', '').upper()
        print(f"Method from httpMethod: {http_method}")
    # Alternative HTTP API format (some configurations have it here)
    elif 'requestContext' in event and 'method' in event.get('requestContext', {}):
        http_method = event.get('requestContext', {}).get('method', '').upper()
        print(f"Method from requestContext.method: {http_method}")
    # Raw check of routeKey for HTTP API format
    elif 'routeKey' in event:
        route_key = event.get('routeKey', '')
        if ' ' in route_key:
            http_method = route_key.split(' ')[0].upper()
            print(f"Method extracted from routeKey: {http_method}")
        else:
            http_method = 'GET' # Default
    # Fallback for direct Lambda invocations
    else:
        http_method = 'GET'
        print("No method found in event, defaulting to GET")
    
    # Handle empty method case
    if not http_method:
        http_method = 'GET'
        print("Empty method found, defaulting to GET")
    
    print(f"Final HTTP Method identified: {http_method}")
    
    # For HEAD or GET requests, check if session exists
    if http_method in ['HEAD', 'GET']:
        try:
            # Extract sessionId from query parameters
            query_params = event.get('queryStringParameters', {}) or {}
            session_id = query_params.get('sessionId')
            
            if not session_id:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"message": "Missing sessionId parameter"})
                }
            
            # Check if session exists
            if check_session_already_saved(session_id):
                return {
                    "statusCode": 409,  # Conflict
                    "headers": headers,
                    "body": json.dumps({"message": "Session already exists"}) if http_method == 'GET' else ""
                }
            else:
                return {
                    "statusCode": 200,
                    "headers": headers,
                    "body": json.dumps({"message": "Session not found"}) if http_method == 'GET' else ""
                }
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": headers,
                "body": json.dumps({"error": str(e)}) if http_method == 'GET' else ""
            }
    
    # Handle POST requests to save a new log
    elif http_method == 'POST':
        try:
            # Parse the request body
            body = json.loads(event.get('body', '{}'))
            
            if not body.get('sessionId') or not body.get('startTime') or not body.get('endTime'):
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"message": "Missing required fields"})
                }
            
            session_id = body.get('sessionId')
            start_time = body.get('startTime')
            end_time = body.get('endTime')
            
            # Check if this session has already been saved
            if check_session_already_saved(session_id):
                return {
                    "statusCode": 409, # Conflict
                    "headers": headers,
                    "body": json.dumps({"message": "This session has already been saved to a driver's log"})
                }
            
            # Check for overlapping time periods with existing logs
            has_overlap, overlapping_id = check_for_overlapping_logs(start_time, end_time)
            if has_overlap:
                return {
                    "statusCode": 409, # Conflict
                    "headers": headers,
                    "body": json.dumps({
                        "message": "This time period overlaps with an existing driver's log entry",
                        "overlappingId": overlapping_id
                    })
                }
            
            # Store additional location data if provided
            locations = body.get('locations', [])
            
            # Create log entry
            log_entry = {
                'id': session_id,
                'timestamp': datetime.utcnow().isoformat(),
                'startTime': start_time,
                'endTime': end_time,
                'distance': body.get('distance'),
                'duration': body.get('duration'),
                'purpose': body.get('purpose', ''),
                'notes': body.get('notes', ''),
                'startAddress': body.get('startAddress', ''),
                'endAddress': body.get('endAddress', ''),
                'locations': locations if locations else None
            }
            
            # Convert any float values to Decimal before saving to DynamoDB
            log_entry = convert_floats_to_decimal(log_entry)
            
            # Save to DynamoDB
            logs_table.put_item(Item=log_entry)
            
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({"message": "Log entry saved successfully", "id": log_entry['id']})
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": headers,
                "body": json.dumps({"error": str(e)})
            }
    
    # Handle OPTIONS requests
    elif http_method == 'OPTIONS':
        # Add debug info
        print("Handling OPTIONS request")
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }
    
    # Method not allowed
    else:
        # Log the unrecognized method for debugging
        print(f"Unrecognized/unsupported method: {http_method}")
        print(f"Route: {event.get('resource', 'unknown')}, Path: {event.get('path', 'unknown')}")
        
        # Allow HEAD by treating it the same as GET
        # This is a failsafe in case method detection didn't work properly
        if 'head' in str(event).lower() or 'HEAD' in str(event):
            print("HEAD method detected in event, handling as GET")
            try:
                # Extract sessionId from query parameters
                query_params = event.get('queryStringParameters', {}) or {}
                session_id = query_params.get('sessionId')
                
                if not session_id:
                    return {
                        "statusCode": 400,
                        "headers": headers,
                        "body": ""  # HEAD should have empty body
                    }
                
                # Check if session exists
                if check_session_already_saved(session_id):
                    return {
                        "statusCode": 409,  # Conflict
                        "headers": headers,
                        "body": ""  # HEAD should have empty body
                    }
                else:
                    return {
                        "statusCode": 200,
                        "headers": headers,
                        "body": ""  # HEAD should have empty body
                    }
            except Exception as e:
                print(f"Error in HEAD fallback: {str(e)}")
                return {
                    "statusCode": 500,
                    "headers": headers,
                    "body": ""  # HEAD should have empty body
                }
        
        # Return method not allowed for other unsupported methods
        return {
            "statusCode": 405,
            "headers": headers,
            "body": json.dumps({"message": "Method not allowed"})
        }