#!/usr/bin/env python3
"""
Offline test for processor.py logic
Processes GPS data from JSONL file through processor logic without DynamoDB dependency
"""

import json
import datetime
import sys
import os

# Add the handlers directory to the path so we can import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'handlers'))

# Import shared GPS processing logic
import gps_processing

# Input and output file paths
INPUT_FILE = "/Users/ralf.sigmund/GitHub/mp_m5_fahrtenbuch/gps_logs/gps_logs/2025-04-22_locations.jsonl"
OUTPUT_FILE = "processor_test_results.jsonl"

def process_single_location_offline(location_data, output_file, processor):
    """Process a single location data point (offline version without DynamoDB)."""
    try:
        # Use the shared GPS processor
        processing_result = processor.process_location(location_data)
        
        # Prepare the result record
        result = {
            "input": location_data,
            "processed_at": datetime.datetime.now().isoformat(),
            "processing_result": "stored" if processing_result["should_store"] else "filtered",
            "stored": processing_result["should_store"],
            "reason": processing_result["reason"],
            "distance_from_last": processing_result["distance_from_last"]
        }
        
        # Add processed item if it would be stored
        if processing_result["should_store"]:
            result["processed_item"] = processing_result["processed_item"]
            result["processing_result"] = "stored"
        else:
            # Determine specific filter reason
            if "outlier" in processing_result["reason"].lower():
                result["processing_result"] = "outlier_filtered"
            else:
                result["processing_result"] = "no_significant_movement"

        output_file.write(json.dumps(result) + '\n')
        return result

    except Exception as e:
        result = {
            "input": location_data,
            "processed_at": datetime.datetime.now().isoformat(),
            "processing_result": "error",
            "stored": False,
            "reason": f"Processing error: {str(e)}",
            "distance_from_last": None
        }
        output_file.write(json.dumps(result) + '\n')
        return result

def main():
    """Main function to process the GPS log file."""
    
    # Configurable parameters - you can adjust these to test different settings
    OUTLIER_THRESHOLD_METERS = 725  # Distance threshold for outlier detection
    MIN_MOVEMENT_METERS = 10        # Minimum movement to consider significant
    MAX_HISTORY_SIZE = 10          # Number of locations to keep in history
    
    print(f"Processing GPS data from: {INPUT_FILE}")
    print(f"Output will be written to: {OUTPUT_FILE}")
    print(f"Configuration:")
    print(f"  Outlier threshold: {OUTLIER_THRESHOLD_METERS}m")
    print(f"  Min movement: {MIN_MOVEMENT_METERS}m")
    print(f"  History size: {MAX_HISTORY_SIZE}")
    print()
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file {INPUT_FILE} does not exist")
        return 1
    
    # Create GPS processor with configurable parameters
    processor = gps_processing.GPSProcessor(
        outlier_threshold_meters=OUTLIER_THRESHOLD_METERS,
        min_movement_meters=MIN_MOVEMENT_METERS,
        max_history_size=MAX_HISTORY_SIZE
    )
    
    # Statistics
    stats = {
        "total_processed": 0,
        "stored": 0,
        "outliers_filtered": 0,
        "no_significant_movement": 0,
        "errors": 0
    }
    
    try:
        with open(INPUT_FILE, 'r') as input_file, open(OUTPUT_FILE, 'w') as output_file:
            print("Starting processing...")
            
            for line_num, line in enumerate(input_file, 1):
                try:
                    # Parse JSON line
                    location_data = json.loads(line.strip())
                    
                    # Process the location
                    result = process_single_location_offline(location_data, output_file, processor)
                    
                    # Update statistics
                    stats["total_processed"] += 1
                    if result["processing_result"] == "stored":
                        stats["stored"] += 1
                    elif result["processing_result"] == "outlier_filtered":
                        stats["outliers_filtered"] += 1
                    elif result["processing_result"] == "no_significant_movement":
                        stats["no_significant_movement"] += 1
                    elif result["processing_result"] == "error":
                        stats["errors"] += 1
                    
                    # Progress indicator
                    if line_num % 100 == 0:
                        print(f"Processed {line_num} lines...")
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    stats["errors"] += 1
                    continue
                    
        print(f"\nProcessing complete!")
        print(f"Results written to: {OUTPUT_FILE}")
        print(f"\nStatistics:")
        print(f"  Total processed: {stats['total_processed']}")
        print(f"  Stored: {stats['stored']}")
        print(f"  Filtered (no movement): {stats['no_significant_movement']}")
        print(f"  Filtered (outliers): {stats['outliers_filtered']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Storage rate: {stats['stored']/stats['total_processed']*100:.1f}%")
        
        return 0
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 