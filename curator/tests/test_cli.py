# curator/tests/test_cli.py
import pytest
from click.testing import CliRunner
from curator.cli import main

@pytest.fixture
def runner():
    """CLI test runner"""
    return CliRunner()

def test_cli_help(runner):
    """Test that CLI shows help"""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "curator" in result.output.lower()
    assert "init" in result.output
    assert "run" in result.output
    assert "status" in result.output

def test_cli_init_requires_name(runner):
    """Test that init requires curator name"""
    result = runner.invoke(main, ["init"])
    assert result.exit_code != 0
    assert "name" in result.output.lower()

def test_cli_run_requires_name(runner):
    """Test that run requires curator name"""
    result = runner.invoke(main, ["run"])
    assert result.exit_code != 0

def test_cli_status_requires_name(runner):
    """Test that status requires curator name"""
    result = runner.invoke(main, ["status"])
    assert result.exit_code != 0
