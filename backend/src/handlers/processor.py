# src/handlers/processor.py
import datetime
import json
import math
import os
import traceback
from typing import Any, Dict, List

import boto3
from boto3.dynamodb.types import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
# Get table names from environment variables or use defaults (matching actual names in AWS)
locations_table_name = os.environ.get(
    "DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations-v2"
)
# Create table resource
table = dynamodb.Table(locations_table_name)
print(f"Using locations table: {locations_table_name}")

# Global state for location history tracking
location_history: List[Dict[str, Any]] = []


def parse_timestamp(time_str: str) -> datetime.datetime:
    """Parse ISO timestamp to datetime object."""
    # Handle the timezone offset
    if "+" in time_str:
        time_part, tz_part = time_str.rsplit("+", 1)
        time_str = time_part  # Ignore timezone for simplicity
    elif time_str.endswith("Z"):
        time_str = time_str[:-1]

    return datetime.datetime.fromisoformat(time_str)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance between two GPS coordinates in meters."""
    R = 6371000  # Earth radius in meters

    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance


def calculate_speed_kmh(distance_meters: float, time_diff_seconds: float) -> float:
    """Calculate speed in km/h given distance and time difference."""
    if time_diff_seconds <= 0:
        return float("inf")

    speed_mps = distance_meters / time_diff_seconds  # meters per second
    speed_kmh = speed_mps * 3.6  # convert to km/h
    return speed_kmh


def is_outlier_temporal(
    location: Dict[str, Any], threshold_meters: float = 100, max_speed_kmh: float = 150
) -> tuple[bool, str]:
    """
    Determine if a location is an outlier based on both distance and realistic vehicle speeds.
    Returns True if the location is likely an outlier.
    """
    global location_history

    if len(location_history) < 1:
        return False, "Insufficient history"

    # Get the most recent location for temporal comparison
    recent_location = location_history[-1]

    # Calculate distance from most recent location
    distance = haversine_distance(
        recent_location["lat"], recent_location["lon"], location["lat"], location["lon"]
    )

    print(f"DEBUG: Comparing locations:")
    print(
        f"  Recent: lat={recent_location['lat']}, lon={recent_location['lon']}, ts={recent_location.get('timestamp', 'N/A')}"
    )
    print(
        f"  Current: lat={location['lat']}, lon={location['lon']}, ts={location.get('timestamp', 'N/A')}"
    )
    print(f"  Distance: {distance:.1f}m")

    # Use the timestamp field directly (epoch seconds)
    try:
        curr_timestamp = location.get("timestamp")
        prev_timestamp = recent_location.get("timestamp")

        if curr_timestamp is not None and prev_timestamp is not None:
            time_diff_seconds = curr_timestamp - prev_timestamp

            print(f"  Time diff: {time_diff_seconds} seconds")

            if time_diff_seconds > 0:
                # Calculate implied speed
                speed_kmh = calculate_speed_kmh(distance, time_diff_seconds)

                print(f"  Calculated speed: {speed_kmh:.1f} km/h")

                # Check if speed is unrealistic
                if speed_kmh > max_speed_kmh:
                    return (
                        True,
                        f"Unrealistic speed: {speed_kmh:.1f} km/h (max: {max_speed_kmh} km/h)",
                    )

                # For very short time gaps, still use distance threshold
                if time_diff_seconds < 10:  # Less than 10 seconds
                    if distance > threshold_meters:
                        return (
                            True,
                            f"Large distance in short time: {distance:.1f}m in {time_diff_seconds:.1f}s",
                        )

                # Speed is reasonable, not an outlier
                return (
                    False,
                    f"Reasonable movement: {distance:.1f}m in {time_diff_seconds/60:.1f}min ({speed_kmh:.1f} km/h)",
                )
            elif time_diff_seconds == 0:
                # Same timestamp - use distance only
                if distance > threshold_meters:
                    return (
                        True,
                        f"Distance threshold exceeded: {distance:.1f}m (same timestamp)",
                    )
                return False, "Same timestamp, distance OK"
            else:
                # Negative time diff (older timestamp) - this shouldn't happen in normal processing
                return True, f"Negative time difference: {time_diff_seconds}s"
        else:
            # No timestamps available, fall back to distance-based detection
            missing_ts = []
            if curr_timestamp is None:
                missing_ts.append("current")
            if prev_timestamp is None:
                missing_ts.append("previous")

            if distance > threshold_meters:
                return (
                    True,
                    f"Distance threshold exceeded: {distance:.1f}m (missing timestamp: {', '.join(missing_ts)})",
                )
            return (
                False,
                f"Distance within threshold (missing timestamp: {', '.join(missing_ts)})",
            )

    except Exception as e:
        # Error processing timestamps, fall back to distance-based detection
        print(f"  ERROR processing timestamps: {e}")
        if distance > threshold_meters:
            return (
                True,
                f"Distance threshold exceeded: {distance:.1f}m (timestamp error: {e})",
            )
        return False, "Distance within threshold (timestamp error)"


def is_significant_movement(
    new_loc: Dict[str, Any], previous_loc: Dict[str, Any], min_distance: float = 10
) -> bool:
    """
    Determine if there's significant movement (more than min_distance meters).
    """
    if not previous_loc:
        return True

    distance = haversine_distance(
        previous_loc["lat"], previous_loc["lon"], new_loc["lat"], new_loc["lon"]
    )

    return distance >= min_distance


def add_to_location_history(location: Dict[str, Any], max_history: int = 10):
    """Add a location to the history buffer for outlier detection."""
    global location_history

    print(
        f"DEBUG: Adding to history: lat={location['lat']}, lon={location['lon']}, ts={location.get('timestamp', 'N/A')}"
    )
    print(f"DEBUG: History size before: {len(location_history)}")

    location_history.append(location)
    if len(location_history) > max_history:
        removed = location_history.pop(0)
        print(
            f"DEBUG: Removed old location from history: lat={removed['lat']}, lon={removed['lon']}, ts={removed.get('timestamp', 'N/A')}"
        )

    print(f"DEBUG: History size after: {len(location_history)}")
    if len(location_history) > 0:
        recent = location_history[-1]
        print(
            f"DEBUG: Most recent in history: lat={recent['lat']}, lon={recent['lon']}, ts={recent.get('timestamp', 'N/A')}"
        )


def prepare_processed_item(location_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a location item for storage in DynamoDB."""
    # Extract device_id, defaulting to 'vehicle_01' if not provided
    device_id = location_data.get("device_id", "vehicle_01")

    # Use provided timestamp or current time
    timestamp = location_data.get("timestamp")
    if timestamp is None:
        timestamp = int(datetime.datetime.utcnow().timestamp())

    # Create ISO timestamp for human readability
    timestamp_iso = datetime.datetime.fromtimestamp(timestamp).isoformat()

    # Process elevation (remove 'M' suffix if present)
    elevation = location_data.get("ele")
    if isinstance(elevation, str) and elevation.endswith("M"):
        elevation = elevation[:-1]

    return {
        "id": device_id,
        "timestamp": timestamp,
        "timestamp_iso": timestamp_iso,
        "lat": location_data["lat"],
        "lon": location_data["lon"],
        "ele": float(elevation) if elevation is not None else None,
        "quality": location_data.get("quality"),
        "processed_at": datetime.datetime.utcnow().isoformat(),
        "cog": location_data.get("cog"),
        "sog": location_data.get("sog"),
        "satellites_used": location_data.get("satellites_used"),
    }


def process_location(event, context):
    """
    Process incoming GPS location data, filter outliers and store significant movements.
    Can handle both single location events, lists of location events, and HTTP API Gateway events.
    """
    try:
        # Handle HTTP API Gateway events
        if isinstance(event, dict) and "body" in event:
            print("Processing HTTP API Gateway event")

            # Parse the body
            body = event.get("body", "{}")
            if isinstance(body, str):
                request_data = json.loads(body)
            else:
                request_data = body

            # Check for skip_outlier_detection parameter
            skip_outlier_detection = request_data.get("skip_outlier_detection", False)

            # Extract the actual location data (remove skip_outlier_detection if present)
            location_data = {
                k: v for k, v in request_data.items() if k != "skip_outlier_detection"
            }

            # Process single location from HTTP request
            result = process_single_location(
                location_data, skip_outlier_detection=skip_outlier_detection
            )

            # Return HTTP response format
            return {
                "statusCode": result["statusCode"],
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": result["body"],
            }

        # Handle direct IoT events (existing logic)
        # Check if the event is a list of locations or a single location
        elif isinstance(event, list):
            print(f"Processing batch of {len(event)} locations")
            results = []
            for location_data in event:
                result = process_single_location(location_data)
                results.append(result)

            # Return a summary of the batch processing
            success_count = sum(1 for r in results if r["statusCode"] == 200)
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "status": f"Processed {len(event)} locations, {success_count} successful",
                        "details": results,
                    }
                ),
            }
        else:
            # Process a single location (direct IoT event)
            return process_single_location(event)

    except Exception as e:
        traceback.print_exc()
        error_response = {"statusCode": 500, "body": json.dumps({"error": str(e)})}

        # If it's an HTTP request, return proper HTTP response
        if isinstance(event, dict) and "body" in event:
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": str(e)}),
            }

        return error_response


def process_single_location(location_data, skip_outlier_detection=False):
    """Process a single location data point."""
    try:
        print(
            f"\nDEBUG: Processing location: lat={location_data['lat']}, lon={location_data['lon']}, ts={location_data.get('timestamp', 'N/A')}"
        )
        print(f"DEBUG: Current history size: {len(location_history)}")
        print(f"DEBUG: Skip outlier detection: {skip_outlier_detection}")

        # Check for outliers using temporal-aware detection (unless skipped)
        if not skip_outlier_detection:
            is_outlier, reason = is_outlier_temporal(
                location_data,
                threshold_meters=725,  # Distance threshold for outlier detection (fallback)
                max_speed_kmh=180,  # Maximum reasonable speed in km/h
            )

            if is_outlier:
                print(f"Not storing location: {reason}")
                return {
                    "statusCode": 200,
                    "body": json.dumps({"status": reason}),
                }

            # Check for significant movement (minimum 3 meters)
            if len(location_history) > 0:
                if not is_significant_movement(
                    location_data, location_history[-1], min_distance=3
                ):
                    print("Not storing location: Insufficient movement")
                    return {
                        "statusCode": 200,
                        "body": json.dumps({"status": "Insufficient movement"}),
                    }
        else:
            print("Skipping outlier detection for bulk reprocessing")

        # Location should be stored - prepare the processed item
        processed_item = prepare_processed_item(location_data)

        # Add to history for future outlier detection (only if not skipping)
        if not skip_outlier_detection:
            add_to_location_history(location_data, max_history=10)

        # Convert to Decimal for DynamoDB storage
        def to_decimal(value):
            if value is None or value == "":
                return None
            return Decimal(str(value))

        # Convert the processed item to DynamoDB format
        dynamodb_item = {
            "id": processed_item["id"],
            "timestamp_iso": processed_item["timestamp_iso"],
            "timestamp": to_decimal(processed_item["timestamp"]),
            "lat": to_decimal(processed_item["lat"]),
            "lon": to_decimal(processed_item["lon"]),
            "ele": to_decimal(processed_item["ele"]),
            "quality": processed_item["quality"],
            "processed_at": processed_item["processed_at"],
            "cog": to_decimal(processed_item.get("cog")),
            "sog": to_decimal(processed_item.get("sog")),
            "satellites_used": to_decimal(processed_item.get("satellites_used")),
        }

        # Remove None values from item
        dynamodb_item = {k: v for k, v in dynamodb_item.items() if v is not None}

        # Store to DynamoDB
        table.put_item(Item=dynamodb_item)

        print(f"Stored location data: {dynamodb_item}")
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "Location processed and stored"}),
        }

    except Exception as e:
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# Legacy function exports for backward compatibility
def reset_location_history():
    """Reset the location history (legacy function)."""
    global location_history
    location_history = []


def get_location_history():
    """Get the current location history (legacy function)."""
    global location_history
    return location_history
