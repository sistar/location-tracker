import { useState, useCallback } from 'react';
import { getAddress as getAddressService, geocodeAddress, validateCoordinates, getAddressCache, updateAddressCache } from '../services';
import type { EditingAddress } from '../types';

interface AddressManagement {
  addressCache: Map<string, string>;
  editingAddress: EditingAddress | null;
  loading: boolean;
}

interface AddressActions {
  getAddress: (lat: number, lon: number) => Promise<string>;
  geocodeAddress: (address: string) => Promise<{lat: number, lon: number} | null>;
  startEditing: (type: 'start' | 'end' | 'stop', current: string, lat: number, lon: number, index?: number) => void;
  updateAddress: (type: 'start' | 'end' | 'stop', newAddress: string, index?: number, validatedLat?: number, validatedLon?: number) => void;
  validateAndUpdate: (type: 'start' | 'end' | 'stop', newAddress: string, index?: number) => Promise<void>;
  cancelEditing: () => void;
}

export function useAddressManagement(): AddressManagement & AddressActions {
  const [addressCache, setAddressCache] = useState<Map<string, string>>(() => getAddressCache());
  const [editingAddress, setEditingAddress] = useState<EditingAddress | null>(null);
  const [loading, setLoading] = useState(false);

  const getAddress = useCallback(async (lat: number, lon: number): Promise<string> => {
    try {
      setLoading(true);
      const address = await getAddressService(lat, lon);
      
      // Update local cache state
      const newCache = new Map(addressCache);
      const cacheKey = `${lat},${lon}`;
      newCache.set(cacheKey, address);
      setAddressCache(newCache);
      updateAddressCache(newCache);
      
      return address;
    } finally {
      setLoading(false);
    }
  }, [addressCache]);

  const handleGeocodeAddress = useCallback(async (address: string): Promise<{lat: number, lon: number} | null> => {
    try {
      setLoading(true);
      return await geocodeAddress(address);
    } finally {
      setLoading(false);
    }
  }, []);

  const startEditing = useCallback((
    type: 'start' | 'end' | 'stop', 
    current: string, 
    lat: number, 
    lon: number, 
    index?: number
  ) => {
    const id = index !== undefined ? `${type}-${index}` : type;
    setEditingAddress({
      id,
      type,
      index,
      current,
      originalLat: lat,
      originalLon: lon
    });
  }, []);

  const updateAddress = useCallback((
    _type: 'start' | 'end' | 'stop', 
    newAddress: string, 
    _index?: number, 
    validatedLat?: number, 
    validatedLon?: number
  ) => {
    if (editingAddress) {
      setEditingAddress({
        ...editingAddress,
        current: newAddress,
        newLat: validatedLat,
        newLon: validatedLon,
        validationError: undefined
      });
    }
  }, [editingAddress]);

  const validateAndUpdate = useCallback(async (
    type: 'start' | 'end' | 'stop', 
    newAddress: string, 
    index?: number
  ) => {
    if (!editingAddress) return;

    try {
      setLoading(true);
      
      // Geocode the new address
      const coords = await handleGeocodeAddress(newAddress);
      if (!coords) {
        setEditingAddress(prev => prev ? {
          ...prev,
          validationError: 'Address not found. Please try a different address.'
        } : null);
        return;
      }

      // Validate coordinates against original location
      const validation = await validateCoordinates(
        editingAddress.originalLat,
        editingAddress.originalLon,
        coords.lat,
        coords.lon
      );

      if (!validation.valid) {
        setEditingAddress(prev => prev ? {
          ...prev,
          validationError: validation.error || `Address is too far from original location (${validation.distance}m)`
        } : null);
        return;
      }

      // Update successful
      updateAddress(type, newAddress, index, coords.lat, coords.lon);
      
    } catch (error) {
      console.error('Error validating address:', error);
      setEditingAddress(prev => prev ? {
        ...prev,
        validationError: 'Error validating address. Please try again.'
      } : null);
    } finally {
      setLoading(false);
    }
  }, [editingAddress, handleGeocodeAddress, updateAddress]);

  const cancelEditing = useCallback(() => {
    setEditingAddress(null);
  }, []);

  return {
    addressCache,
    editingAddress,
    loading,
    getAddress,
    geocodeAddress: handleGeocodeAddress,
    startEditing,
    updateAddress,
    validateAndUpdate,
    cancelEditing
  };
}