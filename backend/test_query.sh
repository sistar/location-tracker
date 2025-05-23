#!/bin/sh
source .env.dev
echo $DYNAMODB_LOCATIONS_TABLE

# Convert ISO timestamps to epoch for the query
# These times correspond to: 2025-04-13T17:37:27+02:00 and 2025-04-13T17:37:32+02:00
# Note: The actual epoch values may need adjustment based on your specific timestamps
START_EPOCH=1744983447
END_EPOCH=1744983452

aws dynamodb query \
  --table-name $DYNAMODB_LOCATIONS_TABLE \
  --key-condition-expression "id = :uid AND #ts BETWEEN :start AND :end" \
  --expression-attribute-names '{"#ts": "timestamp"}' \
  --expression-attribute-values '{":uid":{"S":"vehicle_01"}, ":start":{"N":"'$START_EPOCH'"}, ":end":{"N":"'$END_EPOCH'"}}'

