#!/usr/bin/env python3
"""
Reprocess a single GPS file with enhanced temporal-aware outlier detection
"""

import json
import os
import sys
import boto3
import requests
from datetime import datetime
import time

# Configuration
DYNAMODB_TABLE = "gps-tracking-service-dev-locations-v2"
LAMBDA_ENDPOINT = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/drivers-log"

# Initialize AWS client
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table(DYNAMODB_TABLE)

def reprocess_file(file_path):
    """Reprocess a single GPS file."""
    print(f"\n🔄 Reprocessing: {os.path.basename(file_path)}")
    print("=" * 60)
    
    # Read and analyze file
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    first_data = json.loads(lines[0])
    last_data = json.loads(lines[-1])
    
    device_id = first_data['device_id']
    start_ts = first_data['timestamp']
    end_ts = last_data['timestamp']
    
    print(f"📊 File contains {len(lines)} GPS points")
    print(f"🔧 Device: {device_id}")
    print(f"⏰ Range: {first_data['time']} to {last_data['time']}")
    
    # Check existing data
    try:
        response = table.query(
            KeyConditionExpression='id = :device_id AND #ts BETWEEN :start_ts AND :end_ts',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':device_id': device_id,
                ':start_ts': start_ts,
                ':end_ts': end_ts
            }
        )
        existing_items = response.get('Items', [])
        print(f"🗑️  Will delete {len(existing_items)} existing records")
        
    except Exception as e:
        print(f"❌ Error checking DynamoDB: {e}")
        return False
    
    # Delete existing data
    print(f"\n🗑️  Deleting existing data...")
    deleted_count = 0
    for item in existing_items:
        try:
            table.delete_item(
                Key={
                    'id': item['id'],
                    'timestamp': item['timestamp']
                }
            )
            deleted_count += 1
            if deleted_count % 50 == 0:
                print(f"   Deleted {deleted_count}/{len(existing_items)} records...")
        except Exception as e:
            print(f"   ⚠️  Error deleting record: {e}")
    
    print(f"✅ Deleted {deleted_count} records")
    
    # Resubmit data
    print(f"\n🚀 Resubmitting {len(lines)} GPS points...")
    success_count = 0
    batch_count = 0
    
    for i, line in enumerate(lines):
        try:
            data = json.loads(line)
            
            response = requests.post(
                LAMBDA_ENDPOINT,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"   ⚠️  Failed to submit point {i+1}: {response.status_code}")
                
            # Progress and rate limiting
            if (i + 1) % 50 == 0:
                print(f"   📤 Submitted {i+1}/{len(lines)} points...")
                time.sleep(0.5)  # Rate limiting
                
        except Exception as e:
            print(f"   ❌ Error submitting point {i+1}: {e}")
    
    print(f"✅ Resubmitted {success_count}/{len(lines)} points successfully")
    
    # Summary
    improvement = success_count - len(existing_items)
    if improvement > 0:
        print(f"\n🎉 SUCCESS: +{improvement} more GPS points stored!")
        print(f"   Before: {len(existing_items)} points")
        print(f"   After: {success_count} points") 
        print(f"   Improvement: {improvement/len(lines)*100:.1f}%")
    else:
        print(f"\n📊 Processed but no improvement in storage")
        
    return True

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 reprocess_single_file.py <path_to_jsonl_file>")
        print("\nExample:")
        print("python3 reprocess_single_file.py /path/to/2025-04-22_locations.jsonl")
        return 1
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return 1
    
    print("🔄 GPS File Reprocessing")
    print("Enhanced with temporal-aware outlier detection")
    print("=" * 60)
    
    confirm = input(f"🤔 Reprocess {os.path.basename(file_path)}? (yes/no): ").lower().strip()
    if confirm != 'yes':
        print("❌ Cancelled")
        return 0
    
    try:
        success = reprocess_file(file_path)
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 