# Squishmallows — curation hints

## Directory structure

```
squishmallows/
  CLAUDE.md
  template.schema.json
  _collection.yaml               # the whole "Squishmallows" line
  <number>-<slugified-name>.yaml
```

Flat — one level, no series/set nesting. Squishmallows are released under a
single continuous **Collector Number** sequence spanning every species and
every licensed collab (Pokémon, Disney, Marvel, Harry Potter, Sanrio, and
more), the same way Nendoroid uses one continuous number across franchises —
see [`../../collectible-figures/nendoroids/CLAUDE.md`](../../collectible-figures/nendoroids/CLAUDE.md)
for the analogous shape. Record the licensed franchise via
`attributes.license`, not as a directory split.

**Sub-formats with their own restarting numbering are separate sibling
collections under `plush/`, not nested here.** Squishmallows has several
distinct product formats that each keep their *own* Collector Number
sequence starting back at 1 — confirmed examples are **Fuzz-A-Mallows** and
**Squish-Doos**. Squishville (~2" minis) and Micromallows (~2.5" blind-bag
minis) are also distinct sub-brands with their own scale and packaging, not
just a size variant of the standard line. If curating one of these, add it
as its own collection under `plush/` (e.g. `plush/squishmallows-fuzz-a-mallows/`),
the same way Funko Pop Rides/Town/Moments/Albums are siblings of
`funko-pop/` rather than folded into it — see
[`../../collectible-figures/funko-pop/CLAUDE.md`](../../collectible-figures/funko-pop/CLAUDE.md).

Squishmallows' own "Rarity Scale" (Rare, Ultra Rare, Special Edition, Select
Series, Check-In Series, Founders Edition) is a tag-color/distribution
classification, not a numbering restart by itself — record it via
`attributes.rarity`, not a directory split. **Except**: some sources describe
Check-In Series as also restarting its own Collector Number sequence, which
would make it a numbering sub-line like Fuzz-A-Mallows rather than a plain
rarity tag. This wasn't independently confirmed — verify against the hangtag
or a fan database before filing a Check-In Series item, and treat it as its
own collection (not this directory) if it does turn out to restart numbering.

## Manufacturer

Squishmallows launched in 2017 under **Kelly Toys Holdings, LLC**
("Kellytoy"); **Jazwares, LLC** partnered with Kelly Toys in 2019 and
acquired it outright in April 2020. Use whichever manufacturer name is
actually printed on the item's hangtag/box (`attributes.manufacturer`) rather
than defaulting to one — pre-2020 releases generally credit Kelly Toys,
later releases credit Jazwares. Don't assume; check the actual credit.

## Identifying items

Figures are identified by their **Collector Number**, printed on the hangtag
alongside a size code, e.g. a tag reading `S5 #1366-2` is size 5", Collector
Number 1366, second released version/colorway of that number. Use the bare
Collector Number (without the size prefix) as `attributes.number`; record any
dash-suffixed version as part of the filename (see Naming files below) since
it disambiguates a re-release/colorway of the same base character, the same
way Funko's variant suffix does.

**Collector Number is not globally unique across all of Squishmallows** —
only within this directory's scope (the standard line + licensed collabs).
Fuzz-A-Mallows, Squish-Doos, and possibly Check-In Series each restart their
own sequence (see above) — always confirm which sub-line a number belongs to
before treating it as this directory's own.

Licensed characters (Pokémon, Disney, Sanrio, etc.) don't get a
**Squishdate** (the MM.DD.YYYY design-finalization date Kellytoy/Jazwares
prints for characters they created) or the personality-blurb bio that
standard-line characters get — don't treat a missing Squishdate as an error
for a licensed item.

Look up the number and metadata rather than guessing — the [Squishmallows
Wiki](https://squishmallowsquad.fandom.com/) (Collector Number List, Master
List) and [SquadApp](https://squadapp.app/) are the closest equivalents to
Funko's HobbyDB/Pop Price Guide; cross-reference more than one where
possible, since neither is as consistently authoritative as a
manufacturer-run database.

## Naming files

`<number>-<slugified-name>.yaml`, number zero-padded to 5 digits (e.g.
`01366`). Five digits is a judgment call based on current catalog volume
(Collector Numbers are already past 1,000 as of 2024, and the line is
growing faster than Funko Pop or Nendoroid did at a comparable age) — not a
canonical width, since this is a continuously growing line with no fixed
endpoint. Use the full printed name for the slug (e.g. `hans-the-hedgehog`,
not just `hans`) — Squishmallow names routinely repeat the first name across
unrelated species (see Common pitfalls). When a version suffix is present on
the tag (e.g. the `-2` in `S5 #1366-2`), append a short suffix to keep the
filename unique, e.g. `01366-hans-the-hedgehog.yaml` for the first version,
`01366-hans-the-hedgehog-v2.yaml` for the second.

## Sizes

Unlike Funko's variant suffix or Nendoroid's `-DX` suffix, a size difference
does **not** get its own Collector Number — the same character is typically
sold in several simultaneous sizes (a tag might read `S8`, `S16`, etc. across
different physical products, all sharing one number) with no single size
being more "canonical" than another. Don't try to force one size into
`attributes.size` for a general character entry — leave it off unless you're
cataloguing a specific release where the size is itself the distinguishing
fact (e.g. a retailer-exclusive size, like a 24" Costco-only release).

## `rarity`

`attributes.rarity` is enum-validated in `template.schema.json`. The enum
starts with Jazwares' own published tiers (`Rare`, `Ultra Rare`, `Special
Edition`, `Select Series`, `Founders Edition`) and is expected to grow — it
is not meant to gate curation, and a standard common release simply omits
the field rather than needing a `Common` value. If a real rarity/distribution
label isn't in the enum yet, confirm it against Jazwares' Rarity Scale page
or a fan database, then add it to the `enum` array alongside the item(s)
that need it.

## Common pitfalls

- Don't confuse the **Collector Number** with a UPC/barcode or a retailer's
  internal SKU — the number that matters is the one printed on the hangtag
  next to the size code.
- **Duplicate first names across unrelated species are common** (Squishmallow
  names are drawn from a shared pool independent of species) — always key
  identification off the full name + Collector Number, never the first name
  alone.
- Don't conflate **Squishdate** (design-finalization date) with the item's
  actual release/manufacture date — if populating the top-level `date`
  field, use a real sourced release date per [`../../CLAUDE.md`](../../CLAUDE.md),
  not the Squishdate.
- `manufacturer` isn't always "Jazwares, LLC" — check whether the item
  predates the 2020 acquisition (see Manufacturer above).
- Retailer exclusivity (Target, Walmart, Costco, Amazon, BoxLunch, Claire's,
  Cracker Barrel, Kohl's, and more) isn't centrally documented anywhere
  official — record it via `attributes.exclusive_to` when a source confirms
  it, but don't assume a release is exclusive just because you can't find it
  elsewhere.
- This line has no fixed endpoint, so there's no "verify the set is
  complete" step the way a card set has — completeness here just means
  cross-checking whatever range you're curating against the Squishmallows
  Wiki or SquadApp for that range.
- The Squishmallows Wiki's own per-character pages don't always agree with
  its Collector Number List page (missing `collector_number`/year fields, or
  a squishdate year that doesn't fit the surrounding sequence) — when a
  number's identity or date can't be cross-confirmed against a second
  source, skip it rather than filing a guess. A gap in the sequence (e.g. a
  missing number between two filed ones) means "not yet verified," not
  "doesn't exist."
