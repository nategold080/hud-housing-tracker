"""SQLite database for HUD Affordable Housing Compliance Tracker."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "hud_housing.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get a database connection with WAL mode."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Create all tables."""
    close = False
    if conn is None:
        conn = get_connection()
        close = True

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lihtc_projects (
            hud_id TEXT PRIMARY KEY,
            project_name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            county_fips TEXT,
            latitude REAL,
            longitude REAL,
            total_units INTEGER,
            li_units INTEGER,
            credit_type TEXT,
            placed_in_service_year INTEGER,
            allocation_year INTEGER,
            yr_pis INTEGER,
            yr_alloc INTEGER,
            congress_dist TEXT,
            census_tract TEXT,
            scattered_site INTEGER DEFAULT 0,
            sec8_contract TEXT,
            owner TEXT,
            mgmt_company TEXT,
            source_file TEXT,
            quality_score REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reac_inspections (
            inspection_id TEXT PRIMARY KEY,
            property_id TEXT,
            property_name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            inspection_date TEXT,
            inspection_score REAL,
            health_flag INTEGER DEFAULT 0,
            smoke_detector_flag INTEGER DEFAULT 0,
            property_type TEXT,
            units INTEGER,
            rass_date TEXT,
            source_file TEXT,
            quality_score REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS section8_contracts (
            contract_id TEXT PRIMARY KEY,
            property_id TEXT,
            property_name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            county_code TEXT,
            congress_dist TEXT,
            owner_name TEXT,
            owner_type TEXT,
            mgmt_agent TEXT,
            program_type TEXT,
            contract_term_months INTEGER,
            contract_start_date TEXT,
            contract_end_date TEXT,
            assisted_units INTEGER,
            total_units INTEGER,
            annual_expense REAL,
            rent_per_month REAL,
            latitude REAL,
            longitude REAL,
            source_file TEXT,
            quality_score REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS multifamily_properties (
            property_id TEXT PRIMARY KEY,
            property_name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            county_code TEXT,
            congress_dist TEXT,
            owner_name TEXT,
            mgmt_agent TEXT,
            program_type TEXT,
            assisted_units INTEGER,
            total_units INTEGER,
            has_section_8 INTEGER DEFAULT 0,
            has_lihtc INTEGER DEFAULT 0,
            has_section_202 INTEGER DEFAULT 0,
            has_section_811 INTEGER DEFAULT 0,
            property_category TEXT,
            latitude REAL,
            longitude REAL,
            source_file TEXT,
            quality_score REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cross_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            link_method TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS owners (
            owner_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            property_count INTEGER DEFAULT 0,
            total_units INTEGER DEFAULT 0,
            avg_inspection_score REAL,
            min_inspection_score REAL,
            failed_inspections INTEGER DEFAULT 0,
            states_active TEXT,
            source_types TEXT,
            quality_score REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_lihtc_state ON lihtc_projects(state);
        CREATE INDEX IF NOT EXISTS idx_lihtc_zip ON lihtc_projects(zip_code);
        CREATE INDEX IF NOT EXISTS idx_lihtc_owner ON lihtc_projects(owner);
        CREATE INDEX IF NOT EXISTS idx_lihtc_sec8 ON lihtc_projects(sec8_contract);
        CREATE INDEX IF NOT EXISTS idx_lihtc_pis_year ON lihtc_projects(placed_in_service_year);

        CREATE INDEX IF NOT EXISTS idx_reac_property ON reac_inspections(property_id);
        CREATE INDEX IF NOT EXISTS idx_reac_state ON reac_inspections(state);
        CREATE INDEX IF NOT EXISTS idx_reac_score ON reac_inspections(inspection_score);
        CREATE INDEX IF NOT EXISTS idx_reac_date ON reac_inspections(inspection_date);

        CREATE INDEX IF NOT EXISTS idx_sec8_state ON section8_contracts(state);
        CREATE INDEX IF NOT EXISTS idx_sec8_owner ON section8_contracts(owner_name);
        CREATE INDEX IF NOT EXISTS idx_sec8_property ON section8_contracts(property_id);
        CREATE INDEX IF NOT EXISTS idx_sec8_end ON section8_contracts(contract_end_date);

        CREATE INDEX IF NOT EXISTS idx_mf_state ON multifamily_properties(state);
        CREATE INDEX IF NOT EXISTS idx_mf_owner ON multifamily_properties(owner_name);

        CREATE INDEX IF NOT EXISTS idx_xlink_source
            ON cross_links(source_type, source_id);
        CREATE INDEX IF NOT EXISTS idx_xlink_target
            ON cross_links(target_type, target_id);

        CREATE INDEX IF NOT EXISTS idx_owners_name ON owners(normalized_name);
    """)
    conn.commit()

    if close:
        conn.close()


def upsert_lihtc(conn: sqlite3.Connection, records: list[dict]) -> int:
    """Insert or update LIHTC project records."""
    inserted = 0
    for rec in records:
        conn.execute("""
            INSERT OR REPLACE INTO lihtc_projects (
                hud_id, project_name, address, city, state, zip_code,
                county_fips, latitude, longitude, total_units, li_units,
                credit_type, placed_in_service_year, allocation_year,
                yr_pis, yr_alloc, congress_dist, census_tract,
                scattered_site, sec8_contract, owner, mgmt_company,
                source_file, quality_score, updated_at
            ) VALUES (
                :hud_id, :project_name, :address, :city, :state, :zip_code,
                :county_fips, :latitude, :longitude, :total_units, :li_units,
                :credit_type, :placed_in_service_year, :allocation_year,
                :yr_pis, :yr_alloc, :congress_dist, :census_tract,
                :scattered_site, :sec8_contract, :owner, :mgmt_company,
                :source_file, :quality_score, datetime('now')
            )
        """, rec)
        inserted += 1
    conn.commit()
    return inserted


def upsert_reac(conn: sqlite3.Connection, records: list[dict]) -> int:
    """Insert or update REAC inspection records."""
    inserted = 0
    for rec in records:
        conn.execute("""
            INSERT OR REPLACE INTO reac_inspections (
                inspection_id, property_id, property_name, address, city,
                state, zip_code, inspection_date, inspection_score,
                health_flag, smoke_detector_flag, property_type, units,
                rass_date, source_file, quality_score, updated_at
            ) VALUES (
                :inspection_id, :property_id, :property_name, :address,
                :city, :state, :zip_code, :inspection_date, :inspection_score,
                :health_flag, :smoke_detector_flag, :property_type, :units,
                :rass_date, :source_file, :quality_score, datetime('now')
            )
        """, rec)
        inserted += 1
    conn.commit()
    return inserted


def upsert_section8(conn: sqlite3.Connection, records: list[dict]) -> int:
    """Insert or update Section 8 contract records."""
    inserted = 0
    for rec in records:
        conn.execute("""
            INSERT OR REPLACE INTO section8_contracts (
                contract_id, property_id, property_name, address, city,
                state, zip_code, county_code, congress_dist,
                owner_name, owner_type, mgmt_agent, program_type,
                contract_term_months, contract_start_date, contract_end_date,
                assisted_units, total_units, annual_expense, rent_per_month,
                latitude, longitude, source_file, quality_score, updated_at
            ) VALUES (
                :contract_id, :property_id, :property_name, :address,
                :city, :state, :zip_code, :county_code, :congress_dist,
                :owner_name, :owner_type, :mgmt_agent, :program_type,
                :contract_term_months, :contract_start_date, :contract_end_date,
                :assisted_units, :total_units, :annual_expense, :rent_per_month,
                :latitude, :longitude, :source_file, :quality_score, datetime('now')
            )
        """, rec)
        inserted += 1
    conn.commit()
    return inserted


def upsert_multifamily(conn: sqlite3.Connection, records: list[dict]) -> int:
    """Insert or update multifamily property records."""
    inserted = 0
    for rec in records:
        conn.execute("""
            INSERT OR REPLACE INTO multifamily_properties (
                property_id, property_name, address, city, state, zip_code,
                county_code, congress_dist, owner_name, mgmt_agent,
                program_type, assisted_units, total_units,
                has_section_8, has_lihtc, has_section_202, has_section_811,
                property_category, latitude, longitude,
                source_file, quality_score, updated_at
            ) VALUES (
                :property_id, :property_name, :address, :city, :state,
                :zip_code, :county_code, :congress_dist, :owner_name,
                :mgmt_agent, :program_type, :assisted_units, :total_units,
                :has_section_8, :has_lihtc, :has_section_202, :has_section_811,
                :property_category, :latitude, :longitude,
                :source_file, :quality_score, datetime('now')
            )
        """, rec)
        inserted += 1
    conn.commit()
    return inserted


def insert_cross_links(conn: sqlite3.Connection, links: list[dict]) -> int:
    """Insert cross-link records."""
    inserted = 0
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
        inserted += 1
    conn.commit()
    return inserted


def upsert_owners(conn: sqlite3.Connection, records: list[dict]) -> int:
    """Insert or update owner profile records."""
    inserted = 0
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
        inserted += 1
    conn.commit()
    return inserted


def get_stats(conn: sqlite3.Connection | None = None) -> dict:
    """Get database statistics."""
    close = False
    if conn is None:
        conn = get_connection()
        close = True

    stats = {}
    for table in ["lihtc_projects", "reac_inspections", "section8_contracts",
                   "multifamily_properties", "cross_links", "owners"]:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        stats[table] = row[0]

    # Quality averages
    for table in ["lihtc_projects", "reac_inspections", "section8_contracts",
                   "multifamily_properties"]:
        row = conn.execute(
            f"SELECT AVG(quality_score) FROM {table} WHERE quality_score > 0"
        ).fetchone()
        stats[f"{table}_quality_avg"] = round(row[0], 3) if row[0] else 0.0

    # REAC-specific stats
    row = conn.execute(
        "SELECT AVG(inspection_score) FROM reac_inspections WHERE inspection_score > 0"
    ).fetchone()
    stats["avg_inspection_score"] = round(row[0], 1) if row[0] else 0.0

    row = conn.execute(
        "SELECT COUNT(*) FROM reac_inspections WHERE inspection_score < 60"
    ).fetchone()
    stats["failing_inspections"] = row[0]

    # State counts
    row = conn.execute(
        "SELECT COUNT(DISTINCT state) FROM lihtc_projects WHERE state IS NOT NULL"
    ).fetchone()
    stats["lihtc_states"] = row[0]

    # Total units
    row = conn.execute(
        "SELECT SUM(total_units) FROM lihtc_projects WHERE total_units > 0"
    ).fetchone()
    stats["total_lihtc_units"] = row[0] or 0

    if close:
        conn.close()
    return stats
