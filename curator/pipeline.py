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


BATCH_SIZE = 250


def _call_bulk_import(mcp: MCPClient, collection_id: str, items: list) -> dict:
    """Call bulk_import_curator_batch and raise on failure."""
    result = mcp.call_tool("bulk_import_curator_batch", {
        "collection_id": collection_id,
        "items": items,
        "skip_duplicates": True,
        "localize_images": True,
    }, timeout=600.0)
    if isinstance(result, dict) and not result.get("success", True):
        raise ImportError_(
            result.get("error", "Import failed"),
            mcp_response=result,
        )
    return result


def _merge_summaries(summaries: list[dict]) -> dict:
    """Sum created/updated/skipped/errors across batch results."""
    totals: dict = {}
    for s in summaries:
        for k, v in s.items():
            if isinstance(v, int):
                totals[k] = totals.get(k, 0) + v
    return totals


def import_items(
    config: CuratorConfig,
    data: dict,
    mcp: MCPClient,
) -> dict:
    """Import validated items via MCP bulk import, batched to avoid timeouts.

    Collections are sent first so cards can reference them as parents.
    Remaining items are sent in chunks of BATCH_SIZE.

    Args:
        config: Resolved curator config.
        data: Validated fetched_data.json contents.
        mcp: Connected MCP client.

    Returns:
        Merged import result dict with summary counts.

    Raises:
        ImportError_: If any MCP batch returns success=false.
    """
    items = data["items"]
    collections = [i for i in items if i.get("type") == "collection"]
    rest = [i for i in items if i.get("type") != "collection"]

    batches: list[list] = []
    if collections:
        batches.append(collections)
    for i in range(0, len(rest), BATCH_SIZE):
        batches.append(rest[i:i + BATCH_SIZE])

    if not batches:
        return {"summary": {}}

    total = len(items)
    summaries = []
    for idx, batch in enumerate(batches, 1):
        print(f"Batch {idx}/{len(batches)} ({len(batch)} items)...", flush=True)
        result = _call_bulk_import(mcp, config.collection_id, batch)
        if isinstance(result, dict):
            summaries.append(result.get("summary", {}))

    merged = _merge_summaries(summaries)
    return {"summary": merged}


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
