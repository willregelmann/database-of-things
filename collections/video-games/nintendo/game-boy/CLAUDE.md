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
  item-attributes.schema.json
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

## Sourcing (North American releases)

**Two-source method, adopted after the PR #193 rejection below** — a single
source wasn't enough to avoid the region/publisher and shared-title traps
reliably:

1. **Primary: Wikipedia's ["List of Game Boy games"](https://en.wikipedia.org/wiki/List_of_Game_Boy_games)**
   article — one sortable table, ~1,043 games, with **separate date columns
   per region** (Japan/North America/PAL) and the publisher shown per-region
   in the same row (`Interplay <sup>NA/EU</sup><br/>Imagineer <sup>JP</sup>`,
   "Unreleased" marked explicitly where a region never got it). Filter to
   rows where the NA column isn't "Unreleased". Fetch via
   `en.wikipedia.org/w/api.php?action=parse&page=List_of_Game_Boy_games&prop=wikitext`
   and parse the wikitext table directly — reading date and publisher
   *together* out of the same row is what structurally prevents the
   region-pairing error, rather than cross-matching two separately-sourced
   fields by hand.
2. **Secondary/cross-check: the Nintendo Fandom wiki**
   (`nintendo.fandom.com`), same MediaWiki-API access pattern used for
   Gunpla Wiki elsewhere in this repo (raw `api.php`, browser User-Agent, no
   login needed — rendered pages 402 but the API doesn't). Gives an
   independent developer/publisher/date check plus box art (no equivalent on
   Wikipedia's table). Verified against **date/dev/pub
   conflict-resolution policy**: Wikipedia's value wins on disagreement (it
   already read date+publisher together per-region, which is the safer
   read); a genuine conflict still gets the item filed with Wikipedia's
   value, with the conflict itself noted below rather than silently
   resolved or silently dropped.

**Fandom cross-referencing traps, found piloting 25 games this way (all
resolved in the pipeline, not just noted for next time):**

- **A same-titled Fandom article can silently be about a completely
  different, unrelated game** — looking up "The Amazing Spider-Man" landed
  on an article about the 2012 Wii/3DS movie tie-in, not the 1990 LJN Game
  Boy game; the correct page exists at the disambiguated title `The Amazing
  Spider-Man (Game Boy)`. This is the cross-reference-side twin of the
  shared-title trap below — don't trust a direct title match without
  checking the resolved page's own system/date data actually includes a
  Game Boy entry; fall back to `"<title> (Game Boy)"` or a `list=search`
  query when it doesn't.
- **Many Fandom infoboxes cover several platforms in one article** (NES,
  SNES, Game Boy, Virtual Console re-releases, ...), with `system1`,
  `system2`, `system3`... each carrying its own `systemN = <platform name>`
  label and `systemN<REGION>` date fields. **Match on the slot whose
  `systemN` label actually says "Game Boy"** (excluding "Game Boy Color"/
  "Game Boy Advance") — never assume `system1` is the right one; it's
  whichever platform the article lists first, often the original NES
  release for a multi-platform port.
- **A `<gallery>` block's `|` (filename**`|`**caption) reads as a false field
  boundary to a naive top-level-pipe field splitter** — treat `<gallery>` /
  `</gallery>` as depth-changing tokens the same way `{{`/`}}` and `[[`/`]]`
  already are, or the image field silently truncates and later fields shift
  by one.
- **A gallery's per-image caption can be a region tag ("NA"/"JP"/"EU") on a
  single-platform article, or a platform tag ("NES"/"SNES"/"Game Boy") on a
  multi-platform one — check for a platform tag that explicitly rules an
  image out before falling back to filename heuristics.** A same-titled
  image can be tagged with both a platform AND a region in its filename
  (`"... (NES) (NA).jpg"`) — a naive `"(NA)" in filename` check will
  wrongly accept an NES box just because it also happens to carry a region
  marker.
- **An untagged single (non-gallery) `image =` field on a multi-platform
  article is only safe to use when Game Boy is listed first (`system1`)** —
  otherwise it's conventionally the *first-listed* platform's box art (often
  the original NES release), not Game Boy's, even with no gallery to
  disambiguate. `Alfred Chicken`'s single image was explicitly captioned
  "North American NES box art" despite the article also covering a Game Boy
  release — caught by checking the `caption` field, not just the filename.
  When Game Boy isn't `system1` and the caption doesn't explicitly confirm
  Game Boy, leave the item imageless rather than risk a wrong-platform
  photo (5 of the 25-game pilot batch landed here as genuine, documented
  gaps — not a parsing bug).

**Pilot batch (25 games, alphabetically first): individual sourcing
conflicts, filed with Wikipedia's value per the policy above —**

- *Alleyway*: NA release date. Wikipedia: August 1, 1989. Fandom: August 11,
  1989. Filed as `1989-08-01`.
- *Adventure Island* (NA title for the Game Boy game also known in Japan as
  *Takahashi Meijin no Bōken Jima II*): developer. Wikipedia: Hudson Soft.
  Fandom's closest matching article (`Adventure Island II`, a combined
  NES+GB+VC article) credits Now Production instead — but that credit may
  actually belong to the *next* game in the series (*Adventure Island II:
  Aliens in Paradise*, Japan's *...III*), which Wikipedia independently
  also credits to Now Production. Filed as Hudson Soft; this whole
  franchise's Western/Japanese sequel-numbering is confusing across
  sources and deserves extra care rather than pattern-matching on title
  similarity alone.
- *Arcade Classic No. 3: Galaga / Galaxian*: developer. Wikipedia: Namco.
  Fandom: TOSE (with Namco credited only as the Japan-region *publisher*,
  not developer). Filed as Namco.

## Common pitfalls

- Don't conflate developer and publisher — many Game Boy titles were
  developed by one studio and published by another (or a different
  publisher per region).
- **Never pair a region's release `date` with another region's publisher.**
  The `date` and `publisher` on one record must describe the *same* release.
  A batch of 141 additions was rejected for exactly this (PR #193): *Harvest
  Moon GB* was filed with the Japanese date (Dec 1997) next to
  `publisher: Natsume Inc.`, who published only the North American release
  eight months later, so the record asserted something that never happened.
  Pick one release, and let its region determine both fields.
- **A shared title is not evidence of a shared game.** Western Game Boy
  releases were routinely built by relicensing or reskinning an unrelated
  Japanese cart, so an earlier JP entry with "the same" name is often a
  different product — not an earlier release of this one. Same PR conflated
  two that way (*Double Dragon II*, *F1 Pole Position*). Confirm the two are
  actually the same game before treating the earlier date as this record's
  first release.
- Compilation carts (multiple games on one cartridge) and multiplayer/
  peripheral-bundled releases (e.g. requiring a Game Link Cable accessory)
  need a curation decision before filing — check whether an existing
  precedent applies rather than guessing.
