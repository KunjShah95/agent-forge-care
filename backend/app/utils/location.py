"""
Location parsing utilities for AgentForge Career OS.

Parses free-form location strings (e.g. "San Francisco, CA", "New York, NY, USA",
"London, UK", "Remote", "Mountain View, California, United States") into
structured city/state/country fields.

Uses a regex-based approach with common US state/country mappings.
"""

import re
from typing import Optional

# ─── US State Abbreviation → Full Name ──────────────────────
US_STATE_ABBREVS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

# ─── Country aliases ────────────────────────────────────────
COUNTRY_ALIASES = {
    "usa": "United States", "us": "United States", "united states": "United States",
    "u.s.": "United States", "u.s.a": "United States", "america": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "england": "United Kingdom",
    "gb": "United Kingdom", "great britain": "United Kingdom",
    "canada": "Canada", "ca": "Canada",
    "australia": "Australia", "au": "Australia",
    "india": "India", "in": "India",
    "germany": "Germany", "de": "Germany",
    "france": "France", "fr": "France",
    "japan": "Japan", "jp": "Japan",
    "china": "China", "cn": "China",
    "singapore": "Singapore", "sg": "Singapore",
    "netherlands": "Netherlands", "holland": "Netherlands", "nl": "Netherlands",
}

# ─── Common tech hub city → state mapping ───────────────────
CITY_STATE_MAP = {
    "san francisco": "California",
    "san jose": "California",
    "mountain view": "California",
    "palo alto": "California",
    "menlo park": "California",
    "sunnyvale": "California",
    "cupertino": "California",
    "oakland": "California",
    "berkeley": "California",
    "los angeles": "California",
    "santa monica": "California",
    "san diego": "California",
    "irvine": "California",
    "new york": "New York",
    "brooklyn": "New York",
    "manhattan": "New York",
    "seattle": "Washington",
    "redmond": "Washington",
    "boston": "Massachusetts",
    "cambridge": "Massachusetts",
    "chicago": "Illinois",
    "austin": "Texas",
    "dallas": "Texas",
    "houston": "Texas",
    "portland": "Oregon",
    "denver": "Colorado",
    "boulder": "Colorado",
    "phoenix": "Arizona",
    "miami": "Florida",
    "atlanta": "Georgia",
    "pittsburgh": "Pennsylvania",
    "philadelphia": "Pennsylvania",
    "washington": "District of Columbia",
    "toronto": "Ontario",
    "vancouver": "British Columbia",
    "london": "England",
    "berlin": "Berlin",
    "munich": "Bavaria",
    "paris": "Île-de-France",
    "amsterdam": "North Holland",
    "dublin": "County Dublin",
    "bangalore": "Karnataka",
    "hyderabad": "Telangana",
    "mumbai": "Maharashtra",
    "sydney": "New South Wales",
    "melbourne": "Victoria",
    "tokyo": "Tokyo",
    "singapore": "Singapore",
    "beijing": "Beijing",
    "shanghai": "Shanghai",
}    # ─── Known country names (for detection when state looks like a country) ───
# Note: 2-letter codes like CA, UK, US are deliberately NOT in KNOWN_COUNTRIES
# to avoid matching them before state abbreviation checks.
KNOWN_COUNTRIES = {
    "united states", "usa", "us", "u.s.", "u.s.a", "america",
    "canada", "uk", "u.k.", "united kingdom", "england", "gb", "great britain",
    "australia", "india", "germany", "france", "japan", "china", "singapore",
    "netherlands", "holland", "switzerland", "sweden", "norway", "denmark",
    "finland", "italy", "spain", "portugal", "belgium", "austria", "ireland",
    "new zealand", "south korea", "korea", "israel", "uae", "united arab emirates",
    "brazil", "mexico", "argentina", "south africa",
}


def parse_location(location_str: Optional[str]) -> dict:
    """
    Parse a free-form location string into city/state/country components.

    Handles formats like:
      - "San Francisco, CA"
      - "New York, NY, USA"
      - "London, UK"
      - "Remote / Anywhere"
      - "Mountain View, California, United States"
      - "Bangalore, India"
      - None / ""

    Returns dict with keys: city, state, country (all Optional[str]).
    """
    if not location_str or not isinstance(location_str, str):
        return {"city": None, "state": None, "country": None}

    loc = location_str.strip()

    # Check for "Remote" / "Anywhere" type locations
    if loc.lower() in ("remote", "anywhere", "anywhere in the world", "global"):
        return {"city": None, "state": None, "country": None}

    # Split by comma
    parts = [p.strip() for p in loc.split(",")]
    parts = [p for p in parts if p]  # remove empty parts

    if not parts:
        return {"city": loc, "state": None, "country": None}

    city = parts[0]
    state = None
    country = None

    # Infer from parts count
    if len(parts) >= 3:
        # "City, State, Country" or "City, Region, Country"
        state_candidate = parts[1]
        country_candidate = parts[2]

        # Check if the last part looks like a country
        country_lower = country_candidate.lower()
        if country_lower in KNOWN_COUNTRIES or country_lower in COUNTRY_ALIASES:
            country = COUNTRY_ALIASES.get(country_lower, country_candidate)
            state = _normalize_state(state_candidate)
        else:
            # Might be "City, State, Zip/Extra"
            state = _normalize_state(state_candidate)
            country = "United States"

    elif len(parts) == 2:
        # "City, State" or "City, Country"
        second = parts[1]
        second_lower = second.lower()

        # Check state abbreviation FIRST (before country aliases like "CA"→Canada)
        if _looks_like_state_abbrev(second):
            state = _normalize_state(second)
            country = "United States"
        elif second_lower in KNOWN_COUNTRIES or second_lower in COUNTRY_ALIASES:
            country = COUNTRY_ALIASES.get(second_lower, second)
        else:
            # Could be full state name or region
            state = _normalize_state(second)

    else:
        # Single part - just city name
        city = parts[0]
        # Try to infer state from known city-state mapping
        city_lower = city.lower()
        if city_lower in CITY_STATE_MAP:
            state = CITY_STATE_MAP[city_lower]
            country = "United States"

    # If we have state but no country, default to US
    if state and not country:
        country = "United States"

    return {
        "city": city,
        "state": state,
        "country": country,
    }


def _looks_like_state_abbrev(text: str) -> bool:
    """Check if text looks like a US state abbreviation."""
    cleaned = text.strip().upper()
    return len(cleaned) == 2 and cleaned in US_STATE_ABBREVS


def _normalize_state(text: str) -> str:
    """Normalize a state abbreviation or full name to full state name."""
    cleaned = text.strip().title()
    # Check if it's an abbreviation
    upper = text.strip().upper()
    if len(upper) == 2 and upper in US_STATE_ABBREVS:
        return US_STATE_ABBREVS[upper]
    # Check if it's already a full state name
    for abbr, full in US_STATE_ABBREVS.items():
        if cleaned == full:
            return full
    # Return as-is if we can't match
    return cleaned
