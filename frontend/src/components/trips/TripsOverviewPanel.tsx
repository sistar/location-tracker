import React from 'react';
import { TripCard } from './TripCard';
import type { DriversLogEntry } from '../../types';

interface TripsOverviewPanelProps {
  showTripsOverview: boolean;
  viewMode: string;
  driversLogs: DriversLogEntry[];
  logsLoading: boolean;
  selectedLog: DriversLogEntry | null;
  routeLoading: boolean;
  onFindNewSessions: () => void;
  onRefreshLogs: () => void;
  onTripSelect: (log: DriversLogEntry) => void;
  onTripDeselect: () => void;
}

export const TripsOverviewPanel: React.FC<TripsOverviewPanelProps> = ({
  showTripsOverview,
  viewMode,
  driversLogs,
  logsLoading,
  selectedLog,
  routeLoading,
  onFindNewSessions,
  onRefreshLogs,
  onTripSelect,
  onTripDeselect
}) => {
  if (!showTripsOverview || viewMode !== 'trips') {
    return null;
  }

  return (
    <div style={{
      position: "absolute",
      top: "60px",
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: "#f5f5f5",
      zIndex: 1000,
      overflowY: "auto",
      padding: "20px"
    }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
        <div style={{ 
          display: "flex", 
          justifyContent: "space-between", 
          alignItems: "center", 
          marginBottom: "20px",
          backgroundColor: "white",
          padding: "15px 20px",
          borderRadius: "8px",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
        }}>
          <h2 style={{ margin: 0, color: "#333" }}>My Trip History</h2>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={onFindNewSessions}
              style={{
                padding: "8px 16px",
                backgroundColor: "#4CAF50",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "0.9em"
              }}
            >
              📅 Find New Sessions
            </button>
            <button
              onClick={onRefreshLogs}
              style={{
                padding: "8px 16px",
                backgroundColor: "#007bff",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "0.9em"
              }}
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {logsLoading ? (
          <div style={{ 
            textAlign: 'center', 
            padding: '40px',
            backgroundColor: "white",
            borderRadius: "8px",
            boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
          }}>
            <div style={{ fontSize: "1.2em", color: "#666" }}>Loading your trips...</div>
          </div>
        ) : driversLogs.length === 0 ? (
          <div style={{ 
            textAlign: 'center', 
            padding: '40px',
            backgroundColor: "white",
            borderRadius: "8px",
            boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
          }}>
            <div style={{ fontSize: "1.2em", color: "#666", marginBottom: "10px" }}>No trips found</div>
            <div style={{ color: "#999" }}>Start by scanning for new sessions or take a drive!</div>
          </div>
        ) : (
          <div style={{ 
            display: "grid", 
            gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))", 
            gap: "20px"
          }}>
            {driversLogs.map((log) => (
              <TripCard
                key={log.id}
                log={log}
                isSelected={selectedLog?.id === log.id}
                routeLoading={routeLoading}
                onSelect={onTripSelect}
                onDeselect={onTripDeselect}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};