---
name: run-curator
description: Execute a curator import pipeline
---

# Run Curator

All curators are agent curators. Read `.curator/specs/{Name}/prompt.md` for data source and import instructions.

Read secrets to get `COLLECTION_ID`:
- Local: `.curator/specs/{Name}/secrets.local.env`
- Prod: `.curator/specs/{Name}/secrets.prod.env`

## Execution Flow

- **Phase 1 (Research)** — follow `prompt.md` instructions; use WebFetch to retrieve data from the source; honor any `--limit` argument
- **Phase 2 (Sample Review)** — show a sample of what will be imported for approval before proceeding
- **Phase 3 (Import)** — call `entities_upsert` with the resolved `COLLECTION_ID`

If `--dry-run` is passed, stop after Phase 1 and report what was found without importing.

## Environment

Default env is `local`. Pass `--env=prod` to import to production.
