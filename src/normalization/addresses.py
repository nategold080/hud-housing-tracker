"""Address normalization for cross-linking HUD housing records."""

import re


# Common street type abbreviations
STREET_TYPES = {
    "STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "DRIVE": "DR",
    "ROAD": "RD", "LANE": "LN", "COURT": "CT", "PLACE": "PL",
    "CIRCLE": "CIR", "TERRACE": "TER", "WAY": "WAY", "HIGHWAY": "HWY",
    "PARKWAY": "PKWY", "TRAIL": "TRL", "EXPRESSWAY": "EXPY",
}

# Direction abbreviations
DIRECTIONS = {
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
}

# State abbreviations
STATE_ABBREVS = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
    "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX",
    "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
    "DISTRICT OF COLUMBIA": "DC", "PUERTO RICO": "PR", "GUAM": "GU",
    "VIRGIN ISLANDS": "VI", "AMERICAN SAMOA": "AS",
}


def normalize_address(address: str | None) -> str:
    """Normalize a street address for matching."""
    if not address:
        return ""

    addr = address.upper().strip()

    # Remove unit/apt/suite numbers
    addr = re.sub(r'\b(APT|APARTMENT|UNIT|STE|SUITE|#|BLDG|BUILDING)\s*\.?\s*\S+', '', addr)

    # Normalize street types
    for full, abbr in STREET_TYPES.items():
        addr = re.sub(rf'\b{full}\b\.?', abbr, addr)

    # Normalize directions
    for full, abbr in DIRECTIONS.items():
        addr = re.sub(rf'\b{full}\b\.?', abbr, addr)

    # Remove periods and extra punctuation
    addr = re.sub(r'[.,#]', '', addr)

    # Collapse whitespace
    addr = re.sub(r'\s+', ' ', addr).strip()

    return addr


def normalize_city(city: str | None) -> str:
    """Normalize a city name for matching."""
    if not city:
        return ""

    c = city.upper().strip()

    # Common abbreviations
    c = re.sub(r'\bST\.?\b', 'SAINT', c)
    c = re.sub(r'\bFT\.?\b', 'FORT', c)
    c = re.sub(r'\bMT\.?\b', 'MOUNT', c)

    # Remove punctuation
    c = re.sub(r'[.,]', '', c)
    c = re.sub(r'\s+', ' ', c).strip()

    return c


def normalize_state(state: str | None) -> str:
    """Normalize a state to its 2-letter abbreviation."""
    if not state:
        return ""

    s = state.upper().strip()

    # Already a 2-letter code
    if len(s) == 2 and s in STATE_ABBREVS.values():
        return s

    # Full name lookup
    if s in STATE_ABBREVS:
        return STATE_ABBREVS[s]

    return s


def normalize_zip(zip_code: str | None) -> str:
    """Normalize a ZIP code to 5 digits."""
    if not zip_code:
        return ""

    z = str(zip_code).strip()

    # Extract first 5 digits
    match = re.match(r'^(\d{5})', z)
    if match:
        return match.group(1)

    # Zero-padded (some states like MA, CT have leading zeros)
    if z.isdigit() and len(z) < 5:
        return z.zfill(5)

    return z


def normalize_owner_name(name: str | None) -> str:
    """Normalize an owner/management company name for matching."""
    if not name:
        return ""

    n = name.upper().strip()

    # Strip legal suffixes (3 passes for nested)
    suffixes = [
        r'\bLLC\b', r'\bL\.?L\.?C\.?\b', r'\bINC\b', r'\bINCORPORATED\b',
        r'\bCORP\b', r'\bCORPORATION\b', r'\bLTD\b', r'\bLIMITED\b',
        r'\bLP\b', r'\bL\.?P\.?\b', r'\bLLP\b', r'\bL\.?L\.?P\.?\b',
        r'\bCO\b', r'\bCOMPANY\b', r'\bGROUP\b', r'\bHOLDINGS\b',
        r'\bENTERPRISES\b', r'\bPARTNERS\b', r'\bPARTNERSHIP\b',
        r'\bASSOCIATES\b', r'\bFOUNDATION\b', r'\bTRUST\b',
    ]
    for _ in range(3):
        for suffix in suffixes:
            n = re.sub(suffix + r'\.?,?\s*', ' ', n)

    # Remove "THE" prefix
    n = re.sub(r'^THE\s+', '', n)

    # Remove DBA
    n = re.sub(r'\bD/?B/?A\b.*$', '', n)

    # Remove punctuation except hyphens
    n = re.sub(r'[.,\'\"()&]', ' ', n)

    # Collapse whitespace
    n = re.sub(r'\s+', ' ', n).strip()

    return n


def make_match_key(address: str | None, city: str | None,
                   state: str | None, zip_code: str | None) -> str:
    """Create a normalized matching key from address components."""
    parts = [
        normalize_address(address),
        normalize_city(city),
        normalize_state(state),
        normalize_zip(zip_code),
    ]
    return "|".join(p for p in parts if p)
