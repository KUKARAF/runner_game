# dawarich.py
import requests
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from settings import LOCATION_API_BASE, LOCATION_API_KEY


class Dawarich:
    """Client for interacting with the timeline.osmosis.page API."""

    def __init__(self):
        if not LOCATION_API_KEY:
            raise ValueError("Missing API_KEY. Please set it in your .env file.")

        self.api_base = LOCATION_API_BASE.rstrip("/")
        self.headers = {"Authorization": f"Bearer {LOCATION_API_KEY}"}

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Compute distance in meters between two lat/lon points."""
        R = 6371_000  # meters
        phi1, phi2 = radians(lat1), radians(lat2)
        dphi = radians(lat2 - lat1)
        dlambda = radians(lon2 - lon1)
        a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))

    def get_points_since(self, timestamp_iso: str):
        """Fetch recorded points from a specific timestamp."""
        url = f"{self.api_base}/points"
        params = {"from": timestamp_iso}
        r = requests.get(url, params=params, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def _extract_coords(self, point):
        """Try to extract lat/lon from various possible key patterns."""
        # Common patterns
        for lat_key in ("lat", "latitude", "lat_deg"):
            for lon_key in ("lon", "lng", "longitude", "lon_deg"):
                if lat_key in point and lon_key in point:
                    return float(point[lat_key]), float(point[lon_key])

        # Nested coordinates (like point["location"]["lat"])
        if "location" in point and isinstance(point["location"], dict):
            loc = point["location"]
            for lat_key in ("lat", "latitude"):
                for lon_key in ("lon", "lng", "longitude"):
                    if lat_key in loc and lon_key in loc:
                        return float(loc[lat_key]), float(loc[lon_key])

        return None, None

    def analyze_points(self, points):
        """Calculate latest location, speed, and total distance traveled."""
        if not points:
            print("⚠️ No points returned from API.")
            return None

        # Debug: show keys of first point if needed
        first = points[0]
        if not any(k in first for k in ("lat", "latitude", "location")):
            print("⚠️ Unexpected point format. First point keys:")
            print(list(first.keys()))

        total_distance = 0.0
        coords = []

        for p in points:
            lat, lon = self._extract_coords(p)
            if lat is not None and lon is not None:
                coords.append((lat, lon))

        if len(coords) < 2:
            print("⚠️ Not enough coordinate data to calculate distance.")
            return None

        for (lat1, lon1), (lat2, lon2) in zip(coords, coords[1:]):
            total_distance += self._haversine(lat1, lon1, lat2, lon2)

        latest = points[-1]
        latest_lat, latest_lon = self._extract_coords(latest)
        return {
            "latest_location": (latest_lat, latest_lon),
            "latest_speed": latest.get("speed"),
            "distance_travelled_m": total_distance,
        }

    def since(self, year, month, day):
        """Shortcut: get stats since a given date."""
        timestamp_iso = datetime(year, month, day).isoformat()
        points = self.get_points_since(timestamp_iso)
        return self.analyze_points(points)

    def health(self):
        """Check if API is reachable."""
        url = f"{self.api_base}/health"
        try:
            r = requests.get(url, headers=self.headers, timeout=5)
            return r.status_code, r.text
        except Exception as e:
            return None, str(e)

