import boto3
import json
from datetime import datetime
import argparse
import os
import time

dynamodb = boto3.resource('dynamodb')

# Default table names (corrected based on actual AWS resources)
default_source_table = "gps-tracking-service-dev-locations"
default_source_logs_table = default_source_table + "-logs"  # May not exist yet
default_target_table = "gps-tracking-service-dev-locations-v2"  # Actual table name in AWS
default_target_logs_table = "gps-tracking-service-dev-locations-logs-v2"  # Actual table name in AWS

# Source tables (old schema with string timestamps)
source_table_name = os.environ.get("SOURCE_TABLE", default_source_table)
source_logs_table_name = os.environ.get("SOURCE_LOGS_TABLE", default_source_logs_table)

# Target tables (new schema with numeric timestamps)
target_table_name = os.environ.get("TARGET_TABLE", default_target_table)
target_logs_table_name = os.environ.get("TARGET_LOGS_TABLE", default_target_logs_table)

# Initialize table resources with error handling
try:
    source_table = dynamodb.Table(source_table_name)
    print(f"Connected to source table: {source_table_name}")
except Exception as e:
    print(f"Error connecting to source table {source_table_name}: {str(e)}")
    
try:
    source_logs_table = dynamodb.Table(source_logs_table_name)
    print(f"Connected to source logs table: {source_logs_table_name}")
except Exception as e:
    print(f"Error connecting to source logs table {source_logs_table_name}: {str(e)}")
    
try:
    target_table = dynamodb.Table(target_table_name)
    print(f"Connected to target table: {target_table_name}")
except Exception as e:
    print(f"Error connecting to target table {target_table_name}: {str(e)}")
    
try:
    target_logs_table = dynamodb.Table(target_logs_table_name)
    print(f"Connected to target logs table: {target_logs_table_name}")
except Exception as e:
    print(f"Error connecting to target logs table {target_logs_table_name}: {str(e)}")


def iso_to_epoch(timestamp):
    """Convert timestamp to epoch seconds (UTC)"""
    try:
        # If it's already a Decimal, int, or float, convert directly
        if isinstance(timestamp, (int, float)):
            return int(timestamp)
        
        # Special handling for Decimal type
        from decimal import Decimal
        if isinstance(timestamp, Decimal):
            return int(timestamp)
            
        # If it's a string that looks like a number, convert it
        if isinstance(timestamp, str) and timestamp.replace('.', '', 1).isdigit():
            return int(float(timestamp))
            
        # String timestamp handling
        timestamp_str = str(timestamp)
        
        # Handle common formats with error handling
        if "T" in timestamp_str:
            # Try ISO format
            if "+" in timestamp_str or "Z" in timestamp_str:
                # With timezone
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                # Without timezone
                dt = datetime.fromisoformat(timestamp_str)
        elif "." in timestamp_str and " " in timestamp_str:
            # Try European format
            dt = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M:%S")
        else:
            # Try other common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If all formats fail, raise error
                raise ValueError(f"Unknown timestamp format: {timestamp_str}")
        
        # Convert to epoch
        return int(dt.timestamp())
    except Exception as e:
        print(f"Error converting timestamp '{timestamp}': {str(e)}")
        return None


def decimal_default(obj):
    """Helper function to serialize Decimal objects to float for JSON dumping"""
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def migrate_table(source_table, target_table, dry_run=True, backup_file=None, batch_size=25, max_batches=None):
    """Migrate data from source table (string timestamps) to target table (epoch timestamps) efficiently using batches"""
    migrated = []
    last_evaluated_key = None
    processed = 0
    updated = 0
    batch_count = 0

    print(f"Starting migration from {source_table.name} to {target_table.name}...")
    print(f"Using batch size: {batch_size}, {'No limit' if not max_batches else max_batches} batches")

    while True:
        # Check if we've reached the max number of batches
        if max_batches and batch_count >= max_batches:
            print(f"Reached maximum batch count of {max_batches}")
            break
            
        # Scan with a limit to process in manageable chunks
        scan_kwargs = {"Limit": batch_size}
        if last_evaluated_key:
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = source_table.scan(**scan_kwargs)
        items = response.get('Items', [])
        
        if not items:
            print("No more items to process")
            break
            
        batch_count += 1
        print(f"Processing batch {batch_count} with {len(items)} items...")
        
        # For each batch, we'll collect the items to write in a batch
        batch_items = []
        
        for item in items:
            # Check primary timestamp (sort key)
            ts = item.get('timestamp')
            if not ts:
                continue

            # Handle case where timestamp is already a number (int, float, or Decimal)
            from decimal import Decimal
            if isinstance(ts, (int, float, Decimal)):
                # It's already a numeric timestamp, just convert to ensure it's an int
                epoch_ts = int(float(ts))
                print(f"Item {processed}: {item['id']} - Timestamp already numeric: {ts}")
            else:
                # Convert from string to epoch
                epoch_ts = iso_to_epoch(ts)
                if epoch_ts is None:
                    print(f"Skipping item with invalid timestamp: {item['id']} {ts}")
                    continue
                print(f"Item {processed}: {item['id']} - Converting timestamp: {ts} → {epoch_ts}")

            if dry_run:
                processed += 1
                continue

            # Backup if needed
            if backup_file is not None:
                migrated.append(item.copy())

            # Create a new version of the item with epoch timestamp
            new_item = item.copy()
            new_item['timestamp'] = epoch_ts
            
            # Add a human-readable timestamp for backward compatibility
            if not isinstance(ts, (int, float, Decimal)):
                new_item['timestamp_str'] = ts
            
            # Also update any other timestamp fields in the item
            for field in ['startTime', 'endTime', 'processed_at']:
                if field in new_item and isinstance(new_item[field], str):
                    epoch_field = iso_to_epoch(new_item[field])
                    if epoch_field is not None:
                        new_item[field] = epoch_field
                        new_item[field + '_str'] = new_item[field]  # Store original string

            # Add to batch operations
            batch_items.append(new_item)
            processed += 1
            
        # Write the batch to DynamoDB if not in dry run
        if not dry_run and batch_items:
            print(f"Writing batch of {len(batch_items)} items to target table...")
            
            # DynamoDB batches are limited to 25 items, so we process in smaller chunks if needed
            for i in range(0, len(batch_items), 25):
                chunk = batch_items[i:i+25]
                
                # Use batch_writer for more efficient writing
                with target_table.batch_writer() as batch:
                    for item in chunk:
                        batch.put_item(Item=item)
                        updated += 1
                        
                print(f"Wrote chunk of {len(chunk)} items ({i+1}-{i+len(chunk)} of {len(batch_items)})")
        
        # Get last evaluated key for pagination
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            print("No more pages to process")
            break
            
        print(f"Progress: {processed} items processed, {updated} written so far")

    # Write backup if needed
    if backup_file and not dry_run and migrated:
        print(f"Writing backup to {backup_file}...")
        with open(backup_file, "w") as f:
            json.dump(migrated, f, indent=2, default=decimal_default)

    print(f"✅ Migration from {source_table.name} to {target_table.name} finished.")
    print(f"   Total batches: {batch_count}")
    print(f"   Items processed: {processed}")
    print(f"   Items written: {updated}")
    
    return updated, processed


def does_table_exist(table_name):
    """Check if a DynamoDB table exists"""
    client = boto3.client('dynamodb')
    try:
        client.describe_table(TableName=table_name)
        return True
    except Exception as e:
        if 'ResourceNotFoundException' in str(e):
            return False
        else:
            print(f"Error checking table {table_name}: {str(e)}")
            return False


def migrate(dry_run=True, backup_prefix=None, batch_size=25, max_batches=None):
    """Migrate all tables"""
    total_updated = 0
    total_processed = 0
    
    # Check if tables exist before migrating
    sources_exist = does_table_exist(source_table_name)
    source_logs_exist = does_table_exist(source_logs_table_name)
    targets_exist = does_table_exist(target_table_name)
    target_logs_exist = does_table_exist(target_logs_table_name)
    
    print("\nTable existence check:")
    print(f"Source table ({source_table_name}): {'✅ Exists' if sources_exist else '❌ Not Found'}")
    print(f"Source logs table ({source_logs_table_name}): {'✅ Exists' if source_logs_exist else '❌ Not Found'}")
    print(f"Target table ({target_table_name}): {'✅ Exists' if targets_exist else '❌ Not Found'}")
    print(f"Target logs table ({target_logs_table_name}): {'✅ Exists' if target_logs_exist else '❌ Not Found'}")
    print("")
    
    # Migrate locations table if both source and target exist
    if sources_exist and targets_exist:
        locations_backup = f"{backup_prefix}_locations.json" if backup_prefix else None
        print(f"Migrating from {source_table_name} to {target_table_name}...")
        updated, processed = migrate_table(
            source_table, 
            target_table,
            dry_run=dry_run, 
            backup_file=locations_backup,
            batch_size=batch_size,
            max_batches=max_batches
        )
        total_updated += updated
        total_processed += processed
    else:
        print(f"⚠️ Skipping locations table migration due to missing tables")
    
    # Migrate logs table if both source and target exist
    if source_logs_exist and target_logs_exist:
        logs_backup = f"{backup_prefix}_logs.json" if backup_prefix else None
        print(f"Migrating from {source_logs_table_name} to {target_logs_table_name}...")
        updated, processed = migrate_table(
            source_logs_table, 
            target_logs_table,
            dry_run=dry_run, 
            backup_file=logs_backup,
            batch_size=batch_size,
            max_batches=max_batches
        )
        total_updated += updated
        total_processed += processed
    else:
        print(f"⚠️ Skipping logs table migration due to missing tables")
    
    print(f"=== Migration complete ===")
    print(f"Total items updated: {total_updated}")
    print(f"Total items processed: {total_processed}")
    print(f"Batch size: {batch_size}")
    print(f"Max batches: {'No limit' if not max_batches else max_batches}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate timestamps from ISO format to epoch seconds (UTC)")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would change")
    parser.add_argument("--backup-prefix", type=str, help="Prefix for backup files (will add _locations.json and _logs.json)")
    
    # Source table arguments
    parser.add_argument("--source-table", type=str, help=f"Source locations table (default: {default_source_table})")
    parser.add_argument("--source-logs-table", type=str, help=f"Source logs table (default: {default_source_logs_table})")
    
    # Target table arguments
    parser.add_argument("--target-table", type=str, help=f"Target locations table (default: {default_target_table})")
    parser.add_argument("--target-logs-table", type=str, help=f"Target logs table (default: {default_target_logs_table})")
    
    # Performance tuning arguments
    parser.add_argument("--batch-size", type=int, default=25, help="Number of items to process in each scan batch (default: 25)")
    parser.add_argument("--max-batches", type=int, help="Maximum number of batches to process (useful for testing)")
    
    args = parser.parse_args()
    
    # Override source tables if specified
    if args.source_table:
        source_table = dynamodb.Table(args.source_table)
    if args.source_logs_table:
        source_logs_table = dynamodb.Table(args.source_logs_table)
    
    # Override target tables if specified
    if args.target_table:
        target_table = dynamodb.Table(args.target_table)
    if args.target_logs_table:
        target_logs_table = dynamodb.Table(args.target_logs_table)
    
    # Run the migration with all parameters
    migrate(
        dry_run=args.dry_run, 
        backup_prefix=args.backup_prefix,
        batch_size=args.batch_size,
        max_batches=args.max_batches
    )