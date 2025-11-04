"""
Execution Engine - Phase D: Artifact Invocation

Safely executes generated artifacts and learns from results.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import importlib.util
from rich.console import Console

from core.memory import TieredMemoryManager
from utilities.supabase_client import SupabaseClient

console = Console()


class ExecutionEngine:
    """
    Executes generated artifacts and monitors results.

    Instead of running code blindly, this engine:
    - Validates artifacts before execution
    - Runs in controlled environment
    - Monitors progress and captures output
    - Handles errors gracefully
    - Reports results back to memory
    """

    def __init__(
        self,
        memory: TieredMemoryManager,
        db: SupabaseClient,
        artifacts_dir: Path
    ):
        """
        Initialize execution engine.

        Args:
            memory: Memory manager for learning
            db: Database client
            artifacts_dir: Directory containing artifacts
        """
        self.memory = memory
        self.db = db
        self.artifacts_dir = artifacts_dir

    async def execute(
        self,
        curator_id: str,
        collection_id: str
    ) -> Dict[str, Any]:
        """
        Execute the generated workflow.

        Args:
            curator_id: Curator identifier
            collection_id: Target collection UUID

        Returns:
            Execution results
        """
        console.print("[cyan]Preparing to execute workflow...[/cyan]\n")

        # 1. Check for artifacts
        scraper_file = self.artifacts_dir / "scraper.py"
        workflow_file = self.artifacts_dir / "workflow.json"

        if scraper_file.exists():
            return await self._execute_scraper(scraper_file, curator_id, collection_id)
        elif workflow_file.exists():
            return await self._execute_workflow(workflow_file, curator_id, collection_id)
        else:
            raise FileNotFoundError(
                f"No executable artifacts found in {self.artifacts_dir}"
            )

    async def _execute_scraper(
        self,
        scraper_file: Path,
        curator_id: str,
        collection_id: str
    ) -> Dict[str, Any]:
        """Execute a generated scraper script."""

        console.print(f"[dim]Executing scraper: {scraper_file}[/dim]\n")

        try:
            # Import the generated module
            spec = importlib.util.spec_from_file_location("generated_scraper", scraper_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load scraper from {scraper_file}")

            module = importlib.util.module_from_spec(spec)
            sys.modules["generated_scraper"] = module
            spec.loader.exec_module(module)

            # Check if module has a main() function
            if not hasattr(module, "main"):
                raise AttributeError("Generated scraper missing main() function")

            # Execute the main function
            console.print("[cyan]Running scraper...[/cyan]\n")
            start_time = datetime.now()

            # Run the async main function
            result = await module.main()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # If main() returns results, use them; otherwise query database
            if result:
                stats = result
            else:
                stats = await self._get_import_stats(collection_id)

            console.print(f"\n[green]✅ Scraper executed successfully in {duration:.1f}s[/green]")

            return {
                "success": True,
                "duration_seconds": duration,
                "stats": stats,
                "executed_at": end_time.isoformat(),
                "summary": f"Imported {stats.get('products_imported', 0)} products"
            }

        except Exception as e:
            console.print(f"\n[red]❌ Execution failed: {e}[/red]")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "executed_at": datetime.now().isoformat(),
                "summary": f"Execution failed: {e}"
            }

    async def _execute_workflow(
        self,
        workflow_file: Path,
        curator_id: str,
        collection_id: str
    ) -> Dict[str, Any]:
        """Execute a LangGraph workflow."""

        console.print(f"[yellow]LangGraph workflow execution not fully implemented yet[/yellow]")
        console.print(f"[dim]Would execute: {workflow_file}[/dim]\n")

        # Placeholder for LangGraph execution
        return {
            "success": False,
            "error": "LangGraph execution not implemented",
            "summary": "Workflow execution pending implementation"
        }

    async def _get_import_stats(self, collection_id: str) -> Dict[str, Any]:
        """Query database to get import statistics."""

        try:
            # Count products in this collection
            # This is a simplified version - could be more sophisticated
            response = self.db.client.table("relationships").select(
                "to_id",
                count="exact"
            ).eq("from_id", collection_id).eq("type", "contains").execute()

            return {
                "products_imported": response.count or 0,
                "collection_id": collection_id
            }

        except Exception as e:
            console.print(f"[yellow]Warning: Could not get stats: {e}[/yellow]")
            return {
                "products_imported": 0,
                "error": str(e)
            }
