import type { LocationApiResponse, Location, HistoryApiItem, SessionInfo } from '../types';
import { API_ENDPOINTS } from './api';
import { haversine, formatISOTimestamp } from './utilityService';

export async function fetchLocation(vehicleId: string): Promise<Location> {
  try {
    const url = `${API_ENDPOINTS.LOCATION}?vehicle_id=${vehicleId}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch location");
    const data: LocationApiResponse = await res.json();
    
    if (!data.lat || !data.lon) {
      throw new Error("Invalid location data received");
    }
    
    return {
      lat: parseFloat(data.lat),
      lon: parseFloat(data.lon),
      timestamp: data.timestamp
    };
  } catch (err: unknown) {
    console.error("Error fetching location:", err);
    throw err instanceof Error ? err : new Error("An unknown error occurred");
  }
}

export async function fetchVehicles(): Promise<string[]> {
  try {
    const response = await fetch(API_ENDPOINTS.VEHICLES);
    
    if (!response.ok) {
      console.error('API error:', response.status, response.statusText);
      throw new Error('Failed to fetch vehicles');
    }
    
    const data = await response.json();
    
    if (data && data.vehicle_ids && Array.isArray(data.vehicle_ids)) {
      return data.vehicle_ids;
    }
    
    return [];
  } catch (error) {
    console.error('Error fetching vehicles:', error);
    throw error;
  }
}

export async function fetchHistory(
  vehicleId: string, 
  startTimestamp?: string | number, 
  timeWindowHours: number = 6
): Promise<{ points: Location[]; sessionInfo: SessionInfo | null }> {
  try {
    // Build URL with appropriate parameters
    let url = `${API_ENDPOINTS.HISTORY}?vehicle_id=${vehicleId}`;
    
    // If startTimestamp is provided, add it to URL
    if (startTimestamp) {
      // If it's already a number or numeric string, use it directly
      // Otherwise format it as ISO
      const timestampValue = typeof startTimestamp === 'number' || /^\d+$/.test(String(startTimestamp))
        ? startTimestamp
        : formatISOTimestamp(Number(startTimestamp));
      url += `&start_timestamp=${timestampValue}`;
    }
    
    // Add time window in hours
    url += `&time_window=${timeWindowHours}`;
    
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch history");
    const data: HistoryApiItem[] = await res.json();
    const points = data.map((item: HistoryApiItem) => ({
      lat: parseFloat(item.lat),
      lon: parseFloat(item.lon),
      timestamp: item.timestamp,
      timestamp_str: item.timestamp_str,
      segment_type: item.segment_type || 'moving',
      stop_duration_seconds: item.stop_duration_seconds,
      address: item.address
    }));

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
      
      const sessionInfo: SessionInfo = { 
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
      };

      return { points, sessionInfo };
    }

    return { points, sessionInfo: null };
  } catch (err: unknown) {
    console.error(err instanceof Error ? err.message : 'Unknown error');
    throw err instanceof Error ? err : new Error('Unknown error occurred');
  }
}