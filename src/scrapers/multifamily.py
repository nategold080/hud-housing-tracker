"""HUD Multifamily Properties scraper via ArcGIS FeatureServer.

Source: HUD Open Data - Multifamily Properties Assisted
URL: https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/
Format: ArcGIS REST API (JSON)
Records: ~34,000 properties with REAC inspection scores embedded
"""

import json
import time
from pathlib import Path

import httpx

# ArcGIS FeatureServer endpoints
MF_ASSISTED_URL = (
    "https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/"
    "Multifamily_Properties_Assisted/FeatureServer/0/query"
)
MF_INSURED_URL = (
    "https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/"
    "HUD_Insured_Multifamily_Properties/FeatureServer/0/query"
)

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "raw"

# Fields to request from the assisted properties endpoint
ASSISTED_FIELDS = [
    "PROPERTY_ID", "PROPERTY_NAME_TEXT", "STD_ADDR", "STD_CITY", "STD_ST",
    "STD_ZIP5", "CNTY2KX", "CONGRESSIONAL_DISTRICT_CODE",
    "CLIENT_GROUP_NAME", "CLIENT_GROUP_TYPE",
    "MGMT_AGENT_ORG_NAME", "PROGRAM_TYPE1", "PROGRAM_TYPE2",
    "TOTAL_UNIT_COUNT", "TOTAL_ASSISTED_UNIT_COUNT",
    "IS_SEC8_IND", "IS_202_811_IND", "IS_SUBSIDIZED_IND", "IS_INSURED_IND",
    "TAXCREDIT1", "TAXCREDIT2",
    "REAC_LAST_INSPECTION_SCORE", "REAC_LAST_INSPECTION_DATE",
    "REAC_LAST_INSPECTION_ID",
    "PCT_OCCUPIED", "RENT_PER_MONTH", "SPENDING_PER_MONTH",
    "ANNL_EXPNS_AMNT", "OPIIS_RISK_CATEGORY",
    "EXPIRATION_DATE1", "EXPIRATION_DATE2",
    "CONTRACT1", "CONTRACT2", "CONTRACT_COUNT",
    "FHA_NUM1", "FHA_NUM2",
    "LAT", "LON",
    "TROUBLED_CODE",
]

INSURED_FIELDS = [
    "PROPERTY_ID", "PROPERTY_NAME_TEXT", "ADDRESS_LINE1_TEXT",
    "PLACED_BASE_CITY_NAME_TEXT", "STD_ST", "STD_ZIP5",
    "CNTY_NM2KX", "CONGRESSIONAL_DISTRICT_CODE",
    "PRIMARY_FHA_NUMBER", "PRIMARY_FINANCING_TYPE",
    "PROPERTY_CATEGORY_NAME",
    "TOTAL_UNIT_COUNT", "MAXIMUM_CONTRACT_UNIT_COUNT",
    "IS_SEC8_IND", "IS_SUBSIDIZED_IND", "IS_INSURED_IND",
    "IS_202_811_IND", "IS_202_CAPITAL_ADVANCE_IND", "IS_811_CAPITAL_ADVANCE_IND",
    "REAC_LAST_INSPECTION_SCORE", "REAC_LAST_INSPECTION_DATE",
    "MGMT_AGENT_ORG_NAME",
    "HAS_ACTIVE_FINANCING_IND", "HAS_ACTIVE_ASSISTANCE_IND",
    "LOAN_MATURITY_DATE", "ORIGINAL_LOAN_AMOUNT",
    "LAT", "LON",
]

HEADERS = {
    "User-Agent": "HUD-Housing-Tracker/1.0 (nathanmauricegoldberg@gmail.com)"
}


def download_multifamily_assisted(force: bool = False) -> Path:
    """Download all multifamily assisted property records via ArcGIS pagination."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "multifamily_assisted.json"

    if cache_file.exists() and not force:
        return cache_file

    all_features = _paginate_arcgis(MF_ASSISTED_URL, ",".join(ASSISTED_FIELDS))
    cache_file.write_text(json.dumps(all_features, indent=2))
    return cache_file


def download_multifamily_insured(force: bool = False) -> Path:
    """Download all HUD-insured multifamily property records."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "multifamily_insured.json"

    if cache_file.exists() and not force:
        return cache_file

    all_features = _paginate_arcgis(MF_INSURED_URL, ",".join(INSURED_FIELDS))
    cache_file.write_text(json.dumps(all_features, indent=2))
    return cache_file


def _paginate_arcgis(base_url: str, fields: str, batch_size: int = 2000) -> list[dict]:
    """Paginate through ArcGIS FeatureServer results."""
    all_features = []
    offset = 0

    while True:
        params = {
            "where": "1=1",
            "outFields": fields,
            "resultOffset": offset,
            "resultRecordCount": batch_size,
            "f": "json",
        }
        resp = httpx.get(base_url, params=params, headers=HEADERS,
                         follow_redirects=True, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            break

        all_features.extend(features)
        offset += len(features)

        # Check if we've gotten all records
        if not data.get("exceededTransferLimit", False) and len(features) < batch_size:
            break

        time.sleep(1)  # Rate limit

    return all_features


def parse_multifamily_assisted(json_path: Path | None = None) -> list[dict]:
    """Parse multifamily assisted properties into normalized records."""
    path = json_path or (CACHE_DIR / "multifamily_assisted.json")
    if not path.exists():
        raise FileNotFoundError(f"Multifamily assisted data not found at {path}")

    features = json.loads(path.read_text())
    records = []
    for feat in features:
        attrs = feat.get("attributes", feat)
        rec = _parse_assisted_record(attrs)
        if rec:
            records.append(rec)

    return records


def parse_multifamily_insured(json_path: Path | None = None) -> list[dict]:
    """Parse HUD-insured multifamily properties into normalized records."""
    path = json_path or (CACHE_DIR / "multifamily_insured.json")
    if not path.exists():
        raise FileNotFoundError(f"Multifamily insured data not found at {path}")

    features = json.loads(path.read_text())
    records = []
    for feat in features:
        attrs = feat.get("attributes", feat)
        rec = _parse_insured_record(attrs)
        if rec:
            records.append(rec)

    return records


def _parse_assisted_record(attrs: dict) -> dict | None:
    """Parse a single multifamily assisted property record."""
    prop_id = str(attrs.get("PROPERTY_ID", "")).strip()
    if not prop_id:
        return None

    return {
        "property_id": prop_id,
        "property_name": _clean(attrs.get("PROPERTY_NAME_TEXT")),
        "address": _clean(attrs.get("STD_ADDR")),
        "city": _clean(attrs.get("STD_CITY")),
        "state": _clean(attrs.get("STD_ST")),
        "zip_code": _clean(attrs.get("STD_ZIP5")),
        "county_code": _clean(attrs.get("CNTY2KX")),
        "congress_dist": _clean(attrs.get("CONGRESSIONAL_DISTRICT_CODE")),
        "owner_name": _clean(attrs.get("MGMT_AGENT_ORG_NAME")),
        "mgmt_agent": _clean(attrs.get("MGMT_AGENT_ORG_NAME")),
        "program_type": _clean(attrs.get("PROGRAM_TYPE1")),
        "assisted_units": _safe_int(attrs.get("TOTAL_ASSISTED_UNIT_COUNT")),
        "total_units": _safe_int(attrs.get("TOTAL_UNIT_COUNT")),
        "has_section_8": 1 if attrs.get("IS_SEC8_IND") == "Y" else 0,
        "has_lihtc": 1 if attrs.get("TAXCREDIT1") or attrs.get("TAXCREDIT2") else 0,
        "has_section_202": 1 if attrs.get("IS_202_811_IND") == "Y" else 0,
        "has_section_811": 0,  # Separate from 202
        "property_category": _clean(attrs.get("CLIENT_GROUP_TYPE")),
        "latitude": _safe_float(attrs.get("LAT")),
        "longitude": _safe_float(attrs.get("LON")),
        "source_file": "multifamily_assisted",
        # Extra fields for REAC extraction
        "_reac_score": _clean(attrs.get("REAC_LAST_INSPECTION_SCORE")),
        "_reac_date": attrs.get("REAC_LAST_INSPECTION_DATE"),
        "_reac_id": attrs.get("REAC_LAST_INSPECTION_ID"),
        "_pct_occupied": _safe_float(attrs.get("PCT_OCCUPIED")),
        "_rent_per_month": _safe_int(attrs.get("RENT_PER_MONTH")),
        "_annual_expense": _safe_float(attrs.get("ANNL_EXPNS_AMNT")),
        "_risk_category": _clean(attrs.get("OPIIS_RISK_CATEGORY")),
        "_troubled": _clean(attrs.get("TROUBLED_CODE")),
        "_contract1": _clean(attrs.get("CONTRACT1")),
        "_contract2": _clean(attrs.get("CONTRACT2")),
        "_expiration1": _clean(attrs.get("EXPIRATION_DATE1")),
        "_expiration2": _clean(attrs.get("EXPIRATION_DATE2")),
    }


def _parse_insured_record(attrs: dict) -> dict | None:
    """Parse a single HUD-insured multifamily property record."""
    prop_id = str(attrs.get("PROPERTY_ID", "")).strip()
    if not prop_id:
        return None

    return {
        "property_id": prop_id,
        "property_name": _clean(attrs.get("PROPERTY_NAME_TEXT")),
        "address": _clean(attrs.get("ADDRESS_LINE1_TEXT")),
        "city": _clean(attrs.get("PLACED_BASE_CITY_NAME_TEXT")),
        "state": _clean(attrs.get("STD_ST")),
        "zip_code": _clean(attrs.get("STD_ZIP5")),
        "county_code": _clean(attrs.get("CNTY_NM2KX")),
        "congress_dist": _clean(attrs.get("CONGRESSIONAL_DISTRICT_CODE")),
        "owner_name": None,  # Not in insured dataset
        "mgmt_agent": _clean(attrs.get("MGMT_AGENT_ORG_NAME")),
        "program_type": _clean(attrs.get("PRIMARY_FINANCING_TYPE")),
        "assisted_units": _safe_int(attrs.get("MAXIMUM_CONTRACT_UNIT_COUNT")),
        "total_units": _safe_int(attrs.get("TOTAL_UNIT_COUNT")),
        "has_section_8": 1 if attrs.get("IS_SEC8_IND") == "Y" else 0,
        "has_lihtc": 0,
        "has_section_202": 1 if attrs.get("IS_202_CAPITAL_ADVANCE_IND") == "Y" else 0,
        "has_section_811": 1 if attrs.get("IS_811_CAPITAL_ADVANCE_IND") == "Y" else 0,
        "property_category": _clean(attrs.get("PROPERTY_CATEGORY_NAME")),
        "latitude": _safe_float(attrs.get("LAT")),
        "longitude": _safe_float(attrs.get("LON")),
        "source_file": "multifamily_insured",
        # Extra fields
        "_reac_score": _clean(attrs.get("REAC_LAST_INSPECTION_SCORE")),
        "_reac_date": attrs.get("REAC_LAST_INSPECTION_DATE"),
        "_fha_number": _clean(attrs.get("PRIMARY_FHA_NUMBER")),
        "_financing_type": _clean(attrs.get("PRIMARY_FINANCING_TYPE")),
        "_loan_amount": _safe_float(attrs.get("ORIGINAL_LOAN_AMOUNT")),
    }


def extract_reac_from_multifamily(mf_records: list[dict]) -> list[dict]:
    """Extract REAC inspection records embedded in multifamily data."""
    reac_records = []
    seen_ids = set()

    for rec in mf_records:
        reac_score = rec.get("_reac_score")
        reac_date = rec.get("_reac_date")
        reac_id = rec.get("_reac_id")

        if not reac_score or reac_score in ("", "None"):
            continue

        # Create a unique inspection ID
        if reac_id:
            insp_id = str(int(reac_id)) if isinstance(reac_id, float) else str(reac_id)
        else:
            insp_id = f"REAC-{rec['property_id']}"

        if insp_id in seen_ids:
            continue
        seen_ids.add(insp_id)

        # Convert epoch timestamp to date string
        date_str = ""
        if reac_date and isinstance(reac_date, (int, float)) and reac_date > 0:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(reac_date / 1000, tz=timezone.utc)
            date_str = dt.strftime("%Y-%m-%d")

        # Parse score (might be string like "97" or "97a")
        try:
            score_val = float(str(reac_score).rstrip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ*"))
        except (ValueError, TypeError):
            score_val = None

        reac_records.append({
            "inspection_id": insp_id,
            "property_id": rec["property_id"],
            "property_name": rec.get("property_name", ""),
            "address": rec.get("address", ""),
            "city": rec.get("city", ""),
            "state": rec.get("state", ""),
            "zip_code": rec.get("zip_code", ""),
            "inspection_date": date_str,
            "inspection_score": score_val,
            "health_flag": 0,
            "smoke_detector_flag": 0,
            "property_type": rec.get("property_category", ""),
            "units": rec.get("total_units"),
            "rass_date": None,
            "source_file": rec.get("source_file", "multifamily_assisted"),
        })

    return reac_records


def _clean(val) -> str:
    """Clean a field value."""
    if val is None:
        return ""
    return str(val).strip()


def _safe_int(val) -> int | None:
    """Safely convert to int."""
    if val is None:
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    """Safely convert to float."""
    if val is None:
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None
