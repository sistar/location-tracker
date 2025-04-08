import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timedelta
import math
import requests
from typing import Dict, Any, Optional, List
import urllib.parse
import os
import time
import uuid

# Let API Gateway handle CORS

# Added delay to respect rate limits (1 request per second max)
RATE_LIMIT_DELAY = 1.1  # seconds

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
geocode_cache_table = dynamodb.Table(os.environ.get("DYNAMODB_GEOCODE_CACHE_TABLE", "gps-tracking-service-dev-geocode-cache"))

# Nominatim configuration
NOMINATIM_USER_AGENT = "location-tracker-app/1.0"  # Required by Nominatim usage policy
NOMINATIM_REVERSE_API = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH_API = "https://nominatim.openstreetmap.org/search"
MAX_ADDRESS_DISTANCE = 1000  # Maximum distance (meters) for a valid address

# Rate limiting 
last_request_time = 0

def throttle_requests():
    """Ensure we don't exceed rate limits"""
    global last_request_time
    current_time = time.time()
    time_since_last_request = current_time - last_request_time
    
    if time_since_last_request < RATE_LIMIT_DELAY:
        sleep_time = RATE_LIMIT_DELAY - time_since_last_request
        time.sleep(sleep_time)
    
    last_request_time = time.time()

def get_address_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Try to get an address from the cache"""
    try:
        response = geocode_cache_table.get_item(Key={"cache_key": cache_key})
        if "Item" in response:
            # Check if cache entry is still valid (30 days)
            cached_item = response["Item"]
            cache_time = datetime.fromisoformat(cached_item["timestamp"])
            if datetime.now() - cache_time < timedelta(days=30):
                return cached_item
    except Exception as e:
        print(f"Cache retrieval error: {str(e)}")
    return None

def save_address_to_cache(cache_key: str, address_data: Dict[str, Any]) -> None:
    """Save an address to the cache"""
    try:
        # Include timestamp for cache expiration
        address_data["cache_key"] = cache_key
        address_data["timestamp"] = datetime.now().isoformat()
        
        geocode_cache_table.put_item(Item=address_data)
    except Exception as e:
        print(f"Cache save error: {str(e)}")

def reverse_geocode(lat: float, lng: float) -> Dict[str, Any]:
    """Get address from coordinates with caching"""
    # Create a cache key from lat/lng
    cache_key = f"rev_{lat:.6f}_{lng:.6f}"
    
    # Check cache first
    cached_result = get_address_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    # Not in cache, make API request
    try:
        # Apply rate limiting
        throttle_requests()
        
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "zoom": 18,  # Building level precision
            "addressdetails": 1
        }
        
        headers = {
            "User-Agent": NOMINATIM_USER_AGENT
        }
        
        response = requests.get(
            NOMINATIM_REVERSE_API,
            params=params,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Format address
            address = "Unknown location"
            if data and "display_name" in data:
                # Process and format the address
                display_name = data["display_name"]
                parts = display_name.split(",")
                
                if len(parts) >= 3:
                    # Typically: street, area/district, city, etc.
                    address = f"{parts[0].strip()}, {parts[1].strip()}, {parts[2].strip()}"
                else:
                    address = display_name
            
            result = {
                "address": address,
                "lat": lat,
                "lng": lng,
                "raw_response": data,
                "operation": "reverse"
            }
            
            # Save to cache
            save_address_to_cache(cache_key, result)
            
            return result
    except Exception as e:
        print(f"Geocoding error: {str(e)}")
    
    # Return minimal info if geocoding fails
    return {
        "address": "Location lookup failed",
        "lat": lat,
        "lng": lng,
        "error": "Geocoding failed",
        "operation": "reverse"
    }

def geocode_search(query: str) -> Dict[str, Any]:
    """Search for an address and get coordinates with caching"""
    # Create a cache key from the query
    cache_key = f"search_{urllib.parse.quote(query.lower())}"
    
    # Check cache first
    cached_result = get_address_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    # Not in cache, make API request
    try:
        # Apply rate limiting
        throttle_requests()
        
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        
        headers = {
            "User-Agent": NOMINATIM_USER_AGENT
        }
        
        response = requests.get(
            NOMINATIM_SEARCH_API,
            params=params,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data and len(data) > 0:
                item = data[0]
                result = {
                    "address": query,
                    "formatted_address": item.get("display_name", query),
                    "lat": float(item["lat"]),
                    "lng": float(item["lon"]),
                    "raw_response": item,
                    "operation": "search"
                }
                
                # Save to cache
                save_address_to_cache(cache_key, result)
                
                return result
    except Exception as e:
        print(f"Address search error: {str(e)}")
    
    # Return failure info
    return {
        "address": query,
        "error": "Address not found",
        "operation": "search"
    }

def validate_address_coordinates(orig_lat: float, orig_lng: float, 
                                new_lat: float, new_lng: float) -> Dict[str, Any]:
    """Validate if the new coordinates are within allowed distance"""
    distance = haversine(orig_lat, orig_lng, new_lat, new_lng)
    
    if distance <= MAX_ADDRESS_DISTANCE:
        return {
            "valid": True,
            "distance": distance
        }
    else:
        return {
            "valid": False,
            "distance": distance,
            "error": f"Address is too far ({int(distance)}m)"
        }

def handler(event, context):
    """
    Handle geocoding requests
    
    This Lambda supports:
    - Reverse geocoding (coordinates to address)
    - Forward geocoding (address to coordinates)
    - Address validation
    """
    # API Gateway will handle OPTIONS requests
        
    try:
        # Get query parameters
        query_params = event.get("queryStringParameters", {}) or {}
        body = {}
        
        # Check if we have a body
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except:
                pass
                
        # Determine operation type
        operation = query_params.get("operation") or body.get("operation", "reverse")
        
        if operation == "reverse":
            # Get coordinates from query params or body
            lat = float(query_params.get("lat") or body.get("lat", 0))
            lng = float(query_params.get("lng") or body.get("lng", 0))
            
            if not lat or not lng:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing lat/lng parameters"})
                }
                
            result = reverse_geocode(lat, lng)
            
        elif operation == "search":
            # Get address query from query params or body
            query = query_params.get("query") or body.get("query", "")
            
            if not query:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing address query parameter"})
                }
                
            result = geocode_search(query)
            
        elif operation == "validate":
            # Validate if new coordinates are within range of original
            orig_lat = float(query_params.get("orig_lat") or body.get("orig_lat", 0))
            orig_lng = float(query_params.get("orig_lng") or body.get("orig_lng", 0))
            new_lat = float(query_params.get("new_lat") or body.get("new_lat", 0))
            new_lng = float(query_params.get("new_lng") or body.get("new_lng", 0))
            
            if not all([orig_lat, orig_lng, new_lat, new_lng]):
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing coordinate parameters"})
                }
                
            result = validate_address_coordinates(orig_lat, orig_lng, new_lat, new_lng)
            
        else:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Unknown operation: {operation}"})
            }
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result, default=decimal_default)
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }