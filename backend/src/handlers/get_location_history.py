from decimal import Decimal
import json
import os

import boto3
from boto3.dynamodb.conditions import Key

# IMPORTANT: DynamoDB timestamp schema
# The 'timestamp' field is a Number (representing UTC epoch timestamp in seconds)
# This is used as the sort key in DynamoDB tables


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


dynamodb = boto3.resource("dynamodb")

# Get table names from environment variables or use defaults (matching actual names in AWS)
locations_table_name = os.environ.get(
    "DYNAMODB_LOCATIONS_TABLE", "gps-tracking-service-dev-locations-v2"
)

# Create table resource
table = dynamodb.Table(locations_table_name)
print(f"Using locations table: {locations_table_name}")


def handler(event, context):
    try:
        response = table.query(
            KeyConditionExpression=Key("id").eq("vehicle_01"),
            ScanIndexForward=False,  # newest first
            Limit=50,
        )

        items = response.get("Items", [])
        # Sort by timestamp which is now a number
        items_sorted = sorted(items, key=lambda x: x["timestamp"])

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,GET",
            },
            "body": json.dumps(items_sorted, default=decimal_default),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
