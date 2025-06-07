# Custom Hooks Documentation

## Overview

The Location Tracker application uses custom React hooks to encapsulate state management logic and provide clean, reusable abstractions for complex operations. Each hook follows React hooks conventions and provides a clear interface for state and actions.

## Hook Architecture

### Design Principles
- **Single Responsibility**: Each hook manages a specific domain of state
- **Clear Interfaces**: Consistent return patterns with state and actions
- **Type Safety**: Full TypeScript coverage with defined interfaces
- **Error Handling**: Centralized error management within hooks
- **Performance**: Optimized with useCallback and proper dependencies

### Common Pattern
```typescript
interface HookState {
  // State properties
  data: SomeType;
  loading: boolean;
  error: string | null;
}

interface HookActions {
  // Action functions
  fetchData: () => Promise<void>;
  updateData: (data: SomeType) => void;
  clearData: () => void;
}

export function useCustomHook(): HookState & HookActions {
  // Implementation
}
```

## Hooks

### useAddressManagement

**Purpose**: Manages address geocoding, validation, and caching operations.

**Location**: `src/hooks/useAddressManagement.ts`

**State Interface**:
```typescript
interface AddressManagement {
  addressCache: Map<string, string>;        // Cached address lookups
  editingAddress: EditingAddress | null;    // Currently editing address
  loading: boolean;                         // Loading state for operations
}
```

**Actions Interface**:
```typescript
interface AddressActions {
  getAddress: (lat: number, lon: number) => Promise<string>;
  geocodeAddress: (address: string) => Promise<{lat: number, lon: number} | null>;
  startEditing: (type: 'start' | 'end' | 'stop', current: string, lat: number, lon: number, index?: number) => void;
  updateAddress: (type: 'start' | 'end' | 'stop', newAddress: string, index?: number, validatedLat?: number, validatedLon?: number) => void;
  validateAndUpdate: (type: 'start' | 'end' | 'stop', newAddress: string, index?: number) => Promise<void>;
  cancelEditing: () => void;
}
```

**Key Features**:
- **Address Caching**: Prevents redundant geocoding API calls
- **Validation Workflow**: Validates new addresses against original coordinates
- **Edit State Management**: Tracks current editing operations
- **Error Handling**: Provides validation error feedback

**Usage Example**:
```tsx
const {
  addressCache,
  editingAddress,
  getAddress,
  startEditing,
  validateAndUpdate,
  cancelEditing
} = useAddressManagement();

// Get address for coordinates
const address = await getAddress(latitude, longitude);

// Start editing an address
startEditing('start', currentAddress, latitude, longitude);

// Validate and update
await validateAndUpdate('start', newAddress);
```

### useVehicleManagement

**Purpose**: Manages vehicle selection and vehicle list operations.

**Location**: `src/hooks/useVehicleManagement.ts`

**State Interface**:
```typescript
interface VehicleManagement {
  availableVehicles: string[];    // List of available vehicle IDs
  selectedVehicle: string;        // Currently selected vehicle
  vehiclesLoading: boolean;       // Loading state for vehicle operations
  error: string | null;           // Error state
}
```

**Actions Interface**:
```typescript
interface VehicleActions {
  fetchVehicles: () => Promise<void>;     // Fetch available vehicles
  selectVehicle: (vehicleId: string) => void;  // Select a vehicle
  clearError: () => void;                 // Clear error state
}
```

**Key Features**:
- **Auto-selection**: Automatically selects first vehicle if none selected
- **Error Management**: Handles vehicle fetching errors
- **Loading States**: Provides loading feedback
- **Initial Load**: Fetches vehicles on hook mount

**Usage Example**:
```tsx
const {
  availableVehicles,
  selectedVehicle,
  vehiclesLoading,
  fetchVehicles,
  selectVehicle
} = useVehicleManagement();

// Vehicle selector component
<select value={selectedVehicle} onChange={(e) => selectVehicle(e.target.value)}>
  {availableVehicles.map(vehicle => (
    <option key={vehicle} value={vehicle}>{vehicle}</option>
  ))}
</select>
```

### useLocationData

**Purpose**: Manages location state, history data, and map-related operations.

**Location**: `src/hooks/useLocationData.ts`

**State Interface**:
```typescript
interface LocationData {
  location: Location | null;          // Current location
  history: Location[];                // Historical location points
  isLiveTracking: boolean;           // Live tracking mode
  historyStartTime: number | undefined;  // History query start time
  mapKey: number;                    // Map re-render key
  loading: boolean;                  // Loading state
  error: string | null;              // Error state
}
```

**Actions Interface**:
```typescript
interface LocationActions {
  fetchLocation: (vehicleId: string) => Promise<void>;
  fetchHistory: (vehicleId: string, startTimestamp?: string | number, timeWindowHours?: number) => Promise<{ points: Location[]; sessionInfo: SessionInfo | null }>;
  setIsLiveTracking: (isLive: boolean) => void;
  setLocation: (location: Location | null) => void;
  setHistory: (history: Location[]) => void;
  clearData: () => void;
  refreshMap: () => void;
  setError: (error: string | null) => void;
}
```

**Key Features**:
- **Real-time Location**: Fetches current GPS coordinates
- **Historical Data**: Retrieves and processes location history
- **Map Integration**: Manages map re-rendering with key updates
- **Session Processing**: Returns processed session information
- **State Coordination**: Manages related location states together

**Usage Example**:
```tsx
const {
  location,
  history,
  isLiveTracking,
  fetchLocation,
  fetchHistory,
  setIsLiveTracking,
  clearData
} = useLocationData();

// Start live tracking
setIsLiveTracking(true);
await fetchLocation(vehicleId);

// Get history
const { points, sessionInfo } = await fetchHistory(vehicleId, startTime, 6);
```

### useUIState

**Purpose**: Manages UI state including view modes, panel visibility, and user interface preferences.

**Location**: `src/hooks/useUIState.ts`

**State Interface**:
```typescript
interface UIState {
  viewMode: 'trips' | 'live' | 'timeline';  // Current view mode
  showTripsOverview: boolean;               // Trips panel visibility
  showSessionsPanel: boolean;               // Sessions panel visibility
  showLogsPanel: boolean;                   // Logs panel visibility
  isRawGpsMode: boolean;                   // Raw GPS mode flag
  daysToScan: number;                      // Days for session scanning
  rawGpsDays: number;                      // Days for raw GPS data
  error: string | null;                    // UI error state
}
```

**Actions Interface**:
```typescript
interface UIActions {
  setViewMode: (mode: 'trips' | 'live' | 'timeline') => void;
  setShowTripsOverview: (show: boolean) => void;
  setShowSessionsPanel: (show: boolean) => void;
  setShowLogsPanel: (show: boolean) => void;
  setIsRawGpsMode: (enabled: boolean) => void;
  setDaysToScan: (days: number) => void;
  setRawGpsDays: (days: number) => void;
  setError: (error: string | null) => void;
  switchToTripsView: () => void;      // Convenience method
  switchToLiveView: () => void;       // Convenience method
  switchToTimelineView: () => void;   // Convenience method
}
```

**Key Features**:
- **View Mode Management**: Centralized view state
- **Panel Coordination**: Manages multiple panel visibility states
- **Convenience Methods**: Pre-configured view switching
- **Configuration State**: Days settings for various operations

**Usage Example**:
```tsx
const {
  viewMode,
  showTripsOverview,
  switchToTripsView,
  switchToLiveView,
  setShowLogsPanel
} = useUIState();

// Navigation tabs
<button onClick={switchToTripsView} className={viewMode === 'trips' ? 'active' : ''}>
  My Trips
</button>
<button onClick={switchToLiveView} className={viewMode === 'live' ? 'active' : ''}>
  Live Tracking
</button>
```

### useDriversLogs

**Purpose**: Manages driver's log operations including CRUD operations, form state, and route loading.

**Location**: `src/hooks/useDriversLogs.ts`

**State Interface**:
```typescript
interface DriversLogsState {
  driversLogs: DriversLogEntry[];        // List of saved logs
  selectedLog: DriversLogEntry | null;   // Currently selected log
  logFormData: { purpose: string; notes: string };  // Form data
  showLogForm: boolean;                  // Form visibility
  logSaved: boolean;                     // Save success state
  logSaveError: string | null;           // Save error state
  logsLoading: boolean;                  // Logs loading state
  routeLoading: boolean;                 // Route loading state
  sessionAlreadySaved: boolean;          // Session exists check
}
```

**Actions Interface**:
```typescript
interface DriversLogsActions {
  fetchDriversLogs: (vehicleId: string) => Promise<void>;
  fetchLogRoute: (logId: string, vehicleId: string) => Promise<{ success: boolean; data?: DriversLogEntry; route?: Location[]; error?: string }>;
  saveLog: (sessionInfo: SessionInfo, formData: { purpose: string; notes: string }, history: Location[], vehicleId: string) => Promise<void>;
  checkSessionSaved: (sessionId: string, vehicleId: string) => Promise<boolean>;
  setLogFormData: (data: { purpose: string; notes: string }) => void;
  setShowLogForm: (show: boolean) => void;
  setSelectedLog: (log: DriversLogEntry | null) => void;
  clearLogState: () => void;
  clearErrors: () => void;
}
```

**Key Features**:
- **CRUD Operations**: Complete log management functionality
- **Form Management**: Handles form state and validation
- **Route Loading**: Fetches detailed route data for logs
- **Conflict Detection**: Checks for existing sessions
- **Error Handling**: Comprehensive error management

**Usage Example**:
```tsx
const {
  driversLogs,
  logFormData,
  showLogForm,
  logSaveError,
  fetchDriversLogs,
  saveLog,
  setLogFormData,
  setShowLogForm
} = useDriversLogs();

// Save a trip
await saveLog(sessionInfo, { purpose: 'business', notes: 'Client meeting' }, history, vehicleId);

// Show form
setShowLogForm(true);
```

### useSessionManagement

**Purpose**: Manages session lifecycle, past session scanning, and session loading operations.

**Location**: `src/hooks/useSessionManagement.ts`

**State Interface**:
```typescript
interface SessionManagement {
  sessionInfo: SessionInfo | null;       // Current session metadata
  pastSessions: PastSession[];           // Available past sessions
  selectedSession: PastSession | null;   // Currently selected session
  sessionsLoading: boolean;              // Loading state
  error: string | null;                  // Error state
}
```

**Actions Interface**:
```typescript
interface SessionActions {
  fetchPastSessions: (vehicleId: string, daysToScan: number) => Promise<void>;
  loadPastSession: (session: PastSession) => Promise<{ points: Location[]; sessionInfo: SessionInfo } | null>;
  setSessionInfo: (info: SessionInfo | null) => void;
  setSelectedSession: (session: PastSession | null) => void;
  clearSession: () => void;
  clearError: () => void;
}
```

**Key Features**:
- **Session Scanning**: Finds unsaved GPS sessions
- **Session Loading**: Loads complete session data
- **Metadata Management**: Handles session information
- **Timeline Operations**: Manages historical session access

**Usage Example**:
```tsx
const {
  pastSessions,
  sessionInfo,
  sessionsLoading,
  fetchPastSessions,
  loadPastSession
} = useSessionManagement();

// Scan for sessions
await fetchPastSessions(vehicleId, 7); // Last 7 days

// Load a specific session
const result = await loadPastSession(selectedSession);
if (result) {
  const { points, sessionInfo } = result;
  // Use loaded data
}
```

## Hook Integration Patterns

### Combining Hooks

Hooks can be combined for complex functionality:

```tsx
const LocationTracker = () => {
  const { selectedVehicle } = useVehicleManagement();
  const { 
    location, 
    history, 
    fetchLocation, 
    fetchHistory 
  } = useLocationData();
  const { 
    sessionInfo, 
    setSessionInfo 
  } = useSessionManagement();
  
  useEffect(() => {
    if (selectedVehicle) {
      fetchLocation(selectedVehicle);
    }
  }, [selectedVehicle, fetchLocation]);
  
  const handleFetchHistory = async () => {
    if (selectedVehicle) {
      const result = await fetchHistory(selectedVehicle);
      if (result.sessionInfo) {
        setSessionInfo(result.sessionInfo);
      }
    }
  };
  
  return (
    // Component JSX
  );
};
```

### Hook Dependencies

Some hooks depend on data from others:

```tsx
// Vehicle must be selected before location operations
const { selectedVehicle } = useVehicleManagement();
const { fetchLocation } = useLocationData();

useEffect(() => {
  if (selectedVehicle) {
    fetchLocation(selectedVehicle);
  }
}, [selectedVehicle, fetchLocation]);
```

## Performance Considerations

### Optimization Strategies

1. **useCallback Memoization**: All action functions are memoized
2. **Dependency Arrays**: Carefully managed to prevent unnecessary re-renders
3. **State Batching**: Related state updates are batched together
4. **Error Boundaries**: Hooks include error handling to prevent crashes

### Example Optimizations

```typescript
// In hook implementation
const fetchData = useCallback(async (id: string) => {
  // Implementation
}, []); // Empty deps array since no external dependencies

const updateData = useCallback((data: SomeType) => {
  setData(data);
  setError(null); // Clear errors on successful update
}, []);
```

## Error Handling Patterns

### Consistent Error Management

All hooks follow consistent error handling:

```typescript
const performOperation = useCallback(async () => {
  try {
    setLoading(true);
    setError(null);
    
    const result = await apiCall();
    setState(result);
  } catch (err) {
    console.error('Operation failed:', err);
    setError(err instanceof Error ? err.message : 'Operation failed');
  } finally {
    setLoading(false);
  }
}, []);
```

### Error Recovery

Hooks provide error recovery methods:

```typescript
const clearError = useCallback(() => {
  setError(null);
}, []);

const retryOperation = useCallback(async () => {
  clearError();
  await performOperation();
}, [clearError, performOperation]);
```

## Testing Strategy

### Hook Testing

Custom hooks can be tested using React Testing Library:

```typescript
import { renderHook, act } from '@testing-library/react';
import { useLocationData } from './useLocationData';

describe('useLocationData', () => {
  it('fetches location data correctly', async () => {
    const { result } = renderHook(() => useLocationData());
    
    await act(async () => {
      await result.current.fetchLocation('vehicle_01');
    });
    
    expect(result.current.location).toBeDefined();
    expect(result.current.loading).toBe(false);
  });
  
  it('handles errors gracefully', async () => {
    // Mock API to throw error
    const { result } = renderHook(() => useLocationData());
    
    await act(async () => {
      await result.current.fetchLocation('invalid_vehicle');
    });
    
    expect(result.current.error).toBeDefined();
    expect(result.current.location).toBeNull();
  });
});
```

## Migration Benefits

### Before Hooks (App.tsx with 25+ useState)
- Complex state management
- Tangled dependencies
- Difficult to test
- Hard to reuse logic

### After Hooks (Modular State Management)
- Clear separation of concerns
- Reusable across components
- Easier to test individually
- Better performance optimization
- Cleaner component code

## Future Enhancements

### Planned Improvements
- **State Persistence**: Local storage integration
- **Optimistic Updates**: UI updates before API confirmation
- **Real-time Updates**: WebSocket integration
- **Offline Support**: Offline-first patterns
- **Cache Management**: Advanced caching strategies

### Hook Composition
- **Higher-order Hooks**: Composing multiple hooks
- **Context Integration**: Global state management
- **Middleware Patterns**: Request/response interceptors
- **DevTools Integration**: Debug and monitoring tools

## Usage Guidelines

### When to Create Custom Hooks
- Complex state logic that's reused
- API integration patterns
- Cross-component state sharing
- Business logic encapsulation

### Best Practices
- Single responsibility per hook
- Clear naming conventions
- Comprehensive error handling
- Proper TypeScript typing
- Performance optimization
- Consistent return patterns