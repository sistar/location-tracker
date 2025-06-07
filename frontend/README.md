# Location Tracker Frontend

A React TypeScript application for GPS location tracking, trip management, and historical data visualization.

## Overview

The Location Tracker provides:
- Real-time GPS location display on interactive maps
- Automatic travel session detection with intelligent break handling
- Driver's log functionality for trip annotation and management
- Historical data analysis and visualization
- Address geocoding and validation

## Quick Start

### Development
```bash
npm install
npm run dev
```

### Production Deployment
```bash
npm run build
vercel --prod
```

**Live Application**: [https://location-tracker-frontend-seven.vercel.app/](https://location-tracker-frontend-seven.vercel.app/)

## Documentation

### Architecture & Development
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Complete architecture overview and design principles
- **[COMPONENTS.md](./COMPONENTS.md)** - Component library documentation
- **[HOOKS.md](./HOOKS.md)** - Custom hooks and state management
- **[API.md](./API.md)** - Backend API integration guide

### Project Structure
```
src/
├── types/              # TypeScript definitions
├── services/           # API and business logic
├── components/         # Reusable UI components
├── hooks/              # Custom React hooks
└── App.tsx            # Main application
```


## Recent Updates:

### ✅ Enhanced Trip Overview (COMPLETED)
- Added a prominent navigation bar with "My Trips", "Live Tracking", and "Timeline" tabs
- Implemented a comprehensive trip overview as the default view when opening the app
- Created a modern, card-based layout for browsing saved trips with:
  - Trip date and time information
  - Purpose badges (business, personal, commute, etc.)
  - Route information (start/end addresses)
  - Trip statistics (distance, duration)
  - Notes display
  - Direct "View on Map" functionality
- Integrated with existing driver's logs functionality
- Added "Find New Sessions" button to scan for unsaved trips
- **NEW**: Added "All Data" scan option to search through the entire database for unsaved sessions, in addition to the existing time-range options (1 day, 3 days, 7 days, 14 days, 30 days)

### 🚧 Timeline Overview (IN PROGRESS)
- Navigation tab added but functionality not yet implemented
- Will show location data with visual distinction between trips and unassigned data

TODO:
- ~~there is no overview for the annotated trips. As a user when opening the App I would like to have the option to browse through my already annotated trips~~ ✅ **COMPLETED**
- there should be a timeline overview for location data. Data belonging to trips should be visually distinguishable from location data that has not yet been assigned to a trip

Problems:
- Session Detection is not reliable enough. Filtering raw gps data for redundant information (e.g. vehicle not moving) leads to dropping valuable session data
- The logic does not handle lacking data gracefully (during detection of session boundaries). Sometimes GPS fixes lack and there is very sparse data for a part of a trip. This must not lead to a truncated session.