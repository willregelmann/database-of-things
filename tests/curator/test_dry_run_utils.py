# tests/curator/test_dry_run_utils.py
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".curator/lib"))

from dry_run_utils import MockSupabaseClient


def test_mock_client_captures_entity_insert():
    """Mock client should capture insert operations."""
    client = MockSupabaseClient()

    # Simulate entity insert
    result = client.table("entities").insert({
        "name": "Test Entity",
        "type": "test"
    }).execute()

    # Should capture the insert
    assert len(client.entities) == 1
    assert client.entities[0]["name"] == "Test Entity"
    assert "id" in client.entities[0]  # Should generate UUID


def test_mock_client_returns_empty_for_select():
    """Mock client should return empty results for select queries."""
    client = MockSupabaseClient()

    result = client.table("entities").select("*").eq(
        "external_ids->>test", "123"
    ).execute()

    # Should return empty (simulates "not found")
    assert result.data == []
