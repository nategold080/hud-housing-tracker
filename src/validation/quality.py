"""Quality scoring for HUD housing records."""


def score_lihtc(record: dict) -> float:
    """Score a LIHTC project record (0.0 - 1.0)."""
    score = 0.0
    weights = {
        "has_hud_id": 0.10,
        "has_name": 0.15,
        "has_address": 0.15,
        "has_city_state": 0.10,
        "has_zip": 0.05,
        "has_units": 0.10,
        "has_li_units": 0.05,
        "has_credit_type": 0.05,
        "has_pis_year": 0.10,
        "has_owner": 0.10,
        "has_coords": 0.05,
    }

    if record.get("hud_id"):
        score += weights["has_hud_id"]
    if record.get("project_name"):
        score += weights["has_name"]
    if record.get("address"):
        score += weights["has_address"]
    if record.get("city") and record.get("state"):
        score += weights["has_city_state"]
    if record.get("zip_code"):
        score += weights["has_zip"]
    if _safe_int(record.get("total_units")) and _safe_int(record.get("total_units")) > 0:
        score += weights["has_units"]
    if _safe_int(record.get("li_units")) and _safe_int(record.get("li_units")) > 0:
        score += weights["has_li_units"]
    if record.get("credit_type"):
        score += weights["has_credit_type"]
    if _safe_int(record.get("placed_in_service_year")) and _safe_int(record.get("placed_in_service_year")) > 1980:
        score += weights["has_pis_year"]
    if record.get("owner"):
        score += weights["has_owner"]
    if record.get("latitude") and record.get("longitude"):
        score += weights["has_coords"]

    return round(min(score, 1.0), 3)


def score_reac(record: dict) -> float:
    """Score a REAC inspection record (0.0 - 1.0)."""
    score = 0.0
    weights = {
        "has_inspection_id": 0.10,
        "has_property_id": 0.10,
        "has_name": 0.15,
        "has_address": 0.10,
        "has_city_state": 0.10,
        "has_date": 0.15,
        "has_score": 0.20,
        "has_property_type": 0.05,
        "has_units": 0.05,
    }

    if record.get("inspection_id"):
        score += weights["has_inspection_id"]
    if record.get("property_id"):
        score += weights["has_property_id"]
    if record.get("property_name"):
        score += weights["has_name"]
    if record.get("address"):
        score += weights["has_address"]
    if record.get("city") and record.get("state"):
        score += weights["has_city_state"]
    if record.get("inspection_date"):
        score += weights["has_date"]
    if record.get("inspection_score") is not None:
        score += weights["has_score"]
    if record.get("property_type"):
        score += weights["has_property_type"]
    if _safe_int(record.get("units")) and _safe_int(record.get("units")) > 0:
        score += weights["has_units"]

    return round(min(score, 1.0), 3)


def score_section8(record: dict) -> float:
    """Score a Section 8 contract record (0.0 - 1.0)."""
    score = 0.0
    weights = {
        "has_contract_id": 0.10,
        "has_name": 0.15,
        "has_address": 0.10,
        "has_city_state": 0.10,
        "has_owner": 0.10,
        "has_program_type": 0.10,
        "has_dates": 0.10,
        "has_units": 0.10,
        "has_financials": 0.10,
        "has_coords": 0.05,
    }

    if record.get("contract_id"):
        score += weights["has_contract_id"]
    if record.get("property_name"):
        score += weights["has_name"]
    if record.get("address"):
        score += weights["has_address"]
    if record.get("city") and record.get("state"):
        score += weights["has_city_state"]
    if record.get("owner_name"):
        score += weights["has_owner"]
    if record.get("program_type"):
        score += weights["has_program_type"]
    if record.get("contract_start_date") or record.get("contract_end_date"):
        score += weights["has_dates"]
    if _safe_int(record.get("assisted_units")) and _safe_int(record.get("assisted_units")) > 0:
        score += weights["has_units"]
    if _safe_float(record.get("annual_expense")) and _safe_float(record.get("annual_expense")) > 0:
        score += weights["has_financials"]
    if record.get("latitude") and record.get("longitude"):
        score += weights["has_coords"]

    return round(min(score, 1.0), 3)


def score_multifamily(record: dict) -> float:
    """Score a multifamily property record (0.0 - 1.0)."""
    score = 0.0
    weights = {
        "has_property_id": 0.10,
        "has_name": 0.15,
        "has_address": 0.15,
        "has_city_state": 0.10,
        "has_owner": 0.10,
        "has_program_type": 0.10,
        "has_units": 0.10,
        "has_category": 0.10,
        "has_coords": 0.05,
        "has_subsidy_flags": 0.05,
    }

    if record.get("property_id"):
        score += weights["has_property_id"]
    if record.get("property_name"):
        score += weights["has_name"]
    if record.get("address"):
        score += weights["has_address"]
    if record.get("city") and record.get("state"):
        score += weights["has_city_state"]
    if record.get("owner_name"):
        score += weights["has_owner"]
    if record.get("program_type"):
        score += weights["has_program_type"]
    if _safe_int(record.get("total_units")) and _safe_int(record.get("total_units")) > 0:
        score += weights["has_units"]
    if record.get("property_category"):
        score += weights["has_category"]
    if record.get("latitude") and record.get("longitude"):
        score += weights["has_coords"]
    has_any_flag = any([
        record.get("has_section_8"), record.get("has_lihtc"),
        record.get("has_section_202"), record.get("has_section_811"),
    ])
    if has_any_flag:
        score += weights["has_subsidy_flags"]

    return round(min(score, 1.0), 3)


def _safe_int(val) -> int | None:
    """Safely convert to int."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    """Safely convert to float."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
