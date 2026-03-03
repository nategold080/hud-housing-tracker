"""LIHTC (Low-Income Housing Tax Credit) data scraper.

Source: HUD User - LIHTC Database
URL: https://lihtc.huduser.gov/
Format: CSV download
Records: ~54,000 projects
"""

import csv
import io
import re
import zipfile
from pathlib import Path

import httpx

LIHTC_URL = "https://www.huduser.gov/lihtc/lihtcpub.zip"
CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
CACHE_FILE = CACHE_DIR / "LIHTCPUB.csv"

HEADERS = {
    "User-Agent": "HUD-Housing-Tracker/1.0 (nathanmauricegoldberg@gmail.com)"
}


def download_lihtc(force: bool = False) -> Path:
    """Download LIHTC CSV from HUD User."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if CACHE_FILE.exists() and not force:
        return CACHE_FILE

    # Download ZIP and extract CSV
    resp = httpx.get(LIHTC_URL, headers=HEADERS, follow_redirects=True, timeout=120)
    if resp.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            # Look for the project-level CSV (LIHTCPUB.csv, not BIN)
            csv_names = [n for n in zf.namelist()
                         if n.lower().endswith(".csv") and "bin" not in n.lower()]
            if not csv_names:
                csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if csv_names:
                CACHE_FILE.write_bytes(zf.read(csv_names[0]))
                return CACHE_FILE

    # Try direct CSV fallback
    csv_url = LIHTC_URL.replace(".zip", ".csv")
    resp2 = httpx.get(csv_url, headers=HEADERS, follow_redirects=True, timeout=120)
    if resp2.status_code == 200:
        CACHE_FILE.write_bytes(resp2.content)
        return CACHE_FILE

    raise RuntimeError(f"Failed to download LIHTC data: HTTP {resp.status_code}")


def parse_lihtc(csv_path: Path | None = None) -> list[dict]:
    """Parse LIHTC CSV into normalized records."""
    path = csv_path or CACHE_FILE
    if not path.exists():
        raise FileNotFoundError(f"LIHTC CSV not found at {path}")

    records = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rec = _parse_lihtc_row(row)
            if rec:
                records.append(rec)

    return records


def _parse_lihtc_row(row: dict) -> dict | None:
    """Parse a single LIHTC CSV row into a normalized record."""
    hud_id = _clean(row.get("HUD_ID") or row.get("hud_id", ""))
    if not hud_id:
        return None

    return {
        "hud_id": hud_id,
        "project_name": _clean(row.get("PROJECT") or row.get("project", "")),
        "address": _clean(row.get("PROJ_ADD") or row.get("proj_add", "")),
        "city": _clean(row.get("PROJ_CTY") or row.get("proj_cty", "")),
        "state": _clean(row.get("PROJ_ST") or row.get("proj_st", "")),
        "zip_code": _normalize_zip(row.get("PROJ_ZIP") or row.get("proj_zip", "")),
        "county_fips": _clean(row.get("FIPS2010") or row.get("fips2010", "")),
        "latitude": _safe_float(row.get("LATITUDE") or row.get("latitude")),
        "longitude": _safe_float(row.get("LONGITUDE") or row.get("longitude")),
        "total_units": _safe_int(row.get("N_UNITS") or row.get("n_units")),
        "li_units": _safe_int(row.get("LI_UNITS") or row.get("li_units")),
        "credit_type": _clean(row.get("TYPE") or row.get("type", "")),
        "placed_in_service_year": _safe_int(row.get("YR_PIS") or row.get("yr_pis")),
        "allocation_year": _safe_int(row.get("YR_ALLOC") or row.get("yr_alloc")),
        "yr_pis": _safe_int(row.get("YR_PIS") or row.get("yr_pis")),
        "yr_alloc": _safe_int(row.get("YR_ALLOC") or row.get("yr_alloc")),
        "congress_dist": _clean(row.get("CONGRESS") or row.get("congress", "")),
        "census_tract": _clean(row.get("CENSUS_TRACT") or row.get("census_tract", "")),
        "scattered_site": 1 if _clean(row.get("SCATTERED_SITE_IND") or row.get("scattered_site_ind", "")).upper() == "Y" else 0,
        "sec8_contract": _clean(row.get("SEC8_CONTRACT") or row.get("sec8_contract", "")),
        "owner": _clean(row.get("OWNER") or row.get("owner", "")),
        "mgmt_company": _clean(row.get("MGMT_CO") or row.get("mgmt_co", "")),
        "source_file": "LIHTCPUB.csv",
    }


def _clean(val: str) -> str:
    """Strip and clean a string value."""
    if not val:
        return ""
    return val.strip()


def _normalize_zip(val: str) -> str:
    """Normalize ZIP code to 5 digits."""
    if not val:
        return ""
    val = val.strip()
    match = re.match(r"^(\d{5})", val)
    if match:
        return match.group(1)
    if val.isdigit() and len(val) < 5:
        return val.zfill(5)
    return val


def _safe_int(val) -> int | None:
    """Safely convert to int."""
    if val is None:
        return None
    try:
        v = str(val).strip()
        if not v or v in ("", ".", "9999"):
            return None
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    """Safely convert to float."""
    if val is None:
        return None
    try:
        v = str(val).strip()
        if not v or v == ".":
            return None
        return float(v)
    except (ValueError, TypeError):
        return None
