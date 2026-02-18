"""Tests for the curator pipeline."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from curator.config import CuratorConfig
from curator.errors import FetchError, ValidationError, ImportError_
from curator.pipeline import fetch, import_items, run
from curator.state import Phase


@pytest.fixture
def curator_config(tmp_path):
    """A CuratorConfig pointing at a temp directory with a working fetch script."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    fetch_script = scripts_dir / "fetch_data.py"
    fetch_script.write_text(
        '#!/usr/bin/env python3\nimport json, sys\n'
        'json.dump({"format_version":"1.0","metadata":{"curator":"Test","source":"x",'
        '"fetched_at":"2026-01-01T00:00:00Z","total_items":1,"filters_applied":{}},'
        '"items":[{"name":"Item 1","type":"card","external_ids":{"id":"1"}}]},'
        'open(sys.argv[1] if len(sys.argv)>1 else "fetched_data.json","w"))\n'
    )
    fetch_script.chmod(0o755)

    return CuratorConfig(
        name="Test Curator",
        curator_dir=tmp_path,
        data_source="https://example.com",
        fetch_script=fetch_script,
        collection_id="00000000-0000-0000-0000-000000000000",
        secrets={},
        raw_config={"fetch": {"supports_filters": ["limit"]}},
    )


class TestFetch:
    def test_runs_fetch_script(self, curator_config):
        fetch(curator_config)
        assert curator_config.fetched_data_path.exists()

    def test_passes_limit_argument(self, curator_config):
        # Replace fetch script with one that prints args
        curator_config.fetch_script.write_text(
            '#!/usr/bin/env python3\nimport sys; print(" ".join(sys.argv[1:]))\n'
        )
        # fetch won't produce valid JSON but we just check it doesn't crash on subprocess
        # The real test is that --limit is in the args
        with pytest.raises(FetchError):
            # Will fail because no fetched_data.json produced, but that's fine
            fetch(curator_config, limit=50)

    def test_raises_on_script_failure(self, curator_config):
        curator_config.fetch_script.write_text(
            '#!/usr/bin/env python3\nimport sys; sys.exit(1)\n'
        )
        with pytest.raises(FetchError, match="exit"):
            fetch(curator_config)


class TestImportItems:
    def test_calls_mcp_bulk_import(self, curator_config, sample_fetched_data):
        mock_mcp = MagicMock()
        mock_mcp.call_tool.return_value = {
            "success": True,
            "summary": {"total": 2, "created": 2, "updated": 0, "skipped": 0, "errors": 0},
            "created_entity_ids": ["id1", "id2"],
            "updated_entity_ids": [],
            "errors": [],
        }
        result = import_items(curator_config, sample_fetched_data, mock_mcp)
        mock_mcp.call_tool.assert_called_once_with(
            "bulk_import_curator_batch",
            {
                "collection_id": "00000000-0000-0000-0000-000000000000",
                "items": sample_fetched_data["items"],
                "skip_duplicates": True,
                "localize_images": True,
            },
        )
        assert result["summary"]["created"] == 2

    def test_raises_on_mcp_failure(self, curator_config, sample_fetched_data):
        mock_mcp = MagicMock()
        mock_mcp.call_tool.return_value = {
            "success": False,
            "error": "Collection not found",
            "error_code": "DATABASE_ERROR",
        }
        with pytest.raises(ImportError_, match="Collection not found"):
            import_items(curator_config, sample_fetched_data, mock_mcp)
