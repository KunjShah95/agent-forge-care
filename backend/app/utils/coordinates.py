"""
City coordinate database for plotting opportunities on a map.

Provides approximate lat/lng for common cities worldwide.
Uses the predefined city database first, then falls back to
Nominatim (OpenStreetMap free geocoding API) for any location
not in the predefined list.

Nominatim usage:
  - Free API: https://nominatim.openstreetmap.org/
  - Rate limit: 1 request/second (enforced with delay)
  - Results are cached in-memory to minimize API calls
  - User-Agent header set as per OSM usage policy
"""

import asyncio
import logging
from datetime import UTC, datetime

logger = logging.getLogger("agentforge.coordinates")

# ─── In-memory geocode cache ───────────────────────────────
# Key: normalized "city|state|country" string
# Value: (lat, lng) or None if not found
_geocode_cache: dict[str, tuple[float, float] | None] = {}
_last_nominatim_call: float = 0  # timestamp of last Nominatim request

# ─── City → (latitude, longitude) mapping ──────────────────
# Sources: OpenStreetMap, general knowledge
CITY_COORDS: dict[str, tuple[float, float]] = {
    # ── United States ──
    "san francisco": (37.7749, -122.4194),
    "mountain view": (37.3861, -122.0839),
    "palo alto": (37.4419, -122.1430),
    "menlo park": (37.4530, -122.1817),
    "sunnyvale": (37.3688, -122.0363),
    "cupertino": (37.3230, -122.0322),
    "oakland": (37.8044, -122.2712),
    "berkeley": (37.8716, -122.2727),
    "san jose": (37.3382, -121.8863),
    "los angeles": (34.0522, -118.2437),
    "santa monica": (34.0195, -118.4912),
    "san diego": (32.7157, -117.1611),
    "irvine": (33.6846, -117.8265),
    "new york": (40.7128, -74.0060),
    "brooklyn": (40.6782, -73.9442),
    "manhattan": (40.7831, -73.9712),
    "seattle": (47.6062, -122.3321),
    "redmond": (47.6734, -122.1215),
    "boston": (42.3601, -71.0589),
    "cambridge": (42.3736, -71.1097),
    "chicago": (41.8781, -87.6298),
    "austin": (30.2672, -97.7431),
    "dallas": (32.7767, -96.7970),
    "houston": (29.7604, -95.3698),
    "portland": (45.5152, -122.6784),
    "denver": (39.7392, -104.9903),
    "boulder": (40.0150, -105.2705),
    "phoenix": (33.4484, -112.0740),
    "miami": (25.7617, -80.1918),
    "atlanta": (33.7490, -84.3880),
    "washington": (38.9072, -77.0369),
    "philadelphia": (39.9526, -75.1652),
    "pittsburgh": (40.4406, -79.9959),
    "detroit": (42.3314, -83.0458),
    "minneapolis": (44.9778, -93.2650),
    "tampa": (27.9506, -82.4572),
    "orlando": (28.5383, -81.3792),
    "raleigh": (35.7796, -78.6382),
    "durham": (35.9940, -78.8986),
    "charlotte": (35.2271, -80.8431),
    "nashville": (36.1627, -86.7816),
    "salt lake city": (40.7608, -111.8910),
    "provo": (40.2338, -111.6585),
    "kansas city": (39.0997, -94.5786),
    "st. louis": (38.6270, -90.1994),
    "indianapolis": (39.7684, -86.1581),
    "columbus": (39.9612, -82.9988),
    "madison": (43.0731, -89.4012),
    "ann arbor": (42.2808, -83.7430),
    # ── Canada ──
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "montreal": (45.5017, -73.5673),
    "ottawa": (45.4215, -75.6972),
    "waterloo": (43.4643, -80.5204),
    "calgary": (51.0447, -114.0719),
    # ── United Kingdom ──
    "london": (51.5074, -0.1278),
    "cambridge uk": (52.2053, 0.1218),
    "oxford": (51.7520, -1.2577),
    "manchester": (53.4808, -2.2426),
    "edinburgh": (55.9533, -3.1883),
    # ── Europe ──
    "berlin": (52.5200, 13.4050),
    "munich": (48.1351, 11.5820),
    "paris": (48.8566, 2.3522),
    "amsterdam": (52.3676, 4.9041),
    "dublin": (53.3498, -6.2603),
    "zurich": (47.3769, 8.5417),
    "stockholm": (59.3293, 18.0686),
    "copenhagen": (55.6761, 12.5683),
    "helsinki": (60.1699, 24.9384),
    "oslo": (59.9139, 10.7522),
    "barcelona": (41.3874, 2.1686),
    "madrid": (40.4168, -3.7038),
    "rome": (41.9028, 12.4964),
    "milan": (45.4642, 9.1900),
    "vienna": (48.2082, 16.3738),
    "prague": (50.0755, 14.4378),
    "warsaw": (52.2297, 21.0122),
    "budapest": (47.4979, 19.0402),
    "brussels": (50.8503, 4.3517),
    "lisbon": (38.7223, -9.1393),
    # ── Asia ──
    "tokyo": (35.6762, 139.6503),
    "singapore": (1.3521, 103.8198),
    "hong kong": (22.3193, 114.1694),
    "shanghai": (31.2304, 121.4737),
    "beijing": (39.9042, 116.4074),
    "shenzhen": (22.5431, 114.0579),
    "seoul": (37.5665, 126.9780),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "mumbai": (19.0760, 72.8777),
    "new delhi": (28.6139, 77.2090),
    "pune": (18.5204, 73.8567),
    "chennai": (13.0827, 80.2707),
    "dubai": (25.2048, 55.2708),
    "abudhabi": (24.4539, 54.3773),
    "kuala lumpur": (3.1390, 101.6869),
    "jakarta": (-6.2088, 106.8456),
    "bangkok": (13.7563, 100.5018),
    "ho chi minh city": (10.8231, 106.6297),
    "manila": (14.5995, 120.9842),
    "taipei": (25.0330, 121.5654),
    # ── Oceania ──
    "sydney": (-33.8688, 151.2093),
    "melbourne": (-37.8136, 144.9631),
    "brisbane": (-27.4698, 153.0251),
    "auckland": (-36.8485, 174.7633),
    "wellington": (-41.2865, 174.7762),
    # ── Middle East / Africa ──
    "tel aviv": (32.0853, 34.7818),
    "johannesburg": (-26.2041, 28.0473),
    "cape town": (-33.9249, 18.4241),
    "nairobi": (-1.2921, 36.8219),
    "lagos": (6.5244, 3.3792),
    "cairo": (30.0444, 31.2357),
    # ── South America ──
    "são paulo": (-23.5505, -46.6333),
    "rio de janeiro": (-22.9068, -43.1729),
    "buenos aires": (-34.6037, -58.3816),
    "santiago": (-33.4489, -70.6693),
    "bogotá": (4.7110, -74.0721),
    "mexico city": (19.4326, -99.1332),
}

# ── State-level approximate centers (fallback when city not found) ──
STATE_COORDS: dict[str, tuple[float, float]] = {
    "california": (36.7783, -119.4179),
    "new york": (40.7128, -74.0060),
    "washington": (47.7511, -120.7401),
    "massachusetts": (42.4072, -71.3824),
    "illinois": (40.6331, -89.3985),
    "texas": (31.9686, -99.9018),
    "oregon": (43.8041, -120.5542),
    "colorado": (39.5501, -105.7821),
    "arizona": (34.0489, -111.0937),
    "florida": (27.6648, -81.5158),
    "georgia": (32.1656, -82.9001),
    "pennsylvania": (41.2033, -77.1945),
    "district of columbia": (38.9072, -77.0369),
    "ontario": (51.2538, -85.3232),
    "british columbia": (53.7267, -127.6476),
    "queensland": (-20.9176, 142.7028),
    "new south wales": (-31.2532, 146.9211),
    "victoria": (-36.4854, 140.9771),
    "england": (52.3555, -1.1743),
    "berlin": (52.5200, 13.4050),
    "bavaria": (48.7904, 11.4979),
    "île-de-france": (48.8566, 2.3522),
    "north holland": (52.4107, 4.8444),
    "karnataka": (15.3173, 75.7139),
    "telangana": (18.1124, 79.0193),
    "maharashtra": (19.7515, 75.7139),
}

# ─── Country centroids (fallback when nothing else matches) ──
COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "united states": (39.8283, -98.5795),
    "canada": (56.1304, -106.3468),
    "united kingdom": (55.3781, -3.4360),
    "germany": (51.1657, 10.4515),
    "france": (46.6034, 1.8883),
    "netherlands": (52.1326, 5.2913),
    "ireland": (53.1424, -7.6921),
    "switzerland": (46.8182, 8.2275),
    "sweden": (60.1282, 18.6435),
    "denmark": (56.2639, 9.5018),
    "norway": (60.4720, 8.4689),
    "finland": (61.9241, 25.7482),
    "spain": (40.4637, -3.7492),
    "italy": (41.8719, 12.5674),
    "austria": (47.5162, 14.5501),
    "japan": (36.2048, 138.2529),
    "china": (35.8617, 104.1954),
    "india": (20.5937, 78.9629),
    "australia": (-25.2744, 133.7751),
    "singapore": (1.3521, 103.8198),
    "south korea": (35.9078, 127.7669),
    "brazil": (-14.2350, -51.9253),
    "mexico": (23.6345, -102.5528),
    "argentina": (-38.4161, -63.6167),
    "south africa": (-30.5595, 22.9375),
    "israel": (31.0461, 34.8516),
    "uae": (23.4241, 53.8478),
    "new zealand": (-40.9006, 174.8860),
}


def _build_cache_key(city: str | None, state: str | None, country: str | None) -> str:
    """Build a normalized cache key from location parts."""
    return f"{city or ''}|{state or ''}|{country or ''}"


def _build_nominatim_query(city: str | None, state: str | None, country: str | None) -> str:
    """Build a Nominatim search query string from location parts."""
    parts = [p for p in [city, state, country] if p]
    return ", ".join(parts) if parts else ""


async def _geocode_with_nominatim(
    city: str | None,
    state: str | None,
    country: str | None,
) -> tuple[float, float] | None:
    """
    Geocode a location using the Nominatim (OpenStreetMap) free API.

    Rate-limited to 1 request/second as per Nominatim usage policy.
    Results are cached in-memory so repeated lookups are instant.

    Returns (lat, lng) or None if the location can't be found.
    """
    global _last_nominatim_call

    query = _build_nominatim_query(city, state, country)
    if not query:
        return None

    # Check cache first
    cache_key = _build_cache_key(city, state, country)
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    # Rate limit: ensure at least 1.1 seconds between requests
    now = datetime.now(UTC).timestamp()
    elapsed = now - _last_nominatim_call
    if elapsed < 1.1:
        await asyncio.sleep(1.1 - elapsed)

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers={
                    "User-Agent": "AgentForgeCareerOS/1.0 (support@agentforge.ai)",
                    "Accept": "application/json",
                },
            )
            _last_nominatim_call = datetime.now(UTC).timestamp()

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    result = (lat, lon)
                    _geocode_cache[cache_key] = result
                    return result

        # Not found — cache as None to avoid repeated lookups
        _geocode_cache[cache_key] = None
        return None

    except Exception as e:
        logger.debug("Nominatim geocoding failed for '%s': %s", query, e)
        # Don't cache failures — allow retry on next request
        return None


def get_coordinates(
    city: str | None,
    state: str | None,
    country: str | None,
) -> tuple[float, float] | None:
    """
    Get approximate coordinates for a location (synchronous, predefined list only).

    Tries (in order):
    1. Exact city name match
    2. State name match
    3. Country centroid (approximate)

    Returns (lat, lng) tuple or None if unknown.
    """
    if city:
        city_lower = city.strip().lower()
        if city_lower in CITY_COORDS:
            return CITY_COORDS[city_lower]

    if state:
        state_lower = state.strip().lower()
        if state_lower in STATE_COORDS:
            return STATE_COORDS[state_lower]

    if country:
        country_lower = country.strip().lower()
        if country_lower in COUNTRY_CENTROIDS:
            return COUNTRY_CENTROIDS[country_lower]

    return None


async def get_coordinates_async(
    city: str | None,
    state: str | None,
    country: str | None,
) -> tuple[float, float] | None:
    """
    Get coordinates for a location with Nominatim fallback.

    Tries (in order):
    1. Predefined city database (fast, no API call)
    2. In-memory cache
    3. Nominatim geocoding API (free, rate-limited to 1 req/s)
    4. State-level approximate center
    5. Country centroid

    Caches all results in-memory so subsequent calls are instant.
    """
    # 1. Predefined city match
    if city:
        city_lower = city.strip().lower()
        if city_lower in CITY_COORDS:
            return CITY_COORDS[city_lower]

    # 2. Check cache
    cache_key = _build_cache_key(city, state, country)
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    # 3. Nominatim (async)
    coords = await _geocode_with_nominatim(city, state, country)
    if coords is not None:
        return coords

    # 4. State-level fallback
    if state:
        state_lower = state.strip().lower()
        if state_lower in STATE_COORDS:
            return STATE_COORDS[state_lower]

    # 5. Country centroid
    if country:
        country_lower = country.strip().lower()
        if country_lower in COUNTRY_CENTROIDS:
            return COUNTRY_CENTROIDS[country_lower]

    return None


def clear_geocode_cache() -> None:
    """Clear the in-memory geocode cache. Useful for testing."""
    _geocode_cache.clear()
