# Curator Dry Run Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add dry run capability to curator system that validates imports without database writes.

**Architecture:** MockSupabaseClient intercepts database operations, ImageValidator checks URL accessibility via HEAD requests, DryRunOutput generates YAML/JSON output. Import scripts use --dry-run flag to enable mock mode.

**Tech Stack:** Python 3, Supabase Python SDK, PyYAML, requests

---

## Task 1: Create MockSupabaseClient Foundation

**Files:**
- Create: `.curator/lib/dry_run_utils.py`
- Create: `tests/curator/test_dry_run_utils.py`

**Step 1: Write failing test for MockSupabaseClient**

Create test file:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
mkdir -p tests/curator
cd tests/curator
pytest test_dry_run_utils.py::test_mock_client_captures_entity_insert -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'dry_run_utils'"

**Step 3: Write minimal MockSupabaseClient implementation**

Create the module:

```python
# .curator/lib/dry_run_utils.py
"""Utilities for dry run mode in curator scripts."""

import uuid
from typing import Any, Dict, List, Optional


class MockResponse:
    """Mock response from Supabase operations."""

    def __init__(self, data: List[Dict] = None):
        self.data = data or []
        self.count = len(self.data)


class MockTable:
    """Mock table interface for Supabase operations."""

    def __init__(self, client: 'MockSupabaseClient', table_name: str):
        self.client = client
        self.table_name = table_name
        self._operation = None
        self._data = None
        self._filters = []

    def insert(self, data: Dict) -> 'MockTable':
        """Capture insert operation."""
        self._operation = "insert"
        self._data = data
        return self

    def select(self, columns: str) -> 'MockTable':
        """Capture select operation."""
        self._operation = "select"
        return self

    def eq(self, column: str, value: Any) -> 'MockTable':
        """Capture filter."""
        self._filters.append(("eq", column, value))
        return self

    def execute(self) -> MockResponse:
        """Execute captured operation."""
        if self._operation == "insert":
            # Add UUID to data
            entity = {**self._data, "id": str(uuid.uuid4())}

            # Store based on table
            if self.table_name == "entities":
                self.client.entities.append(entity)
            elif self.table_name == "relationships":
                self.client.relationships.append(entity)

            return MockResponse(data=[entity])

        elif self._operation == "select":
            # Return empty results (simulates "not found")
            return MockResponse(data=[])

        return MockResponse()


class MockSupabaseClient:
    """Mock Supabase client that captures operations without executing them."""

    def __init__(self):
        self.entities: List[Dict] = []
        self.relationships: List[Dict] = []
        self.queries: List[Dict] = []
        self.storage_uploads: List[Dict] = []

    def table(self, table_name: str) -> MockTable:
        """Return mock table interface."""
        return MockTable(self, table_name)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/curator/test_dry_run_utils.py -v
```

Expected: Both tests PASS

**Step 5: Commit**

```bash
git add .curator/lib/dry_run_utils.py tests/curator/test_dry_run_utils.py
git commit -m "feat: add MockSupabaseClient foundation

- Captures entity and relationship inserts
- Returns empty results for select queries
- Generates UUIDs for inserted entities"
```

---

## Task 2: Add MockStorage for Image Operations

**Files:**
- Modify: `.curator/lib/dry_run_utils.py`
- Modify: `tests/curator/test_dry_run_utils.py`

**Step 1: Write failing test for storage operations**

Add to test file:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/curator/test_dry_run_utils.py::test_mock_client_captures_storage_upload -v
```

Expected: FAIL with "AttributeError: 'MockSupabaseClient' object has no attribute 'storage'"

**Step 3: Implement MockStorage classes**

Add to dry_run_utils.py:

```python
class MockStorageBucket:
    """Mock storage bucket interface."""

    def __init__(self, client: 'MockSupabaseClient', bucket_name: str):
        self.client = client
        self.bucket_name = bucket_name

    def upload(self, path: str, file_data: bytes, file_options: Dict = None):
        """Capture upload operation."""
        self.client.storage_uploads.append({
            "bucket": self.bucket_name,
            "path": path,
            "size": len(file_data),
            "content_type": file_options.get("content-type") if file_options else None
        })
        return {"path": path}


class MockStorage:
    """Mock storage interface."""

    def __init__(self, client: 'MockSupabaseClient'):
        self.client = client

    def from_(self, bucket_name: str) -> MockStorageBucket:
        """Return mock bucket interface."""
        return MockStorageBucket(self.client, bucket_name)


# Update MockSupabaseClient class
class MockSupabaseClient:
    """Mock Supabase client that captures operations without executing them."""

    def __init__(self):
        self.entities: List[Dict] = []
        self.relationships: List[Dict] = []
        self.queries: List[Dict] = []
        self.storage_uploads: List[Dict] = []
        self.storage = MockStorage(self)  # Add storage interface

    def table(self, table_name: str) -> MockTable:
        """Return mock table interface."""
        return MockTable(self, table_name)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/curator/test_dry_run_utils.py::test_mock_client_captures_storage_upload -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add .curator/lib/dry_run_utils.py tests/curator/test_dry_run_utils.py
git commit -m "feat: add MockStorage for image upload capture

- Captures storage.from().upload() operations
- Tracks bucket, path, size, and content-type"
```

---

## Task 3: Create ImageValidator

**Files:**
- Modify: `.curator/lib/dry_run_utils.py`
- Modify: `tests/curator/test_dry_run_utils.py`

**Step 1: Write failing test for ImageValidator**

Add to test file:

```python
import requests
from unittest.mock import Mock, patch


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
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/curator/test_dry_run_utils.py::test_image_validator_checks_accessibility -v
```

Expected: FAIL with "ImportError: cannot import name 'ImageValidator'"

**Step 3: Implement ImageValidator**

Add to dry_run_utils.py:

```python
import requests


class ImageValidator:
    """Validates image URLs are accessible without downloading full images."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def validate_image(self, url: str) -> Dict[str, Any]:
        """
        Validate image URL with HEAD request.

        Returns:
            {
                "url": str,
                "accessible": bool,
                "status_code": int,
                "content_type": str,
                "error": str (if failed)
            }
        """
        result = {
            "url": url,
            "accessible": False,
            "status_code": None,
            "content_type": None,
            "error": None
        }

        try:
            # Try HEAD request first (faster, no body download)
            response = requests.head(url, timeout=self.timeout, allow_redirects=True)
            result["status_code"] = response.status_code
            result["content_type"] = response.headers.get('content-type', '')

            # Check if successful and is an image
            if response.status_code == 200:
                if 'image/' in result["content_type"]:
                    result["accessible"] = True
                else:
                    result["error"] = f"Not an image: {result['content_type']}"
            else:
                result["error"] = f"HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            result["error"] = "Timeout"
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)

        return result
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/curator/test_dry_run_utils.py::test_image_validator_checks_accessibility -v
pytest tests/curator/test_dry_run_utils.py::test_image_validator_detects_failures -v
```

Expected: Both tests PASS

**Step 5: Commit**

```bash
git add .curator/lib/dry_run_utils.py tests/curator/test_dry_run_utils.py
git commit -m "feat: add ImageValidator for URL validation

- Validates image accessibility via HEAD request
- Checks status code and content-type
- 5 second timeout with error handling"
```

---

## Task 4: Create DryRunOutput with Hierarchy Builder

**Files:**
- Modify: `.curator/lib/dry_run_utils.py`
- Modify: `tests/curator/test_dry_run_utils.py`

**Step 1: Write failing test for DryRunOutput**

Add to test file:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/curator/test_dry_run_utils.py::test_dry_run_output_builds_hierarchy -v
```

Expected: FAIL with "ImportError: cannot import name 'DryRunOutput'"

**Step 3: Implement DryRunOutput with hierarchy builder**

Add to dry_run_utils.py:

```python
class DryRunOutput:
    """Generates human-readable YAML and structured JSON from dry run results."""

    def __init__(self, mock_client: MockSupabaseClient, image_results: List[Dict]):
        self.entities = mock_client.entities
        self.relationships = mock_client.relationships
        self.image_results = image_results

    def build_hierarchy(self) -> Dict[str, Any]:
        """Build hierarchical structure from flat entities/relationships."""
        # Create entity lookup
        entity_map = {e["id"]: e for e in self.entities}

        # Group relationships by parent
        children_map = {}
        for rel in self.relationships:
            from_id = rel["from_id"]
            if from_id not in children_map:
                children_map[from_id] = []
            children_map[from_id].append({
                "entity_id": rel["to_id"],
                "order": rel.get("order")
            })

        # Sort children by order if present
        for children in children_map.values():
            children.sort(key=lambda x: x["order"] if x["order"] is not None else float('inf'))

        # Build tree recursively
        def build_subtree(entity_id: str) -> Any:
            entity = entity_map.get(entity_id)
            if not entity:
                return None

            # If this entity has children
            if entity_id in children_map:
                children = children_map[entity_id]

                # If children are collections, nest as dict
                first_child = entity_map.get(children[0]["entity_id"])
                if first_child and first_child.get("type") == "collection":
                    return {
                        child_info["entity"]["name"]: build_subtree(child_info["entity_id"])
                        for child_info in children
                        if (child_info := {"entity": entity_map.get(child_info["entity_id"])})
                    }
                # Otherwise, return as list
                else:
                    return [
                        entity_map.get(child_info["entity_id"])
                        for child_info in children
                    ]

            # Leaf node
            return entity

        # Find root entities (not referenced as children)
        child_ids = {rel["to_id"] for rel in self.relationships}
        root_ids = [e["id"] for e in self.entities if e["id"] not in child_ids]

        # Build hierarchy from roots
        hierarchy = {}
        for root_id in root_ids:
            entity = entity_map[root_id]
            hierarchy[entity["name"]] = build_subtree(root_id)

        return hierarchy
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/curator/test_dry_run_utils.py::test_dry_run_output_builds_hierarchy -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add .curator/lib/dry_run_utils.py tests/curator/test_dry_run_utils.py
git commit -m "feat: add DryRunOutput with hierarchy builder

- Builds hierarchical structure from flat entities/relationships
- Nests collections as dicts, items as lists
- Sorts by order field when present"
```

---

## Task 5: Add YAML and JSON Output Methods

**Files:**
- Modify: `.curator/lib/dry_run_utils.py`
- Create: `tests/curator/test_dry_run_output.py`

**Step 1: Install PyYAML dependency**

```bash
pip install pyyaml
```

**Step 2: Write failing test for YAML output**

Create new test file:

```python
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
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/curator/test_dry_run_output.py::test_dry_run_output_saves_json -v
```

Expected: FAIL with "AttributeError: 'DryRunOutput' object has no attribute 'save_json'"

**Step 4: Implement output methods**

Add to dry_run_utils.py:

```python
import json
import yaml


class DryRunOutput:
    """Generates human-readable YAML and structured JSON from dry run results."""

    def __init__(self, mock_client: MockSupabaseClient, image_results: List[Dict]):
        self.entities = mock_client.entities
        self.relationships = mock_client.relationships
        self.image_results = image_results

    # ... existing build_hierarchy method ...

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        # Count by entity type
        type_counts = {}
        for entity in self.entities:
            entity_type = entity.get("type", "unknown")
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

        # Count image results
        images_accessible = sum(1 for r in self.image_results if r.get("accessible"))

        return {
            "entity_types": type_counts,
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "images_validated": len(self.image_results),
            "images_accessible": images_accessible
        }

    def print_yaml(self, max_entities: int = 3):
        """Print YAML summary to terminal (limited to avoid spam)."""
        summary = self.get_summary()
        hierarchy = self.build_hierarchy()

        # Limit hierarchy depth for display
        limited_hierarchy = dict(list(hierarchy.items())[:max_entities])

        output = {
            "Dry Run Results": {
                "Summary": summary,
                "Structure (showing first {} entities)".format(max_entities): limited_hierarchy
            }
        }

        # Add image issues if any
        image_issues = [r for r in self.image_results if not r.get("accessible")]
        if image_issues:
            output["Dry Run Results"]["Image Issues"] = [
                f"{r['url']} ({r.get('error', 'Unknown error')})"
                for r in image_issues[:10]  # Limit to 10
            ]

        print(yaml.dump(output, default_flow_style=False, sort_keys=False))

    def save_json(self, filepath: str):
        """Save complete results to JSON file."""
        data = {
            "summary": self.get_summary(),
            "entities": self.entities,
            "relationships": self.relationships,
            "image_results": self.image_results,
            "hierarchy": self.build_hierarchy()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/curator/test_dry_run_output.py::test_dry_run_output_saves_json -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add .curator/lib/dry_run_utils.py tests/curator/test_dry_run_output.py
git commit -m "feat: add YAML and JSON output methods

- print_yaml() displays summary and limited hierarchy
- save_json() saves complete results to file
- get_summary() provides statistics"
```

---

## Task 6: Update ImageLocalizer to Support Validation Mode

**Files:**
- Modify: `.curator/lib/image_utils.py`
- Create: `tests/curator/test_image_utils_dry_run.py`

**Step 1: Write failing test for validation mode**

Create test file:

```python
# tests/curator/test_image_utils_dry_run.py
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".curator/lib"))

from image_utils import ImageLocalizer
from dry_run_utils import ImageValidator


def test_image_localizer_uses_validator_when_provided():
    """ImageLocalizer should use validator instead of downloading when provided."""
    # Mock Supabase client
    mock_supabase = Mock()

    # Create validator
    validator = ImageValidator()

    # Create localizer with validator
    localizer = ImageLocalizer(mock_supabase, image_validator=validator)

    # Mock validation result
    with patch.object(validator, 'validate_image') as mock_validate:
        mock_validate.return_value = {
            "url": "https://example.com/test.jpg",
            "accessible": True,
            "status_code": 200
        }

        # Should use validator, not download
        image_url, thumbnail_url = localizer.localize_image(
            "https://example.com/test.jpg",
            "test-entity-id"
        )

    # Should return mock URLs
    assert "[would localize from" in image_url
    assert thumbnail_url is None

    # Should have called validator
    mock_validate.assert_called_once()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/curator/test_image_utils_dry_run.py::test_image_localizer_uses_validator_when_provided -v
```

Expected: FAIL with "TypeError: __init__() got an unexpected keyword argument 'image_validator'"

**Step 3: Update ImageLocalizer to accept validator**

Modify image_utils.py:

```python
class ImageLocalizer:
    """Download and localize external images to Supabase storage."""

    def __init__(self, supabase, image_validator=None):
        """
        Initialize ImageLocalizer.

        Args:
            supabase: Supabase client
            image_validator: Optional ImageValidator for dry run mode
        """
        self.supabase = supabase
        self.image_validator = image_validator
        self.session = requests.Session()

    def localize_image(self, external_url: str, entity_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Download external image, generate thumbnail, upload both to storage.

        If image_validator is set (dry run mode), validates URL instead of downloading.

        Returns (image_url, thumbnail_url) or (None, None) on failure.
        """
        if not external_url:
            return None, None

        # DRY RUN MODE: Validate instead of download
        if self.image_validator:
            result = self.image_validator.validate_image(external_url)
            if result["accessible"]:
                return f"[would localize from {external_url}]", None
            else:
                return None, None

        # NORMAL MODE: Existing download/upload logic
        # ... rest of existing code ...
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/curator/test_image_utils_dry_run.py::test_image_localizer_uses_validator_when_provided -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add .curator/lib/image_utils.py tests/curator/test_image_utils_dry_run.py
git commit -m "feat: add dry run mode to ImageLocalizer

- Accept optional image_validator parameter
- Validate URLs instead of downloading when validator present
- Return mock URLs indicating what would be localized"
```

---

## Task 7: Update Import Template with Dry Run Flag

**Files:**
- Modify: `.curator/templates/import_items.py.template`

**Step 1: Add argparse and dry run logic to template**

Modify the template's main() function:

```python
def main():
    import argparse

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Import items to Supabase database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate import without writing to database'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("[COLLECTION_NAME] Importer")  # CUSTOMIZE
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be written to database")
    print("=" * 60)
    print()

    # Load configuration
    supabase_url, supabase_key = load_config()

    # Use mock or real client
    if args.dry_run:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))
        from dry_run_utils import MockSupabaseClient, ImageValidator, DryRunOutput

        supabase = MockSupabaseClient()
        image_validator = ImageValidator()
    else:
        supabase = create_client(supabase_url, supabase_key)
        image_validator = None

    # Load fetched data
    print("Loading fetched data...")
    items = load_fetched_data()
    print(f"Found {len(items)} items to import")
    print()

    # Import items
    if not args.dry_run:
        print("Loading embedding model: sentence-transformers/all-MiniLM-L6-v2")

    importer = ItemImporter(supabase, collection_id)

    # Pass validator to image localizer if present
    if image_validator:
        importer.image_localizer = ImageLocalizer(supabase, image_validator=image_validator)

    if not args.dry_run:
        print("✓ Model loaded\n")

    created, updated, failed = importer.import_all(items)

    print()
    print("=" * 60)

    # Generate dry run output
    if args.dry_run:
        output = DryRunOutput(supabase, getattr(importer, 'image_results', []))
        output.print_yaml(max_entities=3)
        output.save_json('dry_run_results.json')
        print(f"\n✓ Dry run complete. Full results saved to dry_run_results.json")
    else:
        print(f"✓ Complete:")
        print(f"  Created: {created}")
        print(f"  Updated (re-linked): {updated}")
        print(f"  Failed: {failed}")
        print(f"  Total processed: {created + updated}")

    print("=" * 60)
```

**Step 2: Update ItemImporter to track image validation results**

Add to the ItemImporter class in template:

```python
class ItemImporter:
    """Import items to Supabase with best practices."""

    def __init__(self, supabase: Client, collection_id: str):
        self.supabase = supabase
        self.collection_id = collection_id
        self.image_localizer = ImageLocalizer(supabase)
        self.embedding_generator = EmbeddingGenerator()
        self.parent_cache = {}
        self.image_results = []  # Track image validation results
```

Then in the import_item method, capture validation results:

```python
# Localize image if present
if external_image_url:
    print(f"    Processing images for: {name}")

    # Capture validation result if in dry run
    if hasattr(self.image_localizer, 'image_validator') and self.image_localizer.image_validator:
        result = self.image_localizer.image_validator.validate_image(external_image_url)
        self.image_results.append(result)

    image_url, thumbnail_url = self.image_localizer.localize_image(
        external_image_url,
        entity_id
    )
```

**Step 3: Test with Marvel Comics curator**

```bash
cd ".curator/curators/Marvel Comics"
source secrets.env
export FETCH_LIMIT=5

# Run fetch
python3 scripts/fetch_data.py

# Run import in dry run mode
python3 scripts/import_items.py --dry-run
```

Expected: Should show YAML output with structure and save dry_run_results.json

**Step 4: Commit**

```bash
git add .curator/templates/import_items.py.template
git commit -m "feat: add --dry-run flag to import template

- Add argparse for --dry-run flag
- Use MockSupabaseClient when enabled
- Track image validation results
- Generate YAML/JSON output in dry run mode"
```

---

## Task 8: Update Existing Marvel Comics Curator with Dry Run

**Files:**
- Modify: `.curator/curators/Marvel Comics/scripts/import_items.py`

**Step 1: Apply template changes to Marvel Comics curator**

Copy the argparse and dry run logic from the updated template to the Marvel Comics import script.

**Step 2: Test dry run with Marvel Comics**

```bash
cd ".curator/curators/Marvel Comics"
source secrets.env
export FETCH_LIMIT=5
python3 scripts/fetch_data.py
python3 scripts/import_items.py --dry-run
```

Expected output:
```yaml
Dry Run Results:
  Summary:
    entity_types:
      collection: 2
      comic: 5
    total_entities: 7
    total_relationships: 7
    images_validated: 5
    images_accessible: 5
  Structure (showing first 3 entities):
    Marvel Comics:
      Amazing Spider-Man (1963):
        - name: "Amazing Spider-Man #..."
          type: comic
          ...
```

**Step 3: Verify dry_run_results.json created**

```bash
ls -lh dry_run_results.json
cat dry_run_results.json | jq '.summary'
```

Expected: JSON file exists with complete results

**Step 4: Commit**

```bash
git add ".curator/curators/Marvel Comics/scripts/import_items.py"
git commit -m "feat: add dry run support to Marvel Comics curator

- Supports --dry-run flag
- Validates Marvel API data structure
- Checks comic cover image accessibility"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `.curator/README.md`
- Modify: `.curator/templates/README.md`

**Step 1: Add dry run section to curator README**

Add after the "Best Practices" section:

```markdown
## Dry Run Mode

Test curator scripts without writing to the database.

**Usage:**
```bash
cd ".curator/curators/{Collection Name}"
source secrets.env
export FETCH_LIMIT=10  # Limit for testing
python3 scripts/fetch_data.py
python3 scripts/import_items.py --dry-run
```

**What it does:**
- ✅ Runs all import logic (parsing, validation, hierarchy building)
- ✅ Validates image URLs are accessible (HEAD request)
- ✅ Skips: Database writes, image downloads, embedding generation
- ✅ Outputs: YAML summary + complete JSON file

**Output:**
- Terminal: YAML summary with hierarchy (limited to first 3 entities)
- File: `dry_run_results.json` with complete results

**Use cases:**
- Test new curator after init
- Validate data structure before full import
- Debug hierarchy issues
- Check image accessibility
```

**Step 2: Update template README**

Add dry run section to `.curator/templates/README.md`:

```markdown
## Testing Your Curator

### Dry Run (Recommended First Step)

Before importing to the database, validate your scripts with dry run:

```bash
cd ".curator/curators/Your Collection"
source secrets.env
export FETCH_LIMIT=10
python3 scripts/fetch_data.py
python3 scripts/import_items.py --dry-run
```

This validates:
- ✅ Data source is accessible
- ✅ Parsing logic works correctly
- ✅ Hierarchy structure is correct
- ✅ Image URLs are accessible
- ✅ External IDs are unique

**Review the output:**
- Check YAML hierarchy in terminal
- Inspect `dry_run_results.json` for details
- Fix any issues and re-run
```

**Step 3: Commit documentation**

```bash
git add .curator/README.md .curator/templates/README.md
git commit -m "docs: add dry run mode documentation

- Explain usage and benefits
- Show example commands
- List what dry run validates"
```

---

## Task 10: Integration Test with Power Rangers Curator

**Files:**
- Test: Run dry run on existing Power Rangers curator

**Step 1: Apply dry run template to Power Rangers curator**

```bash
cd ".curator/curators/Power Rangers Toys"
# Copy argparse and dry run logic from template to scripts/import_items.py
```

**Step 2: Run dry run with limited dataset**

```bash
source secrets.env
export FETCH_LIMIT=5
python3 scripts/fetch_data.py
python3 scripts/import_items.py --dry-run
```

**Step 3: Verify hierarchical output**

Expected YAML structure:
```yaml
Structure:
  Power Rangers Toys:
    Mighty Morphin Power Rangers:
      2200 Mighty Morphin Power Rangers:
        - name: "Jason Red Ranger"
          order: null
        - name: "Billy Blue Ranger"
```

**Step 4: Commit Power Rangers dry run support**

```bash
git add ".curator/curators/Power Rangers Toys/scripts/import_items.py"
git commit -m "feat: add dry run support to Power Rangers curator

- Supports --dry-run flag
- Validates hierarchical structure (series → toy lines → toys)
- Tests relationship order tracking"
```

---

## Verification Steps

After all tasks complete:

1. **Run Marvel Comics dry run**
   ```bash
   cd ".curator/curators/Marvel Comics"
   source secrets.env
   export FETCH_LIMIT=10
   python3 scripts/fetch_data.py
   python3 scripts/import_items.py --dry-run
   ```
   Expected: YAML shows series → issues hierarchy

2. **Run Power Rangers dry run**
   ```bash
   cd ".curator/curators/Power Rangers Toys"
   source secrets.env
   export FETCH_LIMIT=10
   python3 scripts/fetch_data.py
   python3 scripts/import_items.py --dry-run
   ```
   Expected: YAML shows collection → series → toy lines → toys

3. **Check JSON output has complete data**
   ```bash
   cat dry_run_results.json | jq '.summary'
   cat dry_run_results.json | jq '.entities | length'
   ```

4. **Verify no database writes occurred**
   ```bash
   # Query database - should not have dry run test data
   # (Assuming FETCH_LIMIT created unique test entities)
   ```

## Success Criteria

- ✅ MockSupabaseClient captures all operations
- ✅ ImageValidator checks URL accessibility
- ✅ DryRunOutput generates YAML + JSON
- ✅ Template has --dry-run flag
- ✅ Marvel Comics curator supports dry run
- ✅ Power Rangers curator supports dry run
- ✅ No data written to database in dry run mode
- ✅ Hierarchy displays correctly in YAML
- ✅ Image issues reported clearly
- ✅ Documentation updated

## Next Steps

After implementation:
- Update init-curator skill to offer dry run after generating scripts
- Add dry run to /curator:run command
- Consider adding --dry-run-verbose for more detailed output
