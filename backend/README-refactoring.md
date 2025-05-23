# GPS Processing Refactoring

## Problem Solved

Previously, GPS processing logic was duplicated between:
- `processor.py` (production handler)
- `test_processor_offline.py` (testing script)

This led to manual synchronization issues when tuning parameters like `threshold_meters`.

## Solution

### Shared Module: `gps_processing.py`

Created a shared module containing:
- **Common functions**: `haversine_distance()`, `is_outlier()`, `is_significant_movement()`
- **Utility functions**: `prepare_processed_item()`, `to_decimal_safe()`, `process_elevation()`
- **GPSProcessor class**: Configurable processor with state management

### Refactored Files

1. **`processor.py`**: Now imports shared logic, 52 lines removed
2. **`test_processor_offline.py`**: Uses shared module, easier parameter configuration
3. **`analyze_processor_results.py`**: Analysis script for test results
4. **`test_parameters.py`**: Automated testing of different parameter combinations

## Configuration

Parameters are now centrally configurable:

```python
processor = GPSProcessor(
    outlier_threshold_meters=725,  # Distance threshold for outlier detection
    min_movement_meters=10,        # Minimum movement to store location
    max_history_size=10           # Number of locations in history buffer
)
```

## Usage

### Testing Different Parameters

```bash
# Edit parameters in test_processor_offline.py
python3 test_processor_offline.py

# Or use automated testing
python3 test_parameters.py
```

### Updating Production

Once you find optimal parameters through testing:

1. Update the parameters in `processor.py`:
   ```python
   gps_processor = gps_processing.GPSProcessor(
       outlier_threshold_meters=YOUR_OPTIMAL_VALUE,
       min_movement_meters=YOUR_OPTIMAL_VALUE,
       max_history_size=10
   )
   ```

2. Deploy with `serverless deploy`

## Benefits

- ✅ **No Code Duplication**: Single source of truth for GPS logic
- ✅ **Easy Parameter Tuning**: Change once, affects both test and production
- ✅ **Maintainable**: Bug fixes apply to both test and production
- ✅ **Testable**: Comprehensive offline testing before deployment
- ✅ **Configurable**: Easy A/B testing of different filtering strategies

## Testing Results

Recent test with 725m outlier threshold on 2329 GPS points:
- **73.2% stored** (vs 4.6% with 100m threshold)
- **0.6% outliers filtered** (vs 69.3% with 100m)
- **Average 17.6 seconds** between stored points
- **375.9m average distance** between stored points

This shows the significant impact of parameter tuning on data retention! 