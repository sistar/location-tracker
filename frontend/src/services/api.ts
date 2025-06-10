// Get API base URL from environment variable with fallback to dev
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com";

// API endpoint constants
export const API_ENDPOINTS = {
  LOCATION: `${API_BASE_URL}/location/latest`,
  HISTORY: `${API_BASE_URL}/location/dynamic-history`,
  RAW_HISTORY: `${API_BASE_URL}/location/raw-history`,
  DRIVERS_LOG: `${API_BASE_URL}/drivers-log`,
  DRIVERS_LOGS: `${API_BASE_URL}/drivers-logs`,
  GEOCODE: `${API_BASE_URL}/geocode`,
  VEHICLES: `${API_BASE_URL}/vehicles`,
  SCAN_SESSIONS: `${API_BASE_URL}/scan-sessions`
};

export const MAX_ADDRESS_DISTANCE = 1000; // Maximum distance (meters) for a valid address