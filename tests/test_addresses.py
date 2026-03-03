"""Tests for address normalization."""

import pytest
from src.normalization.addresses import (
    normalize_address, normalize_city, normalize_state,
    normalize_zip, normalize_owner_name, make_match_key,
)


class TestNormalizeAddress:
    def test_basic(self):
        assert normalize_address("123 Main Street") == "123 MAIN ST"

    def test_with_apt(self):
        result = normalize_address("123 Main Street Apt 4B")
        assert "APT" not in result
        assert "123 MAIN ST" in result

    def test_with_suite(self):
        result = normalize_address("500 North Boulevard Suite 200")
        assert "SUITE" not in result
        assert "N BLVD" in result

    def test_directions(self):
        assert normalize_address("100 North Main Street") == "100 N MAIN ST"

    def test_compound_direction(self):
        assert normalize_address("200 Northeast 5th Avenue") == "200 NE 5TH AVE"

    def test_empty(self):
        assert normalize_address("") == ""
        assert normalize_address(None) == ""

    def test_periods(self):
        result = normalize_address("123 N. Main St.")
        assert "." not in result

    def test_unit_number(self):
        result = normalize_address("456 Oak Lane #12")
        assert "#" not in result


class TestNormalizeCity:
    def test_basic(self):
        assert normalize_city("Columbus") == "COLUMBUS"

    def test_saint(self):
        assert normalize_city("St. Louis") == "SAINT LOUIS"

    def test_fort(self):
        assert normalize_city("Ft. Worth") == "FORT WORTH"

    def test_mount(self):
        assert normalize_city("Mt. Vernon") == "MOUNT VERNON"

    def test_empty(self):
        assert normalize_city(None) == ""
        assert normalize_city("") == ""


class TestNormalizeState:
    def test_abbreviation(self):
        assert normalize_state("OH") == "OH"

    def test_full_name(self):
        assert normalize_state("Ohio") == "OH"

    def test_full_name_two_words(self):
        assert normalize_state("New York") == "NY"

    def test_dc(self):
        assert normalize_state("District of Columbia") == "DC"

    def test_empty(self):
        assert normalize_state(None) == ""


class TestNormalizeZip:
    def test_five_digit(self):
        assert normalize_zip("43215") == "43215"

    def test_nine_digit(self):
        assert normalize_zip("43215-1234") == "43215"

    def test_leading_zero(self):
        assert normalize_zip("06103") == "06103"

    def test_short_zip(self):
        assert normalize_zip("6103") == "06103"

    def test_empty(self):
        assert normalize_zip(None) == ""


class TestNormalizeOwnerName:
    def test_basic(self):
        assert normalize_owner_name("ABC Housing LLC") == "ABC HOUSING"

    def test_inc(self):
        assert normalize_owner_name("National Housing Inc.") == "NATIONAL HOUSING"

    def test_dba(self):
        result = normalize_owner_name("ABC Corp DBA Best Housing")
        assert "DBA" not in result
        assert "ABC" in result

    def test_the_prefix(self):
        assert normalize_owner_name("The Housing Authority") == "HOUSING AUTHORITY"

    def test_nested_suffixes(self):
        result = normalize_owner_name("ABC Holdings Group LLC")
        assert "HOLDINGS" not in result
        assert "GROUP" not in result
        assert "LLC" not in result

    def test_empty(self):
        assert normalize_owner_name(None) == ""
        assert normalize_owner_name("") == ""


class TestMakeMatchKey:
    def test_full_key(self):
        key = make_match_key("123 Main St", "Columbus", "OH", "43215")
        assert "123 MAIN ST" in key
        assert "COLUMBUS" in key
        assert "OH" in key
        assert "43215" in key

    def test_partial_key(self):
        key = make_match_key("123 Main St", None, "OH", None)
        assert "123 MAIN ST" in key
        assert "OH" in key

    def test_empty(self):
        key = make_match_key(None, None, None, None)
        assert key == ""
