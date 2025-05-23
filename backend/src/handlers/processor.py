# src/handlers/processor.py
import datetime
import json
import os
from typing import Any, Dict
import traceback

import boto3
from boto3.dynamodb.types import Decimal

# Import shared GPS processing logic
import gps_processing

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
# Get table names from environment variables or use defaults (matching actual names in AWS)
locations_table_name = os.environ.get("DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations-v2")
# Create table resource
table = dynamodb.Table(locations_table_name)
print(f"Using locations table: {locations_table_name}")

# Create GPS processor with default parameters
# You can adjust these parameters to tune the filtering behavior
gps_processor = gps_processing.GPSProcessor(
    outlier_threshold_meters=725,  # Distance threshold for outlier detection (fallback)
    min_movement_meters=3,        # Minimum movement to store location  
    max_history_size=10,          # Number of locations to keep in history
    max_speed_kmh=180             # Maximum reasonable speed in km/h
)

def process_location(event, context):
    """
    Process incoming GPS location data, filter outliers and store significant movements.
    Can handle both single location events and lists of location events.
    """
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
    global gps_processor
    
    try:
        # Use the shared GPS processor to determine if location should be stored
        processing_result = gps_processor.process_location(location_data)
        
        if not processing_result["should_store"]:
            print(f"Not storing location: {processing_result['reason']}")
            return {
                "statusCode": 200,
                "body": json.dumps({"status": processing_result["reason"]}),
            }

        # Location should be stored - get the processed item
        processed_item = processing_result["processed_item"]

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
            "satellites_used": to_decimal(processed_item.get("satellites_used"))
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
    gps_processor = gps_processing.GPSProcessor(
        outlier_threshold_meters=100,
        min_movement_meters=10,
        max_history_size=10
    )

def get_location_history():
    """Get the current location history (legacy function)."""
    return gps_processing.get_location_history()
