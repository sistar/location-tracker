# Location Tracker Backend - API Handlers

This document describes the AWS Lambda handlers that power the location tracking backend API. The system is designed to track vehicle locations, process GPS data, and provide various endpoints for location history and driver log management.

## System Overview

The backend uses AWS Lambda functions with DynamoDB for data storage and API Gateway for HTTP endpoints. All handlers support CORS for web frontend integration.

## Database Schema

- **Locations Table**: `gps-tracking-service-{stage}-locations-v2`
  - Partition Key: `id` (vehicle ID)
  - Sort Key: `timestamp` (epoch timestamp)
- **Logs Table**: `gps-tracking-service-{stage}-locations-logs-v2`
  - Stores driver session logs
- **Geocode Cache Table**: `gps-tracking-service-{stage}-geocode-cache`
  - Caches reverse geocoding results

## API Handlers

### 1. Location Data Processing

#### `processor.py`
**Purpose**: Processes incoming GPS location data and stores it in DynamoDB.

**Function**: `process_location`
- Filters out GPS outliers and insignificant movements
- Converts location data to DynamoDB format with Decimal types
- Supports both single location and batch processing
- Maintains location history for outlier detection
- **Minimum Movement**: 10 meters (configurable)
- **Outlier Detection**: Compares against recent location averages

**Key Features**:
- Haversine distance calculation for movement detection
- Quality-based filtering (excellent quality locations prioritized)
- Automatic timestamp handling (ISO to epoch conversion)

---

### 2. Location History Retrieval

#### `get_latest_location.py`
**Endpoint**: `GET /location/latest`
**Purpose**: Retrieves the most recent location for a vehicle.

**Query Parameters**:
- `vehicle_id` (optional): Vehicle identifier (default: "vehicle_01")

**Response**: Latest location point with timestamp conversion for frontend display.

#### `get_location_history.py`
**Endpoint**: `GET /location/history`
**Purpose**: Retrieves the last 50 location points for a vehicle.

**Features**:
- Returns newest locations first
- Limited to 50 points for performance
- Automatic Decimal to float conversion

#### `get_raw_location_history.py`
**Endpoint**: `GET /location/raw-history`
**Purpose**: Retrieves unfiltered location data for a specified time period.

**Query Parameters**:
- `vehicle_id` (optional): Vehicle identifier (default: "vehicle_01")
- `days` (optional): Number of days to look back (default: 7)

**Features**:
- No data filtering or processing
- Supports pagination for large datasets
- Adds human-readable timestamp strings
- Configurable time range (max 7 days default)

#### `get_dynamic_location_history.py`
**Endpoint**: `GET /location/dynamic-history`
**Purpose**: Advanced location history with intelligent filtering and stop detection.

**Query Parameters**:
- `vehicle_id` (optional): Vehicle identifier
- `start_time`: Start timestamp (ISO or epoch)
- `end_time`: End timestamp (ISO or epoch)
- `time_window_hours` (optional): Time window for data retrieval

**Advanced Features**:
- **Phantom Location Cleaning**: Removes GPS noise when vehicle is stopped
- **Stop Detection**: Identifies charging stops vs regular stops
- **Median Position Calculation**: Uses statistical analysis for accurate stop locations
- **Session Extension**: Extends data retrieval around session boundaries
- **Configurable Thresholds**:
  - Stop distance: 140 meters
  - Minimum stop duration: 60 seconds
  - Maximum charging stop: 50 minutes

**Stop Classification**:
- `moving`: Vehicle in motion
- `stopped`: Long-term stop (>50 minutes)
- `charging`: Charging stop (1-50 minutes)

---

### 3. Driver Log Management

#### `save_drivers_log.py`
**Endpoint**: `POST /drivers-log`
**Purpose**: Creates new driver log entries from driving sessions.

**Features**:
- **Overlap Detection**: Prevents duplicate logs for the same time period
- **Session Validation**: Checks if session already exists
- **Multi-HTTP Method Support**: Handles POST, GET, HEAD, OPTIONS
- **Timestamp Conversion**: Supports both ISO and epoch timestamps
- **Vehicle-Specific**: Associates logs with specific vehicle IDs

**Request Body** (POST):
```json
{
  "sessionId": "session_12345_vehicle_01",
  "vehicleId": "vehicle_01",
  "startTime": "2025-01-01T10:00:00",
  "endTime": "2025-01-01T14:00:00",
  "distance": 150000,
  "duration": 240,
  "purpose": "Business trip"
}
```

#### `get_drivers_logs.py`
**Endpoint**: `GET /drivers-logs`
**Purpose**: Retrieves driver log entries with optional route data.

**Query Parameters**:
- `id` (optional): Specific log ID to retrieve
- `vehicle_id` (optional): Filter by vehicle ID (default: "vehicle_01")
- `route` (optional): Include route data if set to "true"

**Features**:
- **Individual Log Retrieval**: Get specific log by ID
- **Vehicle Filtering**: Filter logs by vehicle ID
- **Route Integration**: Optionally include full route coordinates
- **Timestamp Sorting**: Returns newest logs first
- **Location Data Fetching**: Retrieves actual GPS points for route visualization

---

### 4. Session Analysis

#### `scan_unsaved_sessions.py`
**Endpoint**: `GET /scan-sessions`
**Purpose**: Identifies driving sessions that haven't been saved as driver logs.

**Query Parameters**:
- `vehicle_id` (optional): Vehicle identifier (default: "vehicle_01")
- `days` (optional): Days to scan back (default: 7) or "all" to scan entire dataset

**Enhanced Scanning Options**:
- **Efficient Frontend Scanning**: Use `days` parameter to limit scan range for faster responses
- **Complete Dataset Analysis**: Use `days=all` to scan entire location history for comprehensive session detection
- **No Artificial Limits**: Removed previous 30-day maximum restriction
- **Flexible Time Ranges**: Support any number of days for custom analysis periods

**Session Detection Logic**:
- **Session Gap**: 60-minute gap between points creates new session
- **Minimum Duration**: 5 minutes minimum session length
- **Minimum Distance**: 500 meters minimum movement
- **Overlap Check**: Excludes sessions already covered by existing logs

**Session Metrics Calculated**:
- Total distance and duration
- Moving vs stopped time
- Average speed during movement
- Number of stops
- Start/end coordinates

**Configuration**:
- `SESSION_GAP_MINUTES`: 60
- `MIN_SESSION_DURATION_MINUTES`: 5
- `MIN_SESSION_DISTANCE_METERS`: 500
- `MAX_SESSIONS_TO_RETURN`: 10

**Response Format**:
```json
{
  "vehicle_id": "vehicle_01",
  "scan_period": {
    "start": "2025-01-01T00:00:00",
    "end": "2025-01-08T00:00:00",
    "days": 7,
    "scan_all": false,
    "total_data_points": 1542
  },
  "sessions": [...],
  "total_sessions_found": 3
}
```

**Usage Examples**:
- Frontend efficiency: `GET /scan-sessions?days=7` (scan last 7 days)
- Complete analysis: `GET /scan-sessions?days=all` (scan entire dataset)
- Custom range: `GET /scan-sessions?days=30` (scan last 30 days)
- Multi-vehicle: `GET /scan-sessions?vehicle_id=vehicle_02&days=all`

---

### 5. Utility Handlers

#### `get_vehicle_ids.py`
**Endpoint**: `GET /vehicles`
**Purpose**: Returns all unique vehicle IDs in the system.

**Response**:
```json
{
  "vehicle_ids": ["vehicle_01", "vehicle_02", "vehicle_03"]
}
```

#### `geocode_service.py`
**Endpoint**: `GET|POST /geocode`
**Purpose**: Reverse geocoding service with caching.

**Features**:
- **Reverse Geocoding**: Convert coordinates to addresses
- **Forward Geocoding**: Convert addresses to coordinates
- **Rate Limiting**: Respects Nominatim API limits (1.1s between requests)
- **Caching**: 30-day cache for geocoding results
- **Address Validation**: Validates coordinates against original address

**Query Parameters** (GET):
- `lat`: Latitude for reverse geocoding
- `lon`: Longitude for reverse geocoding
- `q`: Address query for forward geocoding

**Request Body** (POST):
```json
{
  "lat": 52.520008,
  "lon": 13.404954
}
```

---

## Common Features Across Handlers

### Error Handling
- Comprehensive try-catch blocks
- Structured error responses
- Detailed logging for debugging

### CORS Support
- Headers for cross-origin requests
- Support for web frontend integration
- OPTIONS method handling

### Data Type Conversion
- Automatic Decimal to float conversion for JSON serialization
- Timestamp format standardization
- Safe type conversion with fallbacks

### Performance Optimizations
- DynamoDB pagination support
- Query optimization with proper key conditions
- Response size limiting

## Environment Variables

- `DYNAMODB_LOCATIONS_TABLE`: Main locations table name
- `DYNAMODB_LOCATIONS_LOGS_TABLE`: Driver logs table name
- `DYNAMODB_GEOCODE_CACHE_TABLE`: Geocoding cache table name
- `ALLOWED_ORIGINS`: CORS allowed origins

## Development Notes

### Timestamp Handling
The system uses epoch timestamps (seconds) as DynamoDB sort keys for efficient querying. Handlers automatically convert between ISO strings and epoch timestamps as needed.

### GPS Data Quality
The system implements sophisticated filtering to handle GPS accuracy issues:
- Outlier detection based on movement patterns
- Phantom location cleaning for stopped vehicles
- Quality-based prioritization

### Rate Limiting
The geocoding service implements rate limiting to respect external API constraints and avoid service disruption.

## Testing

Each handler can be tested individually through API Gateway endpoints or direct Lambda invocation. The system includes comprehensive error handling and logging for troubleshooting. 