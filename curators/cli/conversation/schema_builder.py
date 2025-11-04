"""
Schema Builder - Builds collection schema with user approval.

Proposes a schema structure based on discovered sources, then enters
a conversational loop allowing user to approve or request adjustments.
"""

from typing import List, Dict, Any
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

from core.llm import get_llm
from core.discovery_agent import DiscoveryAgent
from core.memory import TieredMemoryManager

console = Console()


class SchemaBuilder:
    """
    Builds collection schema with conversational approval loop.

    Analyzes sources and proposes a schema structure that the user
    can approve or adjust.
    """

    def __init__(self):
        """Initialize schema builder."""
        self.llm = get_llm()

    async def propose_and_approve(
        self,
        sources: List[Dict[str, Any]],
        instructions: str,
        collection_id: str
    ) -> Dict[str, Any]:
        """
        Propose schema and get user approval.

        Args:
            sources: Discovered data sources
            instructions: User instructions
            collection_id: Target collection UUID

        Returns:
            Approved schema dict
        """
        # For Phase 3A, use existing discovery flow
        # Full conversational loop to be implemented in Phase 3B

        console.print("[dim]Analyzing sources to generate schema...[/dim]\n")

        # Use existing DiscoveryAgent for initial analysis
        memory = TieredMemoryManager(curator_id=f"temp-{collection_id[:8]}")
        discovery_agent = DiscoveryAgent(llm=self.llm, memory=memory)

        # Analyze first source
        source_url = sources[0].get("url") if sources else None
        if source_url:
            discovery_report = await discovery_agent.analyze_source(source_url)

            # Extract schema from discovery
            analysis = discovery_report.get("analysis", {})

            schema = {
                "root_collection": {
                    "id": collection_id,
                    "name": instructions,
                    "attributes": {}
                },
                "subcollections": [],
                "product_attributes": analysis.get("data_available", {}),
                "extraction_strategy": analysis.get("extraction_strategy", "html_scraping"),
                "selectors": analysis.get("selectors", {})
            }

            # Display schema proposal
            schema_text = f"""[cyan]Root Collection:[/cyan] {schema['root_collection']['name']}
[cyan]Extraction Strategy:[/cyan] {schema['extraction_strategy']}
[cyan]Available Data:[/cyan] {', '.join([k for k, v in schema['product_attributes'].items() if v])}"""

            panel = Panel(
                schema_text,
                title="[bold cyan]Recommended Schema[/bold cyan]",
                border_style="cyan"
            )
            console.print(panel)
            console.print()

            # Get approval (for now, just confirm)
            approved = Confirm.ask("[yellow]Approve this schema?[/yellow]", default=True)

            if approved:
                console.print("[green]Schema approved[/green]\n")
                return schema
            else:
                console.print("[yellow]Schema adjustment not yet implemented[/yellow]")
                console.print("[dim]Using proposed schema for now[/dim]\n")
                return schema

        # Fallback: minimal schema
        return {
            "root_collection": {
                "id": collection_id,
                "name": instructions,
                "attributes": {}
            },
            "subcollections": [],
            "product_attributes": {},
            "extraction_strategy": "manual"
        }
