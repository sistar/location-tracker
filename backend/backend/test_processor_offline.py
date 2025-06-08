#!/usr/bin/env python3
"""
Offline test for processor.py logic
Processes GPS data from JSONL file through processor logic without DynamoDB dependency
"""

import datetime
from decimal import Decimal
import json
import math
import os
import sys
from typing import Any, Dict, List

# Add the handlers directory to the path so we can import processor functions
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'handlers'))

# Input and output file paths
INPUT_FILE = "/Users/ralf.sigmund/GitHub/mp_m5_fahrtenbuch/gps_logs/gps_logs/2025-04-22_locations.jsonl"
OUTPUT_FILE = "processor_test_results.jsonl"

# Global variables (matching processor.py)
last_valid_location = None
location_history: List[Dict[str, Any]] = []

def reset_location_history():
    """Reset the location history."""
    global location_history
    location_history = []

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

def is_outlier(location: Dict[str, Any], threshold_meters: float = 725) -> bool:
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

def to_decimal_safe(value):
    """Safely convert values to Decimal (for JSON serialization we'll use float)."""
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return None

def process_single_location_offline(location_data, output_file):
    """Process a single location data point (offline version without DynamoDB)."""
    global last_valid_location, location_history

    try:
        # Add to location history for filtering
        location_history.append(location_data)
        if len(location_history) > 10:
            location_history.pop(0)

        # Prepare the result record
        result = {
            "input": location_data,
            "processed_at": datetime.datetime.now().isoformat(),
            "processing_result": None,
            "stored": False,
            "reason": None,
            "distance_from_last": None
        }

        # Calculate distance from last valid location if available
        if last_valid_location:
            result["distance_from_last"] = haversine_distance(
                last_valid_location["lat"], last_valid_location["lon"],
                location_data["lat"], location_data["lon"]
            )

        # Check if outlier
        if is_outlier(location_data):
            result["processing_result"] = "outlier_filtered"
            result["reason"] = "Location identified as outlier"
            output_file.write(json.dumps(result) + '\n')
            return result

        # Check if there's significant movement compared to the last stored location
        if last_valid_location and not is_significant_movement(location_data, last_valid_location):
            result["processing_result"] = "no_significant_movement"
            result["reason"] = "Movement less than minimum threshold"
            output_file.write(json.dumps(result) + '\n')
            return result

        # This is a valid location with significant movement, prepare for "storage"
        timestamp_iso = location_data.get("time", datetime.datetime.now().isoformat())

        # Process elevation
        elevation_in_meters = str(location_data.get("ele", 0))
        if "M" in str(elevation_in_meters):
            elevation_in_meters = elevation_in_meters.replace("M", "")

        # Create the processed item (what would be stored in DynamoDB)
        processed_item = {
            "id": location_data.get("device_id", "unknown_device"),
            "timestamp_iso": timestamp_iso,
            "timestamp": to_decimal_safe(location_data.get("timestamp")),
            "lat": to_decimal_safe(location_data["lat"]),
            "lon": to_decimal_safe(location_data["lon"]),
            "ele": to_decimal_safe(elevation_in_meters),
            "quality": location_data.get("quality", "unknown"),
            "processed_at": datetime.datetime.now().isoformat(),
            "cog": to_decimal_safe(location_data.get("cog")),
            "sog": to_decimal_safe(location_data.get("sog")),
            "satellites_used": to_decimal_safe(location_data.get("satellites_used"))
        }

        # Remove None values from item
        processed_item = {k: v for k, v in processed_item.items() if v is not None}

        # Update the last valid location
        last_valid_location = location_data.copy()

        result["processing_result"] = "stored"
        result["stored"] = True
        result["processed_item"] = processed_item
        result["reason"] = "Valid location with significant movement"

        output_file.write(json.dumps(result) + '\n')
        return result

    except Exception as e:
        result["processing_result"] = "error"
        result["reason"] = f"Processing error: {str(e)}"
        output_file.write(json.dumps(result) + '\n')
        return result

def main():
    """Main function to process the GPS log file."""
    print(f"Processing GPS data from: {INPUT_FILE}")
    print(f"Output will be written to: {OUTPUT_FILE}")
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file {INPUT_FILE} does not exist")
        return 1
    
    # Reset processing state
    reset_location_history()
    global last_valid_location
    last_valid_location = None
    
    # Statistics
    stats = {
        "total_processed": 0,
        "stored": 0,
        "outliers_filtered": 0,
        "no_significant_movement": 0,
        "errors": 0
    }
    
    try:
        with open(INPUT_FILE, 'r') as input_file, open(OUTPUT_FILE, 'w') as output_file:
            print("Starting processing...")
            
            for line_num, line in enumerate(input_file, 1):
                try:
                    # Parse JSON line
                    location_data = json.loads(line.strip())
                    
                    # Process the location
                    result = process_single_location_offline(location_data, output_file)
                    
                    # Update statistics
                    stats["total_processed"] += 1
                    if result["processing_result"] == "stored":
                        stats["stored"] += 1
                    elif result["processing_result"] == "outlier_filtered":
                        stats["outliers_filtered"] += 1
                    elif result["processing_result"] == "no_significant_movement":
                        stats["no_significant_movement"] += 1
                    elif result["processing_result"] == "error":
                        stats["errors"] += 1
                    
                    # Progress indicator
                    if line_num % 100 == 0:
                        print(f"Processed {line_num} lines...")
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    stats["errors"] += 1
                    continue
                    
        print(f"\nProcessing complete!")
        print(f"Results written to: {OUTPUT_FILE}")
        print(f"\nStatistics:")
        print(f"  Total processed: {stats['total_processed']}")
        print(f"  Stored: {stats['stored']}")
        print(f"  Filtered (no movement): {stats['no_significant_movement']}")
        print(f"  Filtered (outliers): {stats['outliers_filtered']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Storage rate: {stats['stored']/stats['total_processed']*100:.1f}%")
        
        return 0
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 