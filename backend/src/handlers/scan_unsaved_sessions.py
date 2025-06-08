from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
import math
import os
import statistics
import traceback
from typing import Any, Dict, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Key

# Database setup
dynamodb = boto3.resource("dynamodb")
locations_table = dynamodb.Table(
    os.environ.get("DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations-v2")
)
logs_table = dynamodb.Table(
    os.environ.get(
        "DYNAMODB_LOCATIONS_LOGS_TABLE", "gps-tracking-service-dev-locations-logs-v2"
    )
)

# Configuration parameters
SESSION_GAP_MINUTES = (
    180  # Increased gap in minutes to consider a new session (3 hours instead of 2)
)
MIN_SESSION_DURATION_MINUTES = 5  # Minimum session duration in minutes
MIN_SESSION_DISTANCE_METERS = 500  # Minimum distance for a valid session
MAX_SESSIONS_TO_RETURN = 100  # Maximum number of sessions to return

# New: Additional parameters for smarter session detection
MAX_STOP_GAP_MINUTES = (
    45  # Maximum gap during a normal stop before considering it a new session
)
MAX_CHARGING_GAP_MINUTES = (
    300  # Maximum gap during charging (5 hours) before considering it a new session
)
MAX_SPEED_KMH = 150  # Maximum reasonable vehicle speed for gap analysis


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def clean_phantom_locations(locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove phantom location fixes when vehicle is stopped - same as in get_dynamic_location_history"""
    # Configuration parameters
    STOP_DISTANCE_THRESHOLD = (
        140  # Max distance (meters) between points to be considered 'stopped'
    )
    MIN_STOP_DURATION_SECONDS = (
        10 * 60
    )  # Minimum duration (seconds) for a stop to be cleaned
    MEDIAN_WINDOW_SIZE = 18  # Number of points to consider for median calculation

    if len(locations) < 3:
        return locations  # Not enough data points to process

    # Sort by timestamp ascending
    sorted_locations = sorted(locations, key=lambda x: x["timestamp"])

    # Calculate median of next n points for each location
    for i in range(len(sorted_locations)):
        end_idx = min(i + 1 + MEDIAN_WINDOW_SIZE, len(sorted_locations))
        if i + 1 < end_idx:  # At least one point ahead
            future_points = sorted_locations[i + 1 : end_idx]

            # Calculate median position
            future_lats = [float(loc["lat"]) for loc in future_points]
            future_lngs = [float(loc["lon"]) for loc in future_points]

            if future_lats and future_lngs:
                sorted_locations[i]["next_n_median_latitude"] = statistics.median(
                    future_lats
                )
                sorted_locations[i]["next_n_median_longitude"] = statistics.median(
                    future_lngs
                )

    # Initialize cleaned data list and processing index
    cleaned_data = []
    i = 0
    n = len(sorted_locations)

    while i < n:
        current_point = sorted_locations[i]

        # Start checking for a stop from the next point
        j = i + 1
        stop_candidates = [
            current_point
        ]  # Current point is always the start of a potential stop/movement

        # Find consecutive points within the distance threshold of the start point's next median
        while j < n:
            next_point = sorted_locations[j]

            # Skip points without median calculations (typically points near the end)
            if (
                "next_n_median_latitude" not in current_point
                or "next_n_median_longitude" not in current_point
                or "next_n_median_latitude" not in next_point
                or "next_n_median_longitude" not in next_point
            ):
                break

            distance = haversine(
                current_point["next_n_median_latitude"],
                current_point["next_n_median_longitude"],
                next_point["next_n_median_latitude"],
                next_point["next_n_median_longitude"],
            )

            if distance < STOP_DISTANCE_THRESHOLD:
                stop_candidates.append(next_point)
                j += 1
            else:
                break  # Movement detected, stop sequence ends

        # Evaluate the identified sequence (stop_candidates)
        if (
            len(stop_candidates) > 1
        ):  # We found at least one subsequent point that was 'stopped'
            start_time = datetime.fromtimestamp(int(stop_candidates[0]["timestamp"]))
            end_time = datetime.fromtimestamp(int(stop_candidates[-1]["timestamp"]))
            duration = (end_time - start_time).total_seconds()

            if duration >= MIN_STOP_DURATION_SECONDS:
                # Long stop: Keep only the first point and mark it as a stop point
                stop_candidate = stop_candidates[0].copy()
                stop_candidate["segment_type"] = "stopped"
                stop_candidate["stop_duration_seconds"] = duration
                cleaned_data.append(stop_candidate)
                # Move the main index past all points in this long stop
                i = j
            else:
                # Short stop or just noise: Keep all points in the sequence as movement
                for point in stop_candidates:
                    point_copy = point.copy()
                    point_copy["segment_type"] = "moving"
                    cleaned_data.append(point_copy)
                # Move the main index past all points in this sequence
                i = j
        else:
            # No stop detected starting at current_point, mark as moving
            point_copy = current_point.copy()
            point_copy["segment_type"] = "moving"
            cleaned_data.append(point_copy)
            i += 1

    # Remove the temporary median fields before returning
    for loc in cleaned_data:
        if "next_n_median_latitude" in loc:
            del loc["next_n_median_latitude"]
        if "next_n_median_longitude" in loc:
            del loc["next_n_median_longitude"]

    return cleaned_data


def fetch_vehicle_locations(
    vehicle_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Fetch locations for a vehicle within a time range"""
    try:
        print(f"Fetching data for vehicle {vehicle_id}")

        # Define query parameters
        query_params = {"KeyConditionExpression": Key("id").eq(vehicle_id)}

        # Add time range condition if provided
        if start_date and end_date:
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            query_params["KeyConditionExpression"] = Key("id").eq(vehicle_id) & Key(
                "timestamp"
            ).between(start_timestamp, end_timestamp)

        # Query the locations table
        response = locations_table.query(**query_params)
        items = response.get("Items", [])
        print(f"Found {len(items)} location data points")

        # Handle pagination if necessary
        while "LastEvaluatedKey" in response:
            response = locations_table.query(
                **query_params, ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            new_items = response.get("Items", [])
            items.extend(new_items)
            print(f"Retrieved additional {len(new_items)} points, total: {len(items)}")

        return items
    except Exception as e:
        print(f"Error fetching vehicle locations: {str(e)}")
        print(traceback.format_exc())
        return []


def is_time_in_existing_log(vehicle_id: str, timestamp: str) -> bool:
    """Check if a timestamp falls within any existing driver's log entry"""
    try:
        # Scan all log entries (in a production app, you'd use a GSI or more optimized approach)
        response = logs_table.scan()
        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = logs_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        # Check if the timestamp falls within any log entry's time range
        # and belongs to the same vehicle
        for item in items:
            start_time = item.get("startTime")
            end_time = item.get("endTime")
            log_vehicle_id = item.get("vehicleId")

            if start_time and end_time and log_vehicle_id == vehicle_id:
                if start_time <= timestamp <= end_time:
                    print(f"existing log {item} for timestamp {timestamp}")
                    return True

        return False
    except Exception as e:
        print(f"Error checking existing logs: {str(e)}")
        return False


def is_new_session_gap(
    last_location: Dict[str, Any], current_location: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Determine if there should be a session break between two locations
    Returns (is_new_session, reason)
    """
    last_timestamp = datetime.fromtimestamp(int(last_location["timestamp"]))
    current_timestamp = datetime.fromtimestamp(int(current_location["timestamp"]))
    time_gap_minutes = (current_timestamp - last_timestamp).total_seconds() / 60

    # Calculate distance between points
    distance_meters = haversine(
        float(last_location["lat"]),
        float(last_location["lon"]),
        float(current_location["lat"]),
        float(current_location["lon"]),
    )

    # Check if the last location was charging
    last_segment_type = last_location.get("segment_type", "moving")
    is_charging_gap = last_segment_type == "charging"

    # Use different thresholds based on whether it's a charging stop
    max_gap_threshold = (
        MAX_CHARGING_GAP_MINUTES if is_charging_gap else MAX_STOP_GAP_MINUTES
    )

    # If gap is very long (> 3 hours for normal, > 5 hours for charging), definitely a new session
    if time_gap_minutes > SESSION_GAP_MINUTES:
        if not is_charging_gap or time_gap_minutes > MAX_CHARGING_GAP_MINUTES:
            return (
                True,
                f"Long time gap: {time_gap_minutes:.1f} minutes ({'charging' if is_charging_gap else 'normal'})",
            )

    # If gap is short (< threshold), likely same session
    if time_gap_minutes <= max_gap_threshold:
        gap_type = "charging" if is_charging_gap else "normal"
        return False, f"Short {gap_type} gap: {time_gap_minutes:.1f} minutes"

    # For medium gaps, check if movement is reasonable
    if time_gap_minutes > max_gap_threshold:
        # Calculate implied speed if this were continuous movement
        if time_gap_minutes > 0:
            implied_speed_kmh = (distance_meters / 1000) / (time_gap_minutes / 60)

            # For charging gaps, be more lenient with speed checks
            speed_threshold = MAX_SPEED_KMH * (2 if is_charging_gap else 1)

            # If implied speed is reasonable, probably same session
            if implied_speed_kmh <= speed_threshold:
                gap_type = "charging" if is_charging_gap else "normal"
                return (
                    False,
                    f"Reasonable speed {gap_type} gap: {time_gap_minutes:.1f}min, {implied_speed_kmh:.1f}km/h",
                )
            else:
                gap_type = "charging" if is_charging_gap else "normal"
                return (
                    True,
                    f"Unreasonable speed {gap_type} gap: {time_gap_minutes:.1f}min, {implied_speed_kmh:.1f}km/h",
                )

    # Default to continuing session for medium gaps
    gap_type = "charging" if is_charging_gap else "normal"
    return False, f"Medium {gap_type} gap continued: {time_gap_minutes:.1f} minutes"


def identify_sessions(
    vehicle_id: str, locations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Identify distinct sessions from locations data"""
    if not locations:
        return []

    # Sort locations by timestamp
    sorted_locations = sorted(locations, key=lambda x: x["timestamp"])

    # Apply phantom cleanup to identify stops vs moving segments
    # cleaned_locations = clean_phantom_locations(sorted_locations)
    cleaned_locations = sorted_locations

    # Find session boundaries with improved logic
    sessions = []
    current_session = []

    for i, location in enumerate(cleaned_locations):
        current_timestamp = datetime.fromtimestamp(int(location["timestamp"]))

        # Check if this point starts a new session (improved logic)
        if current_session:  # If we have a previous location
            last_location = current_session[-1]
            is_new_session, reason = is_new_session_gap(last_location, location)

            if is_new_session:
                # Process completed session
                last_timestamp = datetime.fromtimestamp(int(last_location["timestamp"]))
                print(
                    f"ending session: {reason} (current:{current_timestamp} prev:{last_timestamp})"
                )

                session_info = process_session(vehicle_id, current_session)
                if session_info:
                    sessions.append(session_info)
                current_session = []

        # Add point to current session
        current_session.append(location)

    # Process the last session
    if current_session:
        session_info = process_session(vehicle_id, current_session)
        if session_info:
            sessions.append(session_info)

    return sessions


def process_session(
    vehicle_id: str, session_points: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Process a session and calculate relevant metrics"""
    if not session_points or len(session_points) < 2:
        return None

    # Sort by timestamp to ensure correct order
    session_points = sorted(session_points, key=lambda x: x["timestamp"])

    start_point = session_points[0]
    end_point = session_points[-1]
    start_time = datetime.fromtimestamp(int(start_point["timestamp"]))
    end_time = datetime.fromtimestamp(int(end_point["timestamp"]))

    # Calculate duration in minutes
    duration = (end_time - start_time).total_seconds() / 60

    # Skip sessions that are too short
    if duration < MIN_SESSION_DURATION_MINUTES:
        return None

    # Calculate distance and movement metrics
    total_distance = 0
    moving_points = []
    stopped_points = []
    moving_time = 0
    stopped_time = 0

    for i in range(1, len(session_points)):
        prev = session_points[i - 1]
        curr = session_points[i]

        # Calculate distance for this segment
        segment_distance = haversine(
            float(prev["lat"]),
            float(prev["lon"]),
            float(curr["lat"]),
            float(curr["lon"]),
        )

        total_distance += segment_distance

        # Track moving vs stopped points
        if curr.get("segment_type") == "stopped":
            stopped_points.append(curr)
            if curr.get("stop_duration_seconds"):
                stopped_time += (
                    float(curr["stop_duration_seconds"]) / 60
                )  # Convert to minutes
        else:
            moving_points.append(curr)
            prev_time = datetime.fromtimestamp(int(prev["timestamp"]))
            curr_time = datetime.fromtimestamp(int(curr["timestamp"]))
            moving_time += (
                curr_time - prev_time
            ).total_seconds() / 60  # Convert to minutes

    # Skip sessions with very little movement
    if total_distance < MIN_SESSION_DISTANCE_METERS:
        print(
            f"skipping session with dist {total_distance} from {start_time} to {end_time}"
        )
        return None

    # Calculate average speed (km/h) during moving segments
    avg_speed = 0
    if moving_time > 0:
        # Convert: meters/minute to km/hour
        avg_speed = (total_distance / 1000) / (moving_time / 60)

    # Generate a unique session ID
    session_id = f"session_{start_time.timestamp():.0f}_{vehicle_id}"

    # Check if this session is already covered by an existing driver's log
    if is_time_in_existing_log(
        vehicle_id, start_point["timestamp"]
    ) or is_time_in_existing_log(vehicle_id, end_point["timestamp"]):
        print(f"skipping session overlapping from {start_time} to {end_time}")
        # Skip this session as it overlaps with an existing log
        return None

    # Create session info object with ISO timestamps for easier analysis
    session_info = {
        "id": session_id,
        "vehicleId": vehicle_id,
        "startTime": start_point["timestamp"],
        "endTime": end_point["timestamp"],
        "startTimeISO": start_time.isoformat(),
        "endTimeISO": end_time.isoformat(),
        "duration": duration,
        "distance": total_distance,
        "movingTime": moving_time,
        "stoppedTime": stopped_time,
        "avgSpeed": avg_speed,
        "numPoints": len(session_points),
        "numStops": len(stopped_points),
        "startLat": float(start_point["lat"]),
        "startLon": float(start_point["lon"]),
        "endLat": float(end_point["lat"]),
        "endLon": float(end_point["lon"]),
    }

    return session_info


def handler(event, context):
    try:
        # Extract query parameters
        query_params = event.get("queryStringParameters", {}) or {}
        vehicle_id = query_params.get("vehicle_id", "vehicle_01")

        # Handle days parameter - if not specified or set to "all", scan entire dataset
        days_param = query_params.get("days", "7")
        scan_all = days_param.lower() == "all" if isinstance(days_param, str) else False

        if scan_all:
            # Scan entire dataset - no date range restriction
            start_date = None
            end_date = None
            days_to_scan = None
            print(f"Scanning entire location dataset for vehicle {vehicle_id}")
        else:
            # Use specified days parameter for efficient scanning
            try:
                days_to_scan = int(days_param)
                if days_to_scan <= 0:
                    days_to_scan = 7  # Default to 7 days if invalid value
            except (ValueError, TypeError):
                days_to_scan = 7  # Default to 7 days if invalid value

            # Calculate date range for limited scan
            end_date = datetime.now(tz=UTC)
            start_date = end_date - timedelta(days=days_to_scan)
            print(
                f"Scanning {days_to_scan} days of location data for vehicle {vehicle_id}"
            )

        # Fetch location data for the vehicle
        locations = fetch_vehicle_locations(vehicle_id, start_date, end_date)

        if not locations:
            scan_type = "entire dataset" if scan_all else f"last {days_to_scan} days"
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "message": f"No location data found for the vehicle in the {scan_type}",
                        "vehicle_id": vehicle_id,
                        "scan_all": scan_all,
                    }
                ),
            }

        print(f"Processing {len(locations)} location points for session detection")

        # Identify sessions
        sessions = identify_sessions(vehicle_id, locations)

        # Sort by start time (newest first)
        sessions = sorted(sessions, key=lambda x: x["startTime"], reverse=True)

        # Limit the number of sessions returned
        sessions = sessions[:MAX_SESSIONS_TO_RETURN]

        # Format response
        response = {
            "vehicle_id": vehicle_id,
            "scan_period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
                "days": days_to_scan,
                "scan_all": scan_all,
                "total_data_points": len(locations),
            },
            "sessions": sessions,
            "total_sessions_found": len(sessions),
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(response, default=decimal_default),
        }

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
