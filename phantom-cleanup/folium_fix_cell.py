# Fixed create_location_map function for the notebook
# Run this cell to replace the problematic function

def create_location_map_fixed(df, title="Vehicle Location Track"):
    """
    Create an interactive folium map showing the vehicle's route
    Fixed version without problematic tile layers
    """
    if df.empty:
        print("No data to visualize")
        return None
    
    # Calculate map center
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    
    # Create base map with reliable tiles
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Add working tile layers only
    folium.TileLayer('CartoDB positron').add_to(m)
    folium.TileLayer('CartoDB Dark_Matter').add_to(m)
    
    # Route line
    if len(df) > 1:
        coordinates = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        
        # Add the route line
        folium.PolyLine(
            coordinates,
            color='blue',
            weight=3,
            opacity=0.8,
            popup='Vehicle Route'
        ).add_to(m)
    
    # Add markers for key points
    if len(df) > 0:
        # Start point (green)
        start_point = df.iloc[0]
        folium.Marker(
            [start_point['lat'], start_point['lon']],
            popup=f"Start: {start_point['datetime'].strftime('%H:%M:%S')}",
            icon=folium.Icon(color='green', icon='play')
        ).add_to(m)
        
        # End point (red)
        end_point = df.iloc[-1]
        folium.Marker(
            [end_point['lat'], end_point['lon']],
            popup=f"End: {end_point['datetime'].strftime('%H:%M:%S')}",
            icon=folium.Icon(color='red', icon='stop')
        ).add_to(m)
    
    # Add time-based markers
    step = max(1, len(df) // 20)  # Show max 20 markers
    for i in range(0, len(df), step):
        row = df.iloc[i]
        
        # Create popup text
        popup_text = f"""
        Time: {row['datetime'].strftime('%H:%M:%S')}<br>
        Lat: {row['lat']:.6f}<br>
        Lon: {row['lon']:.6f}
        """
        
        if 'speed_kmh' in df.columns:
            popup_text += f"<br>Speed: {row['speed_kmh']:.1f} km/h"
        
        folium.CircleMarker(
            [row['lat'], row['lon']],
            radius=3,
            popup=popup_text,
            color='orange',
            fill=True,
            fillColor='orange',
            fillOpacity=0.7
        ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add title
    title_html = f'<h3 align="center" style="font-size:16px"><b>{title}</b></h3>'
    m.get_root().html.add_child(folium.Element(title_html))
    
    return m

# Replace the original function call
if not df.empty:
    map_title = f"Vehicle {VEHICLE_ID} Track - {TARGET_DATE}"
    location_map = create_location_map_fixed(df, map_title)  # Use the fixed function
    
    if location_map:
        print(f"Interactive map created for {len(df)} location points")
        display(location_map)
else:
    print("No location data available to create map") 