# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Database of Things (DBoT) is a public, file-based catalog of collectibles data.
There is no database, no server, and no secrets here — canonical data lives as
plain files in `collections/`, curators (human or AI) propose changes as pull
requests, and CI validates every change before it can merge.

**Mission**: Build the most comprehensive collectibles database on the Internet.

**Core Philosophy**: DBoT stays deliberately dumb. It's a transparent git repo
with a CI job that checks data quality — nothing more. Anyone could clone it and
use it for something else entirely. Consumers (like Will's Attic) pull from this
repo on their own schedule and build whatever infrastructure they need on top;
none of that lives here.

See `docs/dbot-target-architecture.md` for the full design rationale and the
migration history that got the project here.

**Not optimizing for**:
- Exhaustive metadata (that's what `source_url` is for)
- Real-time market data (this is a catalog, not a marketplace)
- A write API of any kind — the only way to change data is a PR

## Repo Layout

```
collections/
  <category>/
    AGENTS.md                 # curation hints for this whole category
    template.schema.json      # JSON Schema for item `attributes`
    _collection.yaml          # this collection's own entity record
    <set>/
      _collection.yaml        # nested collection; inherits AGENTS.md + template
                               # from the nearest ancestor unless it has its own
      <item>.yaml
tools/collections-validate/    # CI validator (Node/ajv)
docs/dbot-target-architecture.md  # the design doc — read this first
.curator/                      # legacy per-collection agent specs, pending
                                # migration into collections/<category>/AGENTS.md
                                # or removal (see that dir's own docs)
```

## Entity File Format

One YAML file per entity — human-readable, diffable, comments allowed for
curator notes.

```yaml
id: 3f4334f3-6a41-45fb-a1c1-dcf44566491e   # stable UUID, generated once, never reused
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

- `attributes` is validated against the collection's `template.schema.json`; the
  structural fields (`id`, `name`, `type`) are validated the same way everywhere.
- **No `collection:`/`parent_collection:` field.** Parent membership is *derived
  from directory position* — a file's parent is whatever `_collection.yaml` sits
  above it in the tree. Moving a file (`git mv`) re-parents it; there's no
  separate reference to keep in sync, and the validator rejects one if it finds it.
- Every directory that represents a collection (top-level or nested) needs a
  `_collection.yaml`, same shape as any other entity plus `type: collection`.
- `AGENTS.md` and `template.schema.json` are only required where a directory's
  conventions differ from its parent's — a nested set normally inherits both.

## Curation Workflow

Use the `collections-curate` skill (`.claude/skills/collections-curate/`) to add
or edit entries — it resolves the right template/`AGENTS.md`, generates a UUID,
writes the file in the right place, and runs the validator before opening a PR.

By hand, the flow is:

1. Find the target collection directory under `collections/`.
2. Read the nearest ancestor `AGENTS.md` (walk up until you find one) for
   naming/identification conventions specific to that category.
3. Read the nearest ancestor `template.schema.json` for the expected `attributes`.
4. Generate a new id: `uuidgen`. Never reuse or hand-pick one.
5. Write the entity YAML file.
6. Validate (see below) and fix anything it reports.
7. Open a PR — never push directly to `main`, and never open a PR without the
   user confirming first.

## Validating

```bash
cd tools/collections-validate
npm install   # first time only
npm run validate
```

Checks: missing/empty required fields (`id`, `name`, `type`), invalid or
duplicate `id`, missing `AGENTS.md`/`template.schema.json` (own or inherited),
missing `_collection.yaml`, a stray `collection:`/`parent_collection:` field, and
schema violations in `attributes`. CI runs this on every PR that touches
`collections/**` (`.github/workflows/ci.yml`).

## Important Notes

- This repo never holds credentials to anything, never pushes anywhere, and has
  no knowledge of what consumes its data.
- All IDs are UUIDs, generated once via `uuidgen` and never reused.
- Images are referenced by `source_url` only — binary image bytes do not live in
  this repo (see the "Images" section of `docs/dbot-target-architecture.md` for
  where that's headed).

## Reference Documentation

- **Architecture**: `docs/dbot-target-architecture.md` — the current design and
  migration phases.
- **Collections format**: `collections/README.md` — the file-based data model.
- **Curation skill**: `.claude/skills/collections-curate/SKILL.md`.
