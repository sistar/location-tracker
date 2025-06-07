import React from 'react';

interface NavigationTabsProps {
  viewMode: 'trips' | 'live' | 'timeline';
  onViewModeChange: (mode: 'trips' | 'live' | 'timeline') => void;
  routeLoading: boolean;
  selectedLog: unknown | null;
}

export const NavigationTabs: React.FC<NavigationTabsProps> = ({
  viewMode,
  onViewModeChange,
  routeLoading,
  selectedLog
}) => {
  return (
    <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
      <button 
        onClick={() => onViewModeChange('trips')}
        style={{
          padding: '10px 20px',
          backgroundColor: viewMode === 'trips' ? '#007bff' : '#6c757d',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer'
        }}
      >
        My Trips
      </button>
      <button 
        onClick={() => onViewModeChange('live')}
        style={{
          padding: '10px 20px',
          backgroundColor: viewMode === 'live' ? '#007bff' : '#6c757d',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer'
        }}
      >
        Live Tracking
      </button>
      <button 
        onClick={() => onViewModeChange('timeline')}
        style={{
          padding: '10px 20px',
          backgroundColor: viewMode === 'timeline' ? '#007bff' : '#6c757d',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer'
        }}
      >
        Timeline
      </button>
      {routeLoading && (
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#fff3cd', 
          border: '1px solid #ffeaa7', 
          borderRadius: '5px',
          color: '#856404'
        }}>
          {selectedLog ? 'Loading route...' : 'Loading...'}
        </div>
      )}
    </div>
  );
};