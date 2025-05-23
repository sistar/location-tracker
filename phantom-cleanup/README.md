# Phantom Cleanup Data Analysis

This directory contains Jupyter notebooks and tools for developing and testing GPS data cleaning algorithms used in the location tracker backend.

## Notebooks

### `phantom_cleanup.ipynb`
Main algorithm development notebook for GPS data cleaning and analysis:
- Phantom location detection and removal algorithms
- Session analysis and segmentation logic
- Distance calculations and movement pattern recognition
- Stop classification (moving, stopped, charging)
- Data quality metrics and validation

### `display_raw.ipynb`
Visualization notebook for raw GPS data analysis:
- Reads JSONL files from device SD card (`gps_logs/` directory)
- Creates interactive Folium maps for data visualization
- Displays location tracks and patterns
- Useful for validating data collection and identifying issues

## Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start Jupyter:
   ```bash
   jupyter notebook
   ```

## Data Sources

- **Raw GPS Logs**: JSONL files stored on device SD card, transferred using `mpremote fs cp :/sd/gps_logs TARGET_DIR`
- **Test Data**: Sample location data in `stop_phase_gps_data.json`
- **Production Data**: Can connect to DynamoDB tables for testing algorithms on live data

## Key Features

The algorithms developed here are implemented in the backend handlers:
- **Session Detection**: Time gaps, minimum duration/distance thresholds
- **Phantom Cleanup**: Median position calculation for stationary periods
- **Movement Classification**: Speed analysis, stop detection
- **Data Validation**: GPS accuracy filtering, outlier detection

## Development Workflow

1. Use notebooks to prototype and test algorithms
2. Validate with real GPS data from device logs
3. Implement proven algorithms in backend handlers
4. Use visualizations to verify algorithm effectiveness

## Dependencies

Key packages used:
- **pandas**: Data manipulation and analysis
- **folium**: Interactive map visualizations
- **numpy**: Numerical computations
- **jupyter**: Notebook environment
- **boto3**: AWS DynamoDB integration (when testing live data)

See `requirements.txt` for complete dependency list. 