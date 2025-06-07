// API Response Types
export interface LocationApiResponse {
  lat: string;
  lon: string;
  timestamp: number;
}

export interface HistoryApiItem {
  lat: string;
  lon: string;
  timestamp: number;
  timestamp_str?: string;
  segment_type?: string;
  stop_duration_seconds?: number;
  isWithinSession?: boolean;
  isExtendedContext?: boolean;
  address?: string;
}

export interface DriversLogsApiResponse {
  logs: {
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
    route?: Array<{
      lat: number;
      lon: number;
      timestamp: number;
      timestamp_str?: string;
      segment_type?: string;
      stop_duration_seconds?: number;
      address?: string;
      isWithinSession?: boolean;
      isExtendedContext?: boolean;
    }>;
  }[];
}

export interface GeocodeApiResponse {
  address: string;
  error?: string;
}