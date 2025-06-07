#!/usr/bin/env python3
"""
Script to run tests with coverage reporting for the location tracker backend.
"""

import subprocess
import sys
import os

def main():
    """Run tests with coverage."""
    # Change to the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Add src to Python path
    src_path = os.path.join(backend_dir, 'src')
    sys.path.insert(0, src_path)
    
    # List of handler files to include in coverage
    handler_files = [
        'src/handlers/processor.py',
        'src/handlers/get_latest_location.py',
        'src/handlers/get_raw_location_history.py',
        'src/handlers/get_dynamic_location_history.py', 
        'src/handlers/get_location_history.py',
        'src/handlers/get_vehicle_ids.py',
        'src/handlers/get_drivers_logs.py',
        'src/handlers/save_drivers_log.py',
        'src/handlers/scan_unsaved_sessions.py',
        'src/handlers/geocode_service.py',
        'src/handlers/gps_processing.py'
    ]
    
    # Filter to only existing files
    existing_files = [f for f in handler_files if os.path.exists(f)]
    
    if not existing_files:
        print("No handler files found for coverage analysis")
        return 1
    
    # Run coverage with the handlers module
    cmd = [
        sys.executable, '-m', 'coverage', 'run',
        '--source=handlers',
        '--omit=*/test*,*/__pycache__/*,*/node_modules/*,handlers/certifi*,handlers/charset_normalizer*,handlers/idna*,handlers/requests*,handlers/urllib3*,handlers/bin/*',
        '-m', 'pytest', 'test/', '-v'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print("Tests failed")
        return result.returncode
    
    # Generate reports
    print("\n" + "="*60)
    print("COVERAGE REPORT")
    print("="*60)
    
    # Terminal report
    subprocess.run([sys.executable, '-m', 'coverage', 'report', '--show-missing'])
    
    # HTML report
    subprocess.run([sys.executable, '-m', 'coverage', 'html'])
    print(f"\nHTML coverage report generated in: {os.path.join(backend_dir, 'htmlcov', 'index.html')}")
    
    # XML report
    subprocess.run([sys.executable, '-m', 'coverage', 'xml'])
    print(f"XML coverage report generated: {os.path.join(backend_dir, 'coverage.xml')}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())