import type { DriversLogsApiResponse, DriversLogEntry, Location, SessionInfo } from '../types';
import { API_ENDPOINTS } from './api';

export async function checkSessionSaved(sessionId: string, vehicleId: string): Promise<boolean> {
  try {
    // Use a HEAD request to check if the session exists
    // This is a simplified approach - in a real system, you might have a dedicated API endpoint
    const response = await fetch(`${API_ENDPOINTS.DRIVERS_LOG}?sessionId=${sessionId}&vehicle_id=${vehicleId}`, {
      method: 'HEAD',
    });
    
    if (response.status === 409) {
      // Session already exists
      return true;
    } else {
      return false;
    }
  } catch (error) {
    console.error('Error checking session status:', error);
    return false;
  }
}

export async function saveDriverLog(
  sessionInfo: SessionInfo,
  logFormData: { purpose: string; notes: string },
  history: Location[],
  vehicleId: string
): Promise<{ success: boolean; error?: string; overlappingId?: string }> {
  try {
    console.log('🚀 Starting to save driver log...');
    console.log('Session info:', sessionInfo);
    console.log('Form data:', logFormData);
    
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
    
    const savePayload = {
      sessionId: sessionInfo.sessionId,
      startTime: sessionInfo.startTime,
      endTime: sessionInfo.endTime,
      distance: sessionInfo.distance,
      duration: sessionInfo.duration,
      purpose: logFormData.purpose,
      notes: logFormData.notes,
      startAddress: sessionInfo.startAddress,
      endAddress: sessionInfo.endAddress,
      vehicleId: vehicleId,
      locations: locationData
    };
    
    console.log('📤 Sending save payload:', savePayload);
    console.log('🚗 Vehicle ID being saved:', vehicleId);
    console.log('📍 API endpoint:', API_ENDPOINTS.DRIVERS_LOG);
    
    const response = await fetch(API_ENDPOINTS.DRIVERS_LOG, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(savePayload)
    });
    
    console.log('📥 Response status:', response.status);
    console.log('📥 Response ok:', response.ok);
    
    // Handle specific error responses
    if (response.status === 409) {
      const errorData = await response.json();
      console.error('❌ Conflict error:', errorData);
      return {
        success: false,
        error: errorData.message || 'This session has already been saved to a driver\'s log',
        overlappingId: errorData.overlappingId
      };
    }
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Save failed:', response.status, errorText);
      return {
        success: false,
        error: `Failed to save driver's log: ${response.status} ${errorText}`
      };
    }
    
    const responseData = await response.json();
    console.log('✅ Save successful! Response:', responseData);
    
    return { success: true };
    
  } catch (err: unknown) {
    console.error('❌ Error saving log:', err);
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Failed to save log'
    };
  }
}

export async function fetchDriversLogs(vehicleId: string): Promise<DriversLogEntry[]> {
  try {
    console.log('🔍 Fetching drivers logs for vehicle:', vehicleId);
    
    // Add vehicle_id parameter to filter logs by vehicle
    const url = `${API_ENDPOINTS.DRIVERS_LOGS}?vehicle_id=${vehicleId}`;
    console.log('📍 Drivers logs API URL:', url);
    
    const response = await fetch(url);
    
    console.log('📥 Drivers logs response status:', response.status);
    console.log('📥 Drivers logs response ok:', response.ok);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Drivers logs API error:', response.status, response.statusText, errorText);
      throw new Error(`Failed to fetch driver's logs: ${response.status} ${errorText}`);
    }
    
    const data: DriversLogsApiResponse = await response.json();
    console.log('✅ Received drivers logs response:', data);
    console.log('📊 Logs array length:', data.logs ? data.logs.length : 'undefined');
    
    if (data.logs && Array.isArray(data.logs)) {
      // Enhanced debugging: log each trip's vehicle ID
      console.log('🚗 Vehicle ID analysis:');
      data.logs.forEach((log: DriversLogEntry, index: number) => {
        console.log(`  Log ${index}: id=${log.id}, vehicleId="${log.vehicleId}", purpose="${log.purpose}"`);
      });
      
      // Client-side filtering as backup - filter out logs that don't match the selected vehicle
      const filteredLogs = data.logs.filter((log: DriversLogEntry) => {
        const logVehicleId = log.vehicleId;
        const matches = logVehicleId === vehicleId;
        
        if (!matches) {
          console.warn(`⚠️ Filtering out log ${log.id}: vehicleId="${logVehicleId}" doesn't match selected="${vehicleId}"`);
        }
        
        return matches;
      });
      
      console.log(`📊 After client-side filtering: ${filteredLogs.length}/${data.logs.length} logs match vehicle "${vehicleId}"`);
      console.log('✅ Set drivers logs state with', filteredLogs.length, 'entries');
      
      return filteredLogs;
    } else {
      console.warn('⚠️ Invalid logs data structure:', data);
      return [];
    }
  } catch (error) {
    console.error('❌ Error fetching drivers logs:', error);
    // Fallback to empty array
    return [];
  }
}

export async function fetchLogRoute(logId: string, vehicleId: string): Promise<{ 
  success: boolean; 
  data?: DriversLogEntry; 
  route?: Location[]; 
  error?: string 
}> {
  try {
    // Fetch the route data - include vehicle_id parameter
    const response = await fetch(`${API_ENDPOINTS.DRIVERS_LOGS}?id=${logId}&route=true&vehicle_id=${vehicleId}`);
    
    if (!response.ok) {
      console.error('API error:', response.status, response.statusText);
      return {
        success: false,
        error: 'Failed to fetch route data'
      };
    }
    
    const data = await response.json();
    
    if (data && data.route && Array.isArray(data.route)) {
      // Filter out any points with null coordinates
      const validRoutePoints = data.route.filter((point: Location) => 
        point && typeof point.lat === 'number' && typeof point.lon === 'number'
      );
      
      if (validRoutePoints.length === 0) {
        return {
          success: false,
          error: 'No valid route points found. The route may be empty.'
        };
      }
      
      return {
        success: true,
        data,
        route: validRoutePoints
      };
    } else {
      return {
        success: false,
        error: 'No route data available'
      };
    }
  } catch (error) {
    console.error('Error fetching route:', error);
    return {
      success: false,
      error: 'Failed to load route data. Please try again.'
    };
  }
}