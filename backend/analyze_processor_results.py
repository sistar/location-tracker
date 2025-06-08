#!/usr/bin/env python3
"""
Analyze the results from processor test
"""

import json


def analyze_results(filename="processor_test_results.jsonl"):
    """Analyze the processor test results."""
    
    stats = {
        "total": 0,
        "stored": 0,
        "outlier_filtered": 0,
        "no_significant_movement": 0,
        "errors": 0
    }
    
    stored_items = []
    distance_stats = []
    
    print(f"Analyzing results from: {filename}")
    print("=" * 50)
    
    with open(filename, 'r') as f:
        for line in f:
            data = json.loads(line)
            stats["total"] += 1
            
            result_type = data["processing_result"]
            if result_type == "stored":
                stats["stored"] += 1
                stored_items.append(data)
                if data["distance_from_last"] is not None:
                    distance_stats.append(data["distance_from_last"])
            elif result_type == "outlier_filtered":
                stats["outlier_filtered"] += 1
            elif result_type == "no_significant_movement":
                stats["no_significant_movement"] += 1
            elif result_type == "error":
                stats["errors"] += 1
    
    # Print basic statistics
    print(f"Processing Results:")
    print(f"  Total records: {stats['total']}")
    print(f"  Stored: {stats['stored']} ({stats['stored']/stats['total']*100:.1f}%)")
    print(f"  Outlier filtered: {stats['outlier_filtered']} ({stats['outlier_filtered']/stats['total']*100:.1f}%)")
    print(f"  No significant movement: {stats['no_significant_movement']} ({stats['no_significant_movement']/stats['total']*100:.1f}%)")
    print(f"  Errors: {stats['errors']} ({stats['errors']/stats['total']*100:.1f}%)")
    
    # Distance analysis
    if distance_stats:
        print(f"\nDistance Analysis (meters):")
        print(f"  Average distance between stored points: {sum(distance_stats)/len(distance_stats):.1f}m")
        print(f"  Min distance: {min(distance_stats):.1f}m")
        print(f"  Max distance: {max(distance_stats):.1f}m")
        
        # Count distances > 1000m (potential jumps)
        large_jumps = [d for d in distance_stats if d > 1000]
        print(f"  Large jumps (>1km): {len(large_jumps)}")
        if large_jumps:
            print(f"    Average large jump: {sum(large_jumps)/len(large_jumps):.1f}m")
    
    # Quality analysis
    if stored_items:
        qualities = [item["input"]["quality"] for item in stored_items]
        quality_counts = {}
        for q in qualities:
            quality_counts[q] = quality_counts.get(q, 0) + 1
        
        print(f"\nQuality Distribution (stored items):")
        for quality, count in sorted(quality_counts.items()):
            print(f"  Quality {quality}: {count} items ({count/len(stored_items)*100:.1f}%)")
    
    # Time range analysis
    if stored_items:
        times = [item["input"]["timestamp"] for item in stored_items]
        duration_seconds = max(times) - min(times)
        duration_hours = duration_seconds / 3600
        
        print(f"\nTime Analysis:")
        print(f"  Time range: {duration_hours:.1f} hours")
        print(f"  Average time between stored points: {duration_seconds/len(stored_items):.1f} seconds")
        
    # Output sample of processed items
    print(f"\nSample of processed items that would be stored:")
    print("-" * 50)
    for i, item in enumerate(stored_items[:3]):
        processed = item["processed_item"]
        print(f"Item {i+1}:")
        print(f"  Device: {processed['id']}")
        print(f"  Time: {processed['timestamp_iso']}")
        print(f"  Location: {processed['lat']:.5f}, {processed['lon']:.5f}")
        print(f"  Quality: {processed['quality']}")
        print(f"  Distance from last: {item['distance_from_last']:.1f}m" if item['distance_from_last'] else "  First point")
        print()

if __name__ == "__main__":
    analyze_results() 