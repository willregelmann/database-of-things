# LEGO — curation hints

## What belongs here

Officially released LEGO building sets — bricks packaged under one official
set number, sold under a **theme** (and often a more specific **subtheme**).
Parked under `model-kits/` for now even though LEGO is a reusable
construction system rather than a single-use kit — see the family's own
[`../CLAUDE.md`](../CLAUDE.md) for why, and don't take that as precedent for
adding other non-kit product types here.

**LEGO Minifigures (the "Collectible Minifigures" blind-bag line) — an open
judgment call, not yet decided.** This standalone numbered series (one
random figure per bag, no set/box identity) is arguably closer to
`collectible-figures/` than to a themed building set — the same kind of call
already made for Power Rangers (see
[`../../collectible-figures/power-rangers/CLAUDE.md`](../../collectible-figures/power-rangers/CLAUDE.md)),
just in the opposite direction. Don't default to filing it under `lego/`
just because it's LEGO-branded — decide explicitly (and document the
reasoning here) when that line actually gets curated. Nothing for it exists
yet. **Not to be confused with the minifigures bundled inside ordinary
sets** — those are components of the set they ship in, see below.

## Themes and subthemes

LEGO organizes sets by **theme** (Star Wars, City, Technic, Ninjago, Creator,
...) and, within many themes, a more specific **subtheme** (e.g. City's
Traffic, Police, or Wildlife subthemes). Use
[Brickset](https://brickset.com/sets/bytheme) or the official LEGO site's own
theme listing as the authoritative grouping — don't invent a theme/subtheme
split that doesn't match how LEGO or Brickset actually categorizes a set.
Not every theme has subthemes; when one doesn't, sets sit directly under the
theme directory.

## Directory structure

```
lego/
  CLAUDE.md
  template.schema.json
  _collection.yaml               # the whole "LEGO" collection
  <theme>/                       # star-wars/, city/, technic/, ninjago/, ...
    _collection.yaml
    <subtheme>/                  # only where the theme genuinely has one
      _collection.yaml
      <set-number>-<slugified-name>.yaml
    <set-number>-<slugified-name>.yaml   # sets directly under the theme when no subtheme applies
```

## Identifying items

A set's **official LEGO set number** (e.g. `75192`) is the primary
identifier — record it as `attributes.number`. LEGO reused set numbers
across unrelated sets in some earlier eras; BrickLink/Brickset disambiguate
with a `-1`/`-2` suffix in their own catalogs, but that suffix isn't part of
the number as printed on the box — only add a disambiguator to this repo's
data (e.g. in the filename) if a genuine collision turns up, don't append it
by default.

## Naming files

`<set-number>-<slugified-name>.yaml`, e.g. `75192-millennium-falcon.yaml`.
Official set numbers aren't sequential within a theme the way Pokémon card
numbers are within a set, so don't zero-pad them — use the number exactly as
LEGO assigned it.

## Attributes

See `template.schema.json`. `attributes.pieceCount` and
`attributes.minifigCount` come from the set's own official packaging/manual
or a reliable source like Brickset — don't estimate.

## Minifigures as components

Sets bundle minifigures — these are components (see root
[`collections/CLAUDE.md`](../../CLAUDE.md), "Components"), not items in
their own right: owning a set's minifigures loose doesn't mean owning the
set. Not the same thing as the standalone blind-bag line discussed above.

Catalogued at `lego/<theme>/_minifigs/<number>-<slugified-name>.yaml` — one
flat bucket per theme, no subtheme nesting (a theme's minifig count is much
smaller than its set count, so it doesn't need the extra split sets get):

```
lego/
  star-wars/
    _collection.yaml
    _minifigs/                       # this theme's minifig components
      template.schema.json
      sw0028-astromech-droid-r2-d2.yaml
    episode-iv/                      # subtheme, sets only
      _collection.yaml
      7140-x-wing-fighter.yaml
```

`_minifigs/` sits *inside* the theme directory rather than in a sibling
top-level `minifigs/` tree, so there's exactly one directory anywhere
asserting "this is the Star Wars theme" — a sibling tree would need its own
`star-wars/` folder that has to be kept in sync with the sets side, with
nothing enforcing that they match. The leading underscore marks it as a
components bucket, not a collection (see root `collections/CLAUDE.md`,
"Components") — it doesn't get its own `_collection.yaml`; the theme's real
description/logo live once, on the theme's own `_collection.yaml`. It still
needs a `template.schema.json` (own or inherited), same as any directory
holding entity files.

If a single theme's minifig count ever approaches the 1000-item guideline
(root `collections/CLAUDE.md`), subdivide `_minifigs/` further (e.g. by era),
the same way sets already are — not needed yet for any curated theme.

**Identifying minifigures**: use the BrickLink/Brickset minifig number (e.g.
`sw0028`) as `attributes.number` — both catalogs share the same numbering
scheme. File a reused minifig (the same minifig reappears across many sets
over the years) under the theme it first appeared in; every other set that
includes it just references the same `id` via `components`, regardless of
which theme's `_minifigs/` bucket it physically lives in.

**Naming files**: `<minifig-number>-<slugified-name>.yaml`. Brickset's
minifig names sometimes spell out an exact print/color variant in full (e.g.
"Luke Skywalker - Pilot Suit, Simple Torso and Helmet, Dark Gray Hips,
Yellow Head") — keep that full name verbatim in the `name` field for
accuracy, but the filename slug can shorten to just the distinguishing
portion.

**A set references its minifigures via the top-level `components` field**,
not an attribute:

```yaml
components:
  - 53708aaf-cb2a-41c7-b03a-bc95d651f563   # sw0028 Astromech Droid, R2-D2
```

`attributes.minifigCount` stays as-is for sets whose specific minifigures
haven't been catalogued yet — it's a summary count, not a replacement for
`components`. Once a set's `components` list is populated, it should equal
`components.length`; both fields can coexist.
