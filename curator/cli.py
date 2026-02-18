"""Click CLI for the curator pipeline."""

from __future__ import annotations

import click

from curator import pipeline
from curator.config import load_config
from curator.errors import CuratorError
from curator.mcp import MCPClient


@click.group()
@click.version_option(package_name="curator")
def cli():
    """Curator CLI - deterministic collectibles import pipeline."""


@cli.command()
@click.argument("name")
@click.option("--env", default="local", type=click.Choice(["local", "prod"]), help="Target environment.")
@click.option("--limit", type=int, default=None, help="Max items to fetch.")
@click.option("--dry-run", is_flag=True, help="Fetch + validate only, skip import.")
def run(name: str, env: str, limit: int | None, dry_run: bool):
    """Run the full curator pipeline: fetch, validate, import."""
    try:
        config = load_config(name, env=env)
        click.echo(f"Running curator: {config.name} (env={env})")

        result = pipeline.run(config, env=env, limit=limit, dry_run=dry_run)

        if result and isinstance(result, dict):
            summary = result.get("summary", {})
            click.echo(
                f"Import complete: "
                f"{summary.get('created', 0)} created, "
                f"{summary.get('updated', 0)} updated, "
                f"{summary.get('skipped', 0)} skipped, "
                f"{summary.get('errors', 0)} errors"
            )
            if result.get("image_processing"):
                img = result["image_processing"]
                click.echo(
                    f"Images: {img.get('succeeded', 0)}/{img.get('attempted', 0)} processed"
                )
        elif not dry_run:
            click.echo("Nothing to import (already up to date).")

    except CuratorError as e:
        raise click.ClickException(str(e))


@cli.command()
@click.argument("name")
@click.option("--limit", type=int, default=None, help="Max items to fetch.")
def fetch(name: str, limit: int | None):
    """Fetch data without importing."""
    try:
        config = load_config(name)
        click.echo(f"Fetching: {config.name}")
        pipeline.fetch(config, limit=limit)
        click.echo(f"Fetch complete: {config.fetched_data_path}")
    except CuratorError as e:
        raise click.ClickException(str(e))


@cli.command(name="import")
@click.argument("name")
@click.option("--env", default="local", type=click.Choice(["local", "prod"]), help="Target environment.")
def import_cmd(name: str, env: str):
    """Import existing fetched_data.json without re-fetching."""
    try:
        config = load_config(name, env=env)
        click.echo(f"Importing: {config.name} (env={env})")

        from curator.validator import validate_file

        data = validate_file(config.fetched_data_path)

        with MCPClient(env=env) as mcp:
            result = pipeline.import_items(config, data, mcp)

        if isinstance(result, dict):
            summary = result.get("summary", {})
            click.echo(
                f"Import complete: "
                f"{summary.get('created', 0)} created, "
                f"{summary.get('updated', 0)} updated, "
                f"{summary.get('skipped', 0)} skipped"
            )
    except CuratorError as e:
        raise click.ClickException(str(e))


@cli.command()
@click.argument("name")
@click.option("--env", default="local", type=click.Choice(["local", "prod"]), help="Target environment.")
def status(name: str, env: str):
    """Show curator collection statistics."""
    try:
        config = load_config(name, env=env)

        with MCPClient(env=env) as mcp:
            stats = mcp.call_tool("get_curator_stats", {"name": name})

        if isinstance(stats, dict):
            click.echo(f"Curator: {stats.get('collection_name', name)}")
            click.echo(f"Items: {stats.get('total_items', 0)}")
            click.echo(f"Last import: {stats.get('last_import', 'never')}")
            click.echo(f"Collection ID: {stats.get('collection_id', 'unknown')}")
        else:
            click.echo(f"Stats: {stats}")

    except CuratorError as e:
        raise click.ClickException(str(e))
