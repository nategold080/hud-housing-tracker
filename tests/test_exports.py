"""Tests for export module."""

import json
import sqlite3
import pytest
from pathlib import Path

from src.storage.database import init_db, upsert_lihtc, upsert_reac
from src.export.exporter import export_all


@pytest.fixture
def populated_db(tmp_path):
    """Create a populated test database."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_db(conn)

    upsert_lihtc(conn, [{
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
        "owner": "Test Owner",
        "mgmt_company": None,
        "source_file": "test",
        "quality_score": 0.9,
    }])

    upsert_reac(conn, [{
        "inspection_id": "INS001",
        "property_id": "PROP001",
        "property_name": "Test",
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

    return conn


class TestExportCsv:
    def test_exports_csv(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.setattr("src.export.exporter.EXPORT_DIR", tmp_path)
        results = export_all(populated_db, fmt="csv")
        assert "csv" in results
        assert len(results["csv"]) >= 2  # lihtc + reac


class TestExportJson:
    def test_exports_json(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.setattr("src.export.exporter.EXPORT_DIR", tmp_path)
        results = export_all(populated_db, fmt="json")
        assert "json" in results

        data = json.loads(Path(results["json"]).read_text())
        assert "lihtc_projects" in data
        assert len(data["lihtc_projects"]) == 1


class TestExportMarkdown:
    def test_exports_markdown(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.setattr("src.export.exporter.EXPORT_DIR", tmp_path)
        results = export_all(populated_db, fmt="markdown")
        assert "markdown" in results

        content = Path(results["markdown"]).read_text()
        assert "HUD Affordable Housing" in content
        assert "Nathan Goldberg" in content
