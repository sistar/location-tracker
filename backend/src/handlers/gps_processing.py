"""
Shared GPS processing logic module
Contains common functions for GPS data filtering and validation
"""

import math
from datetime import datetime
from typing import Any, Dict, List

# Global state for location history tracking
location_history: List[Dict[str, Any]] = []


def reset_location_history():
    """Reset the location history."""
    global location_history
    location_history = []


def get_location_history():
    """Get the current location history."""
    global location_history
    return location_history


def parse_timestamp(time_str: str) -> datetime:
    """Parse ISO timestamp to datetime object."""
    # Handle the timezone offset
    if "+" in time_str:
        time_part, tz_part = time_str.rsplit("+", 1)
        time_str = time_part  # Ignore timezone for simplicity
    elif time_str.endswith("Z"):
        time_str = time_str[:-1]

    return datetime.fromisoformat(time_str)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance between two GPS coordinates in meters."""
    R = 6371000  # Earth radius in meters

    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance


def calculate_speed_kmh(distance_meters: float, time_diff_seconds: float) -> float:
    """Calculate speed in km/h given distance and time difference."""
    if time_diff_seconds <= 0:
        return float("inf")

    speed_mps = distance_meters / time_diff_seconds  # meters per second
    speed_kmh = speed_mps * 3.6  # convert to km/h
    return speed_kmh


def is_outlier_temporal(
    location: Dict[str, Any], threshold_meters: float = 100, max_speed_kmh: float = 150
) -> tuple[bool, str]:
    """
    Determine if a location is an outlier based on both distance and realistic vehicle speeds.
    Returns True if the location is likely an outlier.

    Args:
        location: GPS location data with 'lat', 'lon', and 'time' keys
        threshold_meters: Distance threshold in meters (fallback for missing timestamps)
        max_speed_kmh: Maximum reasonable speed in km/h (default: 150 km/h)

    Returns:
        Tuple of (is_outlier: bool, reason: str)
    """
    global location_history

    if len(location_history) < 1:
        return False, "Insufficient history"

    # Get the most recent location for temporal comparison
    recent_location = location_history[-1]

    # Calculate distance from most recent location
    distance = haversine_distance(
        recent_location["lat"], recent_location["lon"], location["lat"], location["lon"]
    )

    # Try to get timestamps for temporal analysis
    try:
        if "time" in location and "time" in recent_location:
            curr_time = parse_timestamp(location["time"])
            prev_time = parse_timestamp(recent_location["time"])
            time_diff_seconds = (curr_time - prev_time).total_seconds()

            if time_diff_seconds > 0:
                # Calculate implied speed
                speed_kmh = calculate_speed_kmh(distance, time_diff_seconds)

                # Check if speed is unrealistic
                if speed_kmh > max_speed_kmh:
                    return (
                        True,
                        f"Unrealistic speed: {speed_kmh:.1f} km/h (max: {max_speed_kmh} km/h)",
                    )

                # For very short time gaps, still use distance threshold
                if time_diff_seconds < 10:  # Less than 10 seconds
                    if distance > threshold_meters:
                        return (
                            True,
                            f"Large distance in short time: {distance:.1f}m in {time_diff_seconds:.1f}s",
                        )

                # Speed is reasonable, not an outlier
                return (
                    False,
                    f"Reasonable movement: {distance:.1f}m in {time_diff_seconds/60:.1f}min ({speed_kmh:.1f} km/h)",
                )
            else:
                # Same timestamp or negative time diff - use distance only
                if distance > threshold_meters:
                    return (
                        True,
                        f"Distance threshold exceeded: {distance:.1f}m (same timestamp)",
                    )
                return False, "Same timestamp, distance OK"
        else:
            # No timestamps available, fall back to distance-based detection
            if distance > threshold_meters:
                return (
                    True,
                    f"Distance threshold exceeded: {distance:.1f}m (no timestamp)",
                )
            return False, "Distance within threshold"

    except Exception as e:
        # Error parsing timestamps, fall back to distance-based detection
        if distance > threshold_meters:
            return (
                True,
                f"Distance threshold exceeded: {distance:.1f}m (timestamp error)",
            )
        return False, "Distance within threshold"


def is_outlier(location: Dict[str, Any], threshold_meters: float = 100) -> bool:
    """
    Legacy outlier detection function for backward compatibility.
    Now uses temporal-aware detection internally.
    """
    is_outlier_result, _ = is_outlier_temporal(location, threshold_meters)
    return is_outlier_result


def is_significant_movement(
    new_loc: Dict[str, Any], previous_loc: Dict[str, Any], min_distance: float = 10
) -> bool:
    """
    Determine if there's significant movement (more than min_distance meters).

    Args:
        new_loc: Current GPS location data
        previous_loc: Previous valid GPS location data
        min_distance: Minimum distance threshold in meters (default: 10)

    Returns:
        True if movement is significant enough to store
    """
    if not previous_loc:
        return True

    distance = haversine_distance(
        previous_loc["lat"], previous_loc["lon"], new_loc["lat"], new_loc["lon"]
    )

    return distance >= min_distance


def add_to_location_history(location: Dict[str, Any], max_history: int = 10):
    """
    Add a location to the history buffer for outlier detection.

    Args:
        location: GPS location data
        max_history: Maximum number of locations to keep in history
    """
    global location_history
    location_history.append(location)
    if len(location_history) > max_history:
        location_history.pop(0)


def to_decimal_safe(value):
    """
    Safely convert values to float (for JSON serialization).

    Args:
        value: Value to convert

    Returns:
        Float value or None if conversion fails
    """
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return None


def process_elevation(elevation_value):
    """
    Process elevation value, removing 'M' suffix if present.

    Args:
        elevation_value: Raw elevation value

    Returns:
        Processed elevation as string
    """
    elevation_str = str(elevation_value) if elevation_value is not None else "0"
    if "M" in elevation_str:
        elevation_str = elevation_str.replace("M", "")
    return elevation_str


def prepare_processed_item(location_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare a location data item for storage, applying standard transformations.

    Args:
        location_data: Raw GPS location data

    Returns:
        Processed item ready for storage
    """
    import datetime

    timestamp_iso = location_data.get("time", datetime.datetime.now().isoformat())
    elevation_processed = process_elevation(location_data.get("ele", 0))

    item = {
        "id": location_data.get("device_id", "unknown_device"),
        "timestamp_iso": timestamp_iso,
        "timestamp": to_decimal_safe(location_data.get("timestamp")),
        "lat": to_decimal_safe(location_data["lat"]),
        "lon": to_decimal_safe(location_data["lon"]),
        "ele": to_decimal_safe(elevation_processed),
        "quality": location_data.get("quality", "unknown"),
        "processed_at": datetime.datetime.now().isoformat(),
        "cog": to_decimal_safe(location_data.get("cog")),
        "sog": to_decimal_safe(location_data.get("sog")),
        "satellites_used": to_decimal_safe(location_data.get("satellites_used")),
    }

    # Remove None values from item
    return {k: v for k, v in item.items() if v is not None}


class GPSProcessor:
    """
    GPS processing class that maintains state and allows parameter configuration.
    """

    def __init__(
        self,
        outlier_threshold_meters: float = 100,
        min_movement_meters: float = 10,
        max_history_size: int = 10,
        max_speed_kmh: float = 150,
    ):
        """
        Initialize GPS processor with configurable parameters.

        Args:
            outlier_threshold_meters: Distance threshold for outlier detection (fallback)
            min_movement_meters: Minimum movement to consider significant
            max_history_size: Maximum locations to keep in history
            max_speed_kmh: Maximum reasonable speed in km/h for outlier detection
        """
        self.outlier_threshold = outlier_threshold_meters
        self.min_movement = min_movement_meters
        self.max_history = max_history_size
        self.max_speed_kmh = max_speed_kmh
        self.last_valid_location = None
        reset_location_history()

    def should_store_location(self, location_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Determine if a location should be stored based on filtering rules.
        Uses temporal-aware outlier detection.

        Args:
            location_data: GPS location data

        Returns:
            Tuple of (should_store: bool, reason: str)
        """
        # Add to history for outlier detection
        add_to_location_history(location_data, self.max_history)

        # Check if outlier using temporal-aware detection
        is_outlier_result, outlier_reason = is_outlier_temporal(
            location_data, self.outlier_threshold, self.max_speed_kmh
        )

        if is_outlier_result:
            return False, f"Location identified as outlier: {outlier_reason}"

        # Check for significant movement
        if self.last_valid_location and not is_significant_movement(
            location_data, self.last_valid_location, self.min_movement
        ):
            return False, "Movement less than minimum threshold"

        return True, "Valid location with significant movement"

    def process_location(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a location and return processing result.

        Args:
            location_data: GPS location data

        Returns:
            Processing result with decision and processed item if stored
        """
        should_store, reason = self.should_store_location(location_data)

        result = {
            "should_store": should_store,
            "reason": reason,
            "distance_from_last": None,
            "speed_kmh": None,
            "time_gap_minutes": None,
        }

        # Calculate distance and speed from last valid location
        if self.last_valid_location:
            result["distance_from_last"] = haversine_distance(
                self.last_valid_location["lat"],
                self.last_valid_location["lon"],
                location_data["lat"],
                location_data["lon"],
            )

            # Try to calculate speed and time gap
            try:
                if "time" in location_data and "time" in self.last_valid_location:
                    curr_time = parse_timestamp(location_data["time"])
                    prev_time = parse_timestamp(self.last_valid_location["time"])
                    time_diff_seconds = (curr_time - prev_time).total_seconds()

                    if time_diff_seconds > 0:
                        result["time_gap_minutes"] = time_diff_seconds / 60
                        result["speed_kmh"] = calculate_speed_kmh(
                            result["distance_from_last"], time_diff_seconds
                        )
            except Exception:
                # Ignore timestamp parsing errors
                pass

        if should_store:
            result["processed_item"] = prepare_processed_item(location_data)
            self.last_valid_location = location_data.copy()

        return result
