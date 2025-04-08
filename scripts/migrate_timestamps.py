import boto3
import json
from datetime import datetime
import argparse
import os

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get("TABLE_NAME", "LocationTable")
table = dynamodb.Table(table_name)


def normalize_timestamp(ts):
    # Already ISO
    if "T" in ts:
        return ts
    # Try German/European format
    try:
        dt = datetime.strptime(ts, "%d.%m.%Y %H:%M:%S")
        return dt.isoformat()
    except ValueError:
        return ts  # Unknown format, leave as is


def migrate(dry_run=True, backup_file=None):
    migrated = []
    last_evaluated_key = None
    processed = 0
    updated = 0

    while True:
        scan_kwargs = {"Limit": 100}
        if last_evaluated_key:
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            ts = item.get('timestamp')
            if not ts:
                continue

            new_ts = normalize_timestamp(ts)
            if ts == new_ts:
                continue  # already correct

            print(f"Migrating: {item['id']} {ts} → {new_ts}")

            if dry_run:
                continue

            # Backup
            if backup_file is not None:
                migrated.append(item.copy())

            # Delete old item (timestamp is Sort Key!)
            table.delete_item(
                Key={'id': item['id'], 'timestamp': ts}
            )

            # Insert new item
            item['timestamp'] = new_ts
            table.put_item(Item=item)

            updated += 1

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        processed += len(items)

    # Write backup
    if backup_file and not dry_run:
        with open(backup_file, "w") as f:
            json.dump(migrated, f, indent=2)

    print(f"✅ Migration finished. {updated} items updated. {processed} items processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate timestamp format in DynamoDB")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would change")
    parser.add_argument("--backup", type=str, help="Path to backup file (JSON)")
    args = parser.parse_args()

    migrate(dry_run=args.dry_run, backup_file=args.backup)

