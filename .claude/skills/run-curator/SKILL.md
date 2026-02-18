---
name: run-curator
description: Execute a curator import pipeline (fetch, validate, import)
---

# Run Curator

Execute a curator pipeline using the `curator` CLI.

## Usage

When the user says `/curator:run "Name"` or asks to run/import a curator, execute:

```bash
.venv/bin/python -m curator run "Name" --env=local
```

## Parsing Arguments

Map user intent to CLI flags:

| User says | CLI command |
|-----------|------------|
| `/curator:run "Pokemon TCG"` | `python -m curator run "Pokemon TCG"` |
| `/curator:run "Pokemon TCG" --limit=50` | `python -m curator run "Pokemon TCG" --limit 50` |
| `/curator:run "Pokemon TCG" --env=prod` | `python -m curator run "Pokemon TCG" --env prod` |
| `/curator:run "Pokemon TCG" --fetch-only` | `python -m curator fetch "Pokemon TCG"` |
| `/curator:run "Pokemon TCG" --import-only` | `python -m curator import "Pokemon TCG"` |
| `/curator:run "Pokemon TCG" --dry-run` | `python -m curator run "Pokemon TCG" --dry-run` |
| "Import latest Pokemon Base Set cards" | `python -m curator run "Pokemon TCG" --set "Base Set"` |
| "Fetch 50 LEGO sets but don't import" | `python -m curator fetch "LEGO Sets" --limit 50` |

## Execution

1. Run the CLI command via Bash using `.venv/bin/python -m curator`
2. Report the output to the user
3. If it fails with a clear error, report it — the CLI provides actionable messages

## Available Commands

```bash
# Full pipeline: fetch → validate → import
.venv/bin/python -m curator run "Name" --env=local --limit=50

# Fetch only (no import)
.venv/bin/python -m curator fetch "Name" --limit=50

# Import existing fetched_data.json
.venv/bin/python -m curator import "Name" --env=local

# Show collection stats
.venv/bin/python -m curator status "Name" --env=local
```

## Flags

- `--env local|prod` — Target environment (default: local)
- `--limit N` — Max items to fetch
- `--dry-run` — Fetch + validate only, skip import

## Error Recovery

The CLI provides clear error messages. If the user asks you to debug further:

1. Read the traceback
2. Check the curator's fetch script at `.curator/curators/{name}/scripts/fetch_data.py`
3. Fix the issue and re-run

The pipeline is resumable — re-running skips already-completed phases (uses `.curator/curators/{name}/run_status.json`).
