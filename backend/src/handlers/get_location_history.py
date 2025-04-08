import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("gps-tracking-service-dev-locations")  # Change to your table name


def handler(event, context):
    try:
        response = table.query(
            KeyConditionExpression=Key('id').eq('vehicle_01'),
            ScanIndexForward=False,  # newest first
            Limit=50
        )

        items = response.get('Items', [])
        items_sorted = sorted(items, key=lambda x: x['timestamp'])

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,GET"
            },
            "body": json.dumps(items_sorted, default=decimal_default)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }
