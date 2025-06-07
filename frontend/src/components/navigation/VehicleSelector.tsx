import React from 'react';

interface VehicleSelectorProps {
  selectedVehicle: string;
  availableVehicles: string[];
  vehiclesLoading: boolean;
  onVehicleChange: (vehicleId: string) => void;
  onRefreshVehicles: () => void;
}

export const VehicleSelector: React.FC<VehicleSelectorProps> = ({
  selectedVehicle,
  availableVehicles,
  vehiclesLoading,
  onVehicleChange,
  onRefreshVehicles
}) => {
  const handleVehicleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onVehicleChange(e.target.value);
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <label htmlFor="vehicle-select" style={{ fontWeight: 'bold' }}>
        Vehicle:
      </label>
      <select 
        id="vehicle-select"
        value={selectedVehicle} 
        onChange={handleVehicleChange}
        disabled={vehiclesLoading}
        style={{
          padding: '8px 12px',
          borderRadius: '4px',
          border: '1px solid #ccc',
          fontSize: '14px'
        }}
      >
        {availableVehicles.map(vehicleId => (
          <option key={vehicleId} value={vehicleId}>
            {vehicleId}
          </option>
        ))}
      </select>
      <button 
        onClick={onRefreshVehicles}
        disabled={vehiclesLoading}
        style={{
          padding: '8px 12px',
          backgroundColor: '#28a745',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: vehiclesLoading ? 'not-allowed' : 'pointer',
          opacity: vehiclesLoading ? 0.6 : 1
        }}
      >
        {vehiclesLoading ? '...' : '🔄'}
      </button>
    </div>
  );
};