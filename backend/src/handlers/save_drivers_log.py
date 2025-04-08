import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

# Let API Gateway handle CORS

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get("DYNAMODB_LOCATIONS_TABLE", "LocationTable")
logs_table = dynamodb.Table(table_name + "-logs")  # Use a separate table for logs


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def convert_floats_to_decimal(obj):
    """Convert all float values in a dict/list to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(i) for i in obj]
    else:
        return obj


def handler(event, context):
    # API Gateway will handle OPTIONS requests
        
    try:
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        
        if not body.get('sessionId') or not body.get('startTime') or not body.get('endTime'):
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "Missing required fields"})
            }
        
        # Create log entry
        log_entry = {
            'id': body.get('sessionId'),
            'timestamp': datetime.utcnow().isoformat(),
            'startTime': body.get('startTime'),
            'endTime': body.get('endTime'),
            'distance': body.get('distance'),
            'duration': body.get('duration'),
            'purpose': body.get('purpose', ''),
            'notes': body.get('notes', '')
        }
        
        # Convert any float values to Decimal before saving to DynamoDB
        log_entry = convert_floats_to_decimal(log_entry)
        
        # Save to DynamoDB
        logs_table.put_item(Item=log_entry)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Log entry saved successfully", "id": log_entry['id']})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }