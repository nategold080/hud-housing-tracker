"""Tests for HUD housing quality scoring."""

import pytest
from src.validation.quality import (
    score_lihtc, score_reac, score_section8, score_multifamily,
    _safe_int, _safe_float,
)


class TestSafeInt:
    def test_valid_int(self):
        assert _safe_int(42) == 42

    def test_valid_string(self):
        assert _safe_int("42") == 42

    def test_none(self):
        assert _safe_int(None) is None

    def test_empty_string(self):
        assert _safe_int("") is None

    def test_float_string(self):
        assert _safe_int("42.5") is None

    def test_non_numeric(self):
        assert _safe_int("abc") is None


class TestSafeFloat:
    def test_valid_float(self):
        assert _safe_float(42.5) == 42.5

    def test_valid_string(self):
        assert _safe_float("42.5") == 42.5

    def test_none(self):
        assert _safe_float(None) is None

    def test_empty(self):
        assert _safe_float("") is None


class TestScoreLihtc:
    def test_complete_record(self):
        rec = {
            "hud_id": "OH123",
            "project_name": "Test Project",
            "address": "123 Main St",
            "city": "Columbus",
            "state": "OH",
            "zip_code": "43215",
            "total_units": 100,
            "li_units": 80,
            "credit_type": "4%",
            "placed_in_service_year": 2020,
            "owner": "Test Owner LLC",
            "latitude": 39.96,
            "longitude": -82.99,
        }
        score = score_lihtc(rec)
        assert score == 1.0

    def test_minimal_record(self):
        rec = {"hud_id": "OH123"}
        score = score_lihtc(rec)
        assert score == 0.10

    def test_empty_record(self):
        score = score_lihtc({})
        assert score == 0.0

    def test_missing_coords(self):
        rec = {
            "hud_id": "OH123",
            "project_name": "Test",
            "address": "123 Main",
            "city": "Columbus",
            "state": "OH",
            "zip_code": "43215",
            "total_units": 100,
            "li_units": 80,
            "credit_type": "4%",
            "placed_in_service_year": 2020,
            "owner": "Test Owner",
        }
        score = score_lihtc(rec)
        assert score == 0.95

    def test_invalid_year(self):
        rec = {
            "hud_id": "OH123",
            "placed_in_service_year": "bad",
        }
        score = score_lihtc(rec)
        assert score == 0.10  # Only hud_id counts


class TestScoreReac:
    def test_complete_record(self):
        rec = {
            "inspection_id": "INS001",
            "property_id": "PROP001",
            "property_name": "Test Property",
            "address": "123 Main St",
            "city": "Columbus",
            "state": "OH",
            "inspection_date": "2024-01-15",
            "inspection_score": 85,
            "property_type": "Multifamily",
            "units": 100,
        }
        score = score_reac(rec)
        assert score == 1.0

    def test_minimal_record(self):
        rec = {"inspection_id": "INS001", "inspection_score": 72}
        score = score_reac(rec)
        assert score == 0.30  # inspection_id + score

    def test_zero_score_counts(self):
        """A score of 0 is still a valid score."""
        rec = {"inspection_score": 0}
        score = score_reac(rec)
        assert score == 0.20  # has_score


class TestScoreSection8:
    def test_complete_record(self):
        rec = {
            "contract_id": "C001",
            "property_name": "Test",
            "address": "123 Main",
            "city": "Columbus",
            "state": "OH",
            "owner_name": "Test Owner",
            "program_type": "LMSA",
            "contract_start_date": "2020-01-01",
            "assisted_units": 50,
            "annual_expense": 500000.0,
            "latitude": 39.96,
            "longitude": -82.99,
        }
        score = score_section8(rec)
        assert score == 1.0

    def test_empty_record(self):
        score = score_section8({})
        assert score == 0.0


class TestScoreMultifamily:
    def test_complete_record(self):
        rec = {
            "property_id": "P001",
            "property_name": "Test",
            "address": "123 Main",
            "city": "Columbus",
            "state": "OH",
            "owner_name": "Owner",
            "program_type": "Section 8",
            "total_units": 100,
            "property_category": "Elderly",
            "latitude": 39.96,
            "longitude": -82.99,
            "has_section_8": 1,
        }
        score = score_multifamily(rec)
        assert score == 1.0

    def test_subsidy_flags(self):
        rec = {"has_lihtc": 1}
        score = score_multifamily(rec)
        assert score == 0.05  # Just the flag
