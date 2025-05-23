# Raw GPS Mode Feature

This document describes the implementation of the Raw GPS Mode feature for the Location Tracker application.

## Overview

The Raw GPS Mode allows users to view all GPS locations recorded in the last 7 days (or other configurable time period) without any filtering or processing. This provides a way to see the raw data as it was recorded by the GPS device.

## Implementation

### Backend

1. Created a new Lambda function handler:
   - `get_raw_location_history.py` - Retrieves raw location data for the past X days without filtering

2. Added a new API endpoint:
   - `/location/raw-history` - Returns all raw GPS data points within the specified date range

3. Features:
   - Default to showing the last 7 days if not specified
   - Support for customizing the number of days to display
   - Pagination support for handling large datasets
   - Returns the data in newest-first order for better user experience
   - Adds human-readable timestamp strings to each data point

### Frontend

1. Added new state variables to handle Raw GPS Mode:
   - `isRawGpsMode` - Tracks whether the application is in raw GPS mode
   - `rawGpsDays` - Stores the number of days to display in raw mode

2. Added a UI controls:
   - Button to toggle Raw GPS Mode
   - Dropdown to select the number of days (1, 3, 7, 14, 30)
   - Refresh button to reload the data
   - Information panel explaining the raw mode

3. Visualization:
   - Red polyline showing all raw data points
   - Small red markers at regular intervals to show timestamps
   - Display count of total raw data points
   - Popups showing exact coordinates and timestamps

## Testing

### Backend Tests

1. Unit tests in `test_get_raw_location_history.py`:
   - Tests for successful responses
   - Tests for parameter handling (default and custom)
   - Tests for error handling
   - Tests for data structure and formatting

2. Manual endpoint test script:
   - `test_raw_history_endpoint.sh` for testing the deployed API

### Frontend Tests

1. Manual testing script:
   - `test_raw_mode.js` for browser console testing
   - Checks UI elements and interactions
   - Tests mode transitions

## Usage

1. Click the "View Raw GPS Data" button in the application
2. Use the "Days to show" dropdown to adjust the time range
3. Click "Refresh" to reload the data with the current settings
4. Click "Switch to Live Tracking" to return to normal mode

## Future Enhancements

Potential improvements for the Raw GPS Mode:

1. Add filtering options (by time of day, GPS quality, etc.)
2. Add the ability to export raw data as CSV or JSON
3. Implement clustering for better performance with large datasets
4. Add statistical analysis of the raw data points
5. Add visualization of GPS error margins