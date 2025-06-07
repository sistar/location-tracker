import { useState, useCallback } from 'react';
import { 
  fetchPastSessions as fetchPastSessionsService, 
  loadPastSession as loadPastSessionService 
} from '../services';
import type { PastSession, SessionInfo, Location } from '../types';

interface SessionManagement {
  sessionInfo: SessionInfo | null;
  pastSessions: PastSession[];
  selectedSession: PastSession | null;
  sessionsLoading: boolean;
  error: string | null;
}

interface SessionActions {
  fetchPastSessions: (vehicleId: string, daysToScan: number) => Promise<void>;
  loadPastSession: (session: PastSession) => Promise<{ points: Location[]; sessionInfo: SessionInfo } | null>;
  setSessionInfo: (info: SessionInfo | null) => void;
  setSelectedSession: (session: PastSession | null) => void;
  clearSession: () => void;
  clearError: () => void;
}

export function useSessionManagement(): SessionManagement & SessionActions {
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [pastSessions, setPastSessions] = useState<PastSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<PastSession | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPastSessions = useCallback(async (vehicleId: string, daysToScan: number) => {
    try {
      setSessionsLoading(true);
      setPastSessions([]);
      setSelectedSession(null);
      setError(null);
      
      const sessions = await fetchPastSessionsService(vehicleId, daysToScan);
      setPastSessions(sessions);
    } catch (err) {
      console.error('Error fetching past sessions:', err);
      setError('Failed to load past sessions. Please try again.');
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const loadPastSession = useCallback(async (session: PastSession) => {
    try {
      setSessionsLoading(true);
      setSelectedSession(session);
      setError(null);
      
      const result = await loadPastSessionService(session);
      setSessionInfo(result.sessionInfo);
      
      return result;
    } catch (err) {
      console.error('Error loading session:', err);
      setError(`Failed to load session data: ${err instanceof Error ? err.message : 'Unknown error'}`);
      return null;
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const clearSession = useCallback(() => {
    setSessionInfo(null);
    setSelectedSession(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    sessionInfo,
    pastSessions,
    selectedSession,
    sessionsLoading,
    error,
    fetchPastSessions,
    loadPastSession,
    setSessionInfo,
    setSelectedSession,
    clearSession,
    clearError
  };
}