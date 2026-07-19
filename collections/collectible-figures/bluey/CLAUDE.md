# Bluey — curation hints

## What belongs here

Moose Toys' official character figure lines for the *Bluey* animated series
(BBC Studios/Ludo Studio). Moose Toys has held the global master toy license
since 2019 — verify `attributes.manufacturer` as **Moose Toys Pty Ltd** unless
a specific product says otherwise.

Moose Toys sells Bluey across many product families, but only some are
standalone character figures. **Excluded from this category** (same
figures-only scope as the rest of `collectible-figures/` — see
[`../CLAUDE.md`](../CLAUDE.md)):

- Plush (a `plush/` concern if curated, not here)
- Playsets (Family Home, Supermarket, Heeler House, Cruise Ship, ...)
- Vehicles (4WD, Beach Quad, Bus, Garbage Truck, ...) — even ones that
  include an exclusive figure, the vehicle is the product, not the figure
- Games (5-in-1, Bingo's Bingo, Shadowlands board game)
- Mash'ems (squishy fidget collectibles — not poseable/static figures)

**This is not the same exception as Power Rangers.** Power Rangers curates
its whole toy line in one place because the manufacturer releases and
numbers figures/Zords/vehicles/playsets together as one inseparable product
line (see [`../power-rangers/CLAUDE.md`](../power-rangers/CLAUDE.md)). Bluey
is the opposite: Moose Toys sells each product family under its own distinct
name, format, and (where present) numbering, with no shared catalog — closer
to Funko's many independent Pop! formats than to Power Rangers' one line.
Don't fold vehicles/playsets in here just because a figure comes bundled
with one.

## Directory structure

```
bluey/
  CLAUDE.md
  template.schema.json          # generic fallback; each sub-line overrides it
  _collection.yaml               # the whole Bluey figures collection
  fuzzies/                       # soft flocked mini figures, blind-bag
    CLAUDE.md
    template.schema.json
    _collection.yaml
  mini-figures/                  # hard plastic ~1" figures, blind-bag
    CLAUDE.md
    template.schema.json
    _collection.yaml
  poseable-figures/               # 2.5-3" articulated figures, multi-pack/single-pack
    CLAUDE.md
    template.schema.json
    _collection.yaml
```

Each sub-line is its own top-level collection here, the same reasoning as
Nendoroid vs Figma vs Funko Pop under [`../CLAUDE.md`](../CLAUDE.md) — Fuzzies,
Mini Figures, and (Standard) Poseable Figures are different products with
different scale, material, and packaging, not variants of one line.

## No official global numbering

None of Bluey's figure formats print a global catalog/collector number the
way e.g. Funko Pop's "Pop! No." does. Identify figures by character name plus
their pack/series name — see each sub-line's own `CLAUDE.md` for its specific
identification approach and known pitfalls before filing anything.

## Manufacturer

`attributes.manufacturer` is `Moose Toys Pty Ltd` across every sub-line
unless a specific release credits a different legal entity — check the
package/listing rather than assuming.
