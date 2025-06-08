#!/usr/bin/env python3
"""
Reprocess GPS data with enhanced temporal-aware outlier detection
1. For each JSONL file, find the time range (first to last timestamp)
2. Delete old data from DynamoDB for that device_id and timestamp range
3. Send all raw data in chronological order as a batch to the lambda function
"""

from datetime import datetime
import json
import os
import sys
import time
from typing import Any, Dict, List

import boto3
from boto3.dynamodb.conditions import Attr, Key

# Configuration
GPS_LOGS_DIR = "/Users/ralf.sigmund/GitHub/mp_m5_fahrtenbuch/gps_logs/gps_logs"
LAMBDA_FUNCTION_NAME = "location-backend-dev-processLocationData"
DYNAMODB_TABLE = "gps-tracking-service-dev-locations-v2"
DEVICE_ID = "vehicle_01"

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table(DYNAMODB_TABLE)
lambda_client = boto3.client('lambda', region_name='eu-central-1')

def parse_timestamp(time_str: str) -> datetime:
    """Parse ISO timestamp to datetime object with robust error handling."""
    try:
        # Handle different timezone formats
        if '+' in time_str:
            time_part, tz_part = time_str.rsplit('+', 1)
            time_str = time_part  # Ignore timezone for simplicity
        elif time_str.endswith('Z'):
            time_str = time_str[:-1]
        elif ' MES' in time_str:
            # Handle "MES" timezone (Central European Summer Time)
            time_str = time_str.replace(' MES', '')
        elif ' CET' in time_str:
            # Handle "CET" timezone (Central European Time)
            time_str = time_str.replace(' CET', '')
        elif ' CEST' in time_str:
            # Handle "CEST" timezone (Central European Summer Time)
            time_str = time_str.replace(' CEST', '')
        
        # Try to parse the timestamp
        return datetime.fromisoformat(time_str)
    except ValueError as e:
        # If parsing fails, try to extract timestamp from epoch field if available
        print(f"   ⚠️  Warning: Could not parse timestamp '{time_str}': {e}")
        # Return a fallback datetime (we'll use epoch timestamp instead)
        return datetime(1970, 1, 1)

def analyze_jsonl_file(file_path: str) -> Dict[str, Any]:
    """Analyze a JSONL file to extract time range and device info."""
    print(f"\n📂 Analyzing: {os.path.basename(file_path)}")
    
    first_line = None
    last_line = None
    line_count = 0
    device_ids = set()
    parse_errors = 0
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    data = json.loads(line.strip())
                    device_ids.add(data.get('device_id', 'unknown'))
                    
                    if first_line is None:
                        first_line = data
                    last_line = data
                    line_count += 1
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️  Error parsing line {line_num}: {e}")
                    parse_errors += 1
                    continue
    
    if not first_line or not last_line:
        print(f"❌ No valid data found in {file_path}")
        return None
    
    # Use epoch timestamps directly if available, fallback to parsing time field
    start_timestamp = first_line.get('timestamp')
    end_timestamp = last_line.get('timestamp')
    
    if start_timestamp and end_timestamp:
        # Use epoch timestamps
        start_time = datetime.fromtimestamp(start_timestamp)
        end_time = datetime.fromtimestamp(end_timestamp)
    else:
        # Fallback to parsing time field
        try:
            start_time = parse_timestamp(first_line['time'])
            end_time = parse_timestamp(last_line['time'])
            # Convert to epoch if we don't have timestamp field
            if not start_timestamp:
                start_timestamp = int(start_time.timestamp())
            if not end_timestamp:
                end_timestamp = int(end_time.timestamp())
        except Exception as e:
            print(f"❌ Could not determine time range: {e}")
            return None
    
    info = {
        'file_path': file_path,
        'file_name': os.path.basename(file_path),
        'line_count': line_count,
        'device_ids': list(device_ids),
        'start_time': start_time,
        'end_time': end_time,
        'start_timestamp': start_timestamp,
        'end_timestamp': end_timestamp,
        'duration_hours': (end_time - start_time).total_seconds() / 3600,
        'parse_errors': parse_errors
    }
    
    print(f"   📊 Lines: {line_count}")
    if parse_errors > 0:
        print(f"   ⚠️  Parse errors: {parse_errors}")
    print(f"   🔧 Device IDs: {', '.join(device_ids)}")
    print(f"   ⏰ Time range: {start_time} to {end_time}")
    print(f"   ⌛ Duration: {info['duration_hours']:.1f} hours")
    print(f"   📅 Timestamps: {start_timestamp} to {end_timestamp}")
    
    return info

def delete_dynamodb_data(device_id: str, start_timestamp: int, end_timestamp: int) -> int:
    """Delete data from DynamoDB for the given device and timestamp range."""
    print(f"\n🗑️  Deleting DynamoDB data for {device_id} from {start_timestamp} to {end_timestamp}")
    
    deleted_count = 0
    
    try:
        # Query items in the timestamp range
        response = table.query(
            KeyConditionExpression='id = :device_id AND #ts BETWEEN :start_ts AND :end_ts',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':device_id': device_id,
                ':start_ts': start_timestamp,
                ':end_ts': end_timestamp
            }
        )
        
        items = response.get('Items', [])
        print(f"   📋 Found {len(items)} items to delete")
        
        # Delete items in batches
        for item in items:
            try:
                table.delete_item(
                    Key={
                        'id': item['id'],
                        'timestamp': item['timestamp']
                    }
                )
                deleted_count += 1
                
                if deleted_count % 10 == 0:
                    print(f"   🗑️  Deleted {deleted_count}/{len(items)} items...")
                    
            except Exception as e:
                print(f"   ⚠️  Error deleting item {item.get('timestamp')}: {e}")
        
        print(f"   ✅ Deleted {deleted_count} items from DynamoDB")
        
    except Exception as e:
        print(f"   ❌ Error querying/deleting from DynamoDB: {e}")
    
    return deleted_count

def submit_gps_batch(gps_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Submit a batch of GPS data to the lambda function for processing."""
    try:
        print(f"📤 Submitting batch of {len(gps_data_list)} GPS points to lambda...")
        
        # Prepare payload - lambda expects a list for batch processing
        payload = json.dumps(gps_data_list)
        
        # Check payload size (6MB limit for synchronous invocation)
        payload_size_mb = len(payload.encode('utf-8')) / (1024 * 1024)
        print(f"   📦 Payload size: {payload_size_mb:.2f} MB")
        
        if payload_size_mb > 5.5:  # Leave some buffer
            raise ValueError(f"Payload too large: {payload_size_mb:.2f} MB (max ~5.5 MB)")
        
        # Invoke lambda function directly
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=payload.encode('utf-8')
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        print(f"   ✅ Lambda response status: {response_payload.get('statusCode', 'unknown')}")
        
        if response_payload.get('statusCode') == 200:
            body = json.loads(response_payload.get('body', '{}'))
            print(f"   📊 Result: {body.get('status', 'unknown')}")
            
            # Extract success/failure details if available
            details = body.get('details', [])
            if details:
                success_count = sum(1 for d in details if d.get('statusCode') == 200)
                total_count = len(details)
                print(f"   📈 Processed: {success_count}/{total_count} successfully")
                
                return {
                    'success': True,
                    'total': total_count,
                    'successful': success_count,
                    'failed': total_count - success_count,
                    'details': details
                }
            else:
                # Single batch response
                return {
                    'success': True,
                    'total': len(gps_data_list),
                    'successful': len(gps_data_list),
                    'failed': 0,
                    'message': body.get('status', 'Batch processed')
                }
        else:
            print(f"   ❌ Lambda error: {response_payload}")
            return {
                'success': False,
                'error': response_payload.get('body', 'Unknown error'),
                'total': len(gps_data_list),
                'successful': 0,
                'failed': len(gps_data_list)
            }
            
    except Exception as e:
        print(f"   ❌ Error invoking lambda: {e}")
        return {
            'success': False,
            'error': str(e),
            'total': len(gps_data_list),
            'successful': 0,
            'failed': len(gps_data_list)
        }

def resubmit_jsonl_file(file_path: str) -> Dict[str, int]:
    """Resubmit all data from a JSONL file to the lambda function as a single batch."""
    print(f"\n🚀 Resubmitting data from: {os.path.basename(file_path)}")
    
    gps_data_list = []
    parse_errors = 0
    
    # Read all GPS data from file
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    data = json.loads(line.strip())
                    gps_data_list.append(data)
                except json.JSONDecodeError as e:
                    print(f"   ⚠️  Error parsing line {line_num}: {e}")
                    parse_errors += 1
                    continue
    
    if not gps_data_list:
        print("   ❌ No valid GPS data found in file")
        return {
            'total': 0,
            'success': 0,
            'failed': parse_errors,
            'parse_errors': parse_errors
        }
    
    # Sort by timestamp to ensure chronological order
    gps_data_list.sort(key=lambda x: x.get('timestamp', 0))
    print(f"   📊 Loaded {len(gps_data_list)} GPS points (chronologically sorted)")
    
    # Submit entire batch to lambda
    result = submit_gps_batch(gps_data_list)
    
    # Prepare stats
    stats = {
        'total': len(gps_data_list),
        'success': result.get('successful', 0),
        'failed': result.get('failed', 0) + parse_errors,
        'parse_errors': parse_errors,
        'lambda_success': result.get('success', False)
    }
    
    print(f"   📊 Batch submission complete:")
    print(f"      Total GPS points: {stats['total']}")
    print(f"      Successfully processed: {stats['success']}")
    print(f"      Failed: {stats['failed']}")
    print(f"      Parse errors: {stats['parse_errors']}")
    if stats['total'] > 0:
        print(f"      Success rate: {stats['success']/stats['total']*100:.1f}%")
    
    return stats

def process_batch(batch: List[Dict[str, Any]], stats: Dict[str, int]):
    """Legacy function - no longer used with batch processing."""
    pass

def reprocess_file(file_path: str, dry_run: bool = False) -> bool:
    """Reprocess a single JSONL file."""
    print(f"\n{'='*60}")
    print(f"🔄 Processing: {os.path.basename(file_path)}")
    print(f"{'='*60}")
    
    # Analyze the file
    info = analyze_jsonl_file(file_path)
    if not info:
        return False
    
    if dry_run:
        print("🔍 DRY RUN - No actual changes will be made")
        return True
    
    # Confirm before proceeding
    print(f"\n⚠️  About to:")
    print(f"   1. Delete {info['line_count']} potential records from DynamoDB")
    print(f"   2. Resubmit {info['line_count']} GPS points to lambda")
    
    confirm = input("\n🤔 Proceed? (yes/no): ").lower().strip()
    if confirm != 'yes':
        print("❌ Cancelled by user")
        return False
    
    # Delete old data for each device ID
    total_deleted = 0
    for device_id in info['device_ids']:
        deleted = delete_dynamodb_data(
            device_id,
            info['start_timestamp'],
            info['end_timestamp']
        )
        total_deleted += deleted
    
    # Resubmit data
    resubmit_stats = resubmit_jsonl_file(file_path)
    
    print(f"\n✅ File processing complete!")
    print(f"   🗑️  Deleted: {total_deleted} old records")
    print(f"   📤 Resubmitted: {resubmit_stats['success']}/{resubmit_stats['total']} records")
    
    return True

def main():
    """Main function to reprocess all GPS data files."""
    print("🔄 GPS Data Reprocessing Tool")
    print("Enhanced with temporal-aware outlier detection")
    print("="*60)
    
    # Check if GPS logs directory exists
    if not os.path.exists(GPS_LOGS_DIR):
        print(f"❌ GPS logs directory not found: {GPS_LOGS_DIR}")
        return 1
    
    # Get all JSONL files
    jsonl_files = [
        os.path.join(GPS_LOGS_DIR, f) 
        for f in os.listdir(GPS_LOGS_DIR) 
        if f.endswith('.jsonl') and not f.endswith('_test.jsonl')  # Skip test files
    ]
    
    if not jsonl_files:
        print(f"❌ No JSONL files found in {GPS_LOGS_DIR}")
        return 1
    
    jsonl_files.sort()  # Process in chronological order
    
    print(f"\n📂 Found {len(jsonl_files)} JSONL files to process:")
    for f in jsonl_files:
        print(f"   📄 {os.path.basename(f)}")
    
    # Option for dry run
    mode = input("\n🤔 Run mode? (dry/real): ").lower().strip()
    dry_run = mode == 'dry'
    
    if dry_run:
        print("🔍 Running in DRY RUN mode - no changes will be made")
    else:
        print("⚡ Running in REAL mode - data will be deleted and resubmitted")
    
    # Process each file
    total_stats = {'processed': 0, 'success': 0, 'failed': 0}
    
    for file_path in jsonl_files:
        try:
            success = reprocess_file(file_path, dry_run)
            total_stats['processed'] += 1
            
            if success:
                total_stats['success'] += 1
            else:
                total_stats['failed'] += 1
                
        except KeyboardInterrupt:
            print("\n❌ Process interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error processing {os.path.basename(file_path)}: {e}")
            total_stats['failed'] += 1
            continue
    
    print(f"\n{'='*60}")
    print("🏁 REPROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"📊 Summary:")
    print(f"   Files processed: {total_stats['processed']}")
    print(f"   Successful: {total_stats['success']}")
    print(f"   Failed: {total_stats['failed']}")
    
    if not dry_run and total_stats['success'] > 0:
        print(f"\n🎉 GPS data has been reprocessed with enhanced temporal-aware filtering!")
        print(f"   More valid GPS points should now be stored in DynamoDB")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 