"""
Curators CLI - Main entry point for autonomous curator management.

Phase 3: CLI-based conversational curator system with source discovery,
schema approval loops, and workflow generation.

Commands:
- curators init: Initialize a new curator with conversational approval
- curators run: Execute a curator
- curators list: List all curators
- curators info: Show curator details
- curators delete: Remove a curator
"""

import asyncio
import click
from rich.console import Console

from cli.commands.init import init_command
from cli.commands.run import run_command
from cli.commands.list import list_command
from cli.commands.info import info_command
from cli.commands.delete import delete_command

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    Curators - Autonomous agents for importing collectibles data.

    Phase 3: CLI-based conversational system with source discovery.
    """
    pass


@cli.command("init")
@click.option(
    "--collection-id",
    required=True,
    help="UUID of the target collection",
)
@click.option(
    "--instructions",
    default=None,
    help="Optional instructions (e.g., 'Import Elden Ring merchandise')",
)
def init(collection_id: str, instructions: str = None):
    """
    Initialize a new curator with conversational approval loops.

    This command:
    1. Discovers data sources (if not in instructions)
    2. Proposes collection schema → user approves/adjusts
    3. Proposes workflow plan → user approves/adjusts
    4. Creates and stores the curator

    Example:
        curators init --collection-id UUID --instructions "Import Elden Ring merchandise"
    """
    asyncio.run(init_command(collection_id, instructions))


@cli.command("run")
@click.argument("curator_name")
@click.option(
    "--instructions",
    default=None,
    help="Optional run-specific instructions (e.g., 'Only import figurines under €50')",
)
def run(curator_name: str, instructions: str = None):
    """
    Run an existing curator.

    Loads the curator from storage and executes the workflow.

    Example:
        curators run elden-ring-curator
        curators run elden-ring-curator --instructions "Only import figurines under €50"
    """
    asyncio.run(run_command(curator_name, instructions))


@cli.command("list")
def list_curators():
    """
    List all configured curators.

    Shows curator name, collection, last run time, and status.
    """
    asyncio.run(list_command())


@cli.command("info")
@click.argument("curator_name")
def info(curator_name: str):
    """
    Show detailed information about a curator.

    Displays sources, schema, workflow, and run history.

    Example:
        curators info elden-ring-curator
    """
    asyncio.run(info_command(curator_name))


@cli.command("delete")
@click.argument("curator_name")
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def delete(curator_name: str, yes: bool = False):
    """
    Delete a curator (collection is preserved).

    Removes the curator from the database and cleans up artifacts.

    Example:
        curators delete elden-ring-curator
    """
    asyncio.run(delete_command(curator_name, skip_confirm=yes))


if __name__ == "__main__":
    cli()
