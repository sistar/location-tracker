#!/bin/bash

# Change to the backend directory
cd "$(dirname "$0")/.."

# Set up Python path to include the src directory
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run pytest with verbose output
python -m pytest test/test_get_raw_location_history.py -v