"""Shared test fixtures for curator tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_fetched_data():
    """Minimal valid fetched_data.json structure."""
    return {
        "format_version": "1.0",
        "metadata": {
            "curator": "Test Curator",
            "source": "https://example.com",
            "fetched_at": "2026-01-01T00:00:00Z",
            "total_items": 2,
            "filters_applied": {},
        },
        "items": [
            {
                "name": "Test Item 1",
                "type": "card",
                "external_ids": {"test_id": "1"},
            },
            {
                "name": "Test Item 2",
                "type": "card",
                "external_ids": {"test_id": "2"},
            },
        ],
    }
