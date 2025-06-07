import React from 'react';
import type { DriversLogEntry } from '../../types';

interface TripCardProps {
  log: DriversLogEntry;
  isSelected: boolean;
  routeLoading: boolean;
  onSelect: (log: DriversLogEntry) => void;
  onDeselect: () => void;
}

export const TripCard: React.FC<TripCardProps> = ({
  log,
  isSelected,
  routeLoading,
  onSelect,
  onDeselect
}) => {
  return (
    <div style={{ 
      backgroundColor: "white",
      borderRadius: "8px",
      padding: "20px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
      border: isSelected ? "2px solid #007bff" : "1px solid #e0e0e0",
      transition: "all 0.2s ease"
    }}>
      {/* Trip Date and Time */}
      <div style={{ 
        color: '#007bff', 
        fontWeight: 'bold',
        fontSize: '1.1em',
        marginBottom: '10px',
        borderBottom: '1px solid #e0e0e0',
        paddingBottom: '8px'
      }}>
        📅 {new Date(log.startTime * 1000).toLocaleDateString('en-US', { 
          weekday: 'long', 
          year: 'numeric', 
          month: 'long', 
          day: 'numeric' 
        })}
      </div>
      
      {/* Time Range */}
      <div style={{ fontSize: '0.9em', color: '#666', marginBottom: '10px' }}>
        ⏰ {new Date(log.startTime * 1000).toLocaleTimeString()} - {new Date(log.endTime * 1000).toLocaleTimeString()}
      </div>
      
      {/* Purpose Badge */}
      <div style={{ marginBottom: '15px' }}>
        <span style={{
          backgroundColor: log.purpose === 'business' ? '#4CAF50' : 
                           log.purpose === 'personal' ? '#2196F3' :
                           log.purpose === 'commute' ? '#FF9800' : '#9E9E9E',
          color: 'white',
          padding: '4px 12px',
          borderRadius: '20px',
          fontSize: '0.8em',
          fontWeight: 'bold',
          textTransform: 'uppercase'
        }}>
          {log.purpose || 'Unspecified'}
        </span>
      </div>
      
      {/* Route Information */}
      <div style={{ marginBottom: '15px' }}>
        {log.startAddress && (
          <div style={{ fontSize: '0.9em', marginBottom: '5px' }}>
            <strong>📍 From:</strong> {log.startAddress}
          </div>
        )}
        
        {log.endAddress && (
          <div style={{ fontSize: '0.9em', marginBottom: '5px' }}>
            <strong>🏁 To:</strong> {log.endAddress}
          </div>
        )}
      </div>
      
      {/* Trip Stats */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr', 
        gap: '10px',
        marginBottom: '15px',
        padding: '10px',
        backgroundColor: '#f8f9fa',
        borderRadius: '6px'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.2em', fontWeight: 'bold', color: '#333' }}>
            {(log.distance / 1000).toFixed(1)} km
          </div>
          <div style={{ fontSize: '0.8em', color: '#666' }}>Distance</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.2em', fontWeight: 'bold', color: '#333' }}>
            {Math.round(log.duration)} min
          </div>
          <div style={{ fontSize: '0.8em', color: '#666' }}>Duration</div>
        </div>
      </div>
      
      {/* Notes */}
      {log.notes && (
        <div style={{ marginBottom: '15px' }}>
          <strong style={{ fontSize: '0.9em', color: '#333' }}>📝 Notes:</strong>
          <div style={{ 
            backgroundColor: '#f0f0f0', 
            padding: '8px', 
            borderRadius: '4px',
            marginTop: '5px',
            fontSize: '0.9em',
            fontStyle: 'italic'
          }}>
            {log.notes}
          </div>
        </div>
      )}
      
      {/* Action Button */}
      <div style={{ textAlign: 'center' }}>
        {isSelected ? (
          <button
            onClick={onDeselect}
            style={{ 
              padding: '10px 20px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.9em',
              fontWeight: 'bold',
              width: '100%'
            }}
          >
            📍 Currently Viewing - Click to Close
          </button>
        ) : (
          <button
            onClick={() => onSelect(log)}
            disabled={routeLoading}
            style={{ 
              padding: '10px 20px',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              opacity: routeLoading ? 0.7 : 1,
              fontSize: '0.9em',
              fontWeight: 'bold',
              width: '100%'
            }}
          >
            🗺️ {routeLoading ? 'Loading...' : 'View on Map'}
          </button>
        )}
      </div>
    </div>
  );
};