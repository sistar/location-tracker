import type { PastSession, HistoryApiItem, Location, SessionInfo } from '../types';
import { API_ENDPOINTS } from './api';

export async function fetchPastSessions(
  vehicleId: string, 
  daysToScan: number
): Promise<PastSession[]> {
  try {
    // Construct URL based on scan range selection
    let url = `${API_ENDPOINTS.SCAN_SESSIONS}?vehicle_id=${vehicleId}`;
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
        return [];
      }
      throw new Error('Failed to fetch past sessions');
    }
    
    const data = await response.json();
    
    if (data && data.sessions && Array.isArray(data.sessions)) {
      return data.sessions;
    } else {
      return [];
    }
  } catch (error) {
    console.error('Error fetching past sessions:', error);
    throw error;
  }
}

export async function loadPastSession(
  session: PastSession
): Promise<{
  points: Location[];
  sessionInfo: SessionInfo;
}> {
  try {
    console.log('Loading session with exact API format that works manually:');
    console.log('Session:', new Date(session.startTime * 1000).toISOString(), 'to', new Date(session.endTime * 1000).toISOString());
    
    // Use the exact API call format that was confirmed to work manually
    const workingUrl = `${API_ENDPOINTS.HISTORY}?start_timestamp=${new Date(session.startTime * 1000).toISOString()}&vehicle_id=${session.vehicleId}&end_timestamp=${new Date(session.endTime * 1000).toISOString()}`;
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
    const finalPoint = data.find((p: HistoryApiItem) => p.timestamp === session.endTime);
    if (finalPoint) {
      console.log('✅ Found expected final point:', finalPoint);
    } else {
      console.warn(`⚠️ Expected final point (${session.endTime}) not found. Last point:`, data[data.length - 1]);
    }
    
    // Map the data
    const allPoints: Location[] = data.map((item: HistoryApiItem) => ({
      lat: parseFloat(item.lat),
      lon: parseFloat(item.lon),
      timestamp: item.timestamp,
      timestamp_str: item.timestamp_str,
      segment_type: item.segment_type || 'moving',
      stop_duration_seconds: item.stop_duration_seconds,
      address: item.address,
      isWithinSession: true, // All points are within session range
      isExtendedContext: false
    }));
    
    console.log(`Loaded ${allPoints.length} points for session`);
    
    // Set session info
    const sessionInfo: SessionInfo = {
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
    };

    return {
      points: allPoints,
      sessionInfo
    };
  } catch (error) {
    console.error('Error loading session:', error);
    throw error instanceof Error ? error : new Error('Unknown error occurred');
  }
}