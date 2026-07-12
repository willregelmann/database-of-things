# Pokémon TCG — curation hints

## Directory structure

```
pokemon-tcg/
  CLAUDE.md
  template.schema.json
  _collection.yaml              # the whole "Pokémon TCG" collection
  <series>/
    _collection.yaml            # the series, e.g. "Base Series"
    <expansion>/
      _collection.yaml          # the expansion/set, e.g. "Base Set"
      <card>.yaml
```

Three levels under this category, not two: **series → expansion → card**. A
series is a group of related expansions released together under one banner
(e.g. "Base Series" contains Base Set, Jungle, Fossil; "Neo Series" contains Neo
Genesis, Neo Discovery, Neo Revelation, Neo Destiny). An expansion is a single
released set — same level a card-containing directory already occupied before
this convention existed.

**Determining a set's series**: look it up, don't guess from the name alone.
Bulbapedia's "List of Pokémon Trading Card Game expansions" groups every
expansion under its official series — use that grouping, not an invented one.

**Naming series directories**: same convention as expansions — lowercase,
hyphenated (e.g. `base-series`, `neo-series`, `ex-series`).

**Migrating an expansion that's still flat under `pokemon-tcg/`** (not yet
nested under its series): move it, don't recreate it — `git mv <expansion>/
<series>/<expansion>/`. Card `id`s, filenames, and content are untouched by the
move; only the path changes.

## Identifying items

Cards are identified by their **collector number within a set**, formatted as
`number/total` (e.g. `4/102`). This is the single most reliable disambiguator —
prefer it over name matching, since many cards share a name across sets (multiple
"Charizard" printings exist across dozens of sets) and even within a set via
reprints/alt-art variants.

## Verifying a set is complete

A set's total card count is public and fixed (encoded in every card's
`attributes.number` field, e.g. `.../102`). To check completeness:
1. Read any card's `attributes.number` field to get the set total.
2. Confirm that many distinct numbers 1..N exist as entity files in the set
   directory.
3. Cross-reference the full checklist against an authoritative source (Bulbapedia,
   Pokémon TCG API, or Serebii) rather than assuming — some sets have secret rares
   numbered above the printed total (e.g. `103/102`).

## Naming files

`<number>-<slugified-name>.yaml`, number zero-padded to the set's total digit
width, e.g. `004-charizard.yaml` for card `4/102` in a 102-card set. Reprints
of the same name within a set get disambiguated by number, which is already
unique.

## Rarity

`attributes.rarity` is enum-validated in `template.schema.json`. The enum
starts small (`Common`, `Uncommon`, `Rare`, `Holo Rare`, `Rare Holo EX`) and is
expected to grow — it is not meant to gate curation. If a card's real rarity
tier isn't in the enum yet, add it as part of the same PR: confirm the exact
label against an authoritative source (Bulbapedia, Pokémon TCG API, or
Serebii), then add that label to the `enum` array in `template.schema.json`
alongside the card file(s) that need it. Don't invent a label, and don't
reuse a near-miss enum value to dodge a schema edit (e.g. filing a `Rare Holo
GX` card as `Rare Holo EX`).

## Common pitfalls

- Don't confuse a set's *TCG expansion name* with its *physical product name*
  (booster box vs. theme deck exclusives) — the set directory should represent the
  expansion, not a retail SKU.
- Don't confuse *series* with *expansion* — a series (e.g. "Base Series") is
  never a directory that directly contains cards; only an expansion is.
- Promo cards are not part of any numbered set — they belong in a separate
  `promos` collection, not shoehorned into the nearest numbered set.
