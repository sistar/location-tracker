# src/handlers/get_vehicle_ids.py
from decimal import Decimal
import json
import os

import boto3

# DynamoDB setup
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
    try:
        # Scan the table to get all unique vehicle IDs
        # Note: This is a simple implementation. For large tables, you might need pagination.
        response = table.scan(ProjectionExpression="id")

        items = response.get("Items", [])
        if not items:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Methods": "OPTIONS,GET",
                },
                "body": json.dumps({"message": "No vehicles found"}),
            }

        # Extract unique vehicle IDs
        unique_vehicle_ids = list(set(item["id"] for item in items))

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,GET",
            },
            "body": json.dumps({"vehicle_ids": unique_vehicle_ids}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
