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
