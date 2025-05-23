# location-tracker visualize travels and provide a drivers log

The App
- displays gps-locations on the map
- identifies travelling sessions / journeys including short (charging) breaks of up to 60 minutes
- allows user to store a session as a trip and annotate with information (trip purpose, private or business,..)

This is the frontend part

Deployment is achieved by the following commands:
```
npx vite dev
vercel --prod
```

The App can be accessed at [https://location-tracker-frontend-seven.vercel.app/]


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