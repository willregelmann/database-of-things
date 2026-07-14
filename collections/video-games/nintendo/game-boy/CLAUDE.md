# Game Boy — curation hints

## Scope

Original Game Boy (DMG) releases only. **Game Boy Color is a separate
platform**, not a variant of this one — it has its own hardware, its own
product code prefix, and an exclusive library alongside its backward-
compatible one. File it as `video-games/nintendo/game-boy-color/`, a
sibling directory, when it's added — don't fold GBC-exclusive titles in
here.

## Directory structure

```
game-boy/
  CLAUDE.md
  template.schema.json
  _collection.yaml               # the whole "Game Boy" platform
  <slugified-name>.yaml
```

Flat, no sub-grouping — Game Boy games don't have an equivalent to a card
set or a numbered catalog line; each release is independent.

## Identifying items

Nintendo cartridges/boxes carry an official product code (format
`DMG-<code>-<region>`, e.g. `DMG-AREE` for a US release) — verify the exact
code per game against the actual box/cartridge or a reliable database (not
memory) before treating it as a schema field; it may be worth adding a
`catalog_number` attribute once the first real batch confirms the format
holds consistently. Region matters: the same game can have different codes
and sometimes different content across US/EU/JP releases — don't assume
one region's data applies to another without checking.

## Naming files

`<slugified-name>.yaml` — no canonical numbering exists across the
platform's library, so no zero-padded number prefix (per the root
`CLAUDE.md`'s naming rule for collections without canonical numbering).
Disambiguate same-named re-releases/reprints by adding a region or edition
qualifier to the slug if needed once that situation actually arises.

## Common pitfalls

- Don't conflate developer and publisher — many Game Boy titles were
  developed by one studio and published by another (or a different
  publisher per region).
- Compilation carts (multiple games on one cartridge) and multiplayer/
  peripheral-bundled releases (e.g. requiring a Game Link Cable accessory)
  need a curation decision before filing — check whether an existing
  precedent applies rather than guessing.
