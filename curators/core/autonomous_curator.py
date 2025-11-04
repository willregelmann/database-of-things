"""
Autonomous Curator - Meta-system for generating and executing curation solutions.

This is the core orchestrator that:
1. Analyzes data sources autonomously
2. Generates necessary tools/workflows
3. Executes and learns from results
4. Adapts to changes over time
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from rich.console import Console

from core.memory import TieredMemoryManager
from utilities.supabase_client import SupabaseClient
from core.llm import get_llm

console = Console()


class AutonomousCurator:
    """
    Meta-level curator that generates and executes curation solutions.

    Instead of hand-coding scrapers, this curator:
    - Analyzes sources using LLM
    - Generates necessary code/workflows
    - Executes autonomously
    - Learns and adapts
    """

    def __init__(self):
        """Initialize the autonomous curator."""
        self.curator_id: Optional[str] = None
        self.goal: Optional[str] = None
        self.source: Optional[str] = None
        self.collection_id: Optional[str] = None

        # Will be initialized in __aenter__ or initialize()
        self.memory: Optional[TieredMemoryManager] = None
        self.db: Optional[SupabaseClient] = None
        self.llm = None

        # Artifact storage
        self.artifacts_dir: Optional[Path] = None

        # State tracking
        self.initialized = False
        self.discovery_report: Optional[Dict[str, Any]] = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cleanup if needed
        pass

    async def initialize(
        self,
        goal: str,
        source: str,
        collection_id: str,
        curator_id: Optional[str] = None
    ) -> "AutonomousCurator":
        """
        Phase A: Initialization

        User provides minimal input, system sets up for autonomous operation.

        Args:
            goal: What to accomplish (e.g., "Import Elden Ring merchandise")
            source: URL or API endpoint to curate from
            collection_id: Target collection UUID
            curator_id: Optional custom ID (generated if not provided)

        Returns:
            Self for chaining
        """
        console.print("\n[bold cyan]🤖 Initializing Autonomous Curator[/bold cyan]\n")

        # 1. Generate unique curator ID
        if curator_id:
            self.curator_id = curator_id
        else:
            # Generate from goal (slugified)
            slug = goal.lower().replace(" ", "-")[:30]
            unique_suffix = str(uuid.uuid4())[:8]
            self.curator_id = f"{slug}-{unique_suffix}"

        console.print(f"[dim]Curator ID: {self.curator_id}[/dim]")

        # 2. Store inputs
        self.goal = goal
        self.source = source
        self.collection_id = collection_id

        # 3. Initialize core services
        console.print("[dim]Initializing services...[/dim]")
        self.memory = TieredMemoryManager(curator_id=self.curator_id)
        self.db = SupabaseClient()
        self.llm = get_llm()

        # 4. Set up artifact directory
        self.artifacts_dir = Path("artifacts") / self.curator_id
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[dim]Artifact directory: {self.artifacts_dir}[/dim]")

        # 5. Store goal in memory (importance 1.0 - protected)
        console.print("[dim]Storing goal in memory...[/dim]")
        goal_text = f"Curator goal: {goal}. Source: {source}. Collection ID: {collection_id}"
        self.memory.add(
            content=goal_text,
            category="collection_structure",  # Protected importance 1.0
            metadata={
                "goal": goal,
                "source": source,
                "collection_id": collection_id,
                "curator_id": self.curator_id
            }
        )

        # 6. Save metadata to artifact directory
        metadata_file = self.artifacts_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump({
                "curator_id": self.curator_id,
                "goal": goal,
                "source": source,
                "collection_id": collection_id,
                "initialized_at": datetime.now().isoformat(),
                "status": "initialized"
            }, f, indent=2)

        self.initialized = True
        console.print("\n[green]✅ Curator initialized and ready[/green]\n")

        return self

    async def run(self) -> Dict[str, Any]:
        """
        Full autonomous run: discover → generate → execute → learn.

        Returns:
            Execution results
        """
        if not self.initialized:
            raise RuntimeError("Curator not initialized. Call initialize() first.")

        console.print("\n[bold cyan]🚀 Starting Autonomous Run[/bold cyan]\n")

        # Check if we have existing workflow
        existing_workflow = await self._check_existing_workflow()

        if existing_workflow:
            console.print("[yellow]Found existing workflow, checking if reusable...[/yellow]")
            # TODO: Implement workflow validation
            # For now, just reuse
            return await self.execute()
        else:
            console.print("[cyan]No existing workflow, starting from discovery...[/cyan]")

            # Phase B: Discovery
            await self.discover()

            # Phase C: Generate workflow
            await self.generate_workflow()

            # Phase D: Execute
            return await self.execute()

    async def discover(self) -> Dict[str, Any]:
        """
        Phase B: Discovery

        Analyze the source autonomously using LLM.

        Returns:
            Discovery report
        """
        console.print("\n[bold cyan]🔍 Phase B: Discovery[/bold cyan]\n")

        # Import here to avoid circular dependency
        from core.discovery_agent import DiscoveryAgent

        agent = DiscoveryAgent(
            llm=self.llm,
            memory=self.memory
        )

        self.discovery_report = await agent.analyze_source(self.source)

        # Store discovery report
        discovery_file = self.artifacts_dir / "discovery_report.json"
        with open(discovery_file, "w") as f:
            json.dump(self.discovery_report, f, indent=2)

        console.print(f"\n[green]✅ Discovery complete[/green]")
        console.print(f"[dim]Report saved to: {discovery_file}[/dim]\n")

        return self.discovery_report

    async def generate_workflow(self) -> Dict[str, Any]:
        """
        Phase C: Workflow and Tool Creation

        Generate necessary artifacts based on discovery.

        Returns:
            Generated artifact metadata
        """
        console.print("\n[bold cyan]⚙️  Phase C: Workflow Generation[/bold cyan]\n")

        if not self.discovery_report:
            raise RuntimeError("No discovery report. Run discover() first.")

        # Import here to avoid circular dependency
        from core.workflow_generator import WorkflowGenerator

        generator = WorkflowGenerator(
            llm=self.llm,
            memory=self.memory,
            artifacts_dir=self.artifacts_dir
        )

        artifact_info = await generator.generate(
            discovery_report=self.discovery_report,
            goal=self.goal,
            collection_id=self.collection_id
        )

        console.print(f"\n[green]✅ Workflow generated[/green]")
        console.print(f"[dim]Artifacts: {list(artifact_info['files'].keys())}[/dim]\n")

        return artifact_info

    async def execute(self) -> Dict[str, Any]:
        """
        Phase D: Invocation

        Execute the generated workflow and learn from results.

        Returns:
            Execution results
        """
        console.print("\n[bold cyan]▶️  Phase D: Execution[/bold cyan]\n")

        # Import here to avoid circular dependency
        from core.execution_engine import ExecutionEngine

        engine = ExecutionEngine(
            memory=self.memory,
            db=self.db,
            artifacts_dir=self.artifacts_dir
        )

        results = await engine.execute(
            curator_id=self.curator_id,
            collection_id=self.collection_id
        )

        # Store execution results in memory (importance 0.3 - tactical)
        result_text = f"Execution result: {results.get('summary', 'N/A')}"
        self.memory.add(
            content=result_text,
            category="execution_state",  # Tactical importance 0.3
            metadata={
                "curator_id": self.curator_id,
                "success": results.get("success", False),
                **results
            }
        )

        console.print(f"\n[green]✅ Execution complete[/green]")
        console.print(f"[dim]Results: {results.get('summary', 'N/A')}[/dim]\n")

        return results

    async def _check_existing_workflow(self) -> Optional[Dict[str, Any]]:
        """Check if we have an existing workflow for this source."""

        # Check artifact directory for actual executable files
        scraper_file = self.artifacts_dir / "scraper.py"
        workflow_file = self.artifacts_dir / "workflow.json"

        # Only return True if we have actual executable artifacts
        if scraper_file.exists() and scraper_file.stat().st_size > 0:
            console.print(f"[dim]Found existing scraper: {scraper_file}[/dim]")
            return {
                "type": "scraper",
                "file": str(scraper_file)
            }
        elif workflow_file.exists() and workflow_file.stat().st_size > 0:
            console.print(f"[dim]Found existing workflow: {workflow_file}[/dim]")
            return {
                "type": "workflow",
                "file": str(workflow_file)
            }

        # No valid artifacts found
        return None

    def status(self) -> Dict[str, Any]:
        """Get current curator status."""
        return {
            "curator_id": self.curator_id,
            "initialized": self.initialized,
            "goal": self.goal,
            "source": self.source,
            "collection_id": self.collection_id,
            "has_discovery": self.discovery_report is not None,
            "artifacts_dir": str(self.artifacts_dir) if self.artifacts_dir else None
        }
