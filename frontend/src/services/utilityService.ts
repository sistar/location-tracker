// Utility functions for calculations and formatting

export function haversine(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000; // Earth radius in meters
  const toRad = (x: number) => (x * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export function formatISOTimestamp(timestamp: number): string {
  try {
    const date = new Date(timestamp * 1000);
    return date.toISOString().slice(0, 19) + 'Z';
  } catch (error) {
    console.error("Error formatting timestamp:", error);
    return new Date().toISOString().slice(0, 19) + 'Z';
  }
}