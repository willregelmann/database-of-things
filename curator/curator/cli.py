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

console = Console()


def load_env_file(env: str = None):
    """Load environment-specific .env file.

    Args:
        env: Environment name (e.g., "production", "local")
             If None, loads .env or .env.local
    """
    # Detect if we're in curator/ directory or project root
    cwd = Path.cwd()

    # Check if current directory has curator package (we're in curator/)
    if (cwd / "curator" / "__init__.py").exists():
        curator_dir = cwd
    # Otherwise look for curator/ subdirectory (we're in project root)
    elif (cwd / "curator" / "curator" / "__init__.py").exists():
        curator_dir = cwd / "curator"
    else:
        console.print(f"[red]Error: Could not find curator directory[/]")
        console.print(f"[yellow]Run from project root or curator/ directory[/]")
        return False

    if env:
        env_file = curator_dir / f".env.{env}"
        if not env_file.exists():
            console.print(f"[red]Error: Environment file not found: {env_file}[/]")
            console.print(f"[yellow]Create {env_file} with your {env} credentials[/]")
            return False
        load_dotenv(env_file)
        console.print(f"[dim]Loaded environment: {env}[/]\n")
    else:
        # Try .env.local first, then .env
        local_env = curator_dir / ".env.local"
        default_env = curator_dir / ".env"

        if local_env.exists():
            load_dotenv(local_env)
            console.print(f"[dim]Loaded environment: local[/]\n")
        elif default_env.exists():
            load_dotenv(default_env)
            console.print(f"[dim]Loaded environment: default[/]\n")
        else:
            console.print(f"[yellow]No .env file found in {curator_dir}/[/]")

    return True


@click.group()
@click.version_option(version="0.1.0")
@click.option("--env", help="Environment to use (e.g., 'production', 'local')")
@click.pass_context
def main(ctx, env):
    """Curator - Agentic collection management system.

    Create and manage curator agents that autonomously maintain collections.

    Examples:
      curator init "Pokemon TCG"
      curator --env production run "Pokemon TCG"
      curator --env local status "Pokemon TCG"
    """
    # Store env in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['env'] = env

    # Load environment
    load_env_file(env)


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

    # Smart collection search and selection
    if collection_id is None:
        console.print(f"[cyan]Searching for existing collections matching \"{name}\"...[/]\n")

        # Search for collections by name similarity
        search_results = supabase.table("entities").select(
            "id, name, created_at"
        ).eq("type", "collection").ilike("name", f"%{name}%").execute()

        if search_results.data:
            console.print(f"[green]Found {len(search_results.data)} existing collection(s):[/]\n")

            # Display matches with stats
            for idx, collection in enumerate(search_results.data, 1):
                # Get entity count
                count_result = supabase.table("relationships").select(
                    "id", count="exact"
                ).eq("from_id", collection["id"]).eq("type", "contains").execute()

                entity_count = count_result.count or 0
                created = collection["created_at"][:10] if collection.get("created_at") else "Unknown"

                console.print(f"  {idx}. [bold]{collection['name']}[/]")
                console.print(f"     ID: {collection['id']}")
                console.print(f"     Entities: {entity_count} | Created: {created}")
                console.print()

            # Ask user
            console.print("[bold yellow]? Use existing collection or create new?[/]")
            console.print(f"  [1-{len(search_results.data)}] Use existing collection (enter number)")
            console.print(f"  [n] Create new collection \"{name}\"")
            console.print(f"  [q] Cancel")
            console.print()

            choice = console.input("[bold blue]Your choice:[/] ").strip().lower()

            if choice == 'q':
                console.print("[yellow]Cancelled[/]")
                return
            elif choice == 'n':
                # Create new collection
                result = supabase.table("entities").insert({
                    "name": name,
                    "type": "collection"
                }).execute()
                collection_id = result.data[0]["id"]
                console.print(f"\n[green]✓ Created new collection: {collection_id}[/]\n")
            elif choice.isdigit() and 1 <= int(choice) <= len(search_results.data):
                # Use existing collection
                collection_id = search_results.data[int(choice) - 1]["id"]
                collection_name = search_results.data[int(choice) - 1]["name"]
                console.print(f"\n[green]✓ Using existing collection: {collection_name}[/]\n")
            else:
                console.print(f"[red]Invalid choice: {choice}[/]")
                return
        else:
            # No matches found, create new
            console.print(f"[yellow]No existing collections found matching \"{name}\"[/]")
            console.print(f"[cyan]Creating new collection...[/]\n")

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

    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        console.print("[red]Error: Supabase credentials not found[/]")
        return

    # Create clients
    storage = CuratorStorage()
    supabase = create_client(supabase_url, supabase_key)

    # Check curator exists
    if not storage.curator_exists(name):
        console.print(f"[red]Error: Curator '{name}' not found[/]")
        return

    # Load config
    config = storage.load_config(name)

    # Get curator from database
    curator_result = supabase.table("curators").select("*").eq("name", name).single().execute()
    curator = curator_result.data

    # Get collection stats
    collection_id = curator["collection_id"]
    tools = CuratorTools(collection_id, supabase)
    stats = tools.get_collection_stats()

    # Display curator info
    console.print("[bold]Curator Configuration:[/]")
    console.print(f"  Collection ID: {collection_id}")
    console.print(f"  Status: {curator['status']}")
    console.print(f"  Created: {curator['created_at']}")
    console.print(f"  Last run: {curator['last_run_at'] or 'Never'}")
    console.print()

    # Display collection stats
    console.print("[bold]Collection Statistics:[/]")
    console.print(f"  Total entities: {stats['total_entities']}")
    console.print(f"  Subcollections: {stats['total_subcollections']}")
    console.print(f"  Embedding coverage: {stats['has_embeddings']}/{stats['total_entities']}")
    console.print(f"  Thumbnail coverage: {stats['has_thumbnails']}/{stats['total_entities']}")
    console.print()

    # Display entities by type
    if stats['entities_by_type']:
        console.print("[bold]Entities by Type:[/]")
        for entity_type, count in stats['entities_by_type'].items():
            console.print(f"  {entity_type}: {count}")
        console.print()

    # Get recent runs
    runs_result = supabase.table("curator_runs").select("*").eq(
        "curator_id", curator["id"]
    ).order("started_at", desc=True).limit(runs).execute()

    if runs_result.data:
        console.print(f"[bold]Recent Runs ({len(runs_result.data)}):[/]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Started")
        table.add_column("Trigger")
        table.add_column("Status")
        table.add_column("Operations")
        table.add_column("Duration")

        for run in runs_result.data:
            started = run["started_at"][:16].replace("T", " ")
            status_color = {"completed": "green", "failed": "red", "running": "yellow"}.get(run["status"], "white")
            status = f"[{status_color}]{run['status']}[/{status_color}]"

            duration = "?"
            if run.get("completed_at"):
                from datetime import datetime
                start = datetime.fromisoformat(run["started_at"])
                end = datetime.fromisoformat(run["completed_at"])
                duration = str(end - start)

            table.add_row(
                started,
                run["trigger"],
                status,
                str(run.get("operations_count", 0)),
                duration
            )

        console.print(table)


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
