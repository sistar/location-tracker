import { useState, useCallback } from 'react';
import { fetchLocation as fetchLocationService, fetchHistory as fetchHistoryService } from '../services';
import type { Location, SessionInfo } from '../types';

interface LocationData {
  location: Location | null;
  history: Location[];
  isLiveTracking: boolean;
  historyStartTime: number | undefined;
  mapKey: number;
  loading: boolean;
  error: string | null;
}

interface LocationActions {
  fetchLocation: (vehicleId: string) => Promise<void>;
  fetchHistory: (vehicleId: string, startTimestamp?: string | number, timeWindowHours?: number) => Promise<{ points: Location[]; sessionInfo: SessionInfo | null }>;
  setIsLiveTracking: (isLive: boolean) => void;
  setLocation: (location: Location | null) => void;
  setHistory: (history: Location[]) => void;
  clearData: () => void;
  refreshMap: () => void;
  setError: (error: string | null) => void;
}

export function useLocationData(): LocationData & LocationActions {
  const [location, setLocationState] = useState<Location | null>(null);
  const [history, setHistoryState] = useState<Location[]>([]);
  const [isLiveTracking, setIsLiveTracking] = useState(false);
  const [historyStartTime, setHistoryStartTime] = useState<number | undefined>(undefined);
  const [mapKey, setMapKey] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLocation = useCallback(async (vehicleId: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const locationData = await fetchLocationService(vehicleId);
      setLocationState(locationData);
      setMapKey(prev => prev + 1);
    } catch (err) {
      console.error('Error fetching location:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch location');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async (
    vehicleId: string, 
    startTimestamp?: string | number, 
    timeWindowHours: number = 6
  ): Promise<{ points: Location[]; sessionInfo: SessionInfo | null }> => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await fetchHistoryService(vehicleId, startTimestamp, timeWindowHours);
      setHistoryState(result.points);
      
      if (startTimestamp) {
        const timestamp = typeof startTimestamp === 'number' ? startTimestamp : parseInt(startTimestamp);
        setHistoryStartTime(timestamp);
      }
      
      return result;
    } catch (err) {
      console.error('Error fetching history:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
      return { points: [], sessionInfo: null };
    } finally {
      setLoading(false);
    }
  }, []);

  const setLocation = useCallback((newLocation: Location | null) => {
    setLocationState(newLocation);
  }, []);

  const setHistory = useCallback((newHistory: Location[]) => {
    setHistoryState(newHistory);
  }, []);

  const clearData = useCallback(() => {
    setLocationState(null);
    setHistoryState([]);
    setHistoryStartTime(undefined);
    setIsLiveTracking(false);
    setError(null);
  }, []);

  const refreshMap = useCallback(() => {
    setMapKey(prev => prev + 1);
  }, []);

  return {
    location,
    history,
    isLiveTracking,
    historyStartTime,
    mapKey,
    loading,
    error,
    fetchLocation,
    fetchHistory,
    setIsLiveTracking,
    setLocation,
    setHistory,
    clearData,
    refreshMap,
    setError
  };
}