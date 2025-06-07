import { useState, useCallback } from 'react';

interface UIState {
  viewMode: 'trips' | 'live' | 'timeline';
  showTripsOverview: boolean;
  showSessionsPanel: boolean;
  showLogsPanel: boolean;
  isRawGpsMode: boolean;
  daysToScan: number;
  rawGpsDays: number;
  error: string | null;
}

interface UIActions {
  setViewMode: (mode: 'trips' | 'live' | 'timeline') => void;
  setShowTripsOverview: (show: boolean) => void;
  setShowSessionsPanel: (show: boolean) => void;
  setShowLogsPanel: (show: boolean) => void;
  setIsRawGpsMode: (enabled: boolean) => void;
  setDaysToScan: (days: number) => void;
  setRawGpsDays: (days: number) => void;
  setError: (error: string | null) => void;
  switchToTripsView: () => void;
  switchToLiveView: () => void;
  switchToTimelineView: () => void;
}

export function useUIState(): UIState & UIActions {
  const [viewMode, setViewModeState] = useState<'trips' | 'live' | 'timeline'>('live');
  const [showTripsOverview, setShowTripsOverview] = useState(false);
  const [showSessionsPanel, setShowSessionsPanel] = useState(false);
  const [showLogsPanel, setShowLogsPanel] = useState(false);
  const [isRawGpsMode, setIsRawGpsMode] = useState(false);
  const [daysToScan, setDaysToScan] = useState(7);
  const [rawGpsDays, setRawGpsDays] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const setViewMode = useCallback((mode: 'trips' | 'live' | 'timeline') => {
    setViewModeState(mode);
  }, []);

  const switchToTripsView = useCallback(() => {
    setViewModeState('trips');
    setShowTripsOverview(true);
    setShowLogsPanel(false);
    setShowSessionsPanel(false);
    setIsRawGpsMode(false);
  }, []);

  const switchToLiveView = useCallback(() => {
    setViewModeState('live');
    setShowTripsOverview(false);
    setShowLogsPanel(false);
    setShowSessionsPanel(false);
    setIsRawGpsMode(false);
  }, []);

  const switchToTimelineView = useCallback(() => {
    setViewModeState('timeline');
    setShowTripsOverview(false);
    setShowLogsPanel(false);
    setShowSessionsPanel(false);
    setIsRawGpsMode(true);
  }, []);

  return {
    viewMode,
    showTripsOverview,
    showSessionsPanel,
    showLogsPanel,
    isRawGpsMode,
    daysToScan,
    rawGpsDays,
    error,
    setViewMode,
    setShowTripsOverview,
    setShowSessionsPanel,
    setShowLogsPanel,
    setIsRawGpsMode,
    setDaysToScan,
    setRawGpsDays,
    setError,
    switchToTripsView,
    switchToLiveView,
    switchToTimelineView
  };
}