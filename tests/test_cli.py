"""Tests for the CLI interface."""

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from curator.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCLIHelp:
    def test_main_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "fetch" in result.output
        assert "status" in result.output

    def test_run_help(self, runner):
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--limit" in result.output
        assert "--dry-run" in result.output

    def test_fetch_help(self, runner):
        result = runner.invoke(cli, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "NAME" in result.output

    def test_status_help(self, runner):
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0


class TestCLIRun:
    @patch("curator.cli.load_config")
    @patch("curator.cli.pipeline")
    def test_run_invokes_pipeline(self, mock_pipeline, mock_load_config, runner):
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        mock_pipeline.run.return_value = {
            "summary": {"created": 5, "updated": 0, "skipped": 0, "errors": 0}
        }

        result = runner.invoke(cli, ["run", "Pokemon TCG", "--env", "local"])
        assert result.exit_code == 0
        mock_load_config.assert_called_once_with("Pokemon TCG", env="local")
        mock_pipeline.run.assert_called_once()

    @patch("curator.cli.load_config")
    @patch("curator.cli.pipeline")
    def test_run_dry_run(self, mock_pipeline, mock_load_config, runner):
        mock_load_config.return_value = MagicMock()
        mock_pipeline.run.return_value = None

        result = runner.invoke(cli, ["run", "Test", "--dry-run"])
        assert result.exit_code == 0
        call_kwargs = mock_pipeline.run.call_args
        assert call_kwargs.kwargs.get("dry_run") is True or call_kwargs[1].get("dry_run") is True


class TestCLIFetch:
    @patch("curator.cli.load_config")
    @patch("curator.cli.pipeline")
    def test_fetch_only(self, mock_pipeline, mock_load_config, runner):
        mock_load_config.return_value = MagicMock()

        result = runner.invoke(cli, ["fetch", "Pokemon TCG", "--limit", "10"])
        assert result.exit_code == 0
        mock_pipeline.fetch.assert_called_once()


class TestCLIStatus:
    @patch("curator.cli.load_config")
    @patch("curator.cli.MCPClient")
    def test_status_displays_stats(self, mock_mcp_class, mock_load_config, runner):
        mock_load_config.return_value = MagicMock()
        mock_mcp = MagicMock()
        mock_mcp_class.return_value.__enter__ = MagicMock(return_value=mock_mcp)
        mock_mcp_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_mcp.call_tool.return_value = {
            "collection_name": "Pokemon TCG",
            "total_items": 100,
            "last_import": "2026-01-01T00:00:00Z",
        }

        result = runner.invoke(cli, ["status", "Pokemon TCG", "--env", "local"])
        assert result.exit_code == 0
        assert "100" in result.output
