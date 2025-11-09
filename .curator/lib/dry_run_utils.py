"""Utilities for dry run mode in curator scripts."""

import json
import uuid
import yaml
import requests
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
                    result = {}
                    for child_info in children:
                        child_entity = entity_map.get(child_info["entity_id"])
                        if child_entity:
                            result[child_entity["name"]] = build_subtree(child_info["entity_id"])
                    return result
                # Otherwise, return as list
                else:
                    result = []
                    for child_info in children:
                        child_entity = entity_map.get(child_info["entity_id"])
                        if child_entity:
                            result.append(child_entity)
                    return result

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
