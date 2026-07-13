# Nendoroid — curation hints

## Directory structure

```
nendoroids/
  CLAUDE.md
  template.schema.json
  _collection.yaml               # the whole "Nendoroid" line
  <number>-<slugified-name>.yaml
```

Flat — one level, no series/set nesting. Unlike a trading card game, Nendoroid
doesn't release in discrete numbered sets; Good Smile assigns one continuous
catalog number across every franchise, so there's no natural grouping level
to insert. Don't invent one.

**Spin-off lines are siblings, not nested items.** Nendoroid Doll, Nendoroid
More, and Nendoroid Petit are separate Good Smile product lines with their
own numbering — they don't belong in this directory. If curating one, add it
as its own collection under `collectible-figures/`, a sibling of
`nendoroids/`, not folded into this numbering.

## Collection records

The `_collection.yaml` at this level carries `description` beyond the
baseline `id`/`name`/`type` — a short blurb of scope (what the line is, when
it started). Not required by the schema, but match the tone of the existing
record.

## Identifying items

Figures are identified by their **official Nendoroid No.**, e.g. `1200`.
Numbers aren't always bare integers — variant releases use a letter suffix
(e.g. `245b`) or a `-DX` deluxe-version suffix (e.g. `970-DX`); use the number
exactly as Good Smile printed it, don't normalize it away. Prefer the number
over name matching — many characters get multiple Nendoroids across different
versions/re-releases, and the number is the reliable disambiguator.

Look up the number and metadata rather than guessing — Good Smile's own
listing pages (`goodsmile.info/en/nendoroid<range>`) and
[MyFigureCollection](https://myfigurecollection.net/) are the authoritative
sources; use the same source consistently within one PR when cross-checking a
batch.

## Naming files

`<number>-<slugified-name>.yaml`, number zero-padded to 4 digits (e.g.
`0004`), including any letter/`-DX` suffix in the slug portion if needed for
uniqueness (e.g. `0245b-...`). Four digits covers the catalog with headroom;
this is a continuously growing line, unlike a fixed-size card set, so there's
no "total" to pad against — 4 digits is a judgment call based on current
volume (catalog is past #3000 as of 2026), not a canonical width.

## `release_type`

`attributes.release_type` is enum-validated in `template.schema.json`. The
enum starts small (`Standard`, `Exclusive`, `Limited`) and is expected to
grow — it is not meant to gate curation. If a figure's real release
classification isn't in the enum yet (e.g. a specific convention-exclusive
label), add it as part of the same PR: confirm the label against Good
Smile's own listing or MyFigureCollection, then add it to the `enum` array
alongside the figure file(s) that need it.

## Common pitfalls

- Don't confuse the **Nendoroid No.** with a JAN/product barcode or a
  manufacturer SKU — the catalog number is what appears on the box as
  "Nendoroid No. ###".
- `manufacturer` isn't always "Good Smile Company" — some releases are
  co-branded or produced under a different Good Smile subsidiary/partner
  (e.g. Phat Company, Good Smile Arts Shanghai). Check the actual credit,
  don't assume.
- Variant/re-release versions (e.g. a "2.0" re-sculpt, a con-exclusive color
  edition) get their own Nendoroid No. and their own entity file — don't
  merge multiple releases of the same character into one file.
- This line has no fixed endpoint, so there's no "verify the set is
  complete" step the way a card set has — completeness here just means
  cross-checking whatever range you're curating against Good Smile's listing
  pages for that range.
