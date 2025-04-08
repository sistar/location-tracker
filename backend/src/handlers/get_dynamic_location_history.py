import json
import boto3
import os
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timedelta
import math
import statistics
from typing import List, Dict, Any, Tuple


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


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
    
    lats = [float(loc['latitude']) for loc in locations]
    lngs = [float(loc['longitude']) for loc in locations]
    
    median_lat = statistics.median(lats)
    median_lng = statistics.median(lngs)
    
    return median_lat, median_lng


def clean_phantom_locations(locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove phantom location fixes when vehicle is stopped"""
    # Configuration parameters
    STOP_DISTANCE_THRESHOLD = 140    # Max distance (meters) between points to be considered 'stopped'
    MIN_STOP_DURATION_SECONDS = 10 * 60  # Minimum duration (seconds) for a stop to be cleaned
    MEDIAN_WINDOW_SIZE = 18  # Number of points to consider for median calculation
    
    if len(locations) < 3:
        return locations  # Not enough data points to process
    
    # Sort by timestamp ascending
    sorted_locations = sorted(locations, key=lambda x: x['timestamp'])
    
    # Calculate median of next n points for each location
    for i in range(len(sorted_locations)):
        end_idx = min(i + 1 + MEDIAN_WINDOW_SIZE, len(sorted_locations))
        if i + 1 < end_idx:  # At least one point ahead
            future_points = sorted_locations[i+1:end_idx]
            
            # Calculate median position
            future_lats = [float(loc['latitude']) for loc in future_points]
            future_lngs = [float(loc['longitude']) for loc in future_points]
            
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
            start_time = datetime.fromisoformat(stop_candidates[0]['timestamp'])
            end_time = datetime.fromisoformat(stop_candidates[-1]['timestamp'])
            duration = (end_time - start_time).total_seconds()
            
            if duration >= MIN_STOP_DURATION_SECONDS:
                # Long stop: Keep only the first point and mark it as a stop point
                stop_candidate = stop_candidates[0].copy()
                stop_candidate['segment_type'] = 'stopped'
                stop_candidate['stop_duration_seconds'] = duration
                cleaned_data.append(stop_candidate)
                # Move the main index past all points in this long stop
                i = j
            else:
                # Short stop or just noise: Keep all points in the sequence as movement
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


# Database setup
dynamodb = boto3.resource("dynamodb")
locations_table = dynamodb.Table(os.environ.get("DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations"))


def handler(event, context):
    try:
        response = locations_table.query(
            KeyConditionExpression=Key('id').eq('vehicle_01'),
            ScanIndexForward=False,  # newest first
            Limit=500
        )

        items = response.get('Items', [])
        if not items:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "No location data found"})
            }

        # Sort ascending by timestamp
        items_sorted = sorted(items, key=lambda x: x['timestamp'])

        # Filter by movement session
        session = [items_sorted[-1]]  # start from latest
        last_time = datetime.fromisoformat(items_sorted[-1]['timestamp'])

        for i in range(len(items_sorted) - 2, -1, -1):
            curr = items_sorted[i]
            curr_time = datetime.fromisoformat(curr['timestamp'])

            time_diff = last_time - curr_time
            distance = haversine(
                float(curr['latitude']), float(curr['longitude']),
                float(session[-1]['latitude']), float(session[-1]['longitude'])
            )

            if time_diff > timedelta(minutes=60):
                break

            if distance > 20:
                session.append(curr)
                last_time = curr_time

        # Sort chronologically for processing
        session_sorted = sorted(session, key=lambda x: x['timestamp'])
        
        # Clean phantom locations
        cleaned_session = clean_phantom_locations(session_sorted)

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,GET"
            },
            "body": json.dumps(cleaned_session, default=decimal_default)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }