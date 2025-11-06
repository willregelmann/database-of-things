"""CLI interface for curator system."""

import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
import os
from curator.discovery import DiscoverySession
from curator.storage import CuratorStorage
from curator.tools import CuratorTools
from curator.runner import CuratorRunner
from supabase import create_client
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Curator - Agentic collection management system.

    Create and manage curator agents that autonomously maintain collections.
    """
    pass


@main.command()
@click.argument("name")
@click.option("--collection-id", help="Existing collection UUID to manage")
def init(name: str, collection_id: str = None):
    """Initialize a new curator with interactive discovery.

    NAME: Curator name (e.g., "Pokemon TCG")
    """
    console.print(f"\n[bold blue]Initializing curator:[/] {name}\n")

    # Check if curator already exists
    storage = CuratorStorage()
    if storage.curator_exists(name):
        console.print(f"[red]Error: Curator '{name}' already exists[/]")
        return

    # Get credentials
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not anthropic_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment[/]")
        console.print("Set it in .env file or environment variables")
        return

    if not supabase_url or not supabase_key:
        console.print("[red]Error: Supabase credentials not found[/]")
        console.print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        return

    # Create Supabase client
    supabase = create_client(supabase_url, supabase_key)

    # Create or get collection
    if collection_id is None:
        console.print("[yellow]No collection ID provided. Creating new collection...[/]")
        result = supabase.table("entities").insert({
            "name": name,
            "type": "collection"
        }).execute()
        collection_id = result.data[0]["id"]
        console.print(f"[green]✓ Created collection: {collection_id}[/]\n")

    # Run discovery session
    session = DiscoverySession(
        curator_name=name,
        collection_id=collection_id,
        anthropic_key=anthropic_key,
        supabase_client=supabase
    )

    try:
        artifacts = session.run()

        # Save artifacts
        storage.create_curator_directory(name)
        storage.save_plan(name, artifacts["plan"])
        storage.save_scripts(name, artifacts["scripts"])

        # Save config
        config = artifacts.get("config", {})
        config["collection_id"] = collection_id
        storage.save_config(name, config)

        # Prompt for secrets
        secrets_list = artifacts.get("secrets", [])
        if secrets_list:
            console.print("\n[bold yellow]📝 Configure Secrets[/]\n")
            secrets = {}
            for secret in secrets_list:
                console.print(f"[bold]{secret['key']}[/]: {secret['description']}")
                value = console.input("  Value (or press Enter to skip): ").strip()
                if value:
                    secrets[secret['key']] = value

            if secrets:
                storage.save_secrets(name, secrets)
                console.print(f"\n[green]✓ Saved {len(secrets)} secrets[/]")

        # Save to database
        supabase.table("curators").insert({
            "name": name,
            "collection_id": collection_id,
            "config": config
        }).execute()

        console.print(f"\n[bold green]✓ Curator '{name}' initialized successfully![/]\n")
        console.print(f"Run with: [bold]curator run \"{name}\"[/]")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Discovery cancelled[/]")
    except Exception as e:
        console.print(f"\n[red]Error during discovery: {e}[/]")
        import traceback
        traceback.print_exc()


@main.command()
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
def run(name: str, dry_run: bool = False):
    """Run a curator manually.

    NAME: Curator name to run
    """
    console.print(f"\n[bold blue]Running curator:[/] {name}\n")

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/]\n")

    # Get credentials
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not all([anthropic_key, supabase_url, supabase_key]):
        console.print("[red]Error: Missing credentials in environment[/]")
        return

    # Create clients
    storage = CuratorStorage()
    supabase = create_client(supabase_url, supabase_key)

    # Check curator exists
    if not storage.curator_exists(name):
        console.print(f"[red]Error: Curator '{name}' not found[/]")
        console.print(f"Run: [bold]curator init \"{name}\"[/]")
        return

    # Load secrets
    secrets = storage.load_secrets(name)
    for key, value in secrets.items():
        os.environ[key] = value

    # Create runner
    runner = CuratorRunner(
        curator_name=name,
        storage=storage,
        supabase_client=supabase,
        anthropic_key=anthropic_key
    )

    try:
        result = runner.run(dry_run=dry_run)

        if result["status"] == "completed":
            console.print(f"\n[bold green]✓ Run completed successfully[/]")
            console.print(f"Operations: {result['operations_count']}")
            console.print(f"Run ID: {result['run_id']}")
        else:
            console.print(f"\n[bold red]✗ Run failed[/]")
            console.print(f"Error: {result.get('error', 'Unknown')}")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Run cancelled[/]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/]")
        import traceback
        traceback.print_exc()


@main.command()
@click.argument("name")
@click.argument("schedule")
def schedule(name: str, schedule: str):
    """Schedule automatic curator runs.

    NAME: Curator name
    SCHEDULE: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)

    Sets up scheduled execution for the curator.
    """
    console.print(f"\n[bold blue]Scheduling curator:[/] {name}")
    console.print(f"[bold]Schedule:[/] {schedule}\n")

    # TODO: Implement scheduling
    console.print("[yellow]Scheduling not yet implemented[/]")


@main.command()
@click.argument("name")
@click.option("--runs", type=int, default=10, help="Number of recent runs to show")
def status(name: str, runs: int = 10):
    """Show curator status and recent runs.

    NAME: Curator name
    """
    console.print(f"\n[bold blue]Status for:[/] {name}\n")

    # TODO: Implement status display
    console.print("[yellow]Status display not yet implemented[/]")
    console.print("\nWill show:")
    console.print("  • Curator configuration")
    console.print("  • Collection statistics")
    console.print("  • Last run time and result")
    console.print("  • Next scheduled run")
    console.print("  • Recent run history")


@main.command()
@click.argument("name")
def logs(name: str):
    """View curator logs.

    NAME: Curator name
    """
    console.print(f"\n[bold blue]Logs for:[/] {name}\n")

    # TODO: Implement log viewing
    console.print("[yellow]Log viewing not yet implemented[/]")


@main.group()
def secrets():
    """Manage curator secrets (API keys)."""
    pass


@secrets.command(name="add")
@click.argument("name")
@click.argument("key")
@click.argument("value")
def secrets_add(name: str, key: str, value: str):
    """Add a secret for a curator.

    NAME: Curator name
    KEY: Secret key (e.g., "POKEMONTCG_API_KEY")
    VALUE: Secret value
    """
    console.print(f"\n[bold blue]Adding secret for:[/] {name}")
    console.print(f"[bold]Key:[/] {key}\n")

    # TODO: Implement secret storage
    console.print("[yellow]Secret management not yet implemented[/]")


@secrets.command(name="list")
@click.argument("name")
def secrets_list(name: str):
    """List required secrets for a curator.

    NAME: Curator name
    """
    console.print(f"\n[bold blue]Required secrets for:[/] {name}\n")

    # TODO: Implement secret listing
    console.print("[yellow]Secret management not yet implemented[/]")


if __name__ == "__main__":
    main()
