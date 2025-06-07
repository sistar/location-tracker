# API Documentation

## Overview

The Location Tracker frontend integrates with a serverless backend API deployed on AWS Lambda. All API endpoints use HTTPS and return JSON responses.

## Base URL

```
https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com
```

## Endpoints

### 1. Location Services

#### Get Current Location
```http
GET /location/latest?vehicle_id={vehicleId}
```

**Description**: Retrieves the most recent GPS location for a specific vehicle.

**Parameters**:
- `vehicle_id` (required): Vehicle identifier

**Response**:
```typescript
{
  lat: string;        // Latitude as string
  lon: string;        // Longitude as string  
  timestamp: number;  // Unix timestamp
}
```

#### Get Location History
```http
GET /location/dynamic-history?vehicle_id={vehicleId}&start_timestamp={timestamp}&time_window={hours}
```

**Description**: Retrieves processed location history with session analysis.

**Parameters**:
- `vehicle_id` (required): Vehicle identifier
- `start_timestamp` (optional): Starting timestamp (ISO string or epoch)
- `time_window` (optional): Time window in hours (default: 6)
- `end_timestamp` (optional): Ending timestamp for specific ranges

**Response**:
```typescript
Array<{
  lat: string;
  lon: string;
  timestamp: number;
  timestamp_str?: string;
  segment_type?: 'moving' | 'stopped' | 'charging';
  stop_duration_seconds?: number;
  address?: string;
  isWithinSession?: boolean;
  isExtendedContext?: boolean;
}>
```

#### Get Raw GPS History
```http
GET /location/raw-history?vehicle_id={vehicleId}&days={days}
```

**Description**: Retrieves raw, unprocessed GPS data for analysis.

**Parameters**:
- `vehicle_id` (required): Vehicle identifier
- `days` (required): Number of days to retrieve

**Response**: Array of raw GPS points (structure varies)

### 2. Vehicle Management

#### Get Available Vehicles
```http
GET /vehicles
```

**Description**: Retrieves list of available vehicle IDs.

**Response**:
```typescript
{
  vehicle_ids: string[];
}
```

### 3. Driver's Log Services

#### Save Driver's Log Entry
```http
POST /drivers-log
```

**Description**: Saves a new trip to the driver's log.

**Request Body**:
```typescript
{
  sessionId: string;
  startTime: number;      // Unix timestamp
  endTime: number;        // Unix timestamp
  distance: number;       // Distance in meters
  duration: number;       // Duration in minutes
  purpose: string;        // Trip purpose
  notes: string;          // Optional notes
  startAddress?: string;  // Start location address
  endAddress?: string;    // End location address
  vehicleId: string;      // Vehicle identifier
  locations: Array<{     // GPS points for the trip
    lat: number;
    lon: number;
    timestamp: number;
    segment_type?: string;
    stop_duration_seconds?: number;
    address?: string;
  }>;
}
```

**Response**:
```typescript
{
  id: string;           // Generated log entry ID
  message: string;      // Success message
}
```

**Error Responses**:
- `409 Conflict`: Overlapping time period with existing log
  ```typescript
  {
    message: string;
    overlappingId?: string;
  }
  ```

#### Check Session Exists
```http
HEAD /drivers-log?sessionId={sessionId}&vehicle_id={vehicleId}
```

**Description**: Checks if a session already exists in the driver's log.

**Response**:
- `409 Conflict`: Session already exists
- `404 Not Found`: Session does not exist

#### Get Driver's Logs
```http
GET /drivers-logs?vehicle_id={vehicleId}
```

**Description**: Retrieves saved driver's log entries for a vehicle.

**Parameters**:
- `vehicle_id` (optional): Filter by vehicle ID

**Response**:
```typescript
{
  logs: Array<{
    id: string;
    timestamp: number;
    timestamp_str?: string;
    startTime: number;
    endTime: number;
    distance: number;
    duration: number;
    purpose: string;
    notes: string;
    vehicleId?: string;
    startAddress?: string;
    endAddress?: string;
    route?: Array<LocationPoint>;
  }>;
}
```

#### Get Log Route Data
```http
GET /drivers-logs?id={logId}&route=true&vehicle_id={vehicleId}
```

**Description**: Retrieves detailed route data for a specific log entry.

**Parameters**:
- `id` (required): Log entry ID
- `route=true` (required): Flag to include route data
- `vehicle_id` (required): Vehicle identifier

**Response**: Log entry with detailed route array

### 4. Geocoding Services

#### Reverse Geocoding
```http
GET /geocode?operation=reverse&lat={latitude}&lon={longitude}
```

**Description**: Converts coordinates to human-readable address.

**Parameters**:
- `operation=reverse` (required): Operation type
- `lat` (required): Latitude
- `lon` (required): Longitude

**Response**:
```typescript
{
  address: string;
  error?: string;
}
```

#### Forward Geocoding
```http
GET /geocode?operation=search&query={address}
```

**Description**: Converts address to coordinates.

**Parameters**:
- `operation=search` (required): Operation type
- `query` (required): Address to geocode (URL encoded)

**Response**:
```typescript
{
  lat: number;
  lon: number;
  error?: string;
}
```

#### Coordinate Validation
```http
GET /geocode?operation=validate&orig_lat={lat1}&orig_lon={lon1}&new_lat={lat2}&new_lon={lon2}
```

**Description**: Validates if new coordinates are within acceptable distance of original coordinates.

**Parameters**:
- `operation=validate` (required): Operation type
- `orig_lat` (required): Original latitude
- `orig_lon` (required): Original longitude
- `new_lat` (required): New latitude
- `new_lon` (required): New longitude

**Response**:
```typescript
{
  valid: boolean;
  distance: number;    // Distance in meters
  error?: string;
}
```

### 5. Session Management

#### Scan Past Sessions
```http
GET /scan-sessions?vehicle_id={vehicleId}&days={days}
```

**Description**: Scans for unsaved GPS sessions within specified time range.

**Parameters**:
- `vehicle_id` (required): Vehicle identifier
- `days` (required): Number of days to scan (or 'all' for all data)

**Response**:
```typescript
{
  sessions: Array<{
    id: string;
    vehicleId: string;
    startTime: number;     // Unix timestamp
    endTime: number;       // Unix timestamp
    duration: number;      // Duration in minutes
    distance: number;      // Distance in meters
    movingTime: number;    // Moving time in minutes
    stoppedTime: number;   // Stopped time in minutes
    avgSpeed: number;      // Average speed in km/h
    numPoints: number;     // Number of GPS points
    numStops: number;      // Number of stops
    startLat: number;      // Starting latitude
    startLon: number;      // Starting longitude
    endLat: number;        // Ending latitude
    endLon: number;        // Ending longitude
  }>;
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate session)
- `500 Internal Server Error`: Server error

### Error Response Format

```typescript
{
  error: string;          // Error message
  message?: string;       // Additional error details
  overlappingId?: string; // For conflict errors
}
```

## Rate Limiting

The API implements standard AWS API Gateway rate limiting:
- **Burst Limit**: 2000 requests
- **Rate Limit**: 1000 requests per second
- **Quotas**: May apply per API key if configured

## Authentication

Currently, the API operates without authentication. In production environments, consider implementing:
- API Keys
- JWT tokens
- AWS IAM authentication
- CORS restrictions

## Caching Strategy

### Client-Side Caching
- **Address Geocoding**: Cached in memory to prevent redundant requests
- **Vehicle Data**: Cached until manual refresh
- **Session Data**: Cached per session

### Server-Side Caching
- GPS data may be cached on the server
- Geocoding results may be cached to reduce external API calls

## Usage Examples

### Get Current Location
```javascript
const response = await fetch(
  `${API_ENDPOINTS.LOCATION}?vehicle_id=vehicle_01`
);
const location = await response.json();
```

### Save Trip to Driver's Log
```javascript
const tripData = {
  sessionId: 'session_1234567890',
  startTime: 1703001600,
  endTime: 1703005200,
  distance: 15000,
  duration: 60,
  purpose: 'business',
  notes: 'Client meeting',
  vehicleId: 'vehicle_01',
  locations: [/* GPS points */]
};

const response = await fetch(API_ENDPOINTS.DRIVERS_LOG, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(tripData)
});
```

### Geocode Address
```javascript
const address = encodeURIComponent('123 Main St, City, State');
const response = await fetch(
  `${API_ENDPOINTS.GEOCODE}?operation=search&query=${address}`
);
const coordinates = await response.json();
```

## Service Integration

The frontend services layer abstracts these API calls:

- **`locationService.ts`**: Handles location-related endpoints
- **`geocodingService.ts`**: Manages geocoding operations
- **`driversLogService.ts`**: Manages trip logging
- **`sessionsService.ts`**: Handles session management

This abstraction provides:
- Type safety with TypeScript interfaces
- Consistent error handling
- Request/response transformation
- Caching implementation
- Loading state management