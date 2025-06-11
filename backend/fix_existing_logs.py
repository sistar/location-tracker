#!/usr/bin/env python3
"""
Script to fix existing driver logs by adding missing vehicleId field.
"""

import boto3
import json
from decimal import Decimal
from botocore.exceptions import ClientError

# Table names
LOGS_TABLE = "gps-tracking-service-prod-locations-logs-v2"

def decimal_default(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def fix_logs_vehicleId():
    """Add vehicleId field to logs that are missing it"""
    dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
    logs_table = dynamodb.Table(LOGS_TABLE)
    
    print(f"Fixing missing vehicleId fields in {LOGS_TABLE}")
    
    try:
        # Scan the logs table
        print("Scanning logs table...")
        response = logs_table.scan()
        items = response['Items']
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            print(f"Found {len(items)} items so far, continuing scan...")
            response = logs_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        total_items = len(items)
        print(f"Found {total_items} log items to process")
        
        if total_items == 0:
            print("No items found in logs table")
            return
        
        fixed_count = 0
        
        for item in items:
            # Check if vehicleId is missing
            if 'vehicleId' not in item:
                print(f"Item {item.get('id', 'unknown')} is missing vehicleId")
                
                # Try to extract vehicleId from the session ID
                session_id = item.get('id', '')
                vehicle_id = 'vehicle_01'  # default
                
                if session_id:
                    # Session IDs often have format like "session_timestamp_vehicleId"
                    parts = session_id.split('_')
                    if len(parts) >= 3:
                        # Last part might be the vehicle ID
                        potential_vehicle_id = parts[-1]
                        if potential_vehicle_id in ['BlogClient', 'vehicle_01']:
                            vehicle_id = potential_vehicle_id
                            print(f"  Extracted vehicleId '{vehicle_id}' from session ID")
                
                # Update the item
                try:
                    logs_table.update_item(
                        Key={
                            'id': item['id'],
                            'timestamp': item['timestamp']
                        },
                        UpdateExpression='SET vehicleId = :vehicle_id',
                        ExpressionAttributeValues={
                            ':vehicle_id': vehicle_id
                        }
                    )
                    print(f"  ✅ Updated {item['id']} with vehicleId: {vehicle_id}")
                    fixed_count += 1
                except Exception as e:
                    print(f"  ❌ Error updating {item['id']}: {e}")
            else:
                print(f"Item {item.get('id', 'unknown')} already has vehicleId: {item['vehicleId']}")
        
        print(f"✅ Fixed {fixed_count}/{total_items} log entries")
        
    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Code']}: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error during fix: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("DynamoDB Driver Logs Repair Script")
    print("=" * 50)
    
    success = fix_logs_vehicleId()
    if success:
        print("\n✅ Repair completed successfully!")
    else:
        print("\n❌ Repair failed!")
        exit(1)