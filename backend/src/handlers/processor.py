# src/handlers/processor.py
import datetime
import json
import math
import os
from typing import Any, Dict, List
import traceback

import boto3
from boto3.dynamodb.types import Decimal  # Add this import

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
# Get table names from environment variables or use defaults (matching actual names in AWS)
locations_table_name = os.environ.get("DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations-v2")
# Create table resource
table = dynamodb.Table(locations_table_name)
print(f"Using locations table: {locations_table_name}")

# Store the last known valid location
last_valid_location = None
location_history: List[Dict[str, Any]] = []

def reset_location_history():
    """Reset the location history."""
    global location_history
    location_history = []
def get_location_history():
    """Get the current location history."""
    global location_history
    return location_history

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


def is_outlier(location: Dict[str, Any], threshold_meters: float = 100) -> bool:
    """
    Determine if a location is an outlier based on distance from previous locations.
    Returns True if the location is likely an outlier.
    """
    global location_history

    if len(location_history) < 3:
        return False

    # Get previous locations
    recent_locations = location_history[-3:]

    # Calculate average position of recent locations
    avg_lat = sum(loc["lat"] for loc in recent_locations) / len(recent_locations)
    avg_lon = sum(loc["lon"] for loc in recent_locations) / len(recent_locations)

    # Calculate distance from average to current location
    distance = haversine_distance(avg_lat, avg_lon, location["lat"], location["lon"])

    # If distance is over threshold and quality isn't excellent, it's likely an outlier
    return distance > threshold_meters and location.get("quality", "") != "excellent"


def is_significant_movement(
    new_loc: Dict[str, Any], previous_loc: Dict[str, Any], min_distance: float = 10
) -> bool:
    """Determine if there's significant movement (more than min_distance meters)."""
    if not previous_loc:
        return True

    distance = haversine_distance(
        previous_loc["lat"], previous_loc["lon"], new_loc["lat"], new_loc["lon"]
    )

    return distance >= min_distance


def process_location(event, context):
    """
    Process incoming GPS location data, filter outliers and store significant movements.
    Can handle both single location events and lists of location events.
    """
    global last_valid_location, location_history

    try:
        # Check if the event is a list of locations or a single location
        if isinstance(event, list):
            print(f"Processing batch of {len(event)} locations")
            results = []
            for location_data in event:
                result = process_single_location(location_data)
                results.append(result)
            
            # Return a summary of the batch processing
            success_count = sum(1 for r in results if r['statusCode'] == 200)
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": f"Processed {len(event)} locations, {success_count} successful",
                    "details": results
                })
            }
        else:
            # Process a single location
            return process_single_location(event)

    except Exception as e:
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def process_single_location(location_data):
    """Process a single location data point."""
    global last_valid_location, location_history

    try:
        # Add to location history for filtering
        location_history.append(location_data)
        if len(location_history) > 10:
            location_history.pop(0)


        # Check if there's significant movement compared to the last stored location
        if last_valid_location and not is_significant_movement(
            location_data, last_valid_location
        ):
            print(f"No significant movement, ignoring: {location_data}")
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "No significant movement"}),
            }

        # This is a valid location with significant movement, store it
        timestamp_iso = location_data.get("time", datetime.datetime.now().isoformat())

        # Helper function to safely convert values to Decimal
        def to_decimal(value):
            if value is None or value == "":
                return None
            return Decimal(str(value))

        # Save to DynamoDB
        elevation_in_meters = str(location_data.get("ele", 0))
        if "M" in str(elevation_in_meters):
            elevation_in_meters = elevation_in_meters.replace("M", "")  # Remove 'M' suffix

        item = {
            "id": location_data.get("device_id", "unknown_device"),  # Use device_id from location data
            "timestamp_iso": timestamp_iso,  # Store the original ISO timestamp
            "timestamp": to_decimal(location_data.get("timestamp")),  # Use numeric epoch timestamp as sort key
            "lat": to_decimal(location_data["lat"]),
            "lon": to_decimal(location_data["lon"]),
            "ele": to_decimal(elevation_in_meters),
            "quality": location_data.get("quality", "unknown"),
            "processed_at": datetime.datetime.now().isoformat(),
            "cog": to_decimal(location_data.get("cog")),
            "sog": to_decimal(location_data.get("sog")),
            "satellites_used": to_decimal(location_data.get("satellites_used"))
        }

        # Remove None values from item
        item = {k: v for k, v in item.items() if v is not None}

        table.put_item(Item=item)

        # Update the last valid location - store the original data for comparison
        # but keep the item for DynamoDB operations
        last_valid_location = location_data.copy()
        print(f"Stored location data: {item}")
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "Location processed and stored"}),
        }

    except Exception as e:
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
