# tests/curator/test_dry_run_output.py
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".curator/lib"))

from dry_run_utils import DryRunOutput, MockSupabaseClient


def test_dry_run_output_saves_json():
    """DryRunOutput should save complete results to JSON file."""
    client = MockSupabaseClient()

    # Add sample entity
    client.entities.append({
        "id": "test-id",
        "name": "Test Entity",
        "type": "test"
    })

    output = DryRunOutput(client, [])

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output.save_json(f.name)
        temp_path = f.name

    # Read back and verify
    with open(temp_path) as f:
        data = json.load(f)

    assert "entities" in data
    assert len(data["entities"]) == 1
    assert data["entities"][0]["name"] == "Test Entity"

    # Cleanup
    Path(temp_path).unlink()
