"""Cross-linking engine for HUD housing data.

Links LIHTC projects, multifamily properties, REAC inspections,
and Section 8 contracts using:
1. Property ID matching (direct)
2. Address-based matching (normalized)
3. Contract number matching
4. Owner profile aggregation
"""

import sqlite3
from collections import defaultdict

from rapidfuzz import fuzz

from src.normalization.addresses import (
    normalize_address, normalize_city, normalize_state,
    normalize_zip, normalize_owner_name, make_match_key,
)


def cross_link_all(conn: sqlite3.Connection) -> dict:
    """Run all cross-linking strategies and return summary stats."""
    stats = {
        "lihtc_to_reac": 0,
        "lihtc_to_sec8": 0,
        "lihtc_to_multifamily": 0,
        "multifamily_to_reac": 0,
        "address_matches": 0,
        "total_links": 0,
    }

    # Clear existing cross-links
    conn.execute("DELETE FROM cross_links")
    conn.commit()

    # Stage 1: Property ID matching (multifamily → REAC)
    n = _link_by_property_id(conn)
    stats["multifamily_to_reac"] = n
    stats["total_links"] += n

    # Stage 2: Address-based matching (LIHTC → multifamily)
    n = _link_lihtc_to_multifamily(conn)
    stats["lihtc_to_multifamily"] = n
    stats["total_links"] += n

    # Stage 3: Contract number matching (LIHTC → Section 8)
    n = _link_by_contract(conn)
    stats["lihtc_to_sec8"] = n
    stats["total_links"] += n

    # Stage 4: Address-based LIHTC → REAC
    n = _link_lihtc_to_reac(conn)
    stats["lihtc_to_reac"] = n
    stats["total_links"] += n

    # Stage 5: Build owner profiles
    _build_owner_profiles(conn)

    return stats


def _link_by_property_id(conn: sqlite3.Connection) -> int:
    """Link multifamily properties to REAC inspections by property_id."""
    rows = conn.execute("""
        SELECT m.property_id, r.inspection_id
        FROM multifamily_properties m
        JOIN reac_inspections r ON m.property_id = r.property_id
    """).fetchall()

    links = []
    for row in rows:
        links.append({
            "source_type": "multifamily",
            "source_id": row[0],
            "target_type": "reac",
            "target_id": row[1],
            "link_method": "property_id",
            "confidence": 1.0,
        })

    if links:
        _insert_links(conn, links)
    return len(links)


def _link_lihtc_to_multifamily(conn: sqlite3.Connection) -> int:
    """Link LIHTC projects to multifamily properties by address."""
    # Build address index for multifamily properties
    mf_rows = conn.execute("""
        SELECT property_id, address, city, state, zip_code
        FROM multifamily_properties
        WHERE address IS NOT NULL AND address != ''
    """).fetchall()

    mf_index = {}
    for row in mf_rows:
        key = make_match_key(row[1], row[2], row[3], row[4])
        if key:
            mf_index[key] = row[0]

    # Match LIHTC projects
    lihtc_rows = conn.execute("""
        SELECT hud_id, address, city, state, zip_code
        FROM lihtc_projects
        WHERE address IS NOT NULL AND address != ''
    """).fetchall()

    links = []
    for row in lihtc_rows:
        key = make_match_key(row[1], row[2], row[3], row[4])
        if key and key in mf_index:
            links.append({
                "source_type": "lihtc",
                "source_id": row[0],
                "target_type": "multifamily",
                "target_id": mf_index[key],
                "link_method": "address_match",
                "confidence": 0.9,
            })

    # Fuzzy matching for remaining unlinked LIHTC records
    linked_lihtc = {l["source_id"] for l in links}
    unlinked = [r for r in lihtc_rows if r[0] not in linked_lihtc]

    for row in unlinked:
        lihtc_key = make_match_key(row[1], row[2], row[3], row[4])
        if not lihtc_key:
            continue

        best_score = 0
        best_mf_id = None
        lihtc_state = normalize_state(row[3])

        for mf_key, mf_id in mf_index.items():
            # Only fuzzy match within same state
            if lihtc_state and lihtc_state in mf_key:
                score = fuzz.token_sort_ratio(lihtc_key, mf_key)
                if score > best_score and score >= 85:
                    best_score = score
                    best_mf_id = mf_id

        if best_mf_id:
            links.append({
                "source_type": "lihtc",
                "source_id": row[0],
                "target_type": "multifamily",
                "target_id": best_mf_id,
                "link_method": "fuzzy_address",
                "confidence": round(best_score / 100, 2),
            })

    if links:
        _insert_links(conn, links)
    return len(links)


def _link_by_contract(conn: sqlite3.Connection) -> int:
    """Link LIHTC projects to Section 8 contracts by contract number."""
    rows = conn.execute("""
        SELECT l.hud_id, s.contract_id
        FROM lihtc_projects l
        JOIN section8_contracts s ON l.sec8_contract = s.contract_id
        WHERE l.sec8_contract IS NOT NULL AND l.sec8_contract != ''
    """).fetchall()

    links = []
    for row in rows:
        links.append({
            "source_type": "lihtc",
            "source_id": row[0],
            "target_type": "section8",
            "target_id": row[1],
            "link_method": "contract_number",
            "confidence": 1.0,
        })

    if links:
        _insert_links(conn, links)
    return len(links)


def _link_lihtc_to_reac(conn: sqlite3.Connection) -> int:
    """Link LIHTC projects to REAC inspections via address matching."""
    # Build REAC address index
    reac_rows = conn.execute("""
        SELECT inspection_id, address, city, state, zip_code
        FROM reac_inspections
        WHERE address IS NOT NULL AND address != ''
    """).fetchall()

    reac_index = {}
    for row in reac_rows:
        key = make_match_key(row[1], row[2], row[3], row[4])
        if key:
            if key not in reac_index:
                reac_index[key] = []
            reac_index[key].append(row[0])

    # Match LIHTC
    lihtc_rows = conn.execute("""
        SELECT hud_id, address, city, state, zip_code
        FROM lihtc_projects
        WHERE address IS NOT NULL AND address != ''
    """).fetchall()

    links = []
    for row in lihtc_rows:
        key = make_match_key(row[1], row[2], row[3], row[4])
        if key and key in reac_index:
            for reac_id in reac_index[key]:
                links.append({
                    "source_type": "lihtc",
                    "source_id": row[0],
                    "target_type": "reac",
                    "target_id": reac_id,
                    "link_method": "address_match",
                    "confidence": 0.85,
                })

    if links:
        _insert_links(conn, links)
    return len(links)


def _build_owner_profiles(conn: sqlite3.Connection) -> int:
    """Build aggregated owner profiles from all data sources."""
    conn.execute("DELETE FROM owners")

    owner_data = defaultdict(lambda: {
        "names": set(),
        "properties": set(),
        "total_units": 0,
        "scores": [],
        "states": set(),
        "sources": set(),
    })

    # From LIHTC (owner and mgmt_company fields)
    for field in ["owner", "mgmt_company"]:
        rows = conn.execute(f"""
            SELECT {field}, hud_id, total_units, state FROM lihtc_projects
            WHERE {field} IS NOT NULL AND {field} != ''
        """).fetchall()
        for row in rows:
            key = normalize_owner_name(row[0])
            if key:
                owner_data[key]["names"].add(row[0])
                owner_data[key]["properties"].add(row[1])
                owner_data[key]["total_units"] += (row[2] or 0)
                if row[3]:
                    owner_data[key]["states"].add(row[3])
                owner_data[key]["sources"].add("lihtc")

    # From multifamily (owner_name = management agent org name)
    rows = conn.execute("""
        SELECT owner_name, property_id, total_units, state FROM multifamily_properties
        WHERE owner_name IS NOT NULL AND owner_name != ''
    """).fetchall()
    for row in rows:
        key = normalize_owner_name(row[0])
        if key:
            owner_data[key]["names"].add(row[0])
            owner_data[key]["properties"].add(row[1])
            owner_data[key]["total_units"] += (row[2] or 0)
            if row[3]:
                owner_data[key]["states"].add(row[3])
            owner_data[key]["sources"].add("multifamily")

    # From Section 8
    rows = conn.execute("""
        SELECT owner_name, contract_id, assisted_units, state FROM section8_contracts
        WHERE owner_name IS NOT NULL AND owner_name != ''
    """).fetchall()
    for row in rows:
        key = normalize_owner_name(row[0])
        if key:
            owner_data[key]["names"].add(row[0])
            owner_data[key]["properties"].add(row[1])
            owner_data[key]["total_units"] += (row[2] or 0)
            if row[3]:
                owner_data[key]["states"].add(row[3])
            owner_data[key]["sources"].add("section8")

    # Get inspection scores for owner properties
    reac_scores = {}
    rows = conn.execute("""
        SELECT property_id, inspection_score FROM reac_inspections
        WHERE inspection_score IS NOT NULL
    """).fetchall()
    for row in rows:
        reac_scores[str(row[0])] = row[1]

    # Insert owner profiles
    owner_id = 0
    records = []
    for norm_name, data in owner_data.items():
        owner_id += 1
        scores = [reac_scores[p] for p in data["properties"] if p in reac_scores]

        records.append({
            "owner_id": owner_id,
            "owner_name": sorted(data["names"])[0],
            "normalized_name": norm_name,
            "property_count": len(data["properties"]),
            "total_units": data["total_units"],
            "avg_inspection_score": round(sum(scores) / len(scores), 1) if scores else None,
            "min_inspection_score": min(scores) if scores else None,
            "failed_inspections": sum(1 for s in scores if s < 60),
            "states_active": ",".join(sorted(data["states"])),
            "source_types": ",".join(sorted(data["sources"])),
            "quality_score": 0.8,
        })

    if records:
        for rec in records:
            conn.execute("""
                INSERT OR REPLACE INTO owners (
                    owner_id, owner_name, normalized_name, property_count,
                    total_units, avg_inspection_score, min_inspection_score,
                    failed_inspections, states_active, source_types,
                    quality_score, updated_at
                ) VALUES (
                    :owner_id, :owner_name, :normalized_name, :property_count,
                    :total_units, :avg_inspection_score, :min_inspection_score,
                    :failed_inspections, :states_active, :source_types,
                    :quality_score, datetime('now')
                )
            """, rec)
        conn.commit()

    return len(records)


def _insert_links(conn: sqlite3.Connection, links: list[dict]) -> None:
    """Batch insert cross-links."""
    for link in links:
        conn.execute("""
            INSERT INTO cross_links (
                source_type, source_id, target_type, target_id,
                link_method, confidence
            ) VALUES (
                :source_type, :source_id, :target_type, :target_id,
                :link_method, :confidence
            )
        """, link)
    conn.commit()
