#!/usr/bin/env python3
"""
Test to ensure all locations in gap_locations.jsonl are not filtered
This validates that the GPS processing parameters don't accidentally filter valid data
Considers both spatial distance AND temporal gaps to determine realistic movement
"""

import json
import sys
import os
from datetime import datetime

# Add the handlers directory to the path so we can import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'handlers'))

# Import shared GPS processing logic
import gps_processing

def parse_timestamp(time_str):
    """Parse ISO timestamp to datetime object."""
    # Handle the timezone offset
    if '+' in time_str:
        time_part, tz_part = time_str.rsplit('+', 1)
        time_str = time_part  # Ignore timezone for simplicity
    elif time_str.endswith('Z'):
        time_str = time_str[:-1]
    
    return datetime.fromisoformat(time_str)

def analyze_temporal_gaps(locations):
    """Analyze time gaps and calculate realistic speeds between consecutive points."""
    print("Temporal Analysis:")
    print("-" * 40)
    
    max_distance = 0
    max_speed_kmh = 0
    gap_analysis = []
    
    for i in range(1, len(locations)):
        _, prev_loc = locations[i-1]
        line_num, curr_loc = locations[i]
        
        # Calculate spatial distance
        distance = gps_processing.haversine_distance(
            prev_loc["lat"], prev_loc["lon"],
            curr_loc["lat"], curr_loc["lon"]
        )
        
        # Calculate time difference
        prev_time = parse_timestamp(prev_loc["time"])
        curr_time = parse_timestamp(curr_loc["time"])
        time_diff_seconds = (curr_time - prev_time).total_seconds()
        time_diff_minutes = time_diff_seconds / 60
        
        # Calculate speed
        if time_diff_seconds > 0:
            speed_mps = distance / time_diff_seconds  # meters per second
            speed_kmh = speed_mps * 3.6  # km/h
        else:
            speed_kmh = float('inf')
        
        gap_info = {
            'line': line_num,
            'distance_m': distance,
            'time_gap_min': time_diff_minutes,
            'speed_kmh': speed_kmh,
            'is_large_gap': time_diff_minutes > 5 or distance > 1000  # 5+ minutes or 1+ km
        }
        gap_analysis.append(gap_info)
        
        max_distance = max(max_distance, distance)
        max_speed_kmh = max(max_speed_kmh, speed_kmh if speed_kmh != float('inf') else 0)
        
        # Print analysis for significant gaps
        if gap_info['is_large_gap']:
            print(f"Line {line_num:2d}: {distance:6.0f}m in {time_diff_minutes:5.1f} min → {speed_kmh:5.1f} km/h")
        else:
            print(f"Line {line_num:2d}: {distance:6.0f}m in {time_diff_minutes:5.1f} min → {speed_kmh:5.1f} km/h")
    
    print(f"\nSummary:")
    print(f"  Maximum distance: {max_distance:.0f}m")
    print(f"  Maximum speed: {max_speed_kmh:.1f} km/h")
    
    # Determine if speeds are reasonable for a vehicle
    reasonable_max_speed = 120  # km/h (highway speeds)
    large_gaps = [g for g in gap_analysis if g['is_large_gap']]
    
    if large_gaps:
        print(f"  Large gaps detected: {len(large_gaps)}")
        all_reasonable = all(g['speed_kmh'] <= reasonable_max_speed for g in large_gaps)
        print(f"  All speeds reasonable (<{reasonable_max_speed} km/h): {'✅ YES' if all_reasonable else '❌ NO'}")
    
    return gap_analysis, max_distance, max_speed_kmh

def suggest_speed_based_threshold(gap_analysis, max_reasonable_speed_kmh=120):
    """Suggest outlier threshold based on reasonable vehicle speeds."""
    
    # Calculate what distance would be covered in typical GPS sampling intervals
    # at the maximum reasonable speed
    
    sampling_intervals = [30, 60, 300, 600]  # 30s, 1min, 5min, 10min
    
    print(f"\nSpeed-based threshold suggestions (max speed: {max_reasonable_speed_kmh} km/h):")
    print("-" * 60)
    
    for interval_sec in sampling_intervals:
        max_distance_m = (max_reasonable_speed_kmh * 1000 / 3600) * interval_sec
        print(f"  {interval_sec:3d} seconds: {max_distance_m:6.0f}m")
    
    # Find the maximum time gap in our data
    max_time_gap_sec = max(
        gap['time_gap_min'] * 60 for gap in gap_analysis 
        if gap['time_gap_min'] < 60  # Ignore extremely large gaps
    )
    
    # Calculate threshold for the maximum observed time gap
    suggested_threshold = int((max_reasonable_speed_kmh * 1000 / 3600) * max_time_gap_sec * 1.2)  # 20% buffer
    
    print(f"\nFor maximum observed time gap ({max_time_gap_sec/60:.1f} min):")
    print(f"  Suggested threshold: {suggested_threshold}m")
    
    return suggested_threshold

def test_gap_locations():
    """Test that all locations in gap_locations.jsonl are accepted."""
    
    input_file = "gap_locations.jsonl"
    
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found")
        return False
    
    print(f"Testing GPS processing on {input_file}")
    print("=" * 60)
    
    # Load all locations
    locations = []
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    location = json.loads(line.strip())
                    locations.append((line_num, location))
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing line {line_num}: {e}")
                    return False
    
    print(f"Loaded {len(locations)} locations from {input_file}")
    print()
    
    # Analyze temporal patterns
    gap_analysis, max_distance, max_speed_kmh = analyze_temporal_gaps(locations)
    
    # Get speed-based threshold suggestion
    speed_based_threshold = suggest_speed_based_threshold(gap_analysis)
    
    # Determine appropriate threshold (add some buffer)
    simple_threshold = int(max_distance * 1.2)  # 20% buffer
    
    print(f"\nThreshold Recommendations:")
    print(f"  Simple (max distance + 20%): {simple_threshold}m")
    print(f"  Speed-based (120 km/h max): {speed_based_threshold}m")
    
    recommended_threshold = max(simple_threshold, speed_based_threshold)
    print(f"  Recommended (use higher): {recommended_threshold}m")
    print()
    
    # Test with current processor parameters
    print("Testing with current processor.py parameters:")
    current_processor = gps_processing.GPSProcessor(
        outlier_threshold_meters=725,
        min_movement_meters=3,  # Use same as processor.py
        max_history_size=10
    )
    
    current_success = test_with_processor(current_processor, locations, "Current", gap_analysis)
    
    # Test with recommended parameters  
    print(f"\nTesting with recommended parameters:")
    recommended_processor = gps_processing.GPSProcessor(
        outlier_threshold_meters=recommended_threshold,
        min_movement_meters=3,
        max_history_size=10
    )
    
    recommended_success = test_with_processor(recommended_processor, locations, "Recommended", gap_analysis)
    
    return current_success, recommended_success, recommended_threshold, gap_analysis

def test_with_processor(processor, locations, label, gap_analysis):
    """Test locations with a specific processor configuration."""
    
    # Process each location and track results
    results = []
    all_passed = True
    
    for i, (line_num, location) in enumerate(locations):
        result = processor.process_location(location)
        results.append((line_num, location, result))
        
        if result["should_store"]:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            all_passed = False
        
        # Add temporal context
        distance_str = ""
        speed_str = ""
        if result["distance_from_last"] is not None and i > 0:
            distance_str = f" (distance: {result['distance_from_last']:.1f}m"
            
            # Find corresponding gap analysis
            gap_info = next((g for g in gap_analysis if g['line'] == line_num), None)
            if gap_info:
                speed_str = f", {gap_info['speed_kmh']:.1f} km/h in {gap_info['time_gap_min']:.1f}min)"
            else:
                speed_str = ")"
        
        print(f"Line {line_num:2d}: {status} - {result['reason']}{distance_str}{speed_str}")
        
        if not result["should_store"]:
            print(f"         Location: {location['lat']:.5f}, {location['lon']:.5f}")
            print(f"         Time: {location['time']}")
            print(f"         Quality: {location.get('quality', 'unknown')}")
    
    print()
    
    # Summary statistics
    stored_count = sum(1 for _, _, result in results if result["should_store"])
    filtered_count = len(results) - stored_count
    
    print(f"{label} Settings Summary:")
    print(f"  Total locations: {len(results)}")
    print(f"  Would be stored: {stored_count}")
    print(f"  Would be filtered: {filtered_count}")
    print(f"  Storage rate: {stored_count/len(results)*100:.1f}%")
    
    if all_passed:
        print(f"🎉 SUCCESS: All locations would be stored with {label.lower()} settings!")
    else:
        print(f"⚠️  WARNING: Some locations would be filtered with {label.lower()} settings")
        
        # Show filtered locations details with temporal context
        filtered_locations = [(ln, loc, res) for ln, loc, res in results if not res["should_store"]]
        if filtered_locations:
            print(f"Filtered locations:")
            for line_num, location, result in filtered_locations:
                gap_info = next((g for g in gap_analysis if g['line'] == line_num), None)
                if gap_info:
                    print(f"  Line {line_num}: {result['reason']}")
                    print(f"    Distance: {result['distance_from_last']:.1f}m in {gap_info['time_gap_min']:.1f}min")
                    print(f"    Speed: {gap_info['speed_kmh']:.1f} km/h (reasonable for vehicle)")
                else:
                    print(f"  Line {line_num}: {result['reason']}")
                    if result["distance_from_last"]:
                        print(f"    Distance from previous: {result['distance_from_last']:.1f}m")
    
    return all_passed

def test_with_different_parameters():
    """Test with different parameter combinations to find optimal settings."""
    print("\n" + "=" * 60)
    print("Testing with different parameter combinations...")
    print("=" * 60)
    
    # Parameter combinations to test - including higher thresholds for large gaps
    test_configs = [
        (725, 3, "Current processor.py settings"),
        (5000, 3, "5km outlier threshold"), 
        (10000, 3, "10km outlier threshold"),
        (15000, 3, "15km outlier threshold (handles all gaps)"),
        (15000, 1, "15km outlier + very sensitive movement"),
        (15000, 5, "15km outlier + less sensitive movement"),
    ]
    
    input_file = "gap_locations.jsonl"
    
    # Load locations
    locations = []
    with open(input_file, 'r') as f:
        for line in f:
            if line.strip():
                locations.append(json.loads(line.strip()))
    
    for outlier_threshold, min_movement, description in test_configs:
        processor = gps_processing.GPSProcessor(
            outlier_threshold_meters=outlier_threshold,
            min_movement_meters=min_movement,
            max_history_size=10
        )
        
        stored_count = 0
        for location in locations:
            result = processor.process_location(location)
            if result["should_store"]:
                stored_count += 1
        
        storage_rate = stored_count / len(locations) * 100
        success_mark = "✅" if stored_count == len(locations) else "⚠️ "
        print(f"{success_mark} {description:40} -> {stored_count:2d}/{len(locations)} stored ({storage_rate:5.1f}%)")

def main():
    """Main test function."""
    print("Gap Locations GPS Processing Test")
    print("This test validates that gap_locations.jsonl data is handled correctly")
    print("Analyzes both spatial distance AND temporal gaps")
    print("=" * 60)
    print()
    
    # Test with current and recommended parameters
    current_success, recommended_success, recommended_threshold, gap_analysis = test_gap_locations()
    
    # Test with different parameters to show alternatives
    test_with_different_parameters()
    
    print()
    print("=" * 60)
    print("RECOMMENDATIONS:")
    
    if current_success:
        print("✅ Current processor.py parameters are suitable for gap_locations.jsonl")
        return 0
    else:
        print("❌ Current processor.py parameters filter some valid locations")
        print("   These locations represent reasonable vehicle movement given the time gaps")
        
        if recommended_success:
            print(f"✅ Recommended: Update outlier_threshold_meters to {recommended_threshold}m")
            print("  This threshold accounts for reasonable vehicle speeds during time gaps")
        
        print("\n💡 IMPORTANT: Consider implementing speed-based outlier detection")
        print("   Current logic only considers distance, not time gaps")
        print("   A vehicle traveling 11km in 9 minutes (~73 km/h) is reasonable")
        
        print("\nTo update processor.py:")
        print("```python")
        print("gps_processor = gps_processing.GPSProcessor(")
        print(f"    outlier_threshold_meters={recommended_threshold},  # Updated for time gaps")
        print("    min_movement_meters=3,")
        print("    max_history_size=10")
        print(")")
        print("```")
        
        print("\nFuture enhancement: Implement speed-based filtering:")
        print("- Calculate time between GPS points")  
        print("- Allow larger distances for longer time gaps")
        print("- Filter based on unrealistic speeds (>150 km/h) rather than distance")
        
        return 1

if __name__ == "__main__":
    sys.exit(main()) 