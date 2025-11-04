"""
Info Command - Show detailed information about a curator.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from datetime import datetime

from cli.storage.curator_store import CuratorStore
from cli.storage.s3_client import S3StorageManager

console = Console()


async def info_command(curator_name: str):
    """
    Show detailed information about a curator.

    Args:
        curator_name: Curator name
    """
    console.print(f"\nCurator Info: {curator_name}\n")

    # Load curator from database
    store = CuratorStore()
    curator = await store.get_curator_by_name(curator_name)

    if not curator:
        console.print(f"[red]Curator '{curator_name}' not found[/red]\n")
        return

    curator_id = curator["id"]

    # Load metadata from S3
    storage = S3StorageManager()
    metadata = await storage.load_metadata(curator_id)

    # Display curator info
    info_text = f"""[cyan]ID:[/cyan] {curator_id}
[cyan]Name:[/cyan] {curator["name"]}
[cyan]Collection ID:[/cyan] {curator["collection_id"]}
[cyan]Instructions:[/cyan] {curator.get("instructions", "N/A")}
[cyan]Created:[/cyan] {curator.get("created_at", "Unknown")}
[cyan]Last Run:[/cyan] {curator.get("last_run_at", "Never")}
[cyan]Total Runs:[/cyan] {curator.get("total_runs", 0)}"""

    if metadata and "sources" in metadata:
        sources_str = ", ".join([s.get("name", "Unknown") for s in metadata["sources"]])
        info_text += f"\n[cyan]Sources:[/cyan] {sources_str}"

    panel = Panel(info_text, title="[bold green]Curator Details[/bold green]", border_style="cyan")
    console.print(panel)
    console.print()

    # Load and display run history
    console.print("[bold cyan]Run History:[/bold cyan]\n")

    runs = await store.get_curator_runs(curator_id, limit=10)

    if not runs:
        console.print("[yellow]No runs yet[/yellow]\n")
    else:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Started", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Products", style="green", justify="right")
        table.add_column("Duration", style="blue")

        for run in runs:
            started = run.get("started_at", "Unknown")
            try:
                started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                started_str = started_dt.strftime("%Y-%m-%d %H:%M")
            except:
                started_str = "Unknown"

            status = run.get("status", "unknown")
            status_mark = "[OK]" if status == "completed" else "[FAIL]" if status == "failed" else "[RUN]"

            duration = "N/A"
            if run.get("completed_at"):
                try:
                    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    completed_dt = datetime.fromisoformat(run["completed_at"].replace("Z", "+00:00"))
                    duration_sec = (completed_dt - started_dt).total_seconds()
                    duration = f"{duration_sec:.1f}s"
                except:
                    pass

            table.add_row(
                started_str,
                f"{status_mark} {status}",
                str(run.get("products_imported", 0)),
                duration
            )

        console.print(table)
        console.print()
