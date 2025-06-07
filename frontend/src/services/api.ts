// API endpoint constants
export const API_ENDPOINTS = {
  LOCATION: "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/location/latest",
  HISTORY: "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/location/dynamic-history",
  RAW_HISTORY: "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/location/raw-history",
  DRIVERS_LOG: "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/drivers-log",
  DRIVERS_LOGS: "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/drivers-logs",
  GEOCODE: "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/geocode",
  VEHICLES: "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/vehicles",
  SCAN_SESSIONS: "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/scan-sessions"
};

export const MAX_ADDRESS_DISTANCE = 1000; // Maximum distance (meters) for a valid address