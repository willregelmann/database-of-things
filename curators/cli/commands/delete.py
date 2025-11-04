"""
Delete Command - Remove a curator (collection is preserved).
"""

from rich.console import Console
from rich.prompt import Confirm

from cli.storage.curator_store import CuratorStore
from cli.storage.s3_client import S3StorageManager

console = Console()


async def delete_command(curator_name: str, skip_confirm: bool = False):
    """
    Delete a curator (collection data is preserved).

    Args:
        curator_name: Curator name
        skip_confirm: Skip confirmation prompt if True
    """
    console.print(f"\nDeleting Curator: {curator_name}\n")

    # Load curator
    store = CuratorStore()
    curator = await store.get_curator_by_name(curator_name)

    if not curator:
        console.print(f"[red]Curator '{curator_name}' not found[/red]\n")
        return

    curator_id = curator["id"]

    # Show what will be deleted
    console.print("[dim]This will delete:[/dim]")
    console.print(f"  * Curator record: {curator_name}")
    console.print(f"  * All run history")
    console.print(f"  * All artifacts (workflows, schemas, generated code)")
    console.print()
    console.print("[green]This will NOT delete:[/green]")
    console.print(f"  * Collection data (products remain in database)")
    console.print()

    # Confirm deletion
    if not skip_confirm:
        confirmed = Confirm.ask("[yellow]Are you sure?[/yellow]", default=False)
        if not confirmed:
            console.print("[dim]Cancelled[/dim]\n")
            return

    # Delete artifacts from S3
    console.print("[dim]Deleting artifacts from storage...[/dim]")
    storage = S3StorageManager()

    try:
        await storage.delete_curator_artifacts(curator_id)
    except Exception as e:
        console.print(f"[yellow]Warning: Error deleting artifacts: {e}[/yellow]")

    # Delete from database (cascades to curator_runs)
    console.print("[dim]Deleting database records...[/dim]")
    await store.delete_curator(curator_id)

    console.print(f"\n[green]Deleted curator '{curator_name}'[/green]\n")
