"""Integration tests requiring network access and real curator data.

Run with: pytest tests/test_integration.py -v -m integration
Skip with: pytest -m "not integration"
"""

import pytest

from curator.config import load_config
from curator.pipeline import fetch, run
from curator.validator import validate_file


pytestmark = pytest.mark.integration


class TestPokemonTCGFetch:
    """Test fetch + validate with real Pokemon TCG curator (no DB needed)."""

    def setup_method(self):
        """Clean up any leftover state from previous runs."""
        config = load_config("Pokemon TCG")
        if config.status_path.exists():
            config.status_path.unlink()

    def test_fetch_base_set_limited(self):
        """Fetch 5 cards from Base Set and validate the output."""
        config = load_config("Pokemon TCG")
        fetch(config, limit=5, set="Base")

        data = validate_file(config.fetched_data_path)
        assert data["format_version"] == "1.0"
        assert data["metadata"]["curator"] == "Pokemon TCG"
        # Should have at least: 1 series + 1 set + up to 5 cards
        assert len(data["items"]) >= 3
        assert len(data["items"]) <= 7  # series + set + 5 cards

        # Verify item structure
        cards = [i for i in data["items"] if i["type"] == "card"]
        assert len(cards) <= 5
        for card in cards:
            assert "name" in card
            assert "external_ids" in card
            assert "pokemontcg_io" in card["external_ids"]


class TestPokemonTCGDryRun:
    """Test dry run with real Pokemon TCG curator (no DB needed)."""

    def setup_method(self):
        """Clean up any leftover state from previous runs."""
        config = load_config("Pokemon TCG")
        if config.status_path.exists():
            config.status_path.unlink()

    def test_dry_run(self):
        """Dry run fetches and validates without importing."""
        config = load_config("Pokemon TCG")

        result = run(config, env="local", limit=5, dry_run=True, set="Base")
        assert result is None  # dry_run returns None

        # Verify fetched_data.json was produced and is valid
        data = validate_file(config.fetched_data_path)
        assert len(data["items"]) >= 3
