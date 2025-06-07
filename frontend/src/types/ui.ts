// UI-specific types
export type EditingAddress = {
  id: string;
  type: 'start' | 'end' | 'stop';
  index?: number;
  current: string;
  originalLat: number;
  originalLon: number;
  newLat?: number;
  newLon?: number;
  validationError?: string;
};