# Data Migration Scripts

This directory contains scripts for data migration tasks.

## Timestamp Format Migration

The DynamoDB schema now uses numeric epoch timestamps (UTC seconds) instead of ISO format strings for the `timestamp` attribute. This change improves performance and simplifies time-based queries.

### Migration Strategy

Since AWS CloudFormation doesn't support changing DynamoDB attribute types directly, we use a two-phase migration:

1. Create new tables with the proper schema (timestamp as Number)
2. Migrate data from the old tables to the new tables
3. Switch the application to use the new tables

### Migration Steps

1. **Step 1: Deploy New Tables with Updated Schema**

   First, deploy the new V2 tables with proper schema:

   ```bash
   cd ../backend
   serverless deploy --stage dev
   ```

2. **Step 2: Normalize ISO Formats (Optional)**

   If you have multiple timestamp formats in your database, first normalize them:

   ```bash
   # Dry run (no changes)
   python migrate_timestamps.py --dry-run

   # Actual migration with backup
   python migrate_timestamps.py --backup backup.json
   ```

3. **Step 3: Migrate Data to New Tables**

   This script migrates data from old tables to new V2 tables with epoch timestamps:

   ```bash
   # Dry run (just show what would migrate)
   python migrate_to_epoch.py --dry-run

   # Migrate with backup
   python migrate_to_epoch.py --backup-prefix epoch_migration
   
   # Specify custom source/target tables if needed
   python migrate_to_epoch.py \
     --source-table gps-tracking-service-dev-locations \
     --target-table gps-tracking-service-dev-locations-v2-v2 \
     --target-logs-table gps-tracking-service-dev-locations-v2-logs-v2
   
   # Run with performance tuning options
   python migrate_to_epoch.py \
     --batch-size 50 \          # Number of items to retrieve per scan (default: 25)
     --max-batches 5 \          # Limit to 5 batches (useful for testing)
     --backup-prefix epoch_test # Add a backup prefix
   ```

4. **Step 4: Verify Migration**

   After migration, verify that the new tables contain all the expected data:

   ```bash
   # Use AWS CLI to check item counts
   aws dynamodb scan --table-name gps-tracking-service-dev-locations-v2-v2 --select COUNT
   aws dynamodb scan --table-name gps-tracking-service-dev-locations-v2-logs-v2 --select COUNT
   aws dynamodb scan --table-name gps-tracking-service-dev-locations --select COUNT
   ```

### Important Notes

- The new schema stores timestamps as numbers (epoch seconds)
- The backend code adds a human-readable `timestamp_str` field for display
- The frontend has been updated to handle numeric timestamps
- All timestamp calculations use the epoch format for better performance

### Table Naming Convention

Due to a CloudFormation deployment issue, some tables were created with a double "v2" suffix:
- Original tables: `gps-tracking-service-dev-locations` and `gps-tracking-service-dev-locations-logs`
- Current v2 tables: `gps-tracking-service-dev-locations-v2-v2` and `gps-tracking-service-dev-locations-v2-logs-v2`

This has been addressed in the serverless.yml configuration, but the migration script needs to use the actual table names as they exist in AWS.

## Other Scripts

- `migrate_timestamps.py` - Normalizes various timestamp string formats to ISO
- `migrate_to_epoch.py` - Converts ISO timestamp strings to epoch numbers