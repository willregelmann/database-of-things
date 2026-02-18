"""Deterministic curator pipeline: fetch -> validate -> import."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from curator.config import CuratorConfig
from curator.errors import FetchError, ImportError_
from curator.mcp import MCPClient
from curator.state import Phase, load_status, write_status
from curator.validator import validate_file


def fetch(config: CuratorConfig, limit: int | None = None, **extra_args: str):
    """Run the curator's fetch_data.py script.

    Args:
        config: Resolved curator config.
        limit: Optional item limit to pass to script.
        **extra_args: Additional CLI arguments (e.g., set="Base Set").

    Raises:
        FetchError: If script exits non-zero or fetched_data.json not produced.
    """
    cmd = [sys.executable, str(config.fetch_script)]

    if limit is not None:
        cmd.extend(["--limit", str(limit)])

    for key, value in extra_args.items():
        cmd.extend([f"--{key}", str(value)])

    result = subprocess.run(
        cmd,
        cwd=str(config.curator_dir),
        env={**dict(os.environ), **config.secrets},
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout
    )

    if result.returncode != 0:
        raise FetchError(
            f"Fetch script exit code {result.returncode}",
            exit_code=result.returncode,
            stderr=result.stderr,
        )

    if not config.fetched_data_path.exists():
        raise FetchError(
            f"Fetch script succeeded but {config.fetched_data_path.name} not found"
        )


def import_items(
    config: CuratorConfig,
    data: dict,
    mcp: MCPClient,
) -> dict:
    """Import validated items via MCP bulk import.

    Args:
        config: Resolved curator config.
        data: Validated fetched_data.json contents.
        mcp: Connected MCP client.

    Returns:
        Import result dict with summary counts.

    Raises:
        ImportError_: If MCP returns success=false.
    """
    result = mcp.call_tool("bulk_import_curator_batch", {
        "collection_id": config.collection_id,
        "items": data["items"],
        "skip_duplicates": True,
        "localize_images": True,
    })

    if isinstance(result, dict) and not result.get("success", True):
        raise ImportError_(
            result.get("error", "Import failed"),
            mcp_response=result,
        )

    return result


def run(
    config: CuratorConfig,
    env: str = "local",
    limit: int | None = None,
    dry_run: bool = False,
    **extra_args: str,
) -> dict | None:
    """Execute the full curator pipeline: fetch -> validate -> import.

    Args:
        config: Resolved curator config.
        env: Environment for MCP connection.
        limit: Optional item limit for fetch.
        dry_run: If True, fetch + validate only (no import).
        **extra_args: Additional fetch arguments.

    Returns:
        Import result dict, or None if dry_run.
    """
    status = load_status(config.status_path)

    # Phase 1: Fetch
    if status.phase < Phase.FETCHED:
        fetch(config, limit=limit, **extra_args)
        write_status(config.status_path, Phase.FETCHED)

    # Phase 2: Validate (always)
    data = validate_file(config.fetched_data_path)
    write_status(config.status_path, Phase.VALIDATED)

    if dry_run:
        item_count = len(data.get("items", []))
        print(f"Dry run: {item_count} items validated, skipping import.")
        return None

    # Phase 3: Import via MCP
    if status.phase < Phase.IMPORTED:
        with MCPClient(env=env) as mcp:
            result = import_items(config, data, mcp)

        summary = result.get("summary", {}) if isinstance(result, dict) else {}
        write_status(config.status_path, Phase.IMPORTED, result="success", summary=summary)

        return result

    return None
