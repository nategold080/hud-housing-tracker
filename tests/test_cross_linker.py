"""Tests for cross-linking engine."""

import sqlite3
import pytest
from src.storage.database import init_db, upsert_lihtc, upsert_reac, upsert_multifamily
from src.normalization.cross_linker import cross_link_all, _link_by_property_id, _build_owner_profiles


@pytest.fixture
def db():
    """Create an in-memory database with sample data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


@pytest.fixture
def populated_db(db):
    """Database with sample records for cross-linking."""
    # LIHTC project
    upsert_lihtc(db, [{
        "hud_id": "OH001",
        "project_name": "Test Apartments",
        "address": "100 Main St",
        "city": "Columbus",
        "state": "OH",
        "zip_code": "43215",
        "county_fips": None,
        "latitude": 39.96,
        "longitude": -82.99,
        "total_units": 100,
        "li_units": 80,
        "credit_type": "4%",
        "placed_in_service_year": 2020,
        "allocation_year": 2019,
        "yr_pis": 2020,
        "yr_alloc": 2019,
        "congress_dist": None,
        "census_tract": None,
        "scattered_site": 0,
        "sec8_contract": None,
        "owner": "ABC Housing LLC",
        "mgmt_company": None,
        "source_file": "test",
        "quality_score": 0.9,
    }])

    # Multifamily property at same address
    upsert_multifamily(db, [{
        "property_id": "800001",
        "property_name": "Test Apartments",
        "address": "100 Main St",
        "city": "Columbus",
        "state": "OH",
        "zip_code": "43215",
        "county_code": None,
        "congress_dist": None,
        "owner_name": "ABC Housing LLC",
        "mgmt_agent": None,
        "program_type": "LMSA",
        "assisted_units": 80,
        "total_units": 100,
        "has_section_8": 1,
        "has_lihtc": 1,
        "has_section_202": 0,
        "has_section_811": 0,
        "property_category": "Family",
        "latitude": 39.96,
        "longitude": -82.99,
        "source_file": "test",
        "quality_score": 0.85,
    }])

    # REAC inspection for same property
    upsert_reac(db, [{
        "inspection_id": "INS001",
        "property_id": "800001",
        "property_name": "Test Apartments",
        "address": "100 Main St",
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
    }])

    return db


class TestLinkByPropertyId:
    def test_links_mf_to_reac(self, populated_db):
        n = _link_by_property_id(populated_db)
        assert n == 1

        links = populated_db.execute("SELECT * FROM cross_links").fetchall()
        assert len(links) == 1
        assert links[0]["source_type"] == "multifamily"
        assert links[0]["target_type"] == "reac"
        assert links[0]["confidence"] == 1.0

    def test_no_match(self, db):
        upsert_multifamily(db, [{
            "property_id": "800001", "property_name": "Test",
            "address": None, "city": None, "state": "OH", "zip_code": None,
            "county_code": None, "congress_dist": None,
            "owner_name": None, "mgmt_agent": None, "program_type": None,
            "assisted_units": None, "total_units": 50,
            "has_section_8": 0, "has_lihtc": 0, "has_section_202": 0,
            "has_section_811": 0, "property_category": None,
            "latitude": None, "longitude": None,
            "source_file": "test", "quality_score": 0.5,
        }])
        n = _link_by_property_id(db)
        assert n == 0


class TestCrossLinkAll:
    def test_full_pipeline(self, populated_db):
        stats = cross_link_all(populated_db)
        assert stats["multifamily_to_reac"] == 1
        assert stats["lihtc_to_multifamily"] >= 1
        assert stats["total_links"] >= 2

    def test_empty_db(self, db):
        stats = cross_link_all(db)
        assert stats["total_links"] == 0


class TestBuildOwnerProfiles:
    def test_creates_profiles(self, populated_db):
        n = _build_owner_profiles(populated_db)
        assert n >= 1

        owners = populated_db.execute("SELECT * FROM owners").fetchall()
        assert len(owners) >= 1

        # Check that our test owner exists
        abc = [o for o in owners if "ABC" in o["normalized_name"]]
        assert len(abc) == 1
        assert abc[0]["property_count"] >= 1
        assert abc[0]["avg_inspection_score"] == 85.0
