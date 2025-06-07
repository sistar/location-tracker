import React from 'react';
import { NavigationTabs } from './NavigationTabs';
import { VehicleSelector } from './VehicleSelector';
import type { DriversLogEntry } from '../../types';

interface NavigationHeaderProps {
  viewMode: 'trips' | 'live' | 'timeline';
  onViewModeChange: (mode: 'trips' | 'live' | 'timeline') => void;
  selectedVehicle: string;
  availableVehicles: string[];
  vehiclesLoading: boolean;
  routeLoading: boolean;
  selectedLog: DriversLogEntry | null;
  onVehicleChange: (vehicle: string) => void;
  onRefreshVehicles: () => void;
  onLiveTrackingClick: () => void;
}

export const NavigationHeader: React.FC<NavigationHeaderProps> = ({
  viewMode,
  onViewModeChange,
  selectedVehicle,
  availableVehicles,
  vehiclesLoading,
  routeLoading,
  selectedLog,
  onVehicleChange,
  onRefreshVehicles,
  onLiveTrackingClick
}) => {
  return (
    <div style={{
      padding: '20px',
      backgroundColor: '#f8f9fa',
      borderBottom: '1px solid #dee2e6'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px'
      }}>
        <h1 style={{ margin: 0, color: '#333' }}>GPS Location Tracker</h1>
        <VehicleSelector
          selectedVehicle={selectedVehicle}
          availableVehicles={availableVehicles}
          vehiclesLoading={vehiclesLoading}
          onVehicleChange={onVehicleChange}
          onRefreshVehicles={onRefreshVehicles}
        />
      </div>
      
      <NavigationTabs
        viewMode={viewMode}
        onViewModeChange={onViewModeChange}
        routeLoading={routeLoading}
        selectedLog={selectedLog}
      />

      {(viewMode === 'live' || selectedLog) && (
        <div style={{ marginTop: '10px' }}>
          <button 
            onClick={onLiveTrackingClick}
            style={{
              padding: '8px 16px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {selectedLog ? 'Return to Live Tracking' : 'Start Live Tracking'}
          </button>
        </div>
      )}
    </div>
  );
};