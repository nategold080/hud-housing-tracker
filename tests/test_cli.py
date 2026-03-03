"""Tests for CLI commands."""

from click.testing import CliRunner
import pytest
from src.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCli:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "HUD Affordable Housing" in result.output

    def test_download_help(self, runner):
        result = runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0

    def test_pipeline_help(self, runner):
        result = runner.invoke(cli, ["pipeline", "--help"])
        assert result.exit_code == 0

    def test_stats_help(self, runner):
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0

    def test_export_help(self, runner):
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0
        assert "csv" in result.output
        assert "json" in result.output

    def test_dashboard_help(self, runner):
        result = runner.invoke(cli, ["dashboard", "--help"])
        assert result.exit_code == 0
