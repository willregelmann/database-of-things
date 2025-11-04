"""
S3/Supabase Storage client for managing curator artifacts.

Stores curator workflows, discovery reports, generated code, and run results
in S3-compatible storage (Supabase Storage).
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import os

from supabase import create_client, Client


class S3StorageManager:
    """Manages curator artifacts in S3-compatible storage (Supabase Storage)."""

    def __init__(self):
        """Initialize S3/Supabase Storage client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment"
            )

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.bucket_name = "curator-artifacts"
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Ensure the curator-artifacts bucket exists."""
        try:
            self.supabase.storage.get_bucket(self.bucket_name)
        except Exception:
            try:
                self.supabase.storage.create_bucket(
                    self.bucket_name,
                    options={"public": False}
                )
            except Exception:
                pass

    def _build_path(self, curator_id: str, *parts: str) -> str:
        """Build a storage path for a curator artifact."""
        return f"{curator_id}/{'/'.join(parts)}"

    async def save_metadata(self, curator_id: str, metadata: Dict[str, Any]) -> str:
        """Save curator metadata to storage."""
        path = self._build_path(curator_id, "metadata.json")
        content = json.dumps(metadata, indent=2).encode("utf-8")
        self.supabase.storage.from_(self.bucket_name).upload(
            path, content,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
        return f"{self.bucket_name}/{path}"

    async def save_schema(self, curator_id: str, schema: Dict[str, Any]) -> str:
        """Save approved collection schema."""
        path = self._build_path(curator_id, "schema.json")
        content = json.dumps(schema, indent=2).encode("utf-8")
        self.supabase.storage.from_(self.bucket_name).upload(
            path, content,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
        return f"{self.bucket_name}/{path}"

    async def save_workflow(self, curator_id: str, workflow: Dict[str, Any]) -> str:
        """Save approved workflow plan."""
        path = self._build_path(curator_id, "workflow.json")
        content = json.dumps(workflow, indent=2).encode("utf-8")
        self.supabase.storage.from_(self.bucket_name).upload(
            path, content,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
        return f"{self.bucket_name}/{path}"

    async def save_discovery_report(self, curator_id: str, report: Dict[str, Any]) -> str:
        """Save discovery report."""
        path = self._build_path(curator_id, "discovery", "report.json")
        content = json.dumps(report, indent=2).encode("utf-8")
        self.supabase.storage.from_(self.bucket_name).upload(
            path, content,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
        return f"{self.bucket_name}/{path}"

    async def save_generated_code(self, curator_id: str, code: str, filename: str = "scraper.py") -> str:
        """Save generated code (scraper/workflow)."""
        path = self._build_path(curator_id, "generated", "scrapers", filename)
        content = code.encode("utf-8")
        self.supabase.storage.from_(self.bucket_name).upload(
            path, content,
            file_options={"content-type": "text/x-python", "upsert": "true"}
        )
        return f"{self.bucket_name}/{path}"

    async def save_run_results(self, curator_id: str, run_id: str, results: Dict[str, Any]) -> str:
        """Save run execution results."""
        path = self._build_path(curator_id, "runs", run_id, "results.json")
        content = json.dumps(results, indent=2).encode("utf-8")
        self.supabase.storage.from_(self.bucket_name).upload(
            path, content,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
        return f"{self.bucket_name}/{path}"

    async def load_metadata(self, curator_id: str) -> Optional[Dict[str, Any]]:
        """Load curator metadata."""
        path = self._build_path(curator_id, "metadata.json")
        try:
            response = self.supabase.storage.from_(self.bucket_name).download(path)
            return json.loads(response)
        except Exception:
            return None

    async def load_schema(self, curator_id: str) -> Optional[Dict[str, Any]]:
        """Load collection schema."""
        path = self._build_path(curator_id, "schema.json")
        try:
            response = self.supabase.storage.from_(self.bucket_name).download(path)
            return json.loads(response)
        except Exception:
            return None

    async def load_workflow(self, curator_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow plan."""
        path = self._build_path(curator_id, "workflow.json")
        try:
            response = self.supabase.storage.from_(self.bucket_name).download(path)
            return json.loads(response)
        except Exception:
            return None

    async def load_generated_code(self, curator_id: str, filename: str = "scraper.py") -> Optional[str]:
        """Load generated code."""
        path = self._build_path(curator_id, "generated", "scrapers", filename)
        try:
            response = self.supabase.storage.from_(self.bucket_name).download(path)
            return response.decode("utf-8")
        except Exception:
            return None

    async def delete_curator_artifacts(self, curator_id: str):
        """Delete all artifacts for a curator."""
        files = self.supabase.storage.from_(self.bucket_name).list(curator_id)
        file_paths = [f"{curator_id}/{f['name']}" for f in files]
        if file_paths:
            self.supabase.storage.from_(self.bucket_name).remove(file_paths)
