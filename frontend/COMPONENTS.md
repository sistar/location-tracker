# Component Documentation

## Overview

The Location Tracker frontend uses a modular component architecture with reusable React components. Each component is built with TypeScript for type safety and follows React best practices.

## Component Hierarchy

```
App.tsx (Main Container)
├── NavigationHeader
│   ├── NavigationTabs
│   └── VehicleSelector
├── TripsOverviewPanel
│   └── TripCard (multiple)
├── MapView (integrated in App.tsx)
├── SessionInfoPanel (integrated in App.tsx)
├── LogForm
└── Various Panels (integrated in App.tsx)
```

## Components

### Navigation Components

#### NavigationHeader

**Purpose**: Main application header containing navigation and vehicle selection.

**Location**: `src/components/navigation/NavigationHeader.tsx`

**Props**:
```typescript
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
```

**Features**:
- Application title display
- View mode switching tabs
- Vehicle selection dropdown
- Live tracking button
- Loading state indicators

**Usage**:
```tsx
<NavigationHeader
  viewMode={viewMode}
  onViewModeChange={handleViewModeChange}
  selectedVehicle={selectedVehicle}
  availableVehicles={availableVehicles}
  vehiclesLoading={vehiclesLoading}
  routeLoading={routeLoading}
  selectedLog={selectedLog}
  onVehicleChange={handleVehicleChange}
  onRefreshVehicles={fetchVehicles}
  onLiveTrackingClick={handleLiveTrackingClick}
/>
```

#### NavigationTabs

**Purpose**: Tab navigation for switching between view modes.

**Location**: `src/components/navigation/NavigationTabs.tsx`

**Props**:
```typescript
interface NavigationTabsProps {
  viewMode: 'trips' | 'live' | 'timeline';
  onViewModeChange: (mode: 'trips' | 'live' | 'timeline') => void;
  routeLoading: boolean;
  selectedLog: unknown | null;
}
```

**Features**:
- Three view modes: My Trips, Live Tracking, Timeline
- Active state indication
- Loading state display
- Responsive design

#### VehicleSelector

**Purpose**: Dropdown for selecting and managing vehicles.

**Location**: `src/components/navigation/VehicleSelector.tsx`

**Props**:
```typescript
interface VehicleSelectorProps {
  selectedVehicle: string;
  availableVehicles: string[];
  vehiclesLoading: boolean;
  onVehicleChange: (vehicleId: string) => void;
  onRefreshVehicles: () => void;
}
```

**Features**:
- Vehicle selection dropdown
- Refresh button for updating vehicle list
- Loading state handling
- Accessibility support

### Trip Components

#### TripsOverviewPanel

**Purpose**: Main panel displaying a grid of saved trips with management actions.

**Location**: `src/components/trips/TripsOverviewPanel.tsx`

**Props**:
```typescript
interface TripsOverviewPanelProps {
  showTripsOverview: boolean;
  viewMode: string;
  driversLogs: DriversLogEntry[];
  logsLoading: boolean;
  selectedLog: DriversLogEntry | null;
  routeLoading: boolean;
  onFindNewSessions: () => void;
  onRefreshLogs: () => void;
  onTripSelect: (log: DriversLogEntry) => void;
  onTripDeselect: () => void;
}
```

**Features**:
- Conditional rendering based on view mode
- Grid layout for trip cards
- Header with action buttons
- Loading and empty states
- Full-screen overlay positioning

**Layout**:
- Fixed position overlay
- Responsive grid (auto-fill, min 400px columns)
- Scrollable content area
- Action header with buttons

#### TripCard

**Purpose**: Individual trip display card with statistics and actions.

**Location**: `src/components/trips/TripCard.tsx`

**Props**:
```typescript
interface TripCardProps {
  log: DriversLogEntry;
  isSelected: boolean;
  routeLoading: boolean;
  onSelect: (log: DriversLogEntry) => void;
  onDeselect: () => void;
}
```

**Features**:
- Trip date and time display
- Purpose badge with color coding
- Route information (start/end addresses)
- Trip statistics (distance, duration)
- Notes display
- Action buttons (view/close)
- Selection state indication

**Visual Design**:
- Card-style layout with shadow
- Color-coded purpose badges
- Grid layout for statistics
- Hover and selection states
- Responsive design

### Form Components

#### LogForm

**Purpose**: Modal form for saving trips to the driver's log.

**Location**: `src/components/forms/LogForm.tsx`

**Props**:
```typescript
interface LogFormProps {
  showLogForm: boolean;
  sessionInfo: SessionInfo | null;
  selectedLog: DriversLogEntry | null;
  selectedSession: PastSession | null;
  sessionAlreadySaved: boolean;
  logFormData: { purpose: string; notes: string };
  logSaveError: string | null;
  onFormDataChange: (data: { purpose: string; notes: string }) => void;
  onSubmit: (e: FormEvent) => void;
  onCancel: () => void;
}
```

**Features**:
- Purpose selection dropdown
- Notes textarea
- Form validation
- Error display
- Submit and cancel actions
- Conditional rendering based on state

**Form Fields**:
- **Purpose**: Required dropdown (business, commute, personal, delivery, other)
- **Notes**: Optional textarea
- **Actions**: Save and Cancel buttons

## Component Design Patterns

### Prop Interfaces

All components use TypeScript interfaces for props:
```typescript
interface ComponentProps {
  // Required props
  requiredProp: string;
  
  // Optional props
  optionalProp?: boolean;
  
  // Function props
  onAction: (data: SomeType) => void;
  
  // Union types for controlled values
  mode: 'option1' | 'option2' | 'option3';
}
```

### State Management

Components follow these patterns:
- **Controlled Components**: All form inputs are controlled
- **Event Handlers**: Consistent naming (`onAction`, `handleEvent`)
- **Loading States**: Boolean props for loading indicators
- **Error Handling**: Error props passed down from parent

### Styling

Components use inline styles for:
- Rapid development and prototyping
- Component-scoped styling
- Dynamic styling based on props/state

**Style Conventions**:
```typescript
// Consistent spacing and colors
const styles = {
  container: {
    padding: '20px',
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
  },
  
  // Responsive grid layouts
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
    gap: '20px'
  }
};
```

### Accessibility

Components include accessibility features:
- Semantic HTML elements
- ARIA labels where needed
- Keyboard navigation support
- Focus management
- Screen reader friendly text

## Integration with Hooks

Components integrate with custom hooks for state management:

```tsx
// Example: TripsOverviewPanel with hooks
const MyTripsView = () => {
  const { driversLogs, logsLoading, fetchDriversLogs } = useDriversLogs();
  const { selectedLog, setSelectedLog } = useUIState();
  
  return (
    <TripsOverviewPanel
      driversLogs={driversLogs}
      logsLoading={logsLoading}
      selectedLog={selectedLog}
      onTripSelect={setSelectedLog}
      onRefreshLogs={fetchDriversLogs}
      // ... other props
    />
  );
};
```

## Testing Strategy

### Component Testing
- **Props Testing**: Verify component renders with different prop combinations
- **Event Handling**: Test user interactions and callback execution
- **State Changes**: Test visual changes based on state
- **Error States**: Test error display and handling

### Example Test Structure
```typescript
describe('TripCard', () => {
  it('renders trip information correctly', () => {
    // Test basic rendering
  });
  
  it('handles selection state', () => {
    // Test selection/deselection
  });
  
  it('calls onSelect when view button clicked', () => {
    // Test event handling
  });
  
  it('displays loading state correctly', () => {
    // Test loading indicators
  });
});
```

## Performance Considerations

### Optimization Strategies
- **React.memo**: Wrap components to prevent unnecessary re-renders
- **useCallback**: Memoize event handlers passed as props
- **Key Props**: Proper key usage in lists for efficient updates
- **Conditional Rendering**: Only render when needed

### Example Optimizations
```tsx
// Memoized component
export const TripCard = React.memo<TripCardProps>(({ log, onSelect, ... }) => {
  // Component implementation
});

// Memoized callbacks in parent
const handleTripSelect = useCallback((log: DriversLogEntry) => {
  setSelectedLog(log);
}, [setSelectedLog]);
```

## Future Enhancements

### Planned Improvements
- **Component Library Integration**: Material-UI or Chakra UI
- **Animation Library**: Framer Motion for smooth transitions
- **Virtualization**: For large lists of trips
- **Theme Support**: Dark/light mode toggle
- **Mobile Responsiveness**: Enhanced mobile layouts

### Extensibility
- **Compound Components**: For complex UI patterns
- **Render Props**: For flexible component composition
- **Higher-Order Components**: For cross-cutting concerns
- **Context Providers**: For global state management

## Usage Guidelines

### When to Create New Components
- Reusable UI patterns
- Complex logic that can be isolated
- Performance optimization needs
- Testing requirements

### Component Size Guidelines
- Keep components focused on single responsibility
- Split large components (>200 lines) into smaller ones
- Extract complex logic into custom hooks
- Maintain clear prop interfaces

### Naming Conventions
- PascalCase for component names
- Descriptive names indicating purpose
- Consistent prop naming patterns
- Clear event handler naming (`onAction`)

## Migration Status

### Completed Components ✅
- NavigationHeader and sub-components
- TripsOverviewPanel and TripCard
- LogForm

### In Progress 🔄
- Integration into main App.tsx
- Additional panel components
- Map-related components

### Planned 📋
- SessionInfoPanel component
- AddressEditForm component
- Complete App.tsx refactor