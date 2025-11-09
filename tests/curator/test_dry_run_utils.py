# tests/curator/test_dry_run_utils.py
import sys
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

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


def test_mock_client_captures_storage_upload():
    """Mock client should capture storage upload operations."""
    client = MockSupabaseClient()

    # Simulate storage upload
    client.storage.from_('images').upload(
        'originals/test.jpg',
        b'fake image data',
        file_options={"content-type": "image/jpeg"}
    )

    # Should capture the upload
    assert len(client.storage_uploads) == 1
    assert client.storage_uploads[0]["bucket"] == "images"
    assert client.storage_uploads[0]["path"] == "originals/test.jpg"


def test_image_validator_checks_accessibility():
    """ImageValidator should validate image URLs via HEAD request."""
    from dry_run_utils import ImageValidator

    validator = ImageValidator()

    # Mock successful HEAD request
    with patch('requests.head') as mock_head:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_head.return_value = mock_response

        result = validator.validate_image('https://example.com/image.jpg')

    assert result["accessible"] is True
    assert result["status_code"] == 200
    assert result["content_type"] == "image/jpeg"


def test_image_validator_detects_failures():
    """ImageValidator should detect failed requests."""
    from dry_run_utils import ImageValidator

    validator = ImageValidator()

    # Mock 404 response
    with patch('requests.head') as mock_head:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        result = validator.validate_image('https://example.com/missing.jpg')

    assert result["accessible"] is False
    assert result["status_code"] == 404


def test_dry_run_output_builds_hierarchy():
    """DryRunOutput should build hierarchical structure from flat data."""
    from dry_run_utils import DryRunOutput, MockSupabaseClient

    # Create mock client with sample data
    client = MockSupabaseClient()

    # Add collection
    collection_id = str(uuid.uuid4())
    client.entities.append({
        "id": collection_id,
        "name": "Test Collection",
        "type": "collection"
    })

    # Add series
    series_id = str(uuid.uuid4())
    client.entities.append({
        "id": series_id,
        "name": "Test Series",
        "type": "collection"
    })

    # Add issue
    issue_id = str(uuid.uuid4())
    client.entities.append({
        "id": issue_id,
        "name": "Issue #1",
        "type": "comic",
        "attributes": {"issue_number": 1}
    })

    # Add relationships
    client.relationships.append({
        "from_id": collection_id,
        "to_id": series_id,
        "type": "contains"
    })
    client.relationships.append({
        "from_id": series_id,
        "to_id": issue_id,
        "type": "contains",
        "order": 1
    })

    # Build hierarchy
    output = DryRunOutput(client, [])
    hierarchy = output.build_hierarchy()

    # Should nest properly
    assert "Test Collection" in hierarchy
    assert "Test Series" in hierarchy["Test Collection"]
    assert len(hierarchy["Test Collection"]["Test Series"]) == 1
    assert hierarchy["Test Collection"]["Test Series"][0]["name"] == "Issue #1"
