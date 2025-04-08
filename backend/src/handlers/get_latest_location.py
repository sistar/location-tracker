# src/handlers/get_latest_location.py
import boto3
from boto3.dynamodb.conditions import Key
import os
import json
from decimal import Decimal

# Let API Gateway handle CORS

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get("DYNAMODB_LOCATIONS_TABLE")
if not table_name:
    raise ValueError("DYNAMODB_LOCATIONS_TABLE environment variable not set")
table = dynamodb.Table(table_name)


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def handler(event, context):
    # API Gateway will handle OPTIONS requests
        
    try:
        # Query the latest location
        response = table.query(
            KeyConditionExpression=Key('id').eq('vehicle_01'),
            ScanIndexForward=False,  # descending order
            Limit=1
        )

        items = response.get('Items', [])
        if not items:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "No location found"})
            }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(items[0], default=decimal_default)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
