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
  `CLAUDE.md` and `template.schema.json` right next to its entity files

**Not optimizing for**:
- Exhaustive metadata (that's what source links are for)
- Real-time market data (we're a catalog, not a marketplace)

**Curation model**: the catalog is meant to grow and self-correct primarily
through AI agents web-searching for collectible data and opening PRs, not
through a human driving every addition. Two skills carry this:
- `collections-curate` — human- or agent-directed: add or edit specific
  entries
- `collections-audit-fix` — fully autonomous: picks a collection, web-searches
  to verify and fill gaps, opens a PR if anything changed; this is what the
  scheduled hourly job runs

## Repository structure

```
collections/                  # the data — see collections/README.md
  trading-card-games/
    pokemon-tcg/
      CLAUDE.md               # naming conventions, verification, pitfalls
      template.schema.json    # JSON Schema for item attributes, enforced by CI
      original-series/
        base-set/
          004-charizard.yaml
          ...
tags/                          # cross-cutting tag entities — see
                               # docs/primitives/TAG.md
  franchises/
    pokemon.yaml
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
date: "1999-01-09"
attributes:
  number: "4/102"
  rarity: Rare Holo
  illustrator: Mitsuhiro Arita
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
- `CLAUDE.md` and `template.schema.json` are only required where a directory's
  conventions differ from its parent's — a nested set normally inherits both
  from its category.

See [`collections/README.md`](collections/README.md) for the full format and
[`collections/trading-card-games/pokemon-tcg/CLAUDE.md`](collections/trading-card-games/pokemon-tcg/CLAUDE.md) for a
worked example.

## Naming files

`collections/<category>/.../<slugified-name>.yaml` — lowercase, hyphenated.

When a collection has canonical numbering (a collector number, catalog
number, issue number, etc.), **prefix the slug with that number**, zero-padded
to the collection's total digit width — e.g. `004-charizard.yaml` for card
`4/102`. This keeps directory listings in canonical order instead of
alphabetical order. Collections without canonical numbering just use
`<slugified-name>.yaml`.

The category `CLAUDE.md` documents the specifics (which field is canonical,
how to slugify, disambiguation rules) — see
[`collections/trading-card-games/pokemon-tcg/CLAUDE.md`](collections/trading-card-games/pokemon-tcg/CLAUDE.md) for a
worked example.

## Adding or editing an entry

Use the `collections-curate` skill if you're working with Claude Code — it
resolves the right template and `CLAUDE.md`, generates a UUID, writes the file
in the right place, and validates before opening a PR.

Otherwise, validate by hand before opening a PR:

```bash
cd tools/collections-validate
npm install   # first time only
npm run validate
```

CI runs this validator on every PR that touches `collections/**`.

## Curation workflow

1. Branch, add or edit entity files, update `CLAUDE.md`/template if a
   collection's conventions changed.
2. Open a PR. CI validates schema conformance, UUID uniqueness/format, and
   required files.

## Reference documentation

- **Collections format**: [`collections/README.md`](collections/README.md)
- **Category-specific curation**: `collections/<category>/CLAUDE.md`
- **Core data-model primitives**: [`docs/primitives/`](docs/primitives/)
  (`COLLECTION.md`, `ITEM.md`, `COMPONENT.md`, `TAG.md`)
