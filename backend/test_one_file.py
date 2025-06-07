#!/usr/bin/env python3
"""
Test processing one file to verify the approach works
"""

import json
import os
import sys
import boto3
import requests
from datetime import datetime

# Configuration
DYNAMODB_TABLE = "gps-tracking-service-dev-locations-v2"
LAMBDA_ENDPOINT = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/drivers-log"
TEST_FILE = "/Users/ralf.sigmund/GitHub/mp_m5_fahrtenbuch/gps_logs/gps_logs/2025-04-22_locations.jsonl"

# Initialize AWS client
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table(DYNAMODB_TABLE)

def analyze_file():
    """Analyze the test file."""
    print(f"📂 Analyzing: {os.path.basename(TEST_FILE)}")
    
    with open(TEST_FILE, 'r') as f:
        lines = f.readlines()
        first_data = json.loads(lines[0].strip())
        last_data = json.loads(lines[-1].strip())
    
    print(f"   📊 Total lines: {len(lines)}")
    print(f"   🔧 Device ID: {first_data['device_id']}")
    print(f"   ⏰ First: {first_data['time']} (timestamp: {first_data['timestamp']})")
    print(f"   ⏰ Last: {last_data['time']} (timestamp: {last_data['timestamp']})")
    
    return first_data, last_data, len(lines)

def check_existing_data(device_id, start_ts, end_ts):
    """Check how many records exist in DynamoDB for this range."""
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
        
        items = response.get('Items', [])
        print(f"🗃️  Found {len(items)} existing records in DynamoDB for this time range")
        return len(items)
        
    except Exception as e:
        print(f"❌ Error checking DynamoDB: {e}")
        return 0

def main():
    print("🧪 Testing GPS Reprocessing with One File")
    print("=" * 50)
    
    # Analyze the file
    first_data, last_data, total_lines = analyze_file()
    
    # Check existing data
    device_id = first_data['device_id']
    start_ts = first_data['timestamp']
    end_ts = last_data['timestamp']
    
    existing_count = check_existing_data(device_id, start_ts, end_ts)
    
    print(f"\n📊 Summary:")
    print(f"   Raw GPS points in file: {total_lines}")
    print(f"   Currently stored in DB: {existing_count}")
    print(f"   Difference: {total_lines - existing_count} points were filtered")
    
    if existing_count > 0:
        filter_rate = (total_lines - existing_count) / total_lines * 100
        print(f"   Filter rate: {filter_rate:.1f}%")
    
    print(f"\n💡 With enhanced temporal filtering, more of these {total_lines} points should be stored!")
    
    # Ask if user wants to proceed with reprocessing this file
    proceed = input(f"\n🤔 Reprocess this file? (yes/no): ").lower().strip()
    
    if proceed != 'yes':
        print("❌ Cancelled")
        return 0
    
    print(f"\n🚀 This would:")
    print(f"   1. Delete {existing_count} existing records from DynamoDB")
    print(f"   2. Resubmit all {total_lines} GPS points to lambda")
    print(f"   3. Enhanced filtering should store more points")
    
    final_confirm = input(f"\n⚠️  Final confirmation - proceed? (yes/no): ").lower().strip()
    
    if final_confirm != 'yes':
        print("❌ Cancelled")
        return 0
    
    print("\n✅ Proceeding with reprocessing...")
    print("(Use the full reprocess_gps_data.py script for actual implementation)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 