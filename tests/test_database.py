"""Tests for HUD housing database operations."""

import sqlite3
import pytest
from src.storage.database import (
    get_connection, init_db, upsert_lihtc, upsert_reac,
    upsert_section8, upsert_multifamily, insert_cross_links, get_stats,
)


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


class TestInitDb:
    def test_tables_created(self, db):
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [t[0] for t in tables]
        assert "lihtc_projects" in names
        assert "reac_inspections" in names
        assert "section8_contracts" in names
        assert "multifamily_properties" in names
        assert "cross_links" in names
        assert "owners" in names

    def test_indexes_created(self, db):
        indexes = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        names = [i[0] for i in indexes]
        assert len(names) >= 10


class TestUpsertLihtc:
    def test_insert(self, db):
        records = [{
            "hud_id": "OH001",
            "project_name": "Test Project",
            "address": "123 Main St",
            "city": "Columbus",
            "state": "OH",
            "zip_code": "43215",
            "county_fips": "39049",
            "latitude": 39.96,
            "longitude": -82.99,
            "total_units": 100,
            "li_units": 80,
            "credit_type": "4%",
            "placed_in_service_year": 2020,
            "allocation_year": 2019,
            "yr_pis": 2020,
            "yr_alloc": 2019,
            "congress_dist": "OH-03",
            "census_tract": "001234",
            "scattered_site": 0,
            "sec8_contract": None,
            "owner": "Test Owner LLC",
            "mgmt_company": "Test Mgmt",
            "source_file": "test",
            "quality_score": 0.95,
        }]
        count = upsert_lihtc(db, records)
        assert count == 1

        row = db.execute("SELECT * FROM lihtc_projects WHERE hud_id = 'OH001'").fetchone()
        assert row["project_name"] == "Test Project"
        assert row["total_units"] == 100

    def test_upsert_updates(self, db):
        rec = {
            "hud_id": "OH001", "project_name": "V1", "address": None,
            "city": None, "state": "OH", "zip_code": None,
            "county_fips": None, "latitude": None, "longitude": None,
            "total_units": 50, "li_units": 40, "credit_type": None,
            "placed_in_service_year": None, "allocation_year": None,
            "yr_pis": None, "yr_alloc": None, "congress_dist": None,
            "census_tract": None, "scattered_site": 0, "sec8_contract": None,
            "owner": None, "mgmt_company": None, "source_file": "test",
            "quality_score": 0.5,
        }
        upsert_lihtc(db, [rec])
        rec["project_name"] = "V2"
        rec["total_units"] = 60
        upsert_lihtc(db, [rec])

        row = db.execute("SELECT * FROM lihtc_projects WHERE hud_id = 'OH001'").fetchone()
        assert row["project_name"] == "V2"
        assert row["total_units"] == 60


class TestUpsertReac:
    def test_insert(self, db):
        records = [{
            "inspection_id": "INS001",
            "property_id": "PROP001",
            "property_name": "Test Property",
            "address": "123 Main St",
            "city": "Columbus",
            "state": "OH",
            "zip_code": "43215",
            "inspection_date": "2024-01-15",
            "inspection_score": 85.0,
            "health_flag": 0,
            "smoke_detector_flag": 0,
            "property_type": "Multifamily",
            "units": 100,
            "rass_date": None,
            "source_file": "test",
            "quality_score": 0.9,
        }]
        count = upsert_reac(db, records)
        assert count == 1

        row = db.execute("SELECT * FROM reac_inspections WHERE inspection_id = 'INS001'").fetchone()
        assert row["inspection_score"] == 85.0


class TestUpsertSection8:
    def test_insert(self, db):
        records = [{
            "contract_id": "C001",
            "property_id": "P001",
            "property_name": "Test",
            "address": "123 Main",
            "city": "Columbus",
            "state": "OH",
            "zip_code": "43215",
            "county_code": "049",
            "congress_dist": "OH-03",
            "owner_name": "Test Owner",
            "owner_type": "For-Profit",
            "mgmt_agent": "Test Mgmt",
            "program_type": "LMSA",
            "contract_term_months": 240,
            "contract_start_date": "2020-01-01",
            "contract_end_date": "2040-01-01",
            "assisted_units": 50,
            "total_units": 60,
            "annual_expense": 500000.0,
            "rent_per_month": 900.0,
            "latitude": 39.96,
            "longitude": -82.99,
            "source_file": "test",
            "quality_score": 0.85,
        }]
        count = upsert_section8(db, records)
        assert count == 1


class TestCrossLinks:
    def test_insert(self, db):
        links = [{
            "source_type": "lihtc",
            "source_id": "OH001",
            "target_type": "reac",
            "target_id": "INS001",
            "link_method": "property_id",
            "confidence": 0.95,
        }]
        count = insert_cross_links(db, links)
        assert count == 1


class TestGetStats:
    def test_empty_db(self, db):
        stats = get_stats(db)
        assert stats["lihtc_projects"] == 0
        assert stats["reac_inspections"] == 0

    def test_with_data(self, db):
        rec = {
            "hud_id": "OH001", "project_name": "Test", "address": None,
            "city": None, "state": "OH", "zip_code": None,
            "county_fips": None, "latitude": None, "longitude": None,
            "total_units": 100, "li_units": 80, "credit_type": None,
            "placed_in_service_year": None, "allocation_year": None,
            "yr_pis": None, "yr_alloc": None, "congress_dist": None,
            "census_tract": None, "scattered_site": 0, "sec8_contract": None,
            "owner": None, "mgmt_company": None, "source_file": "test",
            "quality_score": 0.8,
        }
        upsert_lihtc(db, [rec])
        stats = get_stats(db)
        assert stats["lihtc_projects"] == 1
        assert stats["lihtc_states"] == 1
        assert stats["total_lihtc_units"] == 100
