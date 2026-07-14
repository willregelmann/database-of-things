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

## Collection records

Every `_collection.yaml` in this category — category, series, and expansion
level alike — carries two fields beyond the baseline `id`/`name`/`type`:

- `category: Trading Card Games` — same value at every level.
- `description` — a short prose blurb of context (release history, scope,
  what it spans). Match the tone of existing `_collection.yaml` files.

Neither is required by the schema, but every existing record has both —
include them when adding a new series or expansion.

Expansions also carry `image.source_url` pointing at the set's official
logo/box art (e.g. the Pokémon TCG API's `images.logo` for that set) when one
exists. Series records usually don't get one — most series (e.g. "Original
Series") are retroactive groupings with no single official logo to point to;
don't invent one.

## Identifying items

Cards are identified by their **collector number within a set**, formatted as
`number/total` (e.g. `4/102`). This is the single most reliable disambiguator —
prefer it over name matching, since many cards share a name across sets (multiple
"Charizard" printings exist across dozens of sets) and even within a set via
reprints/alt-art variants.

**EX Unseen Forces' lettered Unown secret set**: this expansion's 28 secret
Unown cards are printed on their own sub-checklist, numbered `A`–`Z` then
`!` and `?`, with a fixed `/28` denominator (e.g. `G/28`, `!/28`) — entirely
independent of the main `/115` numbering. The card's actual name is just
"Unown" (verified via both the Pokémon TCG API and Bulbapedia's own article
title, e.g. "Unown (EX Unseen Forces G)") — don't append the letter to the
`name` field, it belongs only in `attributes.number`. A naive fetch of a
per-letter Bulbapedia URL can silently 404 into an empty "no text on this
page" stub rather than erroring — confirm you actually got a populated
infobox (check for the "English card no." field) before trusting a page
fetch, and prefer web-searching for the exact article title over guessing
it. `attributes.number`'s pattern allows a single `A`-`Z`/`!`/`?` character
as the numerator to accommodate this.

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

## Third-party data sources can disagree — verify glyphs, not just facts

The Pokémon TCG API (`api.pokemontcg.io`) is a convenient bulk source for
card lists (name, number, rarity, illustrator, image), but it isn't
authoritative for exact typography. Confirmed case: the "Gold Star" Pokémon
of the EX Series (e.g. `Mudkip ★`) come back from the API with `★` (U+2605
BLACK STAR), but the actual printed card and Bulbapedia's own article title
use `☆` (U+2606 WHITE STAR) — `Mudkip ☆`. Use the API for bulk data, but
when a name contains a symbol (stars, gender signs, Greek letters), confirm
the exact codepoint against Bulbapedia's page title or infobox before
writing the entity file — don't assume the API's rendering is correct.

## Common pitfalls

- Don't confuse a set's *TCG expansion name* with its *physical product name*
  (booster box vs. theme deck exclusives) — the set directory should represent the
  expansion, not a retail SKU.
- Don't confuse *series* with *expansion* — a series (e.g. "Base Series") is
  never a directory that directly contains cards; only an expansion is.
- Promo cards are not part of any numbered set — they belong in a `promos`
  collection, not shoehorned into the nearest numbered set. **Whether that
  `promos` collection is scoped to a series depends on whether the promo
  line itself was scoped that way at the time.** From the Nintendo era
  onward, promo lines are explicitly tied to one series — often via a
  number prefix (e.g. "Mega Evolution Promos" uses `MEP`, distinct from
  every other series' promo prefix) — and that promo line lives at
  `<series>/promos/`, a sibling of that series' expansions. But the
  earliest promo line, the **Wizards Black Star Promos** (1999–2003, #1–53),
  predates that convention entirely: Wizards never reset or re-scoped the
  numbering by series, so cards from the Original Series, Neo Series, and
  e-Card Series eras are interleaved in one continuous run. Don't split it
  across series directories to force-fit the later convention — file it as
  its own top-level collection, `pokemon-tcg/wizards-black-star-promos/`,
  a sibling of `original-series/` rather than nested inside it. Whichever
  form a `promos` collection takes, treat it like any other expansion-level
  directory: it needs its own `_collection.yaml` and contains card files
  directly (promo numbering is promo-specific, not tied to any expansion).
