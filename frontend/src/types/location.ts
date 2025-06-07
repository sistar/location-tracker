// Core location and session types
export type Location = {
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

export type SessionInfo = {
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

export type RoutePoint = Location;

export type DriversLogEntry = {
  id: string;
  timestamp: number;  // Creation timestamp (epoch)
  timestamp_str?: string;  // Human-readable format
  startTime: number;  // Start timestamp (epoch)
  endTime: number;    // End timestamp (epoch)
  distance: number;
  duration: number;
  purpose: string;
  notes: string;
  vehicleId?: string;  // Vehicle ID associated with this log entry
  startAddress?: string;
  endAddress?: string;
  route?: RoutePoint[];
};

export type PastSession = {
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