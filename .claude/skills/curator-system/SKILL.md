---
name: curator-system
description: Use when creating curators, running imports, or managing collection imports. Examples: "create a curator for X", "import Pokemon cards", "run curator", "curator secrets".
source_files:
  - .claude/skills/run-curator/SKILL.md
  - .claude/skills/init-curator/SKILL.md
  - .curator/specs/
---

# Curator System

## What This Does

Curators are autonomous Claude agents that browse the web and import collectibles data directly via MCP tools. Each curator is defined by a `prompt.md` describing the data source, hierarchy, and entity schemas.

## Curator Structure

```
.curator/specs/{Collection Name}/
├── config.json           # type: "agent", dedup strategy
├── prompt.md             # Instructions: data source, hierarchy, entity schemas
├── secrets.env           # API keys (if required, gitignored)
├── secrets.local.env     # Local COLLECTION_ID (gitignored)
└── secrets.prod.env      # Production COLLECTION_ID (gitignored)
```

## Bulk Import

All imports use `entities_upsert`:

```
entities_upsert(collection_id=COLLECTION_ID, items=[...])
```

Single transaction, auto-deduplication via `external_ids`, parallel image processing, auto text embeddings.

## Secrets Management

- `secrets.env` — API keys (shared across environments)
- `secrets.local.env` — `COLLECTION_ID=uuid` for local
- `secrets.prod.env` — `COLLECTION_ID=uuid` for production

## Available Curators

Current curators in `.curator/specs/`:
- Pokemon TCG
- Power Rangers Toys
- LEGO Sets
- American Comics
- NTSC Video Games
- Bluey Figures

## Commands

```
/curator:init "Collection Name"    # Create new curator
/curator:run "Collection Name"     # Run import
/curator:run "Name" --env=prod     # Import to production
/curator:run "Name" --dry-run      # Research without importing
/curator:status "Name"             # Show collection stats
```
