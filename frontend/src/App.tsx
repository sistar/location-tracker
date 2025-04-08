import { useEffect, useState, useRef, FormEvent } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

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
const DRIVERS_LOG_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/drivers-log";
const GEOCODE_API = "https://cfqttt9fvi.execute-api.eu-central-1.amazonaws.com/geocode";

const MAX_ADDRESS_DISTANCE = 1000; // Maximum distance (meters) for a valid address

type Location = {
  lat: number;
  lng: number;
  timestamp: string;
  segment_type?: string;
  stop_duration_seconds?: number;
  address?: string;
};

type SessionInfo = {
  duration: number;
  distance: number;
  startTime?: string;
  endTime?: string;
  sessionId?: string;
  movingTime?: number;  // Moving time in minutes
  stoppedTime?: number; // Stopped time in minutes
  avgSpeed?: number;    // Average speed in km/h during moving segments
  startAddress?: string;
  endAddress?: string;
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
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
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
  const [addressCache, setAddressCache] = useState<Map<string, string>>(new Map());
  const [editingAddress, setEditingAddress] = useState<{
    id: string, 
    type: 'start' | 'end' | 'stop', 
    index?: number, 
    current: string,
    originalLat: number,
    originalLng: number,
    newLat?: number,
    newLng?: number,
    validationError?: string
  } | null>(null);


  const fetchLocation = async () => {
    try {
      setError(null);
      const res = await fetch(LOCATION_API);
      if (!res.ok) throw new Error("Failed to fetch location");
      const data = await res.json();
      
      if (!data.latitude || !data.longitude) {
        throw new Error("Invalid location data received");
      }
      
      setLocation({
        lat: parseFloat(data.latitude),
        lng: parseFloat(data.longitude),
        timestamp: data.timestamp
      });
      setLastUpdated(new Date());
      setMapKey(prev => prev + 1);
    } catch (err: any) {
      console.error("Error fetching location:", err);
      setError(err.message || "An unknown error occurred");
    }
  };

  // Function to get address from lat/lng
  const getAddress = async (lat: number, lng: number): Promise<string> => {
    // Check cache first
    const cacheKey = `${lat},${lng}`;
    if (addressCache.has(cacheKey)) {
      return addressCache.get(cacheKey) || 'Unknown location';
    }
    
    try {
      // Create a URL with query parameters
      const apiUrl = `${GEOCODE_API}?operation=reverse&lat=${lat}&lng=${lng}`;
      
      // Use the proxy URL
      const response = await fetch(apiUrl);
      
      if (!response.ok) {
        throw new Error('Geocoding failed');
      }
      
      const data = await response.json();
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
      
      // Save to cache
      const newCache = new Map(addressCache);
      newCache.set(cacheKey, address);
      setAddressCache(newCache);
      
      return address;
    } catch (error) {
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
      
      // Check both lat/lng and lat/lon formats (our backend uses lng, Nominatim uses lon)
      if (data && data.lat && (data.lng || data.lon)) {
        return {
          lat: data.lat,
          lon: data.lon || data.lng
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
  const validateCoordinates = async (origLat: number, origLng: number, newLat: number, newLng: number): Promise<{valid: boolean, distance: number, error?: string}> => {
    try {
      // Format the query for our backend validation API
      const params = new URLSearchParams({
        operation: 'validate',
        orig_lat: origLat.toString(),
        orig_lng: origLng.toString(),
        new_lat: newLat.toString(),
        new_lng: newLng.toString()
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
          newLng: undefined
        });
        return;
      }
      
      // Validate coordinates against original location
      const validation = await validateCoordinates(
        editingAddress.originalLat,
        editingAddress.originalLng,
        coords.lat,
        coords.lon
      );
      
      if (!validation.valid) {
        setEditingAddress({
          ...editingAddress, 
          validationError: validation.error || `Address is too far (${Math.round(validation.distance)}m)`,
          newLat: coords.lat,
          newLng: coords.lon
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
        newLng: undefined
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
            newLng: coords.lon
          });
          
          // Optional: Show distance in UI (without error state)
          if (editingAddress.originalLat && editingAddress.originalLng) {
            const distance = haversine(
              editingAddress.originalLat,
              editingAddress.originalLng,
              coords.lat,
              coords.lon
            );
            
            // Just update UI with distance info but don't mark as error
            if (distance > MAX_ADDRESS_DISTANCE) {
              setEditingAddress({
                ...editingAddress,
                newLat: coords.lat,
                newLng: coords.lon,
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
    validatedLng?: number
  ) => {
    // If coordinates are provided, use them directly
    let newLat: number | undefined = validatedLat;
    let newLng: number | undefined = validatedLng;
    
    // Otherwise use what's in editingAddress
    if (!newLat && !newLng && editingAddress) {
      newLat = editingAddress.newLat;
      newLng = editingAddress.newLng;
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
      if (newLat !== undefined && newLng !== undefined) {
        const newHistory = [...history];
        const pointIndex = type === 'start' ? 0 : newHistory.length - 1;
        
        if (pointIndex >= 0 && pointIndex < newHistory.length) {
          newHistory[pointIndex] = { 
            ...newHistory[pointIndex], 
            lat: newLat,
            lng: newLng,
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
          p.lng === stopPoint.lng && 
          p.timestamp === stopPoint.timestamp
        );
        
        if (pointIndex !== -1) {
          newHistory[pointIndex] = { 
            ...newHistory[pointIndex], 
            address: newAddress,
            lat: newLat !== undefined ? newLat : newHistory[pointIndex].lat,
            lng: newLng !== undefined ? newLng : newHistory[pointIndex].lng
          };
          setHistory(newHistory);
        }
      }
    }
    
    // Close the editing UI
    setEditingAddress(null);
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(HISTORY_API);
      if (!res.ok) throw new Error("Failed to fetch history");
      const data = await res.json();
      const points = data.map((item: any) => ({
        lat: parseFloat(item.latitude),
        lng: parseFloat(item.longitude),
        timestamp: item.timestamp,
        segment_type: item.segment_type || 'moving',
        stop_duration_seconds: item.stop_duration_seconds
      }));
      setHistory(points);

      if (points.length > 1) {
        const start = new Date(points[0].timestamp);
        const end = new Date(points[points.length - 1].timestamp);
        const duration = (end.getTime() - start.getTime()) / (1000 * 60); // in minutes

        let distance = 0;
        for (let i = 1; i < points.length; i++) {
          distance += haversine(
            points[i - 1].lat,
            points[i - 1].lng,
            points[i].lat,
            points[i].lng
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
            const prevTime = new Date(points[i-1].timestamp);
            const currTime = new Date(point.timestamp);
            const timeDiff = (currTime.getTime() - prevTime.getTime()) / (1000 * 60); // minutes
            
            movingTime += timeDiff;
            
            // Add distance between consecutive moving points
            const segmentDistance = haversine(
              points[i-1].lat, points[i-1].lng,
              point.lat, point.lng
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
          sessionId,
          movingTime,
          stoppedTime,
          avgSpeed
        });
        
        // Then fetch addresses asynchronously and update
        const fetchAddresses = async () => {
          try {
            // Get addresses for start and end
            const startAddress = await getAddress(startPoint.lat, startPoint.lng);
            const endAddress = await getAddress(endPoint.lat, endPoint.lng);
            
            // Get addresses for stop points
            const stopPoints = points.filter((p: Location) => p.segment_type === 'stopped');
            for (const stopPoint of stopPoints) {
              if (!stopPoint.address) {
                stopPoint.address = await getAddress(stopPoint.lat, stopPoint.lng);
              }
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
          } catch (error) {
            console.error('Error fetching addresses:', error);
          }
        };
        
        fetchAddresses();
        
        // Reset log form visibility and saved state when we get new session data
        setLogSaved(false);
        setLogSaveError(null);
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
          notes: logFormData.notes
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to save driver\'s log');
      }
      
      setLogSaved(true);
      setShowLogForm(false);
    } catch (err: any) {
      console.error('Error saving log:', err);
      setLogSaveError(err.message || 'Failed to save log');
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchLocation();
    fetchHistory();
    // Set up interval for polling
    const interval = setInterval(fetchLocation, 10000);
    
    // Clean up interval on unmount
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ height: "100%", width: "100%", position: "relative" }}>
      {/* Map - Always rendered to avoid initialization issues */}
      {location ? (
        <MapContainer
          key={mapKey}
          // Type assertion for LatLngExpression
          center={[location.lat, location.lng] as [number, number]}
          zoom={16}
          style={{ height: "100%", width: "100%" }}
          ref={mapRef}
        >
          <TileLayer
            // Type assertion to avoid type errors
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' 
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Marker position={[location.lat, location.lng] as [number, number]}>
            <Popup>Last seen at {location.timestamp}</Popup>
          </Marker>
          {history.length > 1 && (
            <>
              {/* Lines for moving segments */}
              <Polyline
                positions={history
                  .filter(loc => loc.segment_type === 'moving')
                  .map((loc) => [loc.lat, loc.lng])}
                color="blue"
                weight={4}
              />
              
              {/* Preview marker for address editing */}
              {editingAddress?.newLat && editingAddress?.newLng && (
                <Marker
                  position={[editingAddress.newLat, editingAddress.newLng] as [number, number]}
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
              
              {/* Markers for stop segments */}
              {history
                .filter(loc => loc.segment_type === 'stopped')
                .map((loc, index) => (
                  <Marker 
                    key={`stop-${index}`}
                    position={[loc.lat, loc.lng] as [number, number]}
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
                      <strong>Stop Location</strong><br />
                      
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
                          onClick={() => setEditingAddress({
                            id: `stop-${index}`,
                            type: 'stop',
                            index: index,
                            current: loc.address || 'Loading address...',
                            originalLat: loc.lat,
                            originalLng: loc.lng
                          })}
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
                            <span style={{ fontStyle: 'italic' }}>Loading address...</span>
                          )}
                          <span style={{ fontSize: '0.8em', marginLeft: '5px', color: '#666' }}>✎</span>
                        </div>
                      )}
                      
                      Time: {new Date(loc.timestamp).toLocaleTimeString()}<br />
                      Duration: {loc.stop_duration_seconds ? Math.round(loc.stop_duration_seconds / 60) : 0} minutes
                    </Popup>
                  </Marker>
                ))
              }
            </>
            )}
        </MapContainer>
      ) : (
        <div className="map-loading">
          Loading latest location...
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="map-error">
          Error: {error}
          <button
            onClick={fetchLocation}
            style={{ marginLeft: "8px", padding: "4px 8px" }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Last updated info */}
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
        <div>Last updated:{" "}
        {lastUpdated
          ? lastUpdated.toLocaleTimeString()
          : "Fetching..."}
        </div>
          {sessionInfo && (
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
                      Start: {new Date(sessionInfo.startTime || '').toLocaleTimeString()}
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
                            originalLng: startPoint.lng
                          });
                        }}
                      >
                        <span>{sessionInfo.startAddress || 'Loading address...'}</span>
                        <span style={{ fontSize: '0.8em', marginLeft: '5px', color: '#aaa' }}>✎</span>
                      </div>
                    )}
                    
                    <div style={{ fontWeight: 'bold', fontSize: '0.9em', color: '#90caf9' }}>
                      End: {new Date(sessionInfo.endTime || '').toLocaleTimeString()}
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
                            originalLng: endPoint.lng
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
                  </div>
                </div>
                {!logSaved && (
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
              </>
            )}
      </div>
      
      {/* Driver's Log Form */}
      {showLogForm && sessionInfo && (
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