#!/usr/bin/env python3
"""
Test different parameter combinations for GPS processing
"""

import os
import subprocess
import sys


def test_parameters(outlier_threshold, min_movement, description=""):
    """Test a specific parameter combination."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Outlier threshold: {outlier_threshold}m")
    print(f"Min movement: {min_movement}m")
    print(f"{'='*60}")
    
    # Modify the test script parameters temporarily
    test_script = "test_processor_offline.py"
    backup_script = "test_processor_offline.py.backup"
    
    # Read the current script
    with open(test_script, 'r') as f:
        content = f.read()
    
    # Backup the original
    with open(backup_script, 'w') as f:
        f.write(content)
    
    try:
        # Modify parameters
        modified_content = content.replace(
            "OUTLIER_THRESHOLD_METERS = 725",
            f"OUTLIER_THRESHOLD_METERS = {outlier_threshold}"
        ).replace(
            "MIN_MOVEMENT_METERS = 10",
            f"MIN_MOVEMENT_METERS = {min_movement}"
        )
        
        # Write modified script
        with open(test_script, 'w') as f:
            f.write(modified_content)
        
        # Run the test
        result = subprocess.run([sys.executable, test_script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            # Extract statistics from output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Storage rate:' in line:
                    print(f"Result: {line.strip()}")
                    break
        else:
            print(f"Error: {result.stderr}")
            
    finally:
        # Restore original script
        with open(backup_script, 'r') as f:
            original_content = f.read()
        with open(test_script, 'w') as f:
            f.write(original_content)
        os.remove(backup_script)

def main():
    """Test various parameter combinations."""
    print("GPS Processing Parameter Testing")
    print("=" * 60)
    
    # Different parameter combinations to test
    test_cases = [
        (100, 10, "Conservative filtering (original processor.py)"),
        (500, 10, "Moderate outlier threshold"),
        (725, 10, "Current test setting"),
        (1000, 10, "Lenient outlier threshold"),
        (725, 5, "Current outlier + sensitive movement"),
        (725, 20, "Current outlier + less sensitive movement"),
        (100, 5, "Conservative outlier + sensitive movement"),
        (2000, 10, "Very lenient outlier threshold"),
    ]
    
    for outlier_threshold, min_movement, description in test_cases:
        test_parameters(outlier_threshold, min_movement, description)
    
    print(f"\n{'='*60}")
    print("Parameter testing complete!")
    print("You can now choose the best parameters and update:")
    print("1. test_processor_offline.py (for testing)")
    print("2. processor.py (for production)")
    print("3. Or adjust gps_processing.py defaults")

if __name__ == "__main__":
    main() 