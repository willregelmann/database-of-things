"""
Curator Store - Database CRUD operations for curators.

Manages curator and curator_runs records in PostgreSQL via Supabase.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from supabase import create_client, Client


class CuratorStore:
    """
    Database operations for curators table.

    Handles creating, reading, updating, and deleting curator records
    in PostgreSQL via Supabase.
    """

    def __init__(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment"
            )

        self.supabase: Client = create_client(supabase_url, supabase_key)

    async def create_curator(
        self,
        name: str,
        collection_id: str,
        instructions: str,
        curator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new curator record.

        Args:
            name: Unique curator name (e.g., "elden-ring-curator")
            collection_id: Target collection UUID
            instructions: Original user instructions
            curator_id: Optional custom UUID (generated if not provided)

        Returns:
            Created curator record

        Raises:
            Exception if curator with same name already exists
        """
        curator_data = {
            "id": curator_id or str(uuid.uuid4()),
            "name": name,
            "collection_id": collection_id,
            "instructions": instructions,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "total_runs": 0
        }

        response = self.supabase.table("curators").insert(curator_data).execute()
        return response.data[0]

    async def get_curator_by_name(
        self,
        name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get curator by name.

        Args:
            name: Curator name

        Returns:
            Curator record or None if not found
        """
        response = self.supabase.table("curators").select("*").eq("name", name).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

    async def get_curator_by_id(
        self,
        curator_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get curator by ID.

        Args:
            curator_id: Curator UUID

        Returns:
            Curator record or None if not found
        """
        response = self.supabase.table("curators").select("*").eq("id", curator_id).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

    async def list_curators(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all curators.

        Args:
            limit: Maximum number of curators to return

        Returns:
            List of curator records
        """
        response = self.supabase.table("curators").select("*").limit(limit).execute()
        return response.data

    async def update_curator(
        self,
        curator_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update curator record.

        Args:
            curator_id: Curator UUID
            updates: Fields to update

        Returns:
            Updated curator record
        """
        # Always update updated_at
        updates["updated_at"] = datetime.utcnow().isoformat()

        response = self.supabase.table("curators").update(updates).eq("id", curator_id).execute()
        return response.data[0]

    async def delete_curator(
        self,
        curator_id: str
    ):
        """
        Delete a curator record.

        Args:
            curator_id: Curator UUID
        """
        self.supabase.table("curators").delete().eq("id", curator_id).execute()

    # =====================================================
    # Curator Runs Operations
    # =====================================================

    async def create_run(
        self,
        curator_id: str,
        custom_instructions: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new curator run record.

        Args:
            curator_id: Curator UUID
            custom_instructions: Optional run-specific instructions
            run_id: Optional custom UUID

        Returns:
            Created run record
        """
        run_data = {
            "id": run_id or str(uuid.uuid4()),
            "curator_id": curator_id,
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
            "products_imported": 0,
            "custom_instructions": custom_instructions
        }

        response = self.supabase.table("curator_runs").insert(run_data).execute()
        return response.data[0]

    async def update_run(
        self,
        run_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a run record.

        Args:
            run_id: Run UUID
            updates: Fields to update

        Returns:
            Updated run record
        """
        response = self.supabase.table("curator_runs").update(updates).eq("id", run_id).execute()
        return response.data[0]

    async def complete_run(
        self,
        run_id: str,
        products_imported: int,
        results_url: str,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a run as completed.

        Args:
            run_id: Run UUID
            products_imported: Number of products imported
            results_url: S3 URL to results
            success: Whether run succeeded
            error_message: Error message if failed

        Returns:
            Updated run record
        """
        updates = {
            "completed_at": datetime.utcnow().isoformat(),
            "status": "completed" if success else "failed",
            "products_imported": products_imported,
            "results_url": results_url
        }

        if error_message:
            updates["error_message"] = error_message

        return await self.update_run(run_id, updates)

    async def get_curator_runs(
        self,
        curator_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get run history for a curator.

        Args:
            curator_id: Curator UUID
            limit: Maximum number of runs to return

        Returns:
            List of run records (most recent first)
        """
        response = (
            self.supabase.table("curator_runs")
            .select("*")
            .eq("curator_id", curator_id)
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data

    async def get_latest_run(
        self,
        curator_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent run for a curator.

        Args:
            curator_id: Curator UUID

        Returns:
            Latest run record or None
        """
        runs = await self.get_curator_runs(curator_id, limit=1)
        return runs[0] if runs else None
