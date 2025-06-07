import { useState, useCallback } from 'react';
import { 
  fetchDriversLogs as fetchDriversLogsService, 
  fetchLogRoute as fetchLogRouteService,
  saveDriverLog,
  checkSessionSaved as checkSessionSavedService
} from '../services';
import type { DriversLogEntry, SessionInfo, Location } from '../types';

interface DriversLogsState {
  driversLogs: DriversLogEntry[];
  selectedLog: DriversLogEntry | null;
  logFormData: { purpose: string; notes: string };
  showLogForm: boolean;
  logSaved: boolean;
  logSaveError: string | null;
  logsLoading: boolean;
  routeLoading: boolean;
  sessionAlreadySaved: boolean;
}

interface DriversLogsActions {
  fetchDriversLogs: (vehicleId: string) => Promise<void>;
  fetchLogRoute: (logId: string, vehicleId: string) => Promise<{ success: boolean; data?: DriversLogEntry; route?: Location[]; error?: string }>;
  saveLog: (sessionInfo: SessionInfo, formData: { purpose: string; notes: string }, history: Location[], vehicleId: string) => Promise<void>;
  checkSessionSaved: (sessionId: string, vehicleId: string) => Promise<boolean>;
  setLogFormData: (data: { purpose: string; notes: string }) => void;
  setShowLogForm: (show: boolean) => void;
  setSelectedLog: (log: DriversLogEntry | null) => void;
  clearLogState: () => void;
  clearErrors: () => void;
}

export function useDriversLogs(): DriversLogsState & DriversLogsActions {
  const [driversLogs, setDriversLogs] = useState<DriversLogEntry[]>([]);
  const [selectedLog, setSelectedLog] = useState<DriversLogEntry | null>(null);
  const [logFormData, setLogFormData] = useState({ purpose: '', notes: '' });
  const [showLogForm, setShowLogForm] = useState(false);
  const [logSaved, setLogSaved] = useState(false);
  const [logSaveError, setLogSaveError] = useState<string | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);
  const [routeLoading, setRouteLoading] = useState(false);
  const [sessionAlreadySaved, setSessionAlreadySaved] = useState(false);

  const fetchDriversLogs = useCallback(async (vehicleId: string) => {
    if (!vehicleId) {
      console.log('No vehicle selected, skipping drivers logs fetch');
      setDriversLogs([]);
      return;
    }

    try {
      setLogsLoading(true);
      const logs = await fetchDriversLogsService(vehicleId);
      setDriversLogs(logs);
    } catch (error) {
      console.error('Error fetching drivers logs:', error);
      setDriversLogs([]);
    } finally {
      setLogsLoading(false);
    }
  }, []);

  const fetchLogRoute = useCallback(async (logId: string, vehicleId: string) => {
    try {
      setRouteLoading(true);
      const result = await fetchLogRouteService(logId, vehicleId);
      
      if (result.success && result.data && result.route) {
        setSelectedLog({ ...result.data, route: result.route });
      }
      
      return result;
    } catch (error) {
      console.error('Error fetching route:', error);
      return {
        success: false,
        error: 'Failed to load route data. Please try again.'
      };
    } finally {
      setRouteLoading(false);
    }
  }, []);

  const saveLog = useCallback(async (
    sessionInfo: SessionInfo,
    formData: { purpose: string; notes: string },
    history: Location[],
    vehicleId: string
  ) => {
    try {
      setLogSaveError(null);
      
      const result = await saveDriverLog(sessionInfo, formData, history, vehicleId);
      
      if (result.success) {
        setLogSaved(true);
        setShowLogForm(false);
        
        // Add delay and refresh logs
        await new Promise(resolve => setTimeout(resolve, 1000));
        await fetchDriversLogs(vehicleId);
      } else {
        if (result.overlappingId) {
          setLogSaveError(`This time period overlaps with an existing driver's log entry (ID: ${result.overlappingId})`);
        } else {
          setLogSaveError(result.error || 'Failed to save log');
        }
      }
    } catch (error) {
      console.error('Error saving log:', error);
      setLogSaveError(error instanceof Error ? error.message : 'Failed to save log');
    }
  }, [fetchDriversLogs]);

  const checkSessionSaved = useCallback(async (sessionId: string, vehicleId: string): Promise<boolean> => {
    try {
      const saved = await checkSessionSavedService(sessionId, vehicleId);
      setSessionAlreadySaved(saved);
      return saved;
    } catch (error) {
      console.error('Error checking session status:', error);
      return false;
    }
  }, []);

  const clearLogState = useCallback(() => {
    setSelectedLog(null);
    setLogFormData({ purpose: '', notes: '' });
    setShowLogForm(false);
    setLogSaved(false);
    setLogSaveError(null);
    setSessionAlreadySaved(false);
  }, []);

  const clearErrors = useCallback(() => {
    setLogSaveError(null);
  }, []);

  return {
    driversLogs,
    selectedLog,
    logFormData,
    showLogForm,
    logSaved,
    logSaveError,
    logsLoading,
    routeLoading,
    sessionAlreadySaved,
    fetchDriversLogs,
    fetchLogRoute,
    saveLog,
    checkSessionSaved,
    setLogFormData,
    setShowLogForm,
    setSelectedLog,
    clearLogState,
    clearErrors
  };
}