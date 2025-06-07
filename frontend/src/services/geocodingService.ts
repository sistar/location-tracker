import type { GeocodeApiResponse } from '../types';
import { API_ENDPOINTS } from './api';

// Address cache for performance
let addressCache = new Map<string, string>();

export async function getAddress(lat: number, lon: number): Promise<string> {
  // Check cache first
  const cacheKey = `${lat},${lon}`;
  if (addressCache.has(cacheKey)) {
    console.log(`Address cache hit for ${cacheKey}:`, addressCache.get(cacheKey));
    return addressCache.get(cacheKey) || 'Unknown location';
  }
  
  try {
    // Create a URL with query parameters
    const apiUrl = `${API_ENDPOINTS.GEOCODE}?operation=reverse&lat=${lat}&lon=${lon}`;
    console.log(`Fetching address from:`, apiUrl);
    
    // Add timeout to the request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    // Use the proxy URL
    const response = await fetch(apiUrl, {
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    console.log(`Geocoding response status:`, response.status);
    
    if (!response.ok) {
      throw new Error(`Geocoding failed with status: ${response.status}`);
    }
    
    const data: GeocodeApiResponse = await response.json();
    console.log(`Geocoding response data:`, data);
    
    let address = 'Unknown location';
    
    // Check for error in response
    if (data.error) {
      console.error('Geocoding error:', data.error);
      return 'Address lookup failed';
    }
    
    // Use the formatted address from our backend service
    if (data && data.address) {
      address = data.address;
    }
    
    console.log(`Successfully geocoded ${lat},${lon} to:`, address);
    
    // Save to cache
    addressCache.set(cacheKey, address);
    
    return address;
  } catch (error: unknown) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.error('Geocoding request timed out:', error);
      return 'Address lookup timed out';
    }
    console.error('Error fetching address:', error);
    return 'Address lookup failed';
  }
}

export async function geocodeAddress(address: string): Promise<{lat: number, lon: number} | null> {
  try {
    // Create a URL with query parameters
    const apiUrl = `${API_ENDPOINTS.GEOCODE}?operation=search&query=${encodeURIComponent(address)}`;
    
    // Use the proxy URL
    const response = await fetch(apiUrl);
    
    if (!response.ok) {
      throw new Error('Geocoding search failed');
    }
    
    const data = await response.json();
    
    // Check for error in response
    if (data.error) {
      console.error('Geocoding error:', data.error);
      return null;
    }
    
    // Check both lat/lon and lat/lon formats (our backend uses lon, Nominatim uses lon)
    if (data && data.lat && (data.lon || data.lon)) {
      return {
        lat: data.lat,
        lon: data.lon || data.lon
      };
    }
    
    return null;
  } catch (error) {
    console.error('Error geocoding address:', error);
    return null;
  }
}

export async function validateCoordinates(
  origLat: number, 
  origLon: number, 
  newLat: number, 
  newLon: number
): Promise<{valid: boolean, distance: number, error?: string}> {
  try {
    // Format the query for our backend validation API
    const params = new URLSearchParams({
      operation: 'validate',
      orig_lat: origLat.toString(),
      orig_lon: origLon.toString(),
      new_lat: newLat.toString(),
      new_lon: newLon.toString()
    });
    
    const response = await fetch(`${API_ENDPOINTS.GEOCODE}?${params}`);
    
    if (!response.ok) {
      throw new Error('Validation failed');
    }
    
    const data = await response.json();
    return {
      valid: data.valid === true,
      distance: data.distance || 0,
      error: data.error
    };
  } catch (error) {
    console.error('Error validating coordinates:', error);
    return {
      valid: false,
      distance: 0,
      error: 'Validation service error'
    };
  }
}

// Helper function to get current cache for components that need it
export function getAddressCache(): Map<string, string> {
  return addressCache;
}

// Helper function to update cache from components
export function updateAddressCache(newCache: Map<string, string>): void {
  addressCache = newCache;
}