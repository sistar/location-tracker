import json
import boto3
import os
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timedelta
import math
import statistics
from typing import List, Dict, Any, Tuple

# IMPORTANT: DynamoDB timestamp schema
# The 'timestamp' field is a Number (representing UTC epoch timestamp in seconds)
# This is used as the sort key in DynamoDB tables


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def parse_timestamp_safely(timestamp):
    """Parse a timestamp value to a datetime object.
    
    Args:
        timestamp: Either an epoch timestamp (int/float/Decimal) or a timestamp string
        
    Returns:
        datetime: Parsed datetime object
    """
    # If it's already a numeric value (epoch), convert directly
    if isinstance(timestamp, (int, float, Decimal)):
        return datetime.fromtimestamp(float(timestamp))
    
    # If it's a string that contains only digits, treat as epoch timestamp
    if isinstance(timestamp, str) and timestamp.isdigit():
        return datetime.fromtimestamp(float(timestamp))
    
    # Otherwise treat as a string timestamp
    try:
        # First try direct parsing with fromisoformat
        return datetime.fromisoformat(timestamp)
    except ValueError:
        # If it has timezone info like "2025-04-14T02:26:59 MESZ"
        if ' ' in timestamp:
            clean_timestamp = timestamp.split(' ')[0]
            try:
                return datetime.fromisoformat(clean_timestamp)
            except ValueError:
                pass
        
        # Try standard format
        try:
            return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass
        
        # Try other common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d.%m.%Y %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp, fmt)
            except ValueError:
                continue
        
    raise ValueError(f"Unable to parse timestamp: {timestamp}")


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_median_position(locations: List[Dict[str, Any]]) -> Tuple[float, float]:
    """Calculate the median lat/lng position from a list of locations"""
    if not locations:
        return 0.0, 0.0
    
    lats = [float(loc['lat']) for loc in locations]
    lngs = [float(loc['lon']) for loc in locations]
    
    median_lat = statistics.median(lats)
    median_lng = statistics.median(lngs)
    
    return median_lat, median_lng


def clean_phantom_locations(locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove phantom location fixes when vehicle is stopped"""
    # Configuration parameters
    STOP_DISTANCE_THRESHOLD = 140    # Max distance (meters) between points to be considered 'stopped'
    MIN_STOP_DURATION_SECONDS = 60    # Minimum duration (seconds) for a stop to be marked
    MAX_STOP_DURATION_SECONDS = 50 * 60  # Maximum duration (seconds) for a stop to be considered part of the same session (EV charging)
    MEDIAN_WINDOW_SIZE = 18  # Number of points to consider for median calculation
    
    if len(locations) < 3:
        return locations  # Not enough data points to process
    
    # Sort by timestamp ascending (now using numeric epoch values)
    sorted_locations = sorted(locations, key=lambda x: float(x['timestamp']))
    
    # Calculate median of next n points for each location
    for i in range(len(sorted_locations)):
        end_idx = min(i + 1 + MEDIAN_WINDOW_SIZE, len(sorted_locations))
        if i + 1 < end_idx:  # At least one point ahead
            future_points = sorted_locations[i+1:end_idx]
            
            # Calculate median position
            future_lats = [float(loc['lat']) for loc in future_points]
            future_lngs = [float(loc['lon']) for loc in future_points]
            
            if future_lats and future_lngs:
                sorted_locations[i]['next_n_median_latitude'] = statistics.median(future_lats)
                sorted_locations[i]['next_n_median_longitude'] = statistics.median(future_lngs)
    
    # Initialize cleaned data list and processing index
    cleaned_data = []
    i = 0
    n = len(sorted_locations)
    
    while i < n:
        current_point = sorted_locations[i]
        
        # Start checking for a stop from the next point
        j = i + 1
        stop_candidates = [current_point]  # Current point is always the start of a potential stop/movement
        
        # Find consecutive points within the distance threshold of the start point's next median
        while j < n:
            next_point = sorted_locations[j]
            
            # Skip points without median calculations (typically points near the end)
            if ('next_n_median_latitude' not in current_point or 
                'next_n_median_longitude' not in current_point or
                'next_n_median_latitude' not in next_point or
                'next_n_median_longitude' not in next_point):
                break
            
            distance = haversine(
                current_point['next_n_median_latitude'], current_point['next_n_median_longitude'],
                next_point['next_n_median_latitude'], next_point['next_n_median_longitude']
            )
            
            if distance < STOP_DISTANCE_THRESHOLD:
                stop_candidates.append(next_point)
                j += 1
            else:
                break  # Movement detected, stop sequence ends
        
        # Evaluate the identified sequence (stop_candidates)
        if len(stop_candidates) > 1:  # We found at least one subsequent point that was 'stopped'
            # Safely parse timestamps with error handling
            try:
                start_timestamp = stop_candidates[0]['timestamp']
                end_timestamp = stop_candidates[-1]['timestamp']
                
                # Parse timestamps with fallback for timezone issues
                start_time = parse_timestamp_safely(start_timestamp)
                end_time = parse_timestamp_safely(end_timestamp)
                
                duration = (end_time - start_time).total_seconds()
            except Exception as e:
                print(f"Error calculating stop duration: {str(e)}")
                # Use a default duration if parsing fails
                duration = 0
            
            if duration >= MIN_STOP_DURATION_SECONDS:
                # A significant stop - mark as a charging stop for electric vehicles
                # Stops up to 50 minutes are still considered part of the same session
                stop_candidate = stop_candidates[0].copy()
                
                # Classify the stop type based on duration
                if duration > MAX_STOP_DURATION_SECONDS:
                    # Long stop (over 50 minutes) - regular stop
                    stop_candidate['segment_type'] = 'stopped'
                else:
                    # Stop within charging time range (1-50 minutes) - mark as charging
                    stop_candidate['segment_type'] = 'charging'
                
                stop_candidate['stop_duration_seconds'] = duration
                cleaned_data.append(stop_candidate)
                # Move the main index past all points in this stop
                i = j
            else:
                # Very short stop or just noise: Keep all points in the sequence as movement
                for point in stop_candidates:
                    point_copy = point.copy()
                    point_copy['segment_type'] = 'moving'
                    cleaned_data.append(point_copy)
                # Move the main index past all points in this sequence
                i = j
        else:
            # No stop detected starting at current_point, mark as moving
            point_copy = current_point.copy()
            point_copy['segment_type'] = 'moving'
            cleaned_data.append(point_copy)
            i += 1
    
    # Remove the temporary median fields before returning
    for loc in cleaned_data:
        if 'next_n_median_latitude' in loc:
            del loc['next_n_median_latitude']
        if 'next_n_median_longitude' in loc:
            del loc['next_n_median_longitude']
    
    return cleaned_data


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


def query_location_range(table, vehicle_id, start_time, end_time, exclusive_start_key=None):
    """Execute a DynamoDB query for a specific time range"""
    try:
        # Convert string timestamps to epoch if needed
        if isinstance(start_time, str):
            if start_time.isdigit():
                start_time = int(start_time)
            else:
                start_time = int(parse_timestamp_safely(start_time).timestamp())
                
        if isinstance(end_time, str):
            if end_time.isdigit():
                end_time = int(end_time)
            else:
                end_time = int(parse_timestamp_safely(end_time).timestamp())
                
        print(f"Query range (converted): {start_time} to {end_time}")
        print(f"Table being queried: {table.name}")
        print(f"Vehicle ID: {vehicle_id}")
            
        # Construct the query parameters
        query_params = {
            "KeyConditionExpression": Key('id').eq(vehicle_id) & Key('timestamp').between(start_time, end_time),
            "ScanIndexForward": True  # ascending order by timestamp
        }
        
        if exclusive_start_key:
            query_params["ExclusiveStartKey"] = exclusive_start_key
            
        print(f"Query parameters: {query_params}")
        
        # Execute the query
        response = table.query(**query_params)
        
        # Log the results
        items = response.get('Items', [])
        print(f"Query returned {len(items)} items")
        
        return items, None
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        import traceback
        traceback.print_exc()
        return [], str(e)


def calculate_time_window(start_timestamp, end_timestamp, time_window_hours):
    """Calculate appropriate time window based on provided parameters"""
    calculated_start = None
    calculated_end = None
    
    try:
        if start_timestamp and end_timestamp:
            # Case 1: Both timestamps provided - use exact range
            pass  # No calculation needed
        elif start_timestamp:
            # Case 2: Only start_timestamp - calculate end
            start_time = parse_timestamp_safely(start_timestamp)
            end_time = start_time + timedelta(hours=time_window_hours)
            calculated_end = int(end_time.timestamp())  # Convert to epoch
        elif end_timestamp:
            # Case 3: Only end_timestamp - calculate start
            end_time = parse_timestamp_safely(end_timestamp)
            start_time = end_time - timedelta(hours=time_window_hours)
            calculated_start = int(start_time.timestamp())  # Convert to epoch
        else:
            # Case 4: No timestamps - use current time and go back by time_window_hours
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=time_window_hours)
            calculated_start = int(start_time.timestamp())  # Convert to epoch
            calculated_end = int(end_time.timestamp())  # Convert to epoch
            print(f"Using current time range: {start_time.isoformat()} to {end_time.isoformat()}")
            print(f"Generated epoch timestamps: start={calculated_start}, end={calculated_end}")
            
            # DEBUG: Log actual data in the calculated time range
            print(f"Checking if data exists in time range {calculated_start} to {calculated_end}")
            
        return calculated_start, calculated_end, None
    except Exception as e:
        print(f"Error calculating time window: {str(e)}")
        return None, None, str(e)


def extend_session_points(table, vehicle_id, boundary_timestamp, direction="backward", extension_minutes=50):
    """
    Extend session points in either direction
    
    Args:
        table: DynamoDB table object
        vehicle_id: Vehicle identifier
        boundary_timestamp: The current boundary timestamp (epoch or string)
        direction: "backward" or "forward"
        extension_minutes: Minutes to extend
        
    Returns:
        tuple: (new_points, new_boundary_timestamp, error)
    """
    try:
        boundary_time = parse_timestamp_safely(boundary_timestamp)
        
        if direction == "backward":
            # Calculate time before boundary
            extended_time = boundary_time - timedelta(minutes=extension_minutes)
            extended_timestamp = int(extended_time.timestamp())  # Convert to epoch
            start_timestamp = extended_timestamp
            end_timestamp = int(boundary_time.timestamp()) if isinstance(boundary_timestamp, datetime) else boundary_timestamp
        else:  # forward
            # Calculate time after boundary
            extended_time = boundary_time + timedelta(minutes=extension_minutes)
            extended_timestamp = int(extended_time.timestamp())  # Convert to epoch
            start_timestamp = int(boundary_time.timestamp()) if isinstance(boundary_timestamp, datetime) else boundary_timestamp
            end_timestamp = extended_timestamp
            
            # Check if we're already close to current time
            current_time = datetime.now()
            if (current_time - boundary_time).total_seconds() < 300:  # 5 minutes threshold
                print(f"Boundary timestamp is already close to current time - stopping extensions")
                return [], boundary_timestamp, "Close to current time"
        
        print(f"Looking for additional session points from: {start_timestamp} to {end_timestamp}")
        
        # Query for extended points
        query_expression = Key('id').eq(vehicle_id) & Key('timestamp').between(start_timestamp, end_timestamp)
        
        # Exclude boundary point for forward queries after first extension to avoid duplicates
        exclusive_start_key = None
        
        response = table.query(
            KeyConditionExpression=query_expression,
            ScanIndexForward=True,
            ExclusiveStartKey=exclusive_start_key
        )
        
        # Get points from response
        extended_points = response.get('Items', [])
        
        if extended_points:
            # Update boundary timestamp
            new_boundary = extended_points[0]['timestamp'] if direction == "backward" else extended_points[-1]['timestamp']
            return extended_points, new_boundary, None
        else:
            return [], boundary_timestamp, "No points found"
            
    except Exception as e:
        print(f"Error extending session points: {str(e)}")
        return [], boundary_timestamp, str(e)


# Database setup
dynamodb = boto3.resource("dynamodb")

# Get table names from environment variables or use defaults (matching actual names in AWS)
locations_table_name = os.environ.get("DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations-v2")

# Create table resource
locations_table = dynamodb.Table(locations_table_name)
print(f"Using locations table: {locations_table_name}")


def handler(event, context):
    try:
        # Extract parameters from query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        start_timestamp = query_params.get('start_timestamp')
        end_timestamp = query_params.get('end_timestamp')
        time_window = query_params.get('time_window')
        vehicle_id = query_params.get('vehicle_id', 'vehicle_01')
        
        print(f"Request for location history with parameters: {query_params}")
        
        # Convert time_window to hours (default to 6 hours if not provided)
        time_window_hours = 6
        if time_window:
            try:
                time_window_hours = int(time_window)
            except ValueError:
                print(f"Invalid time_window parameter: {time_window}, using default of 6 hours")

        # Calculate time window based on provided parameters
        calculated_start, calculated_end, window_error = calculate_time_window(
            start_timestamp, end_timestamp, time_window_hours
        )
        
        if window_error:
            return create_api_response(400, {"message": "Invalid time range parameters"})
            
        # Use calculated values if originals not provided
        effective_start = start_timestamp or calculated_start
        effective_end = end_timestamp or calculated_end
        
        # For logging, convert epoch timestamps to readable format if needed
        start_display = effective_start
        end_display = effective_end
        
        if isinstance(effective_start, (int, float)):
            start_display = datetime.fromtimestamp(effective_start).isoformat()
        if isinstance(effective_end, (int, float)):
            end_display = datetime.fromtimestamp(effective_end).isoformat()
            
        print(f"Using time range: {start_display} to {end_display}")
        print(f"Timestamp types - start: {type(effective_start)}, end: {type(effective_end)}")
        
        # Query for initial data points
        items, query_error = query_location_range(
            locations_table, vehicle_id, effective_start, effective_end
        )
        
        if query_error:
            return create_api_response(500, query_error, error=True)
            
        if not items:
            return create_api_response(404, {"message": "No location data found in the specified time range"})
            
        print(f"Initial query returned {len(items)} points")
        
        # Extend session backwards
        earliest_timestamp = items[0]['timestamp']
        latest_timestamp = items[-1]['timestamp']
        
        # Backward extension loop
        extension_count = 0
        while extension_count < 15:  # Max 15 extensions
            earlier_points, new_earliest, error = extend_session_points(
                locations_table, vehicle_id, earliest_timestamp, "backward"
            )
            
            if error == "No points found" or error:
                break
                
            if earlier_points:
                print(f"Found {len(earlier_points)} earlier points in extension #{extension_count+1}")
                items = earlier_points + items
                earliest_timestamp = new_earliest
                extension_count += 1
            else:
                break
                
        # Forward extension loop  
        future_extension_count = 0
        while future_extension_count < 15:  # Max 15 extensions
            later_points, new_latest, error = extend_session_points(
                locations_table, vehicle_id, latest_timestamp, "forward"
            )
            
            if error == "No points found" or error == "Close to current time" or error:
                break
                
            if later_points:
                print(f"Found {len(later_points)} later points in extension #{future_extension_count+1}")
                items = items + later_points
                latest_timestamp = new_latest
                future_extension_count += 1
            else:
                break
                
        print(f"Final dataset has {len(items)} points after {extension_count} backward and {future_extension_count} forward extensions")
        
        # Clean phantom locations
        cleaned_session = clean_phantom_locations(items)
        print(f"Returning {len(cleaned_session)} points after cleaning")
        
        # Add a human-readable timestamp for the frontend for each point
        for point in cleaned_session:
            if 'timestamp' in point:
                # Safely handle any timestamp format
                try:
                    if isinstance(point['timestamp'], (int, float, Decimal)):
                        epoch_ts = float(point['timestamp'])
                        point['timestamp_str'] = datetime.fromtimestamp(epoch_ts).isoformat()
                    elif isinstance(point['timestamp'], str):
                        # If it's a string that looks like a number, convert it to epoch first
                        if point['timestamp'].isdigit():
                            epoch_ts = float(point['timestamp'])
                            point['timestamp_str'] = datetime.fromtimestamp(epoch_ts).isoformat()
                        else:
                            # Otherwise assume it's already ISO format
                            point['timestamp_str'] = point['timestamp']
                except Exception as e:
                    print(f"Error converting timestamp to string: {str(e)}")
                    # Provide a fallback timestamp string
                    point['timestamp_str'] = str(point['timestamp'])
        
        return create_api_response(200, cleaned_session)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_api_response(500, str(e), error=True)