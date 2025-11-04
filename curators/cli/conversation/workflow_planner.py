"""
Workflow Planner - Plans execution workflow with user approval.

Proposes a workflow plan based on schema and sources, then enters
a conversational loop allowing user to approve or request adjustments.
"""

from typing import List, Dict, Any
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

from core.llm import get_llm

console = Console()


class WorkflowPlanner:
    """
    Plans execution workflow with conversational approval loop.

    Creates a step-by-step workflow plan that the user can approve
    or adjust.
    """

    def __init__(self):
        """Initialize workflow planner."""
        self.llm = get_llm()

    async def propose_and_approve(
        self,
        schema: Dict[str, Any],
        sources: List[Dict[str, Any]],
        instructions: str
    ) -> Dict[str, Any]:
        """
        Propose workflow and get user approval.

        Args:
            schema: Approved collection schema
            sources: Data sources
            instructions: User instructions

        Returns:
            Approved workflow dict
        """
        console.print("[dim]Generating workflow plan...[/dim]\n")

        # Build workflow from schema
        extraction_strategy = schema.get("extraction_strategy", "html_scraping")
        selectors = schema.get("selectors", {})
        source_url = sources[0].get("url") if sources else None

        workflow = {
            "type": "scraper",
            "source_url": source_url,
            "extraction_strategy": extraction_strategy,
            "selectors": selectors,
            "phases": [
                {
                    "name": "Discovery",
                    "description": "Fetch product listing pages",
                    "estimated_time": "10-30s"
                },
                {
                    "name": "Extraction",
                    "description": "Parse product data using selectors",
                    "estimated_time": "30-60s"
                },
                {
                    "name": "Import",
                    "description": "Create entities and relationships in database",
                    "estimated_time": "30-60s"
                }
            ],
            "estimated_total_time": "1-2 minutes",
            "estimated_cost": "$0.01-0.05"
        }

        # Display workflow proposal
        workflow_text = f"""[cyan]Type:[/cyan] {workflow['type']}
[cyan]Source:[/cyan] {workflow['source_url']}
[cyan]Strategy:[/cyan] {workflow['extraction_strategy']}

[bold cyan]Phases:[/bold cyan]"""

        for i, phase in enumerate(workflow["phases"], 1):
            workflow_text += f"\n  {i}. {phase['name']}: {phase['description']}"

        workflow_text += f"\n\n[cyan]Estimated Time:[/cyan] {workflow['estimated_total_time']}"
        workflow_text += f"\n[cyan]Estimated Cost:[/cyan] {workflow['estimated_cost']}"

        panel = Panel(
            workflow_text,
            title="[bold cyan]Proposed Workflow[/bold cyan]",
            border_style="cyan"
        )
        console.print(panel)
        console.print()

        # Get approval
        approved = Confirm.ask("[yellow]Approve workflow?[/yellow]", default=True)

        if approved:
            console.print("[green]Workflow approved[/green]\n")
            return workflow
        else:
            console.print("[yellow]Workflow adjustment not yet implemented[/yellow]")
            console.print("[dim]Using proposed workflow for now[/dim]\n")
            return workflow
