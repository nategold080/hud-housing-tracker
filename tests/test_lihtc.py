"""Tests for LIHTC scraper."""

import csv
import tempfile
from pathlib import Path

import pytest
from src.scrapers.lihtc import parse_lihtc, _parse_lihtc_row, _safe_int, _safe_float, _normalize_zip


class TestSafeInt:
    def test_valid(self):
        assert _safe_int("42") == 42

    def test_float_string(self):
        assert _safe_int("42.0") == 42

    def test_empty(self):
        assert _safe_int("") is None

    def test_dot(self):
        assert _safe_int(".") is None

    def test_none(self):
        assert _safe_int(None) is None

    def test_9999(self):
        assert _safe_int("9999") is None


class TestSafeFloat:
    def test_valid(self):
        assert _safe_float("39.96") == 39.96

    def test_empty(self):
        assert _safe_float("") is None

    def test_dot(self):
        assert _safe_float(".") is None


class TestNormalizeZip:
    def test_five_digit(self):
        assert _normalize_zip("43215") == "43215"

    def test_nine_digit(self):
        assert _normalize_zip("43215-1234") == "43215"

    def test_short(self):
        assert _normalize_zip("6103") == "06103"

    def test_empty(self):
        assert _normalize_zip("") == ""


class TestParseLihtcRow:
    def test_basic_row(self):
        row = {
            "HUD_ID": "OH12345",
            "PROJECT": "Test Apartments",
            "PROJ_ADD": "100 Main St",
            "PROJ_CTY": "Columbus",
            "PROJ_ST": "OH",
            "PROJ_ZIP": "43215",
            "N_UNITS": "100",
            "LI_UNITS": "80",
            "TYPE": "4%",
            "YR_PIS": "2020",
            "YR_ALLOC": "2019",
            "LATITUDE": "39.96",
            "LONGITUDE": "-82.99",
            "OWNER": "Test Housing LLC",
        }
        rec = _parse_lihtc_row(row)
        assert rec is not None
        assert rec["hud_id"] == "OH12345"
        assert rec["project_name"] == "Test Apartments"
        assert rec["total_units"] == 100
        assert rec["li_units"] == 80
        assert rec["placed_in_service_year"] == 2020
        assert rec["owner"] == "Test Housing LLC"

    def test_no_hud_id(self):
        row = {"HUD_ID": "", "PROJECT": "Test"}
        assert _parse_lihtc_row(row) is None

    def test_lowercase_fields(self):
        """Some CSV files use lowercase field names."""
        row = {
            "hud_id": "CA001",
            "project": "Test",
            "proj_st": "CA",
            "n_units": "50",
        }
        rec = _parse_lihtc_row(row)
        assert rec is not None
        assert rec["hud_id"] == "CA001"
        assert rec["state"] == "CA"
        assert rec["total_units"] == 50

    def test_scattered_site(self):
        row = {"HUD_ID": "OH001", "SCATTERED_SITE_IND": "Y"}
        rec = _parse_lihtc_row(row)
        assert rec["scattered_site"] == 1


class TestParseLihtcCsv:
    def test_parse_from_file(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["HUD_ID", "PROJECT", "PROJ_ST", "N_UNITS"])
            writer.writeheader()
            writer.writerow({"HUD_ID": "OH001", "PROJECT": "Test 1", "PROJ_ST": "OH", "N_UNITS": "100"})
            writer.writerow({"HUD_ID": "CA001", "PROJECT": "Test 2", "PROJ_ST": "CA", "N_UNITS": "200"})
            writer.writerow({"HUD_ID": "", "PROJECT": "No ID", "PROJ_ST": "TX", "N_UNITS": "50"})

        records = parse_lihtc(csv_path)
        assert len(records) == 2
        assert records[0]["hud_id"] == "OH001"
        assert records[1]["state"] == "CA"
