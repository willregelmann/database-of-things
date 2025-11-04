"""
Run Command - Execute a curator workflow.

Loads curator from storage and executes the workflow, optionally with
run-specific instructions.
"""

import uuid
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from cli.storage.curator_store import CuratorStore
from cli.storage.s3_client import S3StorageManager
from core.execution_engine import ExecutionEngine
from utilities.supabase_client import SupabaseClient

console = Console()


async def run_command(curator_name: str, instructions: str = None):
    """
    Execute a curator workflow.

    Args:
        curator_name: Curator name (e.g., "elden-ring-curator")
        instructions: Optional run-specific instructions
    """
    console.print(f"\nRunning Curator: {curator_name}\n")

    if instructions:
        console.print(f"[yellow]Custom Instructions: {instructions}[/yellow]\n")

    # Load curator from database
    store = CuratorStore()
    curator = await store.get_curator_by_name(curator_name)

    if not curator:
        console.print(f"[red]Curator '{curator_name}' not found[/red]\n")
        console.print("[dim]Use 'curators list' to see available curators[/dim]\n")
        return

    curator_id = curator["id"]
    collection_id = curator["collection_id"]

    # Load workflow from S3
    storage = S3StorageManager()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Loading workflow from storage...", total=None)

        workflow = await storage.load_workflow(curator_id)
        metadata = await storage.load_metadata(curator_id)

        if not workflow:
            progress.stop()
            console.print(f"[red]No workflow found for curator '{curator_name}'[/red]\n")
            console.print("[dim]The curator may need to be re-initialized[/dim]\n")
            return

        progress.update(task, description="[green]Workflow loaded[/green]")

    # Create run record
    run_id = str(uuid.uuid4())
    run_record = await store.create_run(
        curator_id=curator_id,
        custom_instructions=instructions,
        run_id=run_id
    )

    console.print(f"[dim]Run ID: {run_id}[/dim]\n")

    # Execute workflow
    try:
        console.print("[bold cyan]Executing workflow...[/bold cyan]\n")

        engine = ExecutionEngine(
            memory=None,  # TODO: Initialize memory manager
            db=SupabaseClient(),
            artifacts_dir=None  # Will use S3 storage
        )

        results = await engine.execute(
            curator_id=curator_id,
            collection_id=collection_id,
            custom_instructions=instructions
        )

        # Save results to S3
        results_url = await storage.save_run_results(curator_id, run_id, results)

        # Update run record
        await store.complete_run(
            run_id=run_id,
            products_imported=results.get("products_imported", 0),
            results_url=results_url,
            success=results.get("success", False),
            error_message=results.get("error")
        )

        # Display results
        if results.get("success"):
            console.print("\n[green]Run Complete![/green]\n")

            results_panel = Panel(
                f"""[cyan]Imported:[/cyan] {results.get('products_imported', 0)} products
[cyan]Duration:[/cyan] {results.get('duration_seconds', 0):.1f}s
[cyan]Results:[/cyan] {results_url}""",
                title="[bold green]Execution Results[/bold green]",
                border_style="green"
            )

            console.print(results_panel)
        else:
            console.print("\n[red]Run Failed[/red]\n")
            console.print(f"[dim]Error: {results.get('error', 'Unknown error')}[/dim]\n")

    except Exception as e:
        # Mark run as failed
        await store.complete_run(
            run_id=run_id,
            products_imported=0,
            results_url="",
            success=False,
            error_message=str(e)
        )

        console.print(f"\n[red]Error executing curator: {e}[/red]\n")

    console.print()
