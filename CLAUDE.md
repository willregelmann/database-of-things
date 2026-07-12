# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Database of Things (DBoT) is a minimal, git-driven database of collectibles —
curated by agents and humans through GitHub pull requests. It's the canonical
collectibles data behind [Will's Attic](https://www.my-attic.online).

**Mission**: Build the most comprehensive collectibles database on the Internet.

**Source of truth**: [`collections/`](collections/) — one YAML file per item,
organized into directories by category. There's no database to write to;
curation *is* opening a pull request. See
[`docs/dbot-target-architecture.md`](docs/dbot-target-architecture.md) for the
full design and where this is headed.

**Core philosophy**:
- Graph model conceptually (many-to-many relationships, arbitrary nesting),
  expressed as directory position rather than database rows or a
  `collection:`/`parent_collection:` field
- Minimal metadata by design — focus on coverage over exhaustive detail
- Source attribution via `source_url` for data provenance
- Curation guidance travels with the data: each category carries its own
  `AGENTS.md` and `template.schema.json` right next to its entity files

**Not optimizing for**:
- Exhaustive metadata (that's what source links are for)
- Real-time market data (we're a catalog, not a marketplace)
- User-generated content (curators maintain data quality)

## Repository structure

```
collections/                  # the data — see collections/README.md
  pokemon-tcg/
    AGENTS.md                 # naming conventions, verification, pitfalls
    template.schema.json      # JSON Schema for item attributes, enforced by CI
    original-series/
      base-set/
        charizard-4-102.yaml
        ...
tools/collections-validate/   # CI validator: schema conformance, UUID
                               # uniqueness, required-file presence
.claude/skills/collections-curate/  # agent tooling for adding/editing entries
docs/                          # design docs
```

## Entity file format

One YAML file per entity (`collections/<category>/.../<item>.yaml`):

```yaml
id: 3f4334f3-6a41-45fb-a1c1-dcf44566491e   # stable, generated once, never reused
name: Charizard
type: card
number: "4/102"
rarity: Holo Rare
year: 1999
attributes:
  hp: 120
  stage: Stage 2
  card_type: Fire
image:
  source_url: https://images.pokemontcg.io/base1/4_hires.png
```

- `attributes` is validated against the collection's `template.schema.json`;
  top-level fields (`id`, `name`, `type`) are structural and validated the
  same way everywhere.
- **No `collection:`/`parent_collection:` field.** An entity's parent is
  whatever directory it's in — the validator rejects these fields if it finds
  them.
- Every collection directory (top-level or nested) needs its own
  `_collection.yaml` — the entity record for the collection/set itself.
- `AGENTS.md` and `template.schema.json` are only required where a directory's
  conventions differ from its parent's — a nested set normally inherits both
  from its category.

See [`collections/README.md`](collections/README.md) for the full format and
[`collections/pokemon-tcg/AGENTS.md`](collections/pokemon-tcg/AGENTS.md) for a
worked example.

## Adding or editing an entry

Use the `collections-curate` skill if you're working with Claude Code — it
resolves the right template and `AGENTS.md`, generates a UUID, writes the file
in the right place, and validates before opening a PR.

Otherwise, validate by hand before opening a PR:

```bash
cd tools/collections-validate
npm install   # first time only
npm run validate
```

CI runs this validator on every PR that touches `collections/**`.

## Curation workflow

1. Branch, add or edit entity files, update `AGENTS.md`/template if a
   collection's conventions changed.
2. Open a PR. CI validates schema conformance, UUID uniqueness/format, and
   required files.
3. Review — human and/or an AI review pass.
4. Merge to `main`. Will's Attic's `attic-api` syncs from `main` on its own
   schedule (see `docs/dbot-target-architecture.md`); this repo never pushes
   anywhere and holds no credentials to anything of Will's Attic's.

## Legacy Supabase (not part of this repo's workflow)

Will's Attic still reads a live, separate Supabase Postgres project directly
over HTTPS/GraphQL for canonical-data reads — the system `collections/` is
replacing, not something this repo manages. This repo no longer holds that
project's schema, migrations, or any write path to it (removed once the
Phase 3 decision was made to discard legacy data rather than migrate it
forward — see `docs/dbot-target-architecture.md`). Decommissioning that live
project is gated on Will's Attic's own migration work (Phase 5/6 in the
target-architecture doc), independent of anything in this repo.

`scripts/` still contains legacy Supabase operational tooling (backups,
thumbnails, embeddings, curator scripts) for whoever operates that live
instance — none of it touches `collections/`.

## Reference documentation

- **Target architecture**: [`docs/dbot-target-architecture.md`](docs/dbot-target-architecture.md)
  — full design, migration phases, open questions
- **Collections format**: [`collections/README.md`](collections/README.md)
- **Category-specific curation**: `collections/<category>/AGENTS.md`
