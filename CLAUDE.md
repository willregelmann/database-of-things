# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Database of Things (DBoT) is a minimal, git-driven database of collectibles —
curated by agents and humans through GitHub pull requests.

**Mission**: Build the most comprehensive collectibles database on the Internet.

**Source of truth**: [`collections/`](collections/) — one YAML file per item,
organized into directories by category. There's no database to write to;
curation *is* opening a pull request.

**Core philosophy**:
- Minimal metadata by design — focus on coverage over exhaustive detail
- Source attribution via `source_url` for data provenance
- Curation guidance travels with the data: each category carries its own
  `AGENTS.md` and `template.schema.json` right next to its entity files

**Not optimizing for**:
- Exhaustive metadata (that's what source links are for)
- Real-time market data (we're a catalog, not a marketplace)

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

## Reference documentation

- **Collections format**: [`collections/README.md`](collections/README.md)
- **Category-specific curation**: `collections/<category>/AGENTS.md`
