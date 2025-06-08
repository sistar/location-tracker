#!/usr/bin/env python3
"""
Script to run tests with coverage reporting for the location tracker backend.
"""

import subprocess
import sys


def main():
    """Run tests with coverage using poetry."""
    
    # Run pytest with coverage using poetry
    cmd = [
        'poetry', 'run', 'pytest', 
        '--cov=src/handlers',
        '--cov-report=term-missing',
        '--cov-report=html',
        '--cov-report=xml',
        '-v'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print("Tests failed")
        return result.returncode
    
    print("\nCoverage reports generated:")
    print("- HTML: htmlcov/index.html")
    print("- XML: coverage.xml")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())