import { useEffect, useState, useRef, FormEvent } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L, { LatLngBoundsExpression } from "leaflet";

// Fix for default marker icons in react-leaflet
// Safe way to update the icon URLs without TypeScript errors
L.Icon.Default.imagePath = "https://unpkg.com/leaflet@1.7.1/dist/images/";

// Alternative approach if the above doesn't work:
// This uses type assertions to avoid TypeScript errors
// @ts-ignore - Leaflet's type definitions might not include this internals
try {
  // @ts-ignore
  delete L.Icon.Default.prototype._getIconUrl;
  
  // @ts-ignore
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png",
    iconUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
    shadowUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png"
  });
} catch (e) {
  console.error("Error setting up Leaflet icons:", e);
}

// Original API endpoints
const LOCATION_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/location/latest";
const HISTORY_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/location/dynamic-history";
const RAW_HISTORY_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/location/raw-history";
const DRIVERS_LOG_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/drivers-log";
const DRIVERS_LOGS_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/drivers-logs";
const GEOCODE_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/geocode";
const VEHICLES_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/vehicles";
const SCAN_SESSIONS_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/scan-sessions";

const MAX_ADDRESS_DISTANCE = 1000; // Maximum distance (meters) for a valid address

type Location = {
  lat: number;
  lon: number;
  timestamp: number;  // Now a number (epoch timestamp)
  timestamp_str?: string;  // Human-readable format added by backend
  segment_type?: string;
  stop_duration_seconds?: number;
  address?: string;
  // New properties for session debugging
  isWithinSession?: boolean;  // True if point is within detected session boundaries
  isExtendedContext?: boolean;  // True if point is outside session (context data)
};

type SessionInfo = {
  duration: number;
  distance: number;
  startTime?: number;       // Start timestamp (epoch)
  endTime?: number;         // End timestamp (epoch)
  startTime_str?: string;   // Human-readable format
  endTime_str?: string;     // Human-readable format
  sessionId?: string;
  movingTime?: number;      // Moving time in minutes
  stoppedTime?: number;     // Stopped time in minutes
  avgSpeed?: number;        // Average speed in km/h during moving segments
  startAddress?: string;
  endAddress?: string;
  extendedStartTime?: number;
  extendedEndTime?: number;
  totalPointsLoaded?: number;
  sessionPointsCount?: number;
  contextPointsCount?: number;
  hasDataMismatch?: boolean;
  mismatchDetails?: string;
};

type RoutePoint = Location;

type DriversLogEntry = {
  id: string;
  timestamp: number;  // Creation timestamp (epoch)
  timestamp_str?: string;  // Human-readable format
  startTime: number;  // Start timestamp (epoch)
  endTime: number;    // End timestamp (epoch)
  distance: number;
  duration: number;
  purpose: string;
  notes: string;
  startAddress?: string;
  endAddress?: string;
  route?: RoutePoint[];
};

type EditingAddress = {
  id: string;
  type: 'start' | 'end' | 'stop';
  index?: number;
  current: string;
  originalLat: number;
  originalLon: number;
  newLat?: number;
  newLon?: number;
  validationError?: string;
};

type PastSession = {
  id: string;
  vehicleId: string;
  startTime: number;  // Start timestamp (epoch)
  endTime: number;    // End timestamp (epoch)
  duration: number;
  distance: number;
  movingTime: number;
  stoppedTime: number;
  avgSpeed: number;
  numPoints: number;
  numStops: number;
  startLat: number;
  startLon: number;
  endLat: number;
  endLon: number;
};

function haversine(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371000; // Earth radius in meters
  const toRad = (x: number) => (x * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}


export default function App() {
  const [location, setLocation] = useState<Location | null>(null);
  const [history, setHistory] = useState<Location[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [mapKey, setMapKey] = useState<number>(0);
  const mapRef = useRef(null);
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [showLogForm, setShowLogForm] = useState<boolean>(false);
  const [logFormData, setLogFormData] = useState({
    purpose: "",
    notes: ""
  });
  const [logSaved, setLogSaved] = useState<boolean>(false);
  const [logSaveError, setLogSaveError] = useState<string | null>(null);
  const [sessionAlreadySaved, setSessionAlreadySaved] = useState<boolean>(false);
  const [driversLogs, setDriversLogs] = useState<DriversLogEntry[]>([]);
  const [selectedLog, setSelectedLog] = useState<DriversLogEntry | null>(null);
  const [logsLoading, setLogsLoading] = useState<boolean>(false);
  const [vehiclesLoading, setVehiclesLoading] = useState<boolean>(false);
  const [availableVehicles, setAvailableVehicles] = useState<string[]>([]);
  const [selectedVehicle, setSelectedVehicle] = useState<string>('');
  const [pastSessions, setPastSessions] = useState<PastSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<PastSession | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState<boolean>(false);
  const [daysToScan, setDaysToScan] = useState<number>(0); // Default to "All Data"
  const [showSessionsPanel, setShowSessionsPanel] = useState<boolean>(false);
  const [showLogsPanel, setShowLogsPanel] = useState<boolean>(false);
  const [isRawGpsMode, setIsRawGpsMode] = useState<boolean>(false);
  const [rawGpsDays] = useState<number>(7);
  const [editingAddress, setEditingAddress] = useState<EditingAddress | null>(null);
  const [addressCache, setAddressCache] = useState<Map<string, string>>(new Map());
  const [routeLoading, setRouteLoading] = useState<boolean>(false);
  const [historyStartTime, setHistoryStartTime] = useState<number | undefined>(undefined);
  const [isLiveTracking, setIsLiveTracking] = useState<boolean>(true);
  const timeWindow = 6; // Fixed at 6 hours
  
  // New state for enhanced UI
  const [viewMode, setViewMode] = useState<'trips' | 'live' | 'timeline'>('trips');
  const [showTripsOverview, setShowTripsOverview] = useState<boolean>(true);


  const fetchLocation = async () => {
    try {
      setError(null);
      const url = `${LOCATION_API}?vehicle_id=${selectedVehicle}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch location");
      const data = await res.json();
      
      if (!data.lat || !data.lon) {
        throw new Error("Invalid location data received");
      }
      
      setLocation({
        lat: parseFloat(data.lat),
        lon: parseFloat(data.lon),
        timestamp: data.timestamp
      });
      setMapKey(prev => prev + 1);
    } catch (err: any) {
      console.error("Error fetching location:", err);
      setError(err.message || "An unknown error occurred");
    }
  };

  // Function to get address from lat/lon
  const getAddress = async (lat: number, lon: number): Promise<string> => {
    // Check cache first
    const cacheKey = `${lat},${lon}`;
    if (addressCache.has(cacheKey)) {
      console.log(`Address cache hit for ${cacheKey}:`, addressCache.get(cacheKey));
      return addressCache.get(cacheKey) || 'Unknown location';
    }
    
    try {
      // Create a URL with query parameters
      const apiUrl = `${GEOCODE_API}?operation=reverse&lat=${lat}&lon=${lon}`;
      console.log(`Fetching address from:`, apiUrl);
      
      // Add timeout to the request
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      // Use the proxy URL
      const response = await fetch(apiUrl, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      console.log(`Geocoding response status:`, response.status);
      
      if (!response.ok) {
        throw new Error(`Geocoding failed with status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log(`Geocoding response data:`, data);
      
      let address = 'Unknown location';
      
      // Check for error in response
      if (data.error) {
        console.error('Geocoding error:', data.error);
        return 'Address lookup failed';
      }
      
      // Use the formatted address from our backend service
      if (data && data.address) {
        address = data.address;
      }
      
      console.log(`Successfully geocoded ${lat},${lon} to:`, address);
      
      // Save to cache
      const newCache = new Map(addressCache);
      newCache.set(cacheKey, address);
      setAddressCache(newCache);
      
      return address;
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.error('Geocoding request timed out:', error);
        return 'Address lookup timed out';
      }
      console.error('Error fetching address:', error);
      return 'Address lookup failed';
    }
  };
  
  // Geocode address to get coordinates using our backend API
  const geocodeAddress = async (address: string): Promise<{lat: number, lon: number} | null> => {
    try {
      // Create a URL with query parameters
      const apiUrl = `${GEOCODE_API}?operation=search&query=${encodeURIComponent(address)}`;
      
      // Use the proxy URL
      const response = await fetch(apiUrl);
      
      if (!response.ok) {
        throw new Error('Geocoding search failed');
      }
      
      const data = await response.json();
      
      // Check for error in response
      if (data.error) {
        console.error('Geocoding error:', data.error);
        return null;
      }
      
      // Check both lat/lon and lat/lon formats (our backend uses lon, Nominatim uses lon)
      if (data && data.lat && (data.lon || data.lon)) {
        return {
          lat: data.lat,
          lon: data.lon || data.lon
        };
      }
      
      return null;
    } catch (error) {
      console.error('Error geocoding address:', error);
      return null;
    }
  };
  
  // Removed unused function
  
  // Handle address input changes with better timing
  const handleAddressChange = (newAddress: string) => {
    // Just update the current text without validation
    setEditingAddress({...editingAddress!, current: newAddress});
    
    // Debounce preview (only shows marker, doesn't validate)
    const timeoutId = setTimeout(() => {
      previewAddress(newAddress);
    }, 1200);
    
    return () => clearTimeout(timeoutId);
  };
  
  // Validate coordinates against original location
  const validateCoordinates = async (origLat: number, origLon: number, newLat: number, newLon: number): Promise<{valid: boolean, distance: number, error?: string}> => {
    try {
      // Format the query for our backend validation API
      const params = new URLSearchParams({
        operation: 'validate',
        orig_lat: origLat.toString(),
        orig_lon: origLon.toString(),
        new_lat: newLat.toString(),
        new_lon: newLon.toString()
      });
      
      const response = await fetch(`${GEOCODE_API}?${params}`);
      
      if (!response.ok) {
        throw new Error('Validation failed');
      }
      
      const data = await response.json();
      return {
        valid: data.valid === true,
        distance: data.distance || 0,
        error: data.error
      };
    } catch (error) {
      console.error('Error validating coordinates:', error);
      return {
        valid: false,
        distance: 0,
        error: 'Validation service error'
      };
    }
  };
  
  // Only validate on explicit user action (e.g., clicking Save)
  const validateAndUpdate = async (type: 'start' | 'end' | 'stop', newAddress: string, index?: number) => {
    if (!editingAddress) return;
    
    // Skip validation for very short inputs
    if (newAddress.length < 5) {
      setEditingAddress({
        ...editingAddress,
        validationError: 'Address too short. Please enter more details.'
      });
      return;
    }
    
    try {
      // Get coordinates for the address
      const coords = await geocodeAddress(newAddress);
      
      if (!coords) {
        setEditingAddress({
          ...editingAddress, 
          validationError: 'Address not found',
          newLat: undefined,
          newLon: undefined
        });
        return;
      }
      
      // Validate coordinates against original location
      const validation = await validateCoordinates(
        editingAddress.originalLat,
        editingAddress.originalLon,
        coords.lat,
        coords.lon
      );
      
      if (!validation.valid) {
        setEditingAddress({
          ...editingAddress, 
          validationError: validation.error || `Address is too far (${Math.round(validation.distance)}m)`,
          newLat: coords.lat,
          newLon: coords.lon
        });
        return;
      }
      
      // Valid address within range - proceed with update
      updateAddress(type, newAddress, index, coords.lat, coords.lon);
    } catch (error) {
      console.error('Error validating address:', error);
      setEditingAddress({
        ...editingAddress, 
        validationError: 'Error validating address',
        newLat: undefined,
        newLon: undefined
      });
    }
  };

  // Preview address result with new coordinates
  const previewAddress = async (newAddress: string) => {
    if (!editingAddress || newAddress.length < 3) return;
    
    // Only try to preview if address is long enough
    if (newAddress.length > 5) {
      try {
        // Clear any previous validation error
        setEditingAddress({
          ...editingAddress,
          validationError: undefined
        });
        
        // Get coordinates for the address
        const coords = await geocodeAddress(newAddress);
        
        if (coords) {
          // Store preview coordinates without validating yet
          setEditingAddress({
            ...editingAddress,
            newLat: coords.lat,
            newLon: coords.lon
          });
          
          // Optional: Show distance in UI (without error state)
          if (editingAddress.originalLat && editingAddress.originalLon) {
            const distance = haversine(
              editingAddress.originalLat,
              editingAddress.originalLon,
              coords.lat,
              coords.lon
            );
            
            // Just update UI with distance info but don't mark as error
            if (distance > MAX_ADDRESS_DISTANCE) {
              setEditingAddress({
                ...editingAddress,
                newLat: coords.lat,
                newLon: coords.lon,
                validationError: `Preview: ${Math.round(distance)}m from original location`
              });
            }
          }
        }
      } catch (error) {
        // Just log error but don't show to user yet
        console.error('Error previewing address:', error);
      }
    }
  };
  
  // Update address for a specific point
  const updateAddress = (
    type: 'start' | 'end' | 'stop', 
    newAddress: string, 
    index?: number, 
    validatedLat?: number, 
    validatedLon?: number
  ) => {
    // If coordinates are provided, use them directly
    let newLat: number | undefined = validatedLat;
    let newLon: number | undefined = validatedLon;
    
    // Otherwise use what's in editingAddress
    if (!newLat && !newLon && editingAddress) {
      newLat = editingAddress.newLat;
      newLon = editingAddress.newLon;
    }
    
    if (type === 'start' || type === 'end') {
      // Update session info for start/end points
      setSessionInfo(prev => {
        if (!prev) return null;
        
        return {
          ...prev,
          [type === 'start' ? 'startAddress' : 'endAddress']: newAddress
        };
      });
      
      // Also update the first/last point in history with new coordinates
      if (newLat !== undefined && newLon !== undefined) {
        const newHistory = [...history];
        const pointIndex = type === 'start' ? 0 : newHistory.length - 1;
        
        if (pointIndex >= 0 && pointIndex < newHistory.length) {
          newHistory[pointIndex] = { 
            ...newHistory[pointIndex], 
            lat: newLat,
            lon: newLon,
            address: newAddress 
          };
          setHistory(newHistory);
        }
      }
    } else if (type === 'stop' && typeof index === 'number') {
      // Update stop point in history
      const newHistory = [...history];
      const stopPoints = newHistory.filter(p => p.segment_type === 'stopped');
      
      if (index < stopPoints.length) {
        const stopPoint = stopPoints[index];
        const pointIndex = newHistory.findIndex(p => 
          p.lat === stopPoint.lat && 
          p.lon === stopPoint.lon && 
          p.timestamp === stopPoint.timestamp
        );
        
        if (pointIndex !== -1) {
          newHistory[pointIndex] = { 
            ...newHistory[pointIndex], 
            address: newAddress,
            lat: newLat !== undefined ? newLat : newHistory[pointIndex].lat,
            lon: newLon !== undefined ? newLon : newHistory[pointIndex].lon
          };
          setHistory(newHistory);
        }
      }
    }
    
    // Close the editing UI
    setEditingAddress(null);
  };

  // Check if a session has already been saved to a driver's log
  const checkSessionSaved = async (sessionId: string) => {
    try {
      // Use a HEAD request to check if the session exists
      // This is a simplified approach - in a real system, you might have a dedicated API endpoint
      const response = await fetch(`${DRIVERS_LOG_API}?sessionId=${sessionId}&vehicle_id=${selectedVehicle}`, {
        method: 'HEAD',
      });
      
      if (response.status === 409) {
        // Session already exists
        setSessionAlreadySaved(true);
        return true;
      } else {
        setSessionAlreadySaved(false);
        return false;
      }
    } catch (error) {
      console.error('Error checking session status:', error);
      return false;
    }
  };

  // Helper function to format timestamps in ISO format without timezone issues
  const formatISOTimestamp = (timestamp: string | number | Date): string => {
    let date: Date;
    
    if (timestamp instanceof Date) {
      date = timestamp;
    } else if (typeof timestamp === 'number') {
      // Convert epoch seconds to milliseconds for JS Date
      date = new Date(timestamp * 1000);
    } else {
      // If it's a string that looks like a number (epoch), convert it
      if (timestamp && !isNaN(Number(timestamp))) {
        date = new Date(Number(timestamp) * 1000);
      } else {
        // Otherwise treat as ISO string
        date = new Date(timestamp);
      }
    }
    
    // Format as ISO string and remove the milliseconds and 'Z' (UTC indicator)
    return date.toISOString().split('.')[0];
  };

  const fetchHistory = async (startTimestamp?: string | number, timeWindowHours: number = 6) => {
    try {
      // Build URL with appropriate parameters
      let url = `${HISTORY_API}?vehicle_id=${selectedVehicle}`;
      
      // If startTimestamp is provided, add it to URL
      if (startTimestamp) {
        // If it's already a number or numeric string, use it directly
        // Otherwise format it as ISO
        const timestampValue = typeof startTimestamp === 'number' || /^\d+$/.test(String(startTimestamp))
          ? startTimestamp
          : formatISOTimestamp(startTimestamp);
        url += `&start_timestamp=${timestampValue}`;
      }
      
      // Add time window in hours
      url += `&time_window=${timeWindowHours}`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch history");
      const data = await res.json();
      const points = data.map((item: any) => ({
        lat: parseFloat(item.lat),
        lon: parseFloat(item.lon),
        timestamp: item.timestamp,
        segment_type: item.segment_type || 'moving',
        stop_duration_seconds: item.stop_duration_seconds
      }));
      setHistory(points);

      if (points.length > 1) {
        // Convert epoch timestamps to Date objects
        const start = new Date(points[0].timestamp * 1000);
        const end = new Date(points[points.length - 1].timestamp * 1000);
        const duration = (end.getTime() - start.getTime()) / (1000 * 60); // in minutes

        let distance = 0;
        for (let i = 1; i < points.length; i++) {
          distance += haversine(
            points[i - 1].lat,
            points[i - 1].lon,
            points[i].lat,
            points[i].lon
          );
        }
        
        // Create a unique session ID using the start timestamp
        const sessionId = `session_${start.getTime()}`;
        
        // Calculate moving and stopped time
        let movingTime = 0;
        let stoppedTime = 0;
        let movingDistance = 0;
        
        // Find moving segments and calculate moving time and distance
        for (let i = 0; i < points.length; i++) {
          const point = points[i];
          
          if (point.segment_type === 'stopped' && point.stop_duration_seconds) {
            // Add stopped time in minutes
            stoppedTime += point.stop_duration_seconds / 60;
          } else if (i > 0 && points[i-1].segment_type === 'moving' && point.segment_type === 'moving') {
            // Calculate time difference between consecutive moving points
            const prevTime = new Date(points[i-1].timestamp * 1000);
            const currTime = new Date(point.timestamp * 1000);
            const timeDiff = (currTime.getTime() - prevTime.getTime()) / (1000 * 60); // minutes
            
            movingTime += timeDiff;
            
            // Add distance between consecutive moving points
            const segmentDistance = haversine(
              points[i-1].lat, points[i-1].lon,
              point.lat, point.lon
            );
            movingDistance += segmentDistance;
          }
        }
        
        // Calculate average speed (km/h) during moving segments
        // Convert: meters/minute to km/hour
        const avgSpeed = movingTime > 0 ? (movingDistance / 1000) / (movingTime / 60) : 0;
        
        // Get addresses for start and end points
        const startPoint = points[0];
        const endPoint = points[points.length - 1];
        
        // First set the session info without addresses to prevent UI delay
        setSessionInfo({ 
          duration, 
          distance, 
          startTime: startPoint.timestamp,
          endTime: endPoint.timestamp,
          startTime_str: startPoint.timestamp_str || new Date(startPoint.timestamp * 1000).toLocaleString(),
          endTime_str: endPoint.timestamp_str || new Date(endPoint.timestamp * 1000).toLocaleString(),
          sessionId,
          movingTime,
          stoppedTime,
          avgSpeed
        });
        
        // Check if this session has already been saved
        await checkSessionSaved(sessionId);
        
        // Then fetch addresses asynchronously and update
        const fetchAddresses = async () => {
          try {
            console.log('Starting to fetch addresses for session...');
            
            // Get addresses for start and end
            console.log('Fetching start address for:', startPoint.lat, startPoint.lon);
            const startAddress = await getAddress(startPoint.lat, startPoint.lon);
            console.log('Got start address:', startAddress);
            
            console.log('Fetching end address for:', endPoint.lat, endPoint.lon);
            const endAddress = await getAddress(endPoint.lat, endPoint.lon);
            console.log('Got end address:', endAddress);
            
            // Get addresses for stop points (including both stopped and charging points)
            const stopPoints = points.filter((p: Location) => 
              p.segment_type === 'stopped' || p.segment_type === 'charging'
            );
            console.log(`Fetching addresses for ${stopPoints.length} stop points (stopped + charging)...`);
            for (const stopPoint of stopPoints) {
              if (!stopPoint.address) {
                console.log('Fetching stop address for:', stopPoint.lat, stopPoint.lon, 'type:', stopPoint.segment_type);
                stopPoint.address = await getAddress(stopPoint.lat, stopPoint.lon);
                console.log('Got stop address:', stopPoint.address);
              }
            }
            
            // Ensure start and end points also get their addresses set
            if (startPoint && !startPoint.address) {
              startPoint.address = startAddress;
            }
            if (endPoint && !endPoint.address) {
              endPoint.address = endAddress;
            }
            
            // Update the session info with addresses
            setSessionInfo(prev => {
              if (!prev) return null;
              return {
                ...prev,
                startAddress,
                endAddress
              };
            });
            
            // Update history with stop addresses
            setHistory([...points]);
            console.log('Finished fetching all addresses');
          } catch (error) {
            console.error('Error fetching addresses:', error);
            // Set fallback addresses if there's an error
            setSessionInfo(prev => {
              if (!prev) return null;
              return {
                ...prev,
                startAddress: 'Address lookup failed',
                endAddress: 'Address lookup failed'
              };
            });
          }
        };
        
        fetchAddresses();
        
        // Reset log form visibility and saved state when we get new session data
        if (!sessionAlreadySaved) {
          setLogSaved(false);
          setLogSaveError(null);
        }
      }
    } catch (err: any) {
      console.error(err.message);
    }
  };
  
  const handleLogFormSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!sessionInfo) return;
    
    try {
      setLogSaveError(null);
      
      // Prepare the locations array with important edited points
      const locationData = history.map(loc => {
        // Only include necessary fields to minimize data size
        return {
          lat: loc.lat,
          lon: loc.lon,
          timestamp: loc.timestamp,
          segment_type: loc.segment_type,
          stop_duration_seconds: loc.stop_duration_seconds,
          address: loc.address
        };
      });
      
      const response = await fetch(DRIVERS_LOG_API, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: sessionInfo.sessionId,
          startTime: sessionInfo.startTime,
          endTime: sessionInfo.endTime,
          distance: sessionInfo.distance,
          duration: sessionInfo.duration,
          purpose: logFormData.purpose,
          notes: logFormData.notes,
          startAddress: sessionInfo.startAddress,
          endAddress: sessionInfo.endAddress,
          vehicleId: selectedVehicle,
          locations: locationData
        })
      });
      
      // Handle specific error responses
      if (response.status === 409) {
        const errorData = await response.json();
        if (errorData.overlappingId) {
          setLogSaveError(`This time period overlaps with an existing driver's log entry (ID: ${errorData.overlappingId})`);
        } else {
          setLogSaveError(errorData.message || 'This session has already been saved to a driver\'s log');
        }
        return;
      }
      
      if (!response.ok) {
        throw new Error('Failed to save driver\'s log');
      }
      
      setLogSaved(true);
      setShowLogForm(false);
      
      // Refresh logs list if panel is open
      if (showLogsPanel) {
        fetchDriversLogs();
      }
    } catch (err: any) {
      console.error('Error saving log:', err);
      setLogSaveError(err.message || 'Failed to save log');
    }
  };

  // Fetch driver's logs from the backend
  const fetchDriversLogs = async () => {
    // Don't attempt to fetch if no vehicle is selected
    if (!selectedVehicle) {
      console.log('No vehicle selected, skipping drivers logs fetch');
      setDriversLogs([]);
      return;
    }
    
    try {
      setLogsLoading(true);
      console.log('Fetching drivers logs for vehicle:', selectedVehicle);
      
      // Add vehicle_id parameter to filter logs by vehicle
      const url = `${DRIVERS_LOGS_API}?vehicle_id=${selectedVehicle}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        console.error('API error:', response.status, response.statusText);
        throw new Error('Failed to fetch driver\'s logs');
      }
      
      const data = await response.json();
      console.log('Received drivers logs:', data);
      setDriversLogs(data.logs || []);
    } catch (error) {
      console.error('Error fetching logs:', error);
      // Fallback to empty array
      setDriversLogs([]);
    } finally {
      setLogsLoading(false);
    }
  };
  
  // Fetch route for a specific driver's log entry
  const fetchLogRoute = async (logId: string) => {
    try {
      setRouteLoading(true);
      
      // Clear any previously selected log route
      setHistory([]);
      
      // Fetch the route data - include vehicle_id parameter
      const response = await fetch(`${DRIVERS_LOGS_API}?id=${logId}&route=true&vehicle_id=${selectedVehicle}`);
      
      if (!response.ok) {
        console.error('API error:', response.status, response.statusText);
        throw new Error('Failed to fetch route data');
      }
      
      const data = await response.json();
      
      if (data && data.route && Array.isArray(data.route)) {
        // Filter out any points with null coordinates
        const validRoutePoints = data.route.filter((point: Location) => 
          point && typeof point.lat === 'number' && typeof point.lon === 'number'
        );
        
        // Set the selected log with route data
        setSelectedLog({
          ...data,
          route: validRoutePoints
        });
        
        // Also set the route points to history for display on the map
        setHistory(validRoutePoints);
        
        // Reset live tracking when viewing a historical route
        setLocation(null);
        
        // Update the map to center on the route
        if (validRoutePoints.length > 0) {
          // Center map on first point of route
          const firstPoint = validRoutePoints[0];
          if (firstPoint && firstPoint.lat && firstPoint.lon) {
            setMapKey(prev => prev + 1); // Force map to recenter
          }
        } else {
          console.warn('Route contains no valid points with coordinates');
          setError('No valid route points found. The route may be empty.');
        }
      } else {
        throw new Error('No route data available');
      }
    } catch (error) {
      console.error('Error fetching route:', error);
      setError('Failed to load route data. Please try again.');
    } finally {
      setRouteLoading(false);
    }
  };
  
  // Fetch available vehicles
  const fetchVehicles = async () => {
    try {
      setVehiclesLoading(true);
      const response = await fetch(VEHICLES_API);
      
      if (!response.ok) {
        console.error('API error:', response.status, response.statusText);
        throw new Error('Failed to fetch vehicles');
      }
      
      const data = await response.json();
      
      if (data && data.vehicle_ids && Array.isArray(data.vehicle_ids)) {
        setAvailableVehicles(data.vehicle_ids);
        
        // If no vehicle is selected yet, select the first one
        if (!selectedVehicle && data.vehicle_ids.length > 0) {
          setSelectedVehicle(data.vehicle_ids[0]);
        }
      }
    } catch (error) {
      console.error('Error fetching vehicles:', error);
    } finally {
      setVehiclesLoading(false);
    }
  };
  
  // Handle vehicle selection change
  const handleVehicleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newVehicleId = e.target.value;
    setSelectedVehicle(newVehicleId);
    // Reset tracking data
    setLocation(null);
    setHistory([]);
    setSessionInfo(null);
    setSelectedSession(null);
    setPastSessions([]);
    setSelectedLog(null);
    setDriversLogs([]);
    
    // Reset to live tracking mode and turn off raw GPS mode
    setHistoryStartTime(undefined);
    setIsLiveTracking(true);
    setIsRawGpsMode(false);
    
    // Fetch new data for the selected vehicle
    fetchLocation();
    fetchHistory(undefined, timeWindow);
    
    // Force map to redraw with correct center/zoom
    setMapKey(prev => prev + 1);
    
    // If logs panel is open, refresh logs for the new vehicle
    if (showLogsPanel) {
      fetchDriversLogs();
    }
  };
  
  // Fetch past unsaved sessions
  const fetchPastSessions = async () => {
    try {
      setSessionsLoading(true);
      setPastSessions([]);
      setSelectedSession(null);
      
      // Construct URL based on scan range selection
      let url = `${SCAN_SESSIONS_API}?vehicle_id=${selectedVehicle}`;
      if (daysToScan === 0) {
        // For "All Data" option, don't add days parameter or use a special value
        url += '&days=all';
      } else {
        // For specific number of days
        url += `&days=${daysToScan}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        if (response.status === 404) {
          // No sessions found is not an error, just return empty array
          setPastSessions([]);
          return;
        }
        throw new Error('Failed to fetch past sessions');
      }
      
      const data = await response.json();
      
      if (data && data.sessions && Array.isArray(data.sessions)) {
        setPastSessions(data.sessions);
      } else {
        setPastSessions([]);
      }
    } catch (error) {
      console.error('Error fetching past sessions:', error);
      setError('Failed to load past sessions. Please try again.');
    } finally {
      setSessionsLoading(false);
    }
  };
  
  // Load a past session with extended context for debugging
  const loadPastSession = async (session: PastSession) => {
    try {
      setSessionsLoading(true);
      setSelectedSession(session);
      
      console.log('Loading session with exact API format that works manually:');
      console.log('Session:', new Date(session.startTime * 1000).toISOString(), 'to', new Date(session.endTime * 1000).toISOString());
      
      // Use the exact API call format that was confirmed to work manually
      const workingUrl = `${HISTORY_API}?start_timestamp=${new Date(session.startTime * 1000).toISOString()}&vehicle_id=${session.vehicleId}&end_timestamp=${new Date(session.endTime * 1000).toISOString()}`;
      console.log('API call:', workingUrl);
      
      const response = await fetch(workingUrl);
      
      if (!response.ok) {
        throw new Error(`API call failed: ${response.status}`);
      }
      
      const data = await response.json();
      console.log(`API returned ${data.length} points`);
      
      if (data.length === 0) {
        throw new Error('No location data found for this session');
      }
      
      // Check for the expected final point
      const finalPoint = data.find((p: any) => p.timestamp === session.endTime);
      if (finalPoint) {
        console.log('✅ Found expected final point:', finalPoint);
      } else {
        console.warn(`⚠️ Expected final point (${session.endTime}) not found. Last point:`, data[data.length - 1]);
      }
      
      // Map the data
      const allPoints: Location[] = data.map((item: any) => ({
        lat: parseFloat(item.lat),
        lon: parseFloat(item.lon),
        timestamp: item.timestamp,
        segment_type: item.segment_type || 'moving',
        stop_duration_seconds: item.stop_duration_seconds,
        isWithinSession: true, // All points are within session range
        isExtendedContext: false
      }));
      
      console.log(`Loaded ${allPoints.length} points for session`);
      
      // Show the data
      setHistory(allPoints);
      
      // Set session info
      setSessionInfo({
        duration: session.duration,
        distance: session.distance,
        startTime: session.startTime,
        endTime: session.endTime,
        sessionId: session.id,
        movingTime: session.movingTime,
        stoppedTime: session.stoppedTime,
        avgSpeed: session.avgSpeed,
        totalPointsLoaded: allPoints.length,
        sessionPointsCount: allPoints.length,
        contextPointsCount: 0,
        hasDataMismatch: !finalPoint,
        mismatchDetails: finalPoint ? undefined : `Session metadata indicates end at ${new Date(session.endTime * 1000).toLocaleString()}, but last GPS point is ${Math.round((session.endTime - allPoints[allPoints.length - 1].timestamp) / 60)} minutes earlier.`
      });
      
      // Reset live tracking
      setLocation(null);
      
      // Update map to center on the data
      setMapKey(prev => prev + 1);
      
      // Switch to this session view
      setShowSessionsPanel(false);
    } catch (error) {
      console.error('Error loading session:', error);
      setError(`Failed to load session data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setSessionsLoading(false);
    }
  };

  // Return to live tracking view
  const returnToLiveTracking = () => {
    setSelectedLog(null);
    setSelectedSession(null);
    setHistoryStartTime(undefined);
    setIsLiveTracking(true);
    setIsRawGpsMode(false);
    fetchLocation();
    fetchHistory(undefined, timeWindow);
  };
  
  const fetchRawGpsData = async (days: number = 7) => {
    try {
      setError(null);
      
      // Build the URL with parameters
      const url = `${RAW_HISTORY_API}?vehicle_id=${selectedVehicle}&days=${days}`;
      console.log(`Fetching raw GPS data from: ${url}`);
      
      // Show loading state
      setSessionInfo(null);
      setLocation(null);
      
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch raw GPS data");
      
      const data = await res.json();
      console.log(`Received ${data.length} raw GPS points`);
      
      if (!data || data.length === 0) {
        setError("No raw GPS data found for the specified time range");
        console.warn("No raw GPS data found");
        return; // Return early instead of throwing an error
      }
      
      // Map the data to our Location type (add segment_type for filtering)
      const points = data.map((item: any) => ({
        lat: parseFloat(item.lat),
        lon: parseFloat(item.lon),
        timestamp: item.timestamp,
        timestamp_str: item.timestamp_str,
        segment_type: 'raw' // Add a segment type for raw points
      }));
      
      // Update the state with raw points
      setHistory(points);
      console.log(`Processed ${points.length} raw data points`);
      
      // Calculate basic stats for the info panel
      if (points.length > 1) {
        // Convert epoch timestamps to Date objects if needed
        const startPoint = points[points.length - 1]; // Newest first, so last in array is earliest
        const endPoint = points[0]; // First in array is latest
        
        const duration = (new Date(endPoint.timestamp * 1000).getTime() - 
                         new Date(startPoint.timestamp * 1000).getTime()) / (1000 * 60); // in minutes
        
        let distance = 0;
        for (let i = 1; i < points.length; i++) {
          distance += haversine(
            points[i - 1].lat,
            points[i - 1].lon,
            points[i].lat,
            points[i].lon
          );
        }
        
        // Set session info with just basic data
        setSessionInfo({
          duration, 
          distance,
          startTime: startPoint.timestamp,
          endTime: endPoint.timestamp,
          startTime_str: startPoint.timestamp_str || new Date(startPoint.timestamp * 1000).toLocaleString(),
          endTime_str: endPoint.timestamp_str || new Date(endPoint.timestamp * 1000).toLocaleString(),
        });
      }
      
      // Force map to redraw with a slight delay to ensure DOM is ready
      setTimeout(() => {
        setMapKey(prev => prev + 1);
        console.log("Map key updated to force redraw");
      }, 200);
      
    } catch (err: any) {
      console.error("Error fetching raw GPS data:", err);
      setError(err.message || "An unknown error occurred");
    }
  };

  // Calculate bounds for the map based on location history
  const calculateMapBounds = (): LatLngBoundsExpression | undefined => {
    if (history.length === 0) return undefined;
    
    // Get min and max lat/lon to create bounds
    const lats = history.map(loc => loc.lat);
    const lons = history.map(loc => loc.lon);
    
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    
    // Add padding to bounds
    const latPadding = (maxLat - minLat) * 0.1;
    const lonPadding = (maxLon - minLon) * 0.1;
    
    // Return in correct format for LatLngBoundsExpression
    return [
      [minLat - latPadding, minLon - lonPadding] as [number, number],
      [maxLat + latPadding, maxLon + lonPadding] as [number, number]
    ];
  };
  
  // Component to adjust the map view when data or mode changes
  const MapController: React.FC<{
    isLiveTracking: boolean;
    history: Location[];
    location: Location | null;
    selectedSession: PastSession | null;
    selectedLog: DriversLogEntry | null;
    isRawGpsMode?: boolean;  // Add raw GPS mode awareness
  }> = ({ isLiveTracking, history, location, selectedSession, selectedLog, isRawGpsMode = false }) => {
    const map = useMap();
    const initialViewSet = useRef(false);
    
    // Fix map initialization issues - first force a resize
    useEffect(() => {
      // Force map invalidation on mount to fix initialization issues
      setTimeout(() => {
        map.invalidateSize();
      }, 100);
    }, [map]);
    
    useEffect(() => {
      // Use setTimeout to ensure this runs after the map is fully rendered
      setTimeout(() => {
        // Always invalidate size first to prevent "Cannot read properties of undefined" errors
        map.invalidateSize();
        
        // If viewing a session, log, or raw GPS data, don't reset view to live location
        if ((selectedSession || selectedLog) && history.length > 1) {
          // Only set view once when session is loaded
          if (!initialViewSet.current) {
            const bounds = calculateMapBounds();
            if (bounds) {
              map.fitBounds(bounds, { 
                animate: true,
                padding: [50, 50] // Add padding around the bounds
              });
              initialViewSet.current = true;
            }
          }
        } else if (isRawGpsMode && history.length > 1) {
          // In raw GPS mode, fit to bounds of all history points
          if (!initialViewSet.current) {
            const bounds = calculateMapBounds();
            if (bounds) {
              map.fitBounds(bounds, { 
                animate: true,
                padding: [50, 50] // Add padding around the bounds
              });
              initialViewSet.current = true;
              console.log("Raw GPS mode: Set map view to bounds of all points");
            }
          }
        } else if (isLiveTracking && location) {
          // In live tracking mode, center on current location
          map.setView([location.lat, location.lon], 16, { animate: true });
        } else if (!isLiveTracking && history.length > 1) {
          // In historical mode, fit to bounds of all history points
          const bounds = calculateMapBounds();
          if (bounds) {
            map.fitBounds(bounds, { 
              animate: true,
              padding: [50, 50] // Add padding around the bounds
            });
          }
        }
        
        // Invalidate size again after view change
        setTimeout(() => {
          map.invalidateSize();
        }, 200);
      }, 100);
    }, [map, isLiveTracking, isRawGpsMode, history, location, selectedSession, selectedLog]);
    
    // Reset the initialViewSet flag when the session/log/mode changes
    useEffect(() => {
      initialViewSet.current = false;
    }, [selectedSession, selectedLog, isRawGpsMode]);
    
    return null;
  };
  
  useEffect(() => {
    // Fetch available vehicles when component mounts
    fetchVehicles();
    
    // Don't fetch logs immediately - wait for vehicle to be selected first
    // This will be handled by the dependency on selectedVehicle below
    
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // Separate effect that depends on selectedVehicle being set
  useEffect(() => {
    // Only proceed if we have a selected vehicle
    if (!selectedVehicle) return;
    
    // If starting with trips view, load the logs now that we have a vehicle
    if (viewMode === 'trips') {
      console.log('Loading driver logs for vehicle:', selectedVehicle);
      fetchDriversLogs();
    }
    
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedVehicle]); // This will run when selectedVehicle is first set
  
  useEffect(() => {
    // If we're viewing a historical route or session, don't set up polling
    if (selectedLog || selectedSession) return;
    
    // Only set up location tracking if we're in live mode
    if (viewMode === 'live') {
      // Handle different modes
      if (isRawGpsMode) {
        // When in raw GPS mode, fetch the raw data
        fetchRawGpsData(rawGpsDays);
        } else {
        // Normal mode - fetch location and history
        fetchLocation();
        fetchHistory(historyStartTime, timeWindow);
        
        // Only set up interval for polling if in live tracking mode
        let interval: NodeJS.Timeout | null = null;
        if (isLiveTracking) {
          interval = setInterval(fetchLocation, 10000);
        }
        
        // Clean up interval on unmount or when mode changes
        return () => {
          if (interval) clearInterval(interval);
        };
      }
    }
  }, [selectedLog, selectedSession, selectedVehicle, historyStartTime, timeWindow, isLiveTracking, isRawGpsMode, rawGpsDays, viewMode]); // Added viewMode dependency
  
  // Fetch logs when the logs panel is opened, when selected vehicle changes, or when in trips view mode
  useEffect(() => {
    // Only proceed if we have a selected vehicle
    if (!selectedVehicle) return;
    
    if (showLogsPanel || viewMode === 'trips') {
      console.log('Fetching drivers logs due to panel/view change for vehicle:', selectedVehicle);
      fetchDriversLogs();
    }
  }, [showLogsPanel, selectedVehicle, viewMode]); // Added viewMode dependency

  return (
    <div style={{ height: "100%", width: "100%", position: "relative" }}>
      {/* Navigation Bar */}
      <div style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: "60px",
        backgroundColor: "#1a1a1a",
        borderBottom: "2px solid #333",
        zIndex: 1001,
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.3)"
      }}>
        <h1 style={{ 
          margin: 0, 
          color: "white", 
          fontSize: "1.5em", 
          marginRight: "30px",
          fontWeight: "bold"
        }}>
          Location Tracker
        </h1>
        
        {/* Navigation Tabs */}
        <div style={{ display: "flex", gap: "10px", marginRight: "auto" }}>
          <button
            onClick={() => {
              setViewMode('trips');
              setShowTripsOverview(true);
              setShowLogsPanel(false);
              setShowSessionsPanel(false);
            }}
            style={{
              padding: "8px 16px",
              backgroundColor: viewMode === 'trips' ? "#007bff" : "transparent",
              color: "white",
              border: viewMode === 'trips' ? "1px solid #007bff" : "1px solid #555",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "0.9em",
              fontWeight: viewMode === 'trips' ? "bold" : "normal"
            }}
          >
            📋 My Trips
          </button>
          
          <button
            onClick={() => {
              setViewMode('live');
              setShowTripsOverview(false);
              setShowLogsPanel(false);
              setShowSessionsPanel(false);
              setSelectedLog(null);
              setSelectedSession(null);
              setIsLiveTracking(true);
              setIsRawGpsMode(false);
              fetchLocation();
              fetchHistory(undefined, timeWindow);
            }}
            style={{
              padding: "8px 16px",
              backgroundColor: viewMode === 'live' ? "#4CAF50" : "transparent",
              color: "white",
              border: viewMode === 'live' ? "1px solid #4CAF50" : "1px solid #555",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "0.9em",
              fontWeight: viewMode === 'live' ? "bold" : "normal"
            }}
          >
            🔴 Live Tracking
          </button>
          
          <button
            onClick={() => {
              setViewMode('timeline');
              setShowTripsOverview(false);
              setShowLogsPanel(false);
              setShowSessionsPanel(false);
              // TODO: Implement timeline view
            }}
            style={{
              padding: "8px 16px",
              backgroundColor: viewMode === 'timeline' ? "#ff9800" : "transparent",
              color: "white",
              border: viewMode === 'timeline' ? "1px solid #ff9800" : "1px solid #555",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "0.9em",
              fontWeight: viewMode === 'timeline' ? "bold" : "normal",
              opacity: 0.7 // Disabled for now
            }}
            disabled={true}
          >
            📊 Timeline (Coming Soon)
          </button>
        </div>
        
        {/* Vehicle Selector */}
        {!selectedLog && (
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <label htmlFor="vehicle-select" style={{ marginRight: '10px', fontSize: '0.9em', color: 'white' }}>
              Vehicle:
            </label>
            <select 
              id="vehicle-select"
              value={selectedVehicle}
              onChange={handleVehicleChange}
              disabled={vehiclesLoading || routeLoading}
              style={{ 
                padding: '6px 10px',
                backgroundColor: '#333',
                color: 'white',
                border: '1px solid #555',
                borderRadius: '4px',
                minWidth: '120px'
              }}
            >
              {vehiclesLoading ? (
                <option>Loading...</option>
              ) : (
                availableVehicles.map(vehicle => (
                  <option key={vehicle} value={vehicle}>
                    {vehicle}
                  </option>
                ))
              )}
            </select>
            <button
              onClick={fetchVehicles}
              style={{
                marginLeft: '8px',
                padding: '6px 8px',
                backgroundColor: '#444',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.8em'
              }}
              title="Refresh vehicle list"
            >
              ↻
            </button>
          </div>
        )}
      </div>

      {/* Enhanced Trips Overview Panel */}
      {showTripsOverview && viewMode === 'trips' && (
        <div style={{
          position: "absolute",
          top: "60px",
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "#f5f5f5",
          zIndex: 1000,
          overflowY: "auto",
          padding: "20px"
        }}>
          <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
            <div style={{ 
              display: "flex", 
              justifyContent: "space-between", 
              alignItems: "center", 
              marginBottom: "20px",
              backgroundColor: "white",
              padding: "15px 20px",
              borderRadius: "8px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
            }}>
              <h2 style={{ margin: 0, color: "#333" }}>My Trip History</h2>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  onClick={() => {
                    setShowSessionsPanel(true);
                    setShowTripsOverview(false);
                    fetchPastSessions();
                  }}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#4CAF50",
                    color: "white",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "0.9em"
                  }}
                >
                  📅 Find New Sessions
                </button>
                <button
                  onClick={() => {
                    fetchDriversLogs();
                  }}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#007bff",
                    color: "white",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "0.9em"
                  }}
                >
                  🔄 Refresh
                </button>
              </div>
            </div>

            {logsLoading ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '40px',
                backgroundColor: "white",
                borderRadius: "8px",
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
              }}>
                <div style={{ fontSize: "1.2em", color: "#666" }}>Loading your trips...</div>
              </div>
            ) : driversLogs.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '40px',
                backgroundColor: "white",
                borderRadius: "8px",
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
              }}>
                <div style={{ fontSize: "1.2em", color: "#666", marginBottom: "10px" }}>No trips found</div>
                <div style={{ color: "#999" }}>Start by scanning for new sessions or take a drive!</div>
              </div>
            ) : (
              <div style={{ 
                display: "grid", 
                gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))", 
                gap: "20px" 
              }}>
                {driversLogs.map((log) => (
                  <div key={log.id} style={{ 
                    backgroundColor: "white",
                    borderRadius: "8px",
                    padding: "20px",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                    border: selectedLog?.id === log.id ? "2px solid #007bff" : "1px solid #e0e0e0",
                    transition: "all 0.2s ease"
                  }}>
                    {/* Trip Date and Time */}
                    <div style={{ 
                      color: '#007bff', 
                      fontWeight: 'bold',
                      fontSize: '1.1em',
                      marginBottom: '10px',
                      borderBottom: '1px solid #e0e0e0',
                      paddingBottom: '8px'
                    }}>
                      📅 {new Date(log.startTime * 1000).toLocaleDateString('en-US', { 
                        weekday: 'long', 
                        year: 'numeric', 
                        month: 'long', 
                        day: 'numeric' 
                      })}
                    </div>
                    
                    {/* Time Range */}
                    <div style={{ fontSize: '0.9em', color: '#666', marginBottom: '10px' }}>
                      ⏰ {new Date(log.startTime * 1000).toLocaleTimeString()} - {new Date(log.endTime * 1000).toLocaleTimeString()}
                    </div>
                    
                    {/* Purpose Badge */}
                    <div style={{ marginBottom: '15px' }}>
                      <span style={{
                        backgroundColor: log.purpose === 'business' ? '#4CAF50' : 
                                         log.purpose === 'personal' ? '#2196F3' :
                                         log.purpose === 'commute' ? '#FF9800' : '#9E9E9E',
                        color: 'white',
                        padding: '4px 12px',
                        borderRadius: '20px',
                        fontSize: '0.8em',
                        fontWeight: 'bold',
                        textTransform: 'uppercase'
                      }}>
                        {log.purpose || 'Unspecified'}
                      </span>
                    </div>
                    
                    {/* Route Information */}
                    <div style={{ marginBottom: '15px' }}>
                      {log.startAddress && (
                        <div style={{ fontSize: '0.9em', marginBottom: '5px' }}>
                          <strong>📍 From:</strong> {log.startAddress}
                        </div>
                      )}
                      
                      {log.endAddress && (
                        <div style={{ fontSize: '0.9em', marginBottom: '5px' }}>
                          <strong>🏁 To:</strong> {log.endAddress}
                        </div>
                      )}
                    </div>
                    
                    {/* Trip Stats */}
                    <div style={{ 
                      display: 'grid', 
                      gridTemplateColumns: '1fr 1fr', 
                      gap: '10px',
                      marginBottom: '15px',
                      padding: '10px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '6px'
                    }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.2em', fontWeight: 'bold', color: '#333' }}>
                          {(log.distance / 1000).toFixed(1)} km
                        </div>
                        <div style={{ fontSize: '0.8em', color: '#666' }}>Distance</div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.2em', fontWeight: 'bold', color: '#333' }}>
                          {Math.round(log.duration)} min
                        </div>
                        <div style={{ fontSize: '0.8em', color: '#666' }}>Duration</div>
                      </div>
                    </div>
                    
                    {/* Notes */}
                    {log.notes && (
                      <div style={{ marginBottom: '15px' }}>
                        <strong style={{ fontSize: '0.9em', color: '#333' }}>📝 Notes:</strong>
                        <div style={{ 
                          backgroundColor: '#f0f0f0', 
                          padding: '8px', 
                          borderRadius: '4px',
                          marginTop: '5px',
                          fontSize: '0.9em',
                          fontStyle: 'italic'
                        }}>
                          {log.notes}
                        </div>
                      </div>
                    )}
                    
                    {/* Action Button */}
                    <div style={{ textAlign: 'center' }}>
                      {selectedLog?.id === log.id ? (
                        <button
                          onClick={() => {
                            setSelectedLog(null);
                            setHistory([]);
                            setLocation(null);
                          }}
                          style={{ 
                            padding: '10px 20px',
                            backgroundColor: '#dc3545',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.9em',
                            fontWeight: 'bold',
                            width: '100%'
                          }}
                        >
                          📍 Currently Viewing - Click to Close
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            fetchLogRoute(log.id);
                            setViewMode('live'); // Switch to map view
                            setShowTripsOverview(false);
                          }}
                          disabled={routeLoading}
                          style={{ 
                            padding: '10px 20px',
                            backgroundColor: '#4CAF50',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            opacity: routeLoading ? 0.7 : 1,
                            fontSize: '0.9em',
                            fontWeight: 'bold',
                            width: '100%'
                          }}
                        >
                          🗺️ {routeLoading ? 'Loading...' : 'View on Map'}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Map - Only render when not showing trips overview */}
      {!showTripsOverview && (location || (selectedLog && history.length > 0) || (selectedSession && history.length > 0) || (isRawGpsMode && history.length > 0)) ? (
        <MapContainer
          key={mapKey}
          // Type assertion for LatLonExpression
          center={
            (selectedLog || selectedSession) && history.length > 0 ? 
              [history[0].lat, history[0].lon] as [number, number] : 
              isRawGpsMode && history.length > 0 ?
                [history[0].lat, history[0].lon] as [number, number] :
                isLiveTracking && location ? 
                  [location.lat, location.lon] as [number, number] :
                  // Default fallback center
                  [52.520008, 13.404954] as [number, number]
          }
          zoom={(selectedLog || selectedSession) ? 14 : isRawGpsMode ? 10 : isLiveTracking ? 16 : 12}
          style={{ 
            height: "100%", 
            width: "100%",
            marginTop: "60px" // Simple top margin for navigation bar
          }}
          ref={mapRef}
          // Initial bounds, will be updated by MapController
        >
          <TileLayer
            // Type assertion to avoid type errors
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' 
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {/* Map Controller to handle dynamic view updates */}
          <MapController 
            isLiveTracking={isLiveTracking}
            history={history}
            location={location}
            selectedSession={selectedSession}
            selectedLog={selectedLog}
            isRawGpsMode={isRawGpsMode}
          />
          
          {/* Show current location marker only when not viewing a route or past session */}
          {location && !selectedLog && !selectedSession && (
            <Marker position={[location.lat, location.lon] as [number, number]}>
              <Popup>Last seen at {location.timestamp_str || new Date(location.timestamp * 1000).toLocaleString()}</Popup>
            </Marker>
          )}
          
          {history.length > 1 && (
            <>
              {/* Lines for moving segments or raw GPS data */}
              <Polyline
                positions={history
                  .filter(loc => (isRawGpsMode || loc.segment_type === 'raw' || loc.segment_type === 'moving' || loc.segment_type === 'charging') && loc.lat != null && loc.lon != null)
                  .map((loc) => [loc.lat, loc.lon])}
                color={isRawGpsMode ? "red" : "blue"}
                weight={isRawGpsMode ? 3 : 4}
                opacity={isRawGpsMode ? 0.5 : 1}
              />
              
              {/* Marker samples for raw GPS mode (show a marker every N points) */}
              {isRawGpsMode && history.length > 0 && 
                history
                  // Take every 15th point (or adjust based on density)
                  .filter((_, idx) => idx % 15 === 0 || idx === history.length - 1)
                  .map((loc, index) => (
                    <Marker
                      key={`raw-${index}`}
                      position={[loc.lat, loc.lon] as [number, number]}
                      icon={new L.Icon({
                        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [15, 24], // Smaller markers for raw data
                        iconAnchor: [7, 24],
                        popupAnchor: [1, -20],
                        shadowSize: [30, 30]
                      })}
                    >
                      <Popup>
                        <strong>Raw GPS Point</strong><br />
                        Time: {loc.timestamp_str || new Date(loc.timestamp * 1000).toLocaleTimeString()}<br />
                        Lat: {loc.lat.toFixed(6)}<br />
                        Lon: {loc.lon.toFixed(6)}
                      </Popup>
                    </Marker>
                  ))
              }
              
              {/* Preview marker for address editing */}
              {editingAddress?.newLat && editingAddress?.newLon && (
                <Marker
                  position={[editingAddress.newLat, editingAddress.newLon] as [number, number]}
                  icon={new L.Icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-yellow.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                  })}
                >
                  <Popup>
                    <strong>New Location</strong><br />
                    {editingAddress.current}<br />
                    <span style={{ fontSize: '0.8em', color: editingAddress.validationError ? '#ff6666' : '#5cb85c' }}>
                      {editingAddress.validationError || (editingAddress.newLat ? 'Preview location' : 'Searching...')}
                    </span>
                  </Popup>
                </Marker>
              )}
              
              {/* Add markers for start and end points of a route if we're viewing a log or session */}
              {(selectedLog || selectedSession) && history.length > 0 && (
                <>
                  {/* Start marker */}
                  {history[0] && history[0].lat != null && history[0].lon != null && (
                    <Marker 
                      key="route-start"
                      position={[history[0].lat, history[0].lon] as [number, number]}
                      icon={new L.Icon({
                        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowSize: [41, 41]
                      })}
                    >
                      <Popup>
                        <strong>Start</strong><br />
                        {history[0].address || 'Starting point'}<br />
                        {history[0].timestamp_str || new Date(history[0].timestamp * 1000).toLocaleTimeString()}
                      </Popup>
                    </Marker>
                  )}
                  
                  {/* End marker */}
                  {history.length > 0 && history[history.length-1] && history[history.length-1].lat != null && history[history.length-1].lon != null && (
                    <Marker 
                      key="route-end"
                      position={[history[history.length-1].lat, history[history.length-1].lon] as [number, number]}
                      icon={new L.Icon({
                        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowSize: [41, 41]
                      })}
                    >
                      <Popup>
                        <strong>End</strong><br />
                        {history[history.length-1].address || 'End point'}<br />
                        {history[history.length-1].timestamp_str || new Date(history[history.length-1].timestamp * 1000).toLocaleTimeString()}
                        {selectedSession && sessionInfo?.hasDataMismatch && (
                          <div style={{ color: '#ff6666', marginTop: '5px', fontSize: '0.8em' }}>
                            ⚠️ Data may be incomplete
                          </div>
                        )}
                      </Popup>
                    </Marker>
                  )}
                </>
              )}
              
              {/* Markers for stop segments - don't show in raw GPS mode */}
              {!isRawGpsMode && history
                .filter(loc => (loc.segment_type === 'stopped' || loc.segment_type === 'charging') && loc.lat != null && loc.lon != null)
                .map((loc, index) => {
                  // Use different colors for regular stops and charging stops
                  const isChargingStop = loc.segment_type === 'charging';
                  const iconUrl = isChargingStop 
                    ? 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-violet.png'  // Purple for charging
                    : 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-orange.png';  // Orange for regular stops
                  
                  return (
                    <Marker 
                      key={`stop-${index}`}
                      position={[loc.lat, loc.lon] as [number, number]}
                      icon={new L.Icon({
                        iconUrl: iconUrl,
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowSize: [41, 41]
                      })}
                    >
                      <Popup>
                        <strong>{loc.segment_type === 'charging' ? 'Charging Stop' : 'Stop Location'}</strong><br />
                        
                        {editingAddress?.type === 'stop' && editingAddress.id === `stop-${index}` ? (
                          <div style={{ marginBottom: '5px' }}>
                            <input
                              type="text"
                              value={editingAddress.current}
                              onChange={(e) => handleAddressChange(e.target.value)}
                              style={{ 
                                backgroundColor: '#fff',
                                border: editingAddress.validationError ? '1px solid #ff6666' : '1px solid #ccc',
                                padding: '4px 8px',
                                borderRadius: '3px',
                                marginBottom: '5px',
                                width: '100%'
                              }}
                            />
                            {editingAddress.validationError && (
                              <div style={{ 
                                color: '#ff6666', 
                                fontSize: '0.8em', 
                                marginBottom: '5px' 
                              }}>
                                {editingAddress.validationError}
                              </div>
                            )}
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <button
                                onClick={() => setEditingAddress(null)}
                                style={{ 
                                  padding: '2px 6px',
                                  backgroundColor: '#eee',
                                  border: '1px solid #ccc',
                                  borderRadius: '3px',
                                  cursor: 'pointer'
                                }}
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => validateAndUpdate('stop', editingAddress.current, index)}
                                style={{ 
                                  padding: '2px 6px',
                                  backgroundColor: '#4CAF50',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '3px',
                                  cursor: 'pointer',
                                  marginLeft: '5px'
                                }}
                              >
                                Save
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div
                            onClick={async () => {
                              // If no address exists, try to fetch it immediately
                              if (!loc.address) {
                                try {
                                  const fetchedAddress = await getAddress(loc.lat, loc.lon);
                                  // Update the location's address in the history array
                                  const updatedHistory = [...history];
                                  const stopIndex = updatedHistory.findIndex(h => 
                                    h.lat === loc.lat && h.lon === loc.lon && h.timestamp === loc.timestamp
                                  );
                                  if (stopIndex !== -1) {
                                    updatedHistory[stopIndex].address = fetchedAddress;
                                    setHistory(updatedHistory);
                                  }
                                } catch (error) {
                                  console.error('Error fetching address on demand:', error);
                                }
                              }
                              
                              setEditingAddress({
                                id: `stop-${index}`,
                                type: 'stop',
                                index: index,
                                current: loc.address || 'Click to load address...',
                                originalLat: loc.lat,
                                originalLon: loc.lon
                              });
                            }}
                            style={{ 
                              marginBottom: '5px', 
                              cursor: 'pointer',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center' 
                            }}
                          >
                            {loc.address ? (
                              <span>{loc.address}</span>
                            ) : (
                              <span style={{ fontStyle: 'italic', color: '#888' }}>Click to load address...</span>
                            )}
                            <span style={{ fontSize: '0.8em', marginLeft: '5px', color: '#666' }}>✎</span>
                          </div>
                        )}
                        
                        Time: {loc.timestamp_str || new Date(loc.timestamp * 1000).toLocaleTimeString()}<br />
                        Duration: {loc.stop_duration_seconds ? Math.round(loc.stop_duration_seconds / 60) : 0} minutes
                        {loc.segment_type === 'charging' && (
                          <div style={{ 
                            color: '#9575cd', 
                            marginTop: '3px',
                            fontStyle: 'italic'
                          }}>
                            ⚡ EV Charging Break
                          </div>
                        )}
                      </Popup>
                    </Marker>
                  );
                })}
              
            </>
            )}
        </MapContainer>
      ) : (
        // Show loading message only when not in trips overview mode
        !showTripsOverview && (
          <div className="map-loading" style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            backgroundColor: "rgba(0,0,0,0.7)",
            color: "white",
            padding: "20px",
            borderRadius: "8px",
            zIndex: 1000
          }}>
            Loading latest location...
          </div>
        )
      )}

      {/* Error message */}
      {error && (
        <div className="map-error" style={{
          position: "absolute",
          top: "80px", // Below navigation bar
          left: "10px",
          backgroundColor: "rgba(220,53,69,0.9)",
          color: "white",
          padding: "10px 15px",
          borderRadius: "6px",
          zIndex: 1000,
          maxWidth: "400px"
        }}>
          Error: {error}
          <button
            onClick={fetchLocation}
            style={{ marginLeft: "8px", padding: "4px 8px", backgroundColor: "white", color: "#dc3545", border: "none", borderRadius: "4px", cursor: "pointer" }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Status info box - only show in live mode when not showing trips overview */}
      {!showTripsOverview && viewMode === 'live' && (
        <div className="map-status" style={{ 
            position: 'absolute', 
            bottom: '10px', 
            left: '10px', 
            zIndex: 1000, 
            backgroundColor: 'rgba(0,0,0,0.7)', 
            padding: '10px', 
            borderRadius: '5px',
            maxWidth: '300px',
            color: 'white',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
          }}>

        {selectedLog ? (
          <div style={{ 
            marginTop: '5px',
            backgroundColor: 'rgba(0,0,0,0.5)',
            padding: '5px',
            borderRadius: '3px'
          }}>
            <div style={{ fontSize: '0.9em', color: '#90caf9' }}>
              {new Date(selectedLog.startTime * 1000).toLocaleDateString()} {new Date(selectedLog.startTime * 1000).toLocaleTimeString()} - {new Date(selectedLog.endTime * 1000).toLocaleTimeString()}
            </div>
            <div style={{ fontSize: '0.9em' }}>
              <strong>Purpose:</strong> {selectedLog.purpose || 'Not specified'}
            </div>
            {!showLogsPanel && (
              <button
                onClick={returnToLiveTracking}
                style={{ 
                  marginTop: '5px',
                  padding: '3px 8px',
                  backgroundColor: '#4285F4',
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  fontSize: '0.8em'
                }}
              >
                Return to Live Tracking
              </button>
            )}
          </div>
        ) : null}
        
        {/* If we're viewing a past session, show info about it */}
        {selectedSession && (
          <div style={{ 
            marginTop: '5px',
            backgroundColor: 'rgba(0,0,0,0.5)',
            padding: '5px',
            borderRadius: '3px'
          }}>
            <div style={{ fontSize: '0.9em', color: '#4fc3f7' }}>
              {new Date(selectedSession.startTime * 1000).toLocaleDateString()} {new Date(selectedSession.startTime * 1000).toLocaleTimeString()} - {new Date(selectedSession.endTime * 1000).toLocaleTimeString()}
            </div>
            <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
              <strong>Distance:</strong> {(selectedSession.distance / 1000).toFixed(2)} km
            </div>
            <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
              <strong>Stops:</strong> {selectedSession.numStops}
            </div>
            <div style={{ display: 'flex' }}>
              {!showLogForm && (
                <button
                  onClick={() => setShowLogForm(true)}
                  style={{ 
                    marginTop: '5px',
                    marginRight: '5px',
                    padding: '3px 8px',
                    backgroundColor: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    fontSize: '0.8em'
                  }}
                >
                  Save to Driver's Log
                </button>
              )}
              <button
                onClick={returnToLiveTracking}
                style={{ 
                  marginTop: '5px',
                  padding: '3px 8px',
                  backgroundColor: '#4285F4',
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  fontSize: '0.8em'
                }}
              >
                Return to Live Tracking
              </button>
            </div>
          </div>
        )}
          {sessionInfo && !selectedLog && (
              <>
                <div style={{ 
                  backgroundColor: 'rgba(0,0,0,0.8)', 
                  padding: '8px', 
                  borderRadius: '5px', 
                  marginTop: '5px',
                  color: 'white'
                }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '5px', color: '#4CAF50' }}>Session Summary</div>
                  
                  {/* Start and End Location */}
                  <div style={{ marginBottom: '5px' }}>
                    <div style={{ fontWeight: 'bold', fontSize: '0.9em', color: '#90caf9' }}>
                      Start: {sessionInfo.startTime_str || (sessionInfo.startTime ? new Date(sessionInfo.startTime * 1000).toLocaleTimeString() : '')}
                    </div>
                    
                    {editingAddress?.type === 'start' ? (
                      <div style={{ display: 'flex', flexDirection: 'column', margin: '5px 0' }}>
                        <input
                          type="text"
                          value={editingAddress.current}
                          onChange={(e) => handleAddressChange(e.target.value)}
                          style={{ 
                            backgroundColor: '#333',
                            color: 'white',
                            border: editingAddress.validationError ? '1px solid #ff6666' : '1px solid #555',
                            padding: '4px 8px',
                            borderRadius: '3px',
                            marginBottom: '5px'
                          }}
                        />
                        {editingAddress.validationError && (
                          <div style={{ 
                            color: '#ff6666', 
                            fontSize: '0.8em', 
                            marginBottom: '5px' 
                          }}>
                            {editingAddress.validationError}
                          </div>
                        )}
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <button
                            onClick={() => setEditingAddress(null)}
                            style={{ 
                              padding: '2px 6px',
                              backgroundColor: '#555',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer'
                            }}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => validateAndUpdate('start', editingAddress.current)}
                            style={{ 
                              padding: '2px 6px',
                              backgroundColor: '#4CAF50',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer',
                              marginLeft: '5px'
                            }}
                          >
                            Save
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div 
                        style={{ 
                          fontSize: '0.9em', 
                          marginLeft: '10px', 
                          marginBottom: '5px',
                          cursor: 'pointer',
                          padding: '2px 5px',
                          borderRadius: '3px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                        onClick={() => {
                          const startPoint = history[0];
                          setEditingAddress({
                            id: 'start',
                            type: 'start',
                            current: sessionInfo.startAddress || 'Loading address...',
                            originalLat: startPoint.lat,
                            originalLon: startPoint.lon
                          });
                        }}
                      >
                        <span>{sessionInfo.startAddress || 'Loading address...'}</span>
                        <span style={{ fontSize: '0.8em', marginLeft: '5px', color: '#aaa' }}>✎</span>
                      </div>
                    )}
                    
                    <div style={{ fontWeight: 'bold', fontSize: '0.9em', color: '#90caf9' }}>
                      End: {sessionInfo.endTime_str || (sessionInfo.endTime ? new Date(sessionInfo.endTime * 1000).toLocaleTimeString() : '')}
                    </div>
                    
                    {editingAddress?.type === 'end' ? (
                      <div style={{ display: 'flex', flexDirection: 'column', margin: '5px 0' }}>
                        <input
                          type="text"
                          value={editingAddress.current}
                          onChange={(e) => handleAddressChange(e.target.value)}
                          style={{ 
                            backgroundColor: '#333',
                            color: 'white',
                            border: editingAddress.validationError ? '1px solid #ff6666' : '1px solid #555',
                            padding: '4px 8px',
                            borderRadius: '3px',
                            marginBottom: '5px'
                          }}
                        />
                        {editingAddress.validationError && (
                          <div style={{ 
                            color: '#ff6666', 
                            fontSize: '0.8em', 
                            marginBottom: '5px' 
                          }}>
                            {editingAddress.validationError}
                          </div>
                        )}
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <button
                            onClick={() => setEditingAddress(null)}
                            style={{ 
                              padding: '2px 6px',
                              backgroundColor: '#555',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer'
                            }}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => validateAndUpdate('end', editingAddress.current)}
                            style={{ 
                              padding: '2px 6px',
                              backgroundColor: '#4CAF50',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer',
                              marginLeft: '5px'
                            }}
                          >
                            Save
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div 
                        style={{ 
                          fontSize: '0.9em', 
                          marginLeft: '10px',
                          cursor: 'pointer',
                          padding: '2px 5px',
                          borderRadius: '3px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                        onClick={() => {
                          const endPoint = history[history.length - 1];
                          setEditingAddress({
                            id: 'end',
                            type: 'end',
                            current: sessionInfo.endAddress || 'Loading address...',
                            originalLat: endPoint.lat,
                            originalLon: endPoint.lon
                          });
                        }}
                      >
                        <span>{sessionInfo.endAddress || 'Loading address...'}</span>
                        <span style={{ fontSize: '0.8em', marginLeft: '5px', color: '#aaa' }}>✎</span>
                      </div>
                    )}
                  </div>
                  
                  <div style={{ borderTop: '1px solid #444', marginTop: '5px', paddingTop: '5px' }}>
                    <div>Total duration: {sessionInfo.duration.toFixed(1)} min</div>
                    <div>Distance: {(sessionInfo.distance / 1000).toFixed(2)} km</div>
                    {sessionInfo.movingTime !== undefined && (
                      <div>Moving time: {sessionInfo.movingTime.toFixed(1)} min</div>
                    )}
                    {sessionInfo.stoppedTime !== undefined && sessionInfo.stoppedTime > 0 ? (
                      <div>Stopped time: {sessionInfo.stoppedTime.toFixed(1)} min</div>
                    ) : (
                      <div>No stops detected</div>
                    )}
                    {sessionInfo.avgSpeed !== undefined && (
                      <div>Average moving speed: {sessionInfo.avgSpeed.toFixed(1)} km/h</div>
                    )}
                    <div>Stops: {history.filter(loc => loc.segment_type === 'stopped').length}</div>
                    
                    {/* Data mismatch warning */}
                    {sessionInfo.hasDataMismatch && sessionInfo.mismatchDetails && (
                      <div style={{ 
                        marginTop: '8px', 
                        paddingTop: '8px', 
                        borderTop: '1px solid #666',
                        backgroundColor: '#4a1f1f',
                        padding: '8px',
                        borderRadius: '4px',
                        border: '1px solid #ff6b6b'
                      }}>
                        <div style={{ fontWeight: 'bold', color: '#ff6b6b', marginBottom: '5px' }}>
                          ⚠️ Data Inconsistency Detected
                        </div>
                        <div style={{ fontSize: '0.8em', color: '#ffcccc' }}>
                          {sessionInfo.mismatchDetails}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                {!logSaved && !sessionAlreadySaved && !selectedLog && !selectedSession && (
                  <button 
                    onClick={() => setShowLogForm(!showLogForm)}
                    style={{ 
                      marginLeft: "10px", 
                      padding: "2px 8px",
                      backgroundColor: "#4CAF50",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer"
                    }}
                  >
                    {showLogForm ? "Hide log form" : "Save to driver's log"}
                  </button>
                )}
                {logSaved && (
                  <span style={{ marginLeft: "10px", color: "green" }}>✓ Log saved</span>
                )}
                {sessionAlreadySaved && (
                  <span style={{ marginLeft: "10px", color: "orange" }}>⚠️ This session has already been saved</span>
                )}
              </>
            )}
      </div>
      )}
      
      {/* Past Sessions Panel */}
      {showSessionsPanel && (
        <div style={{
          position: "absolute",
          top: "10px",
          right: "10px",
          backgroundColor: "#2b2b2b",
          color: "white",
          padding: "15px",
          borderRadius: "8px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.5)",
          zIndex: 1000,
          maxWidth: "400px",
          maxHeight: "80vh",
          overflowY: "auto"
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ margin: "0" }}>Past Sessions</h3>
            <button
              onClick={() => setShowSessionsPanel(false)}
              style={{ 
                padding: '2px 8px',
                backgroundColor: 'transparent',
                color: 'white',
                border: '1px solid #aaa',
                borderRadius: '3px',
                cursor: 'pointer'
              }}
            >
              ✕
            </button>
          </div>
          
          <div style={{ marginBottom: '15px' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px' }}>
              <label htmlFor="days-select" style={{ marginRight: '10px', fontSize: '0.9em' }}>
                Scan range:
              </label>
              <select 
                id="days-select"
                value={daysToScan}
                onChange={(e) => setDaysToScan(parseInt(e.target.value))}
                disabled={sessionsLoading}
                style={{ 
                  padding: '3px 6px',
                  backgroundColor: '#333',
                  color: 'white',
                  border: '1px solid #555',
                  borderRadius: '3px',
                  width: '100px'  // Increased width to accommodate "All Data"
                }}
              >
                <option value={0}>All Data</option>
                <option value={1}>1 day</option>
                <option value={3}>3 days</option>
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
              </select>
              <button
                onClick={fetchPastSessions}
                disabled={sessionsLoading}
                style={{
                  marginLeft: '10px',
                  padding: '3px 8px',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: sessionsLoading ? 'default' : 'pointer',
                  opacity: sessionsLoading ? 0.7 : 1
                }}
              >
                {sessionsLoading ? 'Scanning...' : 'Scan'}
              </button>
            </div>
            <p style={{ fontSize: '0.8em', color: '#aaa', margin: '5px 0' }}>
              This will find sessions that have not been saved to driver's logs yet. Choose "All Data" to scan the entire database or select a specific time range.
            </p>
          </div>
          
          {sessionsLoading ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>Scanning for sessions...</div>
          ) : pastSessions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>No unsaved sessions found in this time range.</div>
          ) : (
            <div>
              <div style={{ fontSize: '0.9em', marginBottom: '10px' }}>
                Found {pastSessions.length} unsaved sessions:
              </div>
              {pastSessions.map((session) => (
                <div key={session.id} style={{ 
                  marginBottom: '15px',
                  backgroundColor: '#333',
                  padding: '10px',
                  borderRadius: '5px'
                }}>
                  <div style={{ fontSize: '0.9em', color: '#4fc3f7', marginBottom: '5px' }}>
                    {new Date(session.startTime * 1000).toLocaleDateString()} {new Date(session.startTime * 1000).toLocaleTimeString()} - {new Date(session.endTime * 1000).toLocaleTimeString()}
                  </div>
                  
                  <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
                    <strong>Distance:</strong> {(session.distance / 1000).toFixed(2)} km
                  </div>
                  
                  <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
                    <strong>Duration:</strong> {session.duration.toFixed(1)} min
                  </div>
                  
                  <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
                    <strong>Stops:</strong> {session.numStops}
                  </div>
                  
                  <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
                    <strong>Avg Speed:</strong> {session.avgSpeed.toFixed(1)} km/h
                  </div>
                  
                  <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between' }}>
                    <button
                      onClick={() => loadPastSession(session)}
                      disabled={sessionsLoading}
                      style={{ 
                        padding: '5px 10px',
                        backgroundColor: '#4CAF50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8em'
                      }}
                    >
                      Load Session
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Drivers Logs Panel */}
      {showLogsPanel && (
        <div style={{
          position: "absolute",
          top: "10px",
          right: "10px",
          backgroundColor: "#2b2b2b",
          color: "white",
          padding: "15px",
          borderRadius: "8px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.5)",
          zIndex: 1000,
          maxWidth: "400px",
          maxHeight: "80vh",
          overflowY: "auto"
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ margin: "0" }}>Driver's Logs</h3>
            <button
              onClick={() => setShowLogsPanel(false)}
              style={{ 
                padding: '2px 8px',
                backgroundColor: 'transparent',
                color: 'white',
                border: '1px solid #aaa',
                borderRadius: '3px',
                cursor: 'pointer'
              }}
            >
              ✕
            </button>
          </div>
          
          {logsLoading ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>Loading logs...</div>
          ) : driversLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>No logs found.</div>
          ) : (
            <div>
              {driversLogs.map((log, index) => (
                <div key={log.id} style={{ 
                  borderBottom: index < driversLogs.length - 1 ? '1px solid #444' : 'none',
                  marginBottom: '10px',
                  backgroundColor: selectedLog?.id === log.id ? '#1e3a5f' : 'transparent',
                  borderRadius: '5px',
                  padding: '10px'
                }}>
                  <div style={{ fontSize: '0.9em', color: '#90caf9', marginBottom: '5px' }}>
                    {new Date(log.startTime * 1000).toLocaleDateString()} {new Date(log.startTime * 1000).toLocaleTimeString()} - {new Date(log.endTime * 1000).toLocaleTimeString()}
                  </div>
                  
                  <div style={{ fontSize: '0.9em', marginBottom: '5px' }}>
                    <strong>Purpose:</strong> {log.purpose || 'Not specified'}
                  </div>
                  
                  {log.startAddress && (
                    <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
                      <strong>From:</strong> {log.startAddress}
                    </div>
                  )}
                  
                  {log.endAddress && (
                    <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
                      <strong>To:</strong> {log.endAddress}
                    </div>
                  )}
                  
                  <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
                    <strong>Distance:</strong> {(log.distance / 1000).toFixed(2)} km
                  </div>
                  
                  <div style={{ fontSize: '0.9em', marginBottom: '3px' }}>
                    <strong>Duration:</strong> {log.duration.toFixed(1)} min
                  </div>
                  
                  {log.notes && (
                    <div style={{ fontSize: '0.9em', marginTop: '5px' }}>
                      <strong>Notes:</strong><br />
                      <div style={{ 
                        backgroundColor: '#333', 
                        padding: '5px', 
                        borderRadius: '3px',
                        marginTop: '3px'
                      }}>
                        {log.notes}
                      </div>
                    </div>
                  )}
                  
                  {/* Button to view the route */}
                  <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'center' }}>
                    {selectedLog?.id === log.id ? (
                      <button
                        onClick={returnToLiveTracking}
                        style={{ 
                          padding: '5px 10px',
                          backgroundColor: '#4285F4',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.8em'
                        }}
                      >
                        Return to Live Tracking
                      </button>
                    ) : (
                      <button
                        onClick={() => fetchLogRoute(log.id)}
                        disabled={routeLoading}
                        style={{ 
                          padding: '5px 10px',
                          backgroundColor: '#4CAF50',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          opacity: routeLoading ? 0.7 : 1,
                          fontSize: '0.8em'
                        }}
                      >
                        {routeLoading ? 'Loading...' : 'View Route'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
              
              <div style={{ textAlign: 'center', marginTop: '10px' }}>
                <button
                  onClick={fetchDriversLogs}
                  style={{ 
                    padding: '5px 10px',
                    backgroundColor: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Refresh
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Driver's Log Form */}
      {showLogForm && sessionInfo && !selectedLog && (selectedSession || !sessionAlreadySaved) && (
        <div style={{
          position: "absolute",
          bottom: "220px",
          left: "10px",
          backgroundColor: "#2b2b2b",
          color: "white",
          padding: "15px",
          borderRadius: "8px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.5)",
          zIndex: 1000,
          maxWidth: "300px"
        }}>
          <h3 style={{ margin: "0 0 10px 0" }}>Save to Driver's Log</h3>
          
          <form onSubmit={handleLogFormSubmit}>
            <div style={{ marginBottom: "10px" }}>
              <label style={{ display: "block", marginBottom: "5px" }}>
                Purpose:
              </label>
              <select 
                value={logFormData.purpose}
                onChange={(e) => setLogFormData({...logFormData, purpose: e.target.value})}
                style={{ 
                  width: "100%", 
                  padding: "8px", 
                  borderRadius: "4px", 
                  border: "1px solid #444",
                  backgroundColor: "#333",
                  color: "white" 
                }}
                required
              >
                <option value="">Select purpose</option>
                <option value="business">Business</option>
                <option value="commute">Commute</option>
                <option value="personal">Personal</option>
                <option value="delivery">Delivery</option>
                <option value="other">Other</option>
              </select>
            </div>
            
            <div style={{ marginBottom: "15px" }}>
              <label style={{ display: "block", marginBottom: "5px" }}>
                Notes:
              </label>
              <textarea
                value={logFormData.notes}
                onChange={(e) => setLogFormData({...logFormData, notes: e.target.value})}
                style={{ 
                  width: "100%", 
                  padding: "8px", 
                  borderRadius: "4px", 
                  border: "1px solid #444", 
                  height: "60px",
                  backgroundColor: "#333",
                  color: "white" 
                }}
              />
            </div>
            
            {logSaveError && (
              <div style={{ color: "red", marginBottom: "10px" }}>
                Error: {logSaveError}
              </div>
            )}
            
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button
                type="button"
                onClick={() => setShowLogForm(false)}
                style={{ 
                  padding: "8px 12px",
                  backgroundColor: "#f0f0f0",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                  cursor: "pointer"
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                style={{ 
                  padding: "8px 12px",
                  backgroundColor: "#4CAF50",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer"
                }}
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}