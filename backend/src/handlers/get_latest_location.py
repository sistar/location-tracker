# src/handlers/get_latest_location.py
from datetime import datetime
from decimal import Decimal
import json
import os

import boto3
from boto3.dynamodb.conditions import Key

# IMPORTANT: DynamoDB timestamp schema
# The 'timestamp' field is a Number (representing UTC epoch timestamp in seconds)
# This is used as the sort key in DynamoDB tables

# Let API Gateway handle CORS

dynamodb = boto3.resource("dynamodb")

# Get table names from environment variables or use defaults (matching actual names in AWS)
locations_table_name = os.environ.get(
    "DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations-v2"
)

# Create table resource
table = dynamodb.Table(locations_table_name)
print(f"Using locations table: {locations_table_name}")


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def handler(event, context):
    # API Gateway will handle OPTIONS requests

    try:
        # Get vehicle_id from query parameters, default to 'vehicle_01'
        query_params = event.get("queryStringParameters", {}) or {}
        vehicle_id = query_params.get("vehicle_id", "vehicle_01")

        # Query the latest location
        response = table.query(
            KeyConditionExpression=Key("id").eq(vehicle_id),
            ScanIndexForward=False,  # descending order
            Limit=1,
        )

        # Add a human-readable timestamp for easier frontend display

        items = response.get("Items", [])
        if not items:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "No location found"}),
            }

        # Add a human-readable timestamp for the frontend
        location = items[0]
        if "timestamp" in location:
            try:
                # Handle different timestamp formats
                if isinstance(location["timestamp"], (int, float, Decimal)):
                    epoch_ts = float(location["timestamp"])
                    location["timestamp_str"] = datetime.fromtimestamp(
                        epoch_ts
                    ).isoformat()
                elif isinstance(location["timestamp"], str):
                    # If it's a string that looks like a number, convert it to epoch first
                    if location["timestamp"].isdigit():
                        epoch_ts = float(location["timestamp"])
                        location["timestamp_str"] = datetime.fromtimestamp(
                            epoch_ts
                        ).isoformat()
                    else:
                        # Otherwise assume it's already ISO format
                        location["timestamp_str"] = location["timestamp"]
            except Exception as e:
                print(f"Error converting timestamp to string: {str(e)}")
                # Provide a fallback timestamp string
                location["timestamp_str"] = str(location["timestamp"])

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(location, default=decimal_default),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }
