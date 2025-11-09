"""Utilities for dry run mode in curator scripts."""

import uuid
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
