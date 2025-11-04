"""
Init Command - Initialize a new curator with conversational approval.

Implements Phase 3B: Conversational Init
- Source discovery (if not in instructions)
- Schema builder with approval loop
- Workflow planner with approval loop
- Curator creation and storage
"""

import uuid
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from core.autonomous_curator import AutonomousCurator
from cli.storage.curator_store import CuratorStore
from cli.storage.s3_client import S3StorageManager
from cli.conversation.source_discovery import SourceDiscoveryAgent
from cli.conversation.schema_builder import SchemaBuilder
from cli.conversation.workflow_planner import WorkflowPlanner

console = Console()


async def init_command(collection_id: str, instructions: str = None):
    """
    Initialize a new curator with conversational approval loops.

    Flow:
    1. Discover data sources (if not in instructions)
    2. Propose schema -> user approves/adjusts
    3. Propose workflow -> user approves/adjusts
    4. Create and store curator

    Args:
        collection_id: Target collection UUID
        instructions: Optional instructions (e.g., "Import Elden Ring merchandise")
    """
    console.print("\n[bold cyan]Initializing Curator...[/bold cyan]\n")

    # Get instructions if not provided
    if not instructions:
        instructions = Prompt.ask(
            "[yellow]What would you like to curate?[/yellow]",
            default="Import collectibles"
        )

    console.print(f"[dim]Instructions: {instructions}[/dim]\n")

    # Phase 1: Source Discovery
    console.print("[bold cyan]Phase 1: Source Discovery[/bold cyan]\n")

    source_discovery = SourceDiscoveryAgent()
    sources = await source_discovery.discover(instructions)

    if not sources:
        console.print("[red]No data sources found. Please provide a source URL.[/red]")
        source_url = Prompt.ask("[yellow]Source URL[/yellow]")
        sources = [{"url": source_url, "name": "Manual Source"}]
    else:
        # Show discovered sources
        console.print("[green]Found potential sources:[/green]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Source", style="green")
        table.add_column("Notes", style="yellow")

        for i, source in enumerate(sources, 1):
            table.add_row(
                str(i),
                source.get("name", "Unknown"),
                source.get("notes", "")
            )

        console.print(table)
        console.print()

        # Let user select sources
        selection = Prompt.ask(
            "[yellow]Which sources? (comma-separated numbers or 'all')[/yellow]",
            default="1"
        )

        if selection.lower() == "all":
            selected_sources = sources
        else:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected_sources = [sources[i] for i in indices if i < len(sources)]

    # Phase 2: Schema Builder (Conversational)
    console.print("\n[bold cyan]Phase 2: Collection Schema[/bold cyan]\n")

    schema_builder = SchemaBuilder()
    approved_schema = await schema_builder.propose_and_approve(
        sources=selected_sources,
        instructions=instructions,
        collection_id=collection_id
    )

    # Phase 3: Workflow Planner (Conversational)
    console.print("\n[bold cyan]Phase 3: Workflow Planning[/bold cyan]\n")

    workflow_planner = WorkflowPlanner()
    approved_workflow = await workflow_planner.propose_and_approve(
        schema=approved_schema,
        sources=selected_sources,
        instructions=instructions
    )

    # Phase 4: Create Curator
    console.print("\n[bold cyan]Phase 4: Creating Curator[/bold cyan]\n")

    # Generate curator name from instructions
    name_suggestion = "-".join(instructions.lower().split()[:3])
    name_suggestion = "".join(c if c.isalnum() or c == "-" else "" for c in name_suggestion)

    curator_name = Prompt.ask(
        "[yellow]Curator name[/yellow]",
        default=name_suggestion
    )

    # Create curator in database
    store = CuratorStore()
    curator_id = str(uuid.uuid4())

    curator = await store.create_curator(
        name=curator_name,
        collection_id=collection_id,
        instructions=instructions,
        curator_id=curator_id
    )

    # Save artifacts to S3
    storage = S3StorageManager()

    metadata = {
        "curator_id": curator_id,
        "name": curator_name,
        "collection_id": collection_id,
        "instructions": instructions,
        "created_at": curator["created_at"],
        "sources": selected_sources
    }

    await storage.save_metadata(curator_id, metadata)
    await storage.save_schema(curator_id, approved_schema)
    await storage.save_workflow(curator_id, approved_workflow)

    # Success message
    console.print("\n[green]Curator Created![/green]\n")

    info_panel = Panel(
        f"""[cyan]Curator ID:[/cyan] {curator_id}
[cyan]Name:[/cyan] {curator_name}
[cyan]Collection:[/cyan] {collection_id}

[green]Ready to run:[/green] curators run {curator_name}""",
        title="[bold green]Curator Info[/bold green]",
        border_style="green"
    )

    console.print(info_panel)
    console.print()
