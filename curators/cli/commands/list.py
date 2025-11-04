"""
List Command - List all configured curators.
"""

from rich.console import Console
from rich.table import Table
from datetime import datetime

from cli.storage.curator_store import CuratorStore

console = Console()


async def list_command():
    """List all configured curators."""
    console.print("\nActive Curators\n")

    store = CuratorStore()
    curators = await store.list_curators()

    if not curators:
        console.print("[yellow]No curators found[/yellow]\n")
        console.print("[dim]Use 'curators init' to create one[/dim]\n")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Collection ID", style="green")
    table.add_column("Last Run", style="yellow")
    table.add_column("Total Runs", style="blue", justify="right")

    for curator in curators:
        last_run = curator.get("last_run_at")
        if last_run:
            try:
                last_run_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                last_run_str = last_run_dt.strftime("%Y-%m-%d %H:%M")
            except:
                last_run_str = "Unknown"
        else:
            last_run_str = "Never"

        table.add_row(
            curator["name"],
            curator["collection_id"][:8] + "...",
            last_run_str,
            str(curator.get("total_runs", 0))
        )

    console.print(table)
    console.print()
