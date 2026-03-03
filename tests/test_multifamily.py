"""Tests for multifamily property scraper."""

import json
import pytest
from pathlib import Path

from src.scrapers.multifamily import (
    _parse_assisted_record, _parse_insured_record,
    extract_reac_from_multifamily,
    parse_multifamily_assisted, parse_multifamily_insured,
)


class TestParseAssistedRecord:
    def test_basic(self):
        attrs = {
            "PROPERTY_ID": "800001234",
            "PROPERTY_NAME_TEXT": "Test Apartments",
            "STD_ADDR": "100 Main St",
            "STD_CITY": "Columbus",
            "STD_ST": "OH",
            "STD_ZIP5": "43215",
            "TOTAL_UNIT_COUNT": 100,
            "TOTAL_ASSISTED_UNIT_COUNT": 80,
            "IS_SEC8_IND": "Y",
            "PROGRAM_TYPE1": "LMSA",
            "LAT": 39.96,
            "LON": -82.99,
            "REAC_LAST_INSPECTION_SCORE": "92",
            "REAC_LAST_INSPECTION_DATE": 1706486400000,
        }
        rec = _parse_assisted_record(attrs)
        assert rec is not None
        assert rec["property_id"] == "800001234"
        assert rec["property_name"] == "Test Apartments"
        assert rec["has_section_8"] == 1
        assert rec["total_units"] == 100
        assert rec["_reac_score"] == "92"

    def test_no_property_id(self):
        attrs = {"PROPERTY_NAME_TEXT": "Test"}
        assert _parse_assisted_record(attrs) is None

    def test_no_section_8(self):
        attrs = {"PROPERTY_ID": "800001", "IS_SEC8_IND": "N"}
        rec = _parse_assisted_record(attrs)
        assert rec["has_section_8"] == 0

    def test_with_lihtc(self):
        attrs = {"PROPERTY_ID": "800001", "TAXCREDIT1": "4%"}
        rec = _parse_assisted_record(attrs)
        assert rec["has_lihtc"] == 1


class TestParseInsuredRecord:
    def test_basic(self):
        attrs = {
            "PROPERTY_ID": "800002345",
            "PROPERTY_NAME_TEXT": "Insured Place",
            "ADDRESS_LINE1_TEXT": "200 Oak Ave",
            "PLACED_BASE_CITY_NAME_TEXT": "Chicago",
            "STD_ST": "IL",
            "STD_ZIP5": "60601",
            "TOTAL_UNIT_COUNT": 50,
            "IS_SEC8_IND": "Y",
            "IS_202_CAPITAL_ADVANCE_IND": "Y",
            "REAC_LAST_INSPECTION_SCORE": "75",
        }
        rec = _parse_insured_record(attrs)
        assert rec is not None
        assert rec["property_id"] == "800002345"
        assert rec["city"] == "Chicago"
        assert rec["has_section_202"] == 1
        assert rec["_reac_score"] == "75"


class TestExtractReac:
    def test_extracts_reac(self):
        mf_records = [
            {
                "property_id": "800001",
                "property_name": "Test",
                "address": "123 Main",
                "city": "Columbus",
                "state": "OH",
                "zip_code": "43215",
                "property_category": "Elderly",
                "total_units": 100,
                "source_file": "multifamily_assisted",
                "_reac_score": "92",
                "_reac_date": 1706486400000,
                "_reac_id": 12345.0,
            },
        ]
        reac = extract_reac_from_multifamily(mf_records)
        assert len(reac) == 1
        assert reac[0]["inspection_id"] == "12345"
        assert reac[0]["inspection_score"] == 92.0
        assert reac[0]["inspection_date"] == "2024-01-29"

    def test_no_reac_score(self):
        mf_records = [
            {"property_id": "800002", "_reac_score": "", "_reac_date": None, "_reac_id": None},
        ]
        reac = extract_reac_from_multifamily(mf_records)
        assert len(reac) == 0

    def test_score_with_suffix(self):
        """REAC scores sometimes have letter suffixes like '92a'."""
        mf_records = [
            {
                "property_id": "800003",
                "property_name": "Test",
                "address": "",
                "city": "",
                "state": "OH",
                "zip_code": "",
                "property_category": "",
                "total_units": 50,
                "source_file": "test",
                "_reac_score": "85a",
                "_reac_date": None,
                "_reac_id": None,
            },
        ]
        reac = extract_reac_from_multifamily(mf_records)
        assert len(reac) == 1
        assert reac[0]["inspection_score"] == 85.0

    def test_dedup_by_id(self):
        rec = {
            "property_id": "800004",
            "property_name": "Test",
            "address": "",
            "city": "",
            "state": "OH",
            "zip_code": "",
            "property_category": "",
            "total_units": 50,
            "source_file": "test",
            "_reac_score": "90",
            "_reac_date": None,
            "_reac_id": 99999.0,
        }
        reac = extract_reac_from_multifamily([rec, rec])
        assert len(reac) == 1  # Deduplicated


class TestParseFromFile:
    def test_parse_assisted_from_json(self, tmp_path):
        data = [
            {"attributes": {"PROPERTY_ID": "800001", "PROPERTY_NAME_TEXT": "Test 1", "STD_ST": "OH"}},
            {"attributes": {"PROPERTY_ID": "800002", "PROPERTY_NAME_TEXT": "Test 2", "STD_ST": "CA"}},
        ]
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))

        records = parse_multifamily_assisted(path)
        assert len(records) == 2
        assert records[0]["property_id"] == "800001"

    def test_parse_insured_from_json(self, tmp_path):
        data = [
            {"attributes": {"PROPERTY_ID": "900001", "PROPERTY_NAME_TEXT": "Ins 1", "STD_ST": "NY"}},
        ]
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))

        records = parse_multifamily_insured(path)
        assert len(records) == 1
