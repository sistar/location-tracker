import { useState, useCallback, useEffect } from 'react';
import { fetchVehicles as fetchVehiclesService } from '../services';

interface VehicleManagement {
  availableVehicles: string[];
  selectedVehicle: string;
  vehiclesLoading: boolean;
  error: string | null;
}

interface VehicleActions {
  fetchVehicles: () => Promise<void>;
  selectVehicle: (vehicleId: string) => void;
  clearError: () => void;
}

export function useVehicleManagement(): VehicleManagement & VehicleActions {
  const [availableVehicles, setAvailableVehicles] = useState<string[]>([]);
  const [selectedVehicle, setSelectedVehicle] = useState<string>('');
  const [vehiclesLoading, setVehiclesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchVehicles = useCallback(async () => {
    try {
      setVehiclesLoading(true);
      setError(null);
      
      const vehicles = await fetchVehiclesService();
      setAvailableVehicles(vehicles);
      
      // If no vehicle is selected yet, select the first one
      if (!selectedVehicle && vehicles.length > 0) {
        setSelectedVehicle(vehicles[0]);
      }
    } catch (err) {
      console.error('Error fetching vehicles:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch vehicles');
    } finally {
      setVehiclesLoading(false);
    }
  }, [selectedVehicle]);

  const selectVehicle = useCallback((vehicleId: string) => {
    setSelectedVehicle(vehicleId);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Fetch vehicles on mount
  useEffect(() => {
    fetchVehicles();
  }, [fetchVehicles]);

  return {
    availableVehicles,
    selectedVehicle,
    vehiclesLoading,
    error,
    fetchVehicles,
    selectVehicle,
    clearError
  };
}