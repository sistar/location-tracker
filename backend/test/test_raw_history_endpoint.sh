#!/bin/bash

# Test script for the raw location history endpoint
# This script makes various API calls to test different aspects of the endpoint

# Base URL - Update this with your actual deployed API URL
API_URL="https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing Raw Location History Endpoint${NC}"
echo "========================================"

# Test 1: Basic request with default parameters
echo -e "\n${BLUE}Test 1: Basic request with default parameters (vehicle_01, 7 days)${NC}"
curl -s "${API_URL}/location/raw-history?vehicle_id=vehicle_01" | jq '.[] | select(.timestamp) | .timestamp_str' | head -n 5
echo -e "\n${GREEN}✓ Basic request completed${NC}"

# Test 2: Specify days parameter
echo -e "\n${BLUE}Test 2: Request with 3 days parameter${NC}"
curl -s "${API_URL}/location/raw-history?vehicle_id=vehicle_01&days=3" | jq '.[] | select(.timestamp) | .timestamp_str' | head -n 5
echo -e "\n${GREEN}✓ Request with days parameter completed${NC}"

# Test 3: Different vehicle ID (if available)
echo -e "\n${BLUE}Test 3: Request with different vehicle ID (vehicle_02)${NC}"
echo "Note: This test will fail if vehicle_02 doesn't exist"
curl -s "${API_URL}/location/raw-history?vehicle_id=vehicle_02" | jq '.[] | select(.timestamp) | .timestamp_str' | head -n 5
echo -e "\n${GREEN}✓ Request for different vehicle completed${NC}"

# Test 4: Compare counts between different day ranges
echo -e "\n${BLUE}Test 4: Comparing counts between different day ranges${NC}"
COUNT_7_DAYS=$(curl -s "${API_URL}/location/raw-history?vehicle_id=vehicle_01" | jq '. | length')
COUNT_3_DAYS=$(curl -s "${API_URL}/location/raw-history?vehicle_id=vehicle_01&days=3" | jq '. | length')

echo "7 days count: $COUNT_7_DAYS"
echo "3 days count: $COUNT_3_DAYS"

# Verify that 7 days has equal or more data points than 3 days
if [ "$COUNT_7_DAYS" -ge "$COUNT_3_DAYS" ]; then
  echo -e "${GREEN}✓ 7 days count is equal to or greater than 3 days count as expected${NC}"
else
  echo -e "${RED}× Data inconsistency: 7 days count ($COUNT_7_DAYS) is less than 3 days count ($COUNT_3_DAYS)${NC}"
fi

# Test 5: Structure check - verify required fields are present
echo -e "\n${BLUE}Test 5: Verifying data structure${NC}"
SAMPLE=$(curl -s "${API_URL}/location/raw-history?vehicle_id=vehicle_01&days=1" | jq '.[0]')

echo "Sample data point:"
echo "$SAMPLE" | jq '.'

# Check required fields
HAS_LAT=$(echo "$SAMPLE" | jq 'has("lat")')
HAS_LON=$(echo "$SAMPLE" | jq 'has("lon")')
HAS_TIMESTAMP=$(echo "$SAMPLE" | jq 'has("timestamp")')
HAS_TIMESTAMP_STR=$(echo "$SAMPLE" | jq 'has("timestamp_str")')

if [ "$HAS_LAT" = "true" ] && [ "$HAS_LON" = "true" ] && [ "$HAS_TIMESTAMP" = "true" ] && [ "$HAS_TIMESTAMP_STR" = "true" ]; then
  echo -e "${GREEN}✓ All required fields are present${NC}"
else
  echo -e "${RED}× Missing required fields:${NC}"
  echo "lat: $HAS_LAT"
  echo "lon: $HAS_LON"
  echo "timestamp: $HAS_TIMESTAMP"
  echo "timestamp_str: $HAS_TIMESTAMP_STR"
fi

echo -e "\n${BLUE}All tests completed${NC}"
echo "========================================"