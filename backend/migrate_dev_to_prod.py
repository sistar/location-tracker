#!/usr/bin/env python3
"""
Script to migrate data from dev to prod DynamoDB tables.
Copies data from gps-tracking-service-dev-locations-v2 to gps-tracking-service-prod-locations-v2
"""

import boto3
import json
from decimal import Decimal
from botocore.exceptions import ClientError
import time

# Table names
SOURCE_TABLE = "gps-tracking-service-dev-locations-v2"
TARGET_TABLE = "gps-tracking-service-prod-locations-v2"

def decimal_default(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def copy_table_data():
    """Copy all data from source table to target table"""
    dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
    
    source_table = dynamodb.Table(SOURCE_TABLE)
    target_table = dynamodb.Table(TARGET_TABLE)
    
    print(f"Starting migration from {SOURCE_TABLE} to {TARGET_TABLE}")
    
    try:
        # Scan the source table
        print("Scanning source table...")
        response = source_table.scan()
        items = response['Items']
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            print(f"Found {len(items)} items so far, continuing scan...")
            response = source_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        total_items = len(items)
        print(f"Found {total_items} items to migrate")
        
        if total_items == 0:
            print("No items found in source table")
            return
        
        # Batch write to target table
        print("Starting batch write to target table...")
        batch_size = 25  # DynamoDB batch write limit
        
        with target_table.batch_writer() as batch:
            for i, item in enumerate(items):
                try:
                    # Put item to target table
                    batch.put_item(Item=item)
                    
                    if (i + 1) % batch_size == 0:
                        print(f"Processed {i + 1}/{total_items} items")
                        time.sleep(0.1)  # Small delay to avoid throttling
                        
                except Exception as e:
                    print(f"Error writing item {i}: {e}")
                    print(f"Item: {json.dumps(item, default=decimal_default)}")
                    continue
        
        print(f"Migration completed! Copied {total_items} items")
        
        # Verify the copy
        print("Verifying migration...")
        target_response = target_table.scan(Select='COUNT')
        target_count = target_response['Count']
        
        while 'LastEvaluatedKey' in target_response:
            target_response = target_table.scan(
                Select='COUNT',
                ExclusiveStartKey=target_response['LastEvaluatedKey']
            )
            target_count += target_response['Count']
        
        print(f"Source table items: {total_items}")
        print(f"Target table items: {target_count}")
        
        if target_count >= total_items:
            print("✅ Migration verification successful!")
        else:
            print("⚠️ Warning: Target table has fewer items than expected")
            
    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Code']}: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error during migration: {e}")
        return False
    
    return True

def check_table_exists(table_name):
    """Check if a table exists"""
    dynamodb = boto3.client('dynamodb', region_name='eu-central-1')
    
    try:
        response = dynamodb.describe_table(TableName=table_name)
        status = response['Table']['TableStatus']
        print(f"Table {table_name} exists with status: {status}")
        return status == 'ACTIVE'
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"Table {table_name} does not exist")
            return False
        else:
            print(f"Error checking table {table_name}: {e}")
            return False

if __name__ == "__main__":
    print("DynamoDB Data Migration Script")
    print("=" * 50)
    
    # Check if both tables exist
    if not check_table_exists(SOURCE_TABLE):
        print(f"❌ Source table {SOURCE_TABLE} not found or not active")
        exit(1)
    
    if not check_table_exists(TARGET_TABLE):
        print(f"❌ Target table {TARGET_TABLE} not found or not active")
        exit(1)
    
    # Proceed with migration
    print(f"\nCopying ALL data from:")
    print(f"  SOURCE: {SOURCE_TABLE}")
    print(f"  TARGET: {TARGET_TABLE}")
    print(f"\nStarting migration...")
    
    success = copy_table_data()
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        exit(1)