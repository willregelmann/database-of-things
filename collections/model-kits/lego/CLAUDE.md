# LEGO — curation hints

## What belongs here

Officially released LEGO building sets — bricks packaged under one official
set number, sold under a **theme** (and often a more specific **subtheme**).
Parked under `model-kits/` for now even though LEGO is a reusable
construction system rather than a single-use kit — see the family's own
[`../CLAUDE.md`](../CLAUDE.md) for why, and don't take that as precedent for
adding other non-kit product types here.

**LEGO Minifigures — an open judgment call, not yet decided.** The
"Collectible Minifigures" blind-bag series (numbered series, one random
random figure per bag, no set/box identity) is arguably closer to
`collectible-figures/` than to a themed building set — the same kind of call
already made for Power Rangers (see
[`../../collectible-figures/power-rangers/CLAUDE.md`](../../collectible-figures/power-rangers/CLAUDE.md)),
just in the opposite direction. Don't default to filing it under `lego/`
just because it's LEGO-branded — decide explicitly (and document the
reasoning here) when that line actually gets curated. Nothing for it exists
yet.

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
