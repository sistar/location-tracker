#!/usr/bin/env python3
"""
Test to demonstrate the improvement from temporal-aware outlier detection
Shows how the same GPS data is handled differently with and without time consideration
"""

import json
import sys
import os

# Add the handlers directory to the path so we can import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'handlers'))

import gps_processing

def test_temporal_vs_distance_based():
    """Test the difference between temporal and distance-based outlier detection."""
    
    print("Temporal vs Distance-Based Outlier Detection Test")
    print("=" * 60)
    
    # Sample data: vehicle traveling from point A to point B with time gap
    locations = [
        {
            "lat": 41.82243, 
            "lon": 2.763198, 
            "time": "2025-04-22T14:42:48+02:00",
            "device_id": "vehicle_01"
        },
        {
            "lat": 41.91968, 
            "lon": 2.792471, 
            "time": "2025-04-22T14:51:00+02:00",  # 8.2 minutes later
            "device_id": "vehicle_01"
        }
    ]
    
    distance = gps_processing.haversine_distance(
        locations[0]["lat"], locations[0]["lon"],
        locations[1]["lat"], locations[1]["lon"]
    )
    
    # Calculate time gap and speed
    time1 = gps_processing.parse_timestamp(locations[0]["time"])
    time2 = gps_processing.parse_timestamp(locations[1]["time"])
    time_gap_minutes = (time2 - time1).total_seconds() / 60
    speed_kmh = gps_processing.calculate_speed_kmh(distance, (time2 - time1).total_seconds())
    
    print(f"Test scenario:")
    print(f"  Distance: {distance:.0f}m")
    print(f"  Time gap: {time_gap_minutes:.1f} minutes")
    print(f"  Speed: {speed_kmh:.1f} km/h")
    print()
    
    # Test old distance-based logic
    print("1. Old Distance-Based Detection (threshold: 725m):")
    gps_processing.reset_location_history()
    gps_processing.add_to_location_history(locations[0])
    
    # Simulate old logic
    old_is_outlier = distance > 725
    print(f"   Result: {'❌ OUTLIER' if old_is_outlier else '✅ VALID'}")
    print(f"   Reason: Distance {distance:.0f}m > 725m threshold")
    print()
    
    # Test new temporal-aware logic
    print("2. New Temporal-Aware Detection (max speed: 150 km/h):")
    is_outlier_result, reason = gps_processing.is_outlier_temporal(
        locations[1], 
        threshold_meters=725,
        max_speed_kmh=150
    )
    print(f"   Result: {'❌ OUTLIER' if is_outlier_result else '✅ VALID'}")
    print(f"   Reason: {reason}")
    print()
    
    # Test with different speed limits
    print("3. Testing with different speed limits:")
    speed_limits = [50, 80, 120, 150, 200]
    for limit in speed_limits:
        is_outlier_result, reason = gps_processing.is_outlier_temporal(
            locations[1], 
            threshold_meters=725,
            max_speed_kmh=limit
        )
        status = '❌ OUTLIER' if is_outlier_result else '✅ VALID'
        print(f"   {limit:3d} km/h limit: {status}")
    
    print()
    return not is_outlier_result  # Return True if the new system correctly accepts it

def test_edge_cases():
    """Test edge cases for temporal outlier detection."""
    
    print("Edge Cases Test")
    print("=" * 40)
    
    # Test cases: [distance_m, time_gap_min, expected_speed_kmh, should_be_valid]
    test_cases = [
        (1000, 1, 60, True, "City driving"),
        (5000, 3, 100, True, "Highway driving"),
        (20000, 10, 120, True, "Long highway stretch"),
        (50000, 10, 300, False, "Unrealistic speed"),
        (1000, 0.5, 120, True, "Short burst"),
        (10000, 0.5, 1200, False, "Teleportation"),
    ]
    
    base_location = {
        "lat": 41.8, 
        "lon": 2.7, 
        "time": "2025-04-22T14:00:00+02:00",
        "device_id": "vehicle_01"
    }
    
    all_passed = True
    
    for i, (distance_m, time_gap_min, expected_speed, should_be_valid, description) in enumerate(test_cases, 1):
        # Create second location
        # Approximate lat/lon change (rough calculation)
        lat_change = distance_m / 111000  # Roughly 111km per degree latitude
        
        from datetime import datetime, timedelta
        base_time = gps_processing.parse_timestamp(base_location["time"])
        new_time = base_time + timedelta(minutes=time_gap_min)
        
        new_location = {
            "lat": base_location["lat"] + lat_change,
            "lon": base_location["lon"],
            "time": new_time.isoformat(),
            "device_id": "vehicle_01"
        }
        
        # Reset and test
        gps_processing.reset_location_history()
        gps_processing.add_to_location_history(base_location)
        
        is_outlier_result, reason = gps_processing.is_outlier_temporal(
            new_location, 
            threshold_meters=1000,
            max_speed_kmh=150
        )
        
        actual_valid = not is_outlier_result
        test_passed = actual_valid == should_be_valid
        
        if not test_passed:
            all_passed = False
        
        status = "✅ PASS" if test_passed else "❌ FAIL"
        result = "VALID" if actual_valid else "OUTLIER"
        
        print(f"   Test {i}: {status} - {description}")
        print(f"     {distance_m}m in {time_gap_min:.1f}min → {result}")
        print(f"     Expected: {'VALID' if should_be_valid else 'OUTLIER'}, Got: {result}")
    
    return all_passed

def main():
    """Main test function."""
    print("Testing Enhanced GPS Processing with Temporal Awareness")
    print("=" * 60)
    print()
    
    # Test main scenario
    scenario_passed = test_temporal_vs_distance_based()
    
    print()
    
    # Test edge cases
    edge_cases_passed = test_edge_cases()
    
    print()
    print("=" * 60)
    print("SUMMARY:")
    
    if scenario_passed and edge_cases_passed:
        print("✅ All tests PASSED!")
        print("✅ Temporal-aware outlier detection is working correctly")
        print("✅ Gap locations are now properly handled")
        print()
        print("Benefits of temporal-aware detection:")
        print("  • Considers realistic vehicle speeds")
        print("  • Allows large distances over long time gaps")
        print("  • Filters true outliers (unrealistic speeds)")
        print("  • No more false positives from valid long-distance travel")
        return 0
    else:
        print("❌ Some tests FAILED")
        print("⚠️  Temporal-aware detection may need adjustment")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 