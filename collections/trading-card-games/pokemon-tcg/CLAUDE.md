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

**e-Card Series `H`-prefixed numbering**: Aquapolis and Skyridge each give
certain Rare cards a separate Holo-foil printing, numbered independently of
the main checklist as `H1`–`H32` with its own fixed denominator — e.g. `H1/H32`,
not `H1/147`. Confirm the exact printed number against Bulbapedia's card
infobox ("English card no.") rather than assuming; don't reuse the set's main
denominator for these. `attributes.number`'s pattern allows an optional
leading `H` on either side of the fraction to accommodate this.

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

identifier. Confirmed cases: the "Shiny" secret sub-line that runs across
*four* Diamond & Pearl/Platinum Series sets without resetting (Stormfront
`SH1`-`SH3`, Platinum `SH4`-`SH6`, Supreme Victors `SH7`-`SH9`, Platinum:
Arceus `SH10`-`SH12`), Rising Rivals' Rotom-themed `RT1`-`RT6`, Platinum:
Arceus' `AR1`-`AR9`, the DP Black Star Promos line (`DP01`-`DP56`), and the
HGSS Black Star Promos line (`HGSS01`-`HGSS25`), all zero-padded as printed.
Verify via Bulbapedia's "English card no." field the same way as any other
numbering quirk — don't assume a denominator exists just because every other
case so far has had one, and don't assume a prefix resets to 1 in a later
set just because the set changed. `attributes.number`'s pattern allows a
bare 1-4-uppercase-letter prefix followed by digits (widened from 1-3 to
fit `HGSS01`-`HGSS25`), with no `/denominator`, to accommodate this.

**The Pokémon TCG API's `rarity` field is wrong for every bare-numbered
special-subset card checked so far.** All of `SH1`-`SH12`, `RT1`-`RT6`, and
`AR1`-`AR9` come back from the API as plain `"Rare"`, but every one
independently checked directly against Bulbapedia's own infobox (not a
search summary — fetch the raw page) is actually `Rare Holo`. This was
caught only after 3 of these cards had already been merged with the wrong
value in an earlier PR and had to be corrected after the fact. Don't trust
the API's `rarity` field for cards with this numbering pattern — verify
each subset directly against Bulbapedia before writing anything, even if
you've already verified a different subset with the same prefix pattern
in a different set.

**Fully spelled-out numbers, no digits at all**: the HeartGold & SoulSilver
Series' "Alph Lithograph" secret card — one per mainline expansion, same
name and illustrator every time, disambiguated only by which expansion
it's in — is printed with its English card number spelled out as a word:
`ONE`, `TWO`, `THREE`, `FOUR` for the four expansions in release order.
Confirmed via Bulbapedia's "English card no." field. `attributes.number`'s
pattern has a dedicated `ONE|TWO|THREE|FOUR` alternative for this rather
than a generic word-matcher, since it's a closed, known set.

**Unown cards on a set's *main* numbered checklist keep the bracket**: outside
the EX Unseen Forces secret sub-checklist above, every other Unown printing
(Neo Discovery/Revelation/Destiny, Diamond & Pearl Series, etc.) is named
`Unown [A]` — brackets included — both in the Pokémon TCG API's `name` field
and as the established convention across dozens of already-curated files.
Bulbapedia's *article title* for these drops the brackets (e.g. "Unown A
(Diamond & Pearl 65)"), but that's MediaWiki's own title-simplification, not
the printed card name — don't let a page title override a name the API
already gives you consistently. When multiple parallel agents touched Unown
cards in the same PR, some incorrectly stripped the brackets based on the
Bulbapedia title alone; keep the brackets.

**Prefixed-fraction subsets (`RC*`, `SV*`, ...)**: unlike every bare-prefix
subset (no fraction at all — see below), some subsets ARE printed with a
fraction, but the *denominator* is also prefixed, not the set's main
total: `RC1/RC25`, not `RC1/113`. Confirmed via Bulbapedia's raw wikitext
(`cardno=RC1/RC25`, `cardno=SV1/SV94`). Known cases so far: Legendary
Treasures' and Generations' separate "Radiant Collection"s (`RC25` and
`RC32` respectively — the denominator isn't fixed, check each set) and
Hidden Fates' "Shiny Vault" (`SV94`, folded into the `hidden-fates/`
directory alongside Hidden Fates' own numbered checklist — Shiny Vault is
not a separate expansion, Bulbapedia treats it as part of Hidden Fates).
`attributes.number`'s pattern allows any 0-2-uppercase-letter prefix on
either side of the fraction rather than an enumerated list of known
prefixes, since a new one has shown up in each of the last few series.
**Zero-pad the numeral in the filename to the collection's own width**,
same as any other numbered set (e.g. `rc01`-`rc25`, not `rc1`-`rc25`) —
Legendary Treasures originally shipped with `rc1`-`rc9` unpadded, which
sorted after `rc25` in a directory listing; fixed alongside the
Generations addition that caught it.

**BW Black Star Promos has a genuine printed inconsistency — don't
normalize it.** Cards are numbered `BW01`-`BW101` (2 digits), except
Reshiram and Zekrom, which are printed `BW004`/`BW005` (3 digits) — this
is confirmed as the actual printed number by multiple independent
commercial listings, not an API typo. Use each card's number exactly as
the API gives it; don't zero-pad the whole line to a uniform width.

**Kalos Starter Set has no rarity symbol on any card — omit the field,
don't guess.** All 39 cards return `rarity: null` from the API, and
Bulbapedia's raw wikitext confirms it: no `rarity=` parameter at all in
the template call (unlike a genuinely-uncredited-illustrator case, where
the card still has other rarity data). This is a real starter/beginner
product without rarity tiers, not a data gap. Same treatment as omitting
`illustrator` when uncredited: leave `attributes.rarity` out of the file
entirely rather than inventing a value.

**"Yellow A Alternate cards" are a separate, later collection — exclude
them from the mainline expansion they appear to belong to.** Starting
around Flashfire, several XY-era sets contain extra cards with a letter
suffix on their number (e.g. `88a`, `98a`/`98b`). These look like
alternate-art secret rares of the base numbered card, but Bulbapedia's
raw wikitext shows their `expansion=` parameter is literally `Yellow A
Alternate cards`, not the set they're numbered alongside (confirmed on 2
cards from 2 different sets) — a distinct reprint line, first released
during the *Sun & Moon* era via the Mega Powers Collection, that reuses
XY-era card numbers with a letter appended and a yellow "A" symbol to
keep them format-legal only alongside their original printing. **Do not
generate files for these letter-suffixed cards as part of a mainline XY
expansion** — they're out of scope until "Yellow A Alternate cards" gets
curated as its own collection. This also explains an API metadata
inconsistency: most sets' `total` field already excludes these cards, but
not consistently (Ancient Origins' `total: 100` excludes its one `75a`
card, while other sets' `total` appears to include theirs) — don't trust
the set-level `total` field for your generation target; count printed +
genuine secret rares (digits only, no letter suffix) yourself instead.

## Verifying a set is complete

A set's total card count is public and fixed (encoded in every card's
`attributes.number` field, e.g. `.../102`). To check completeness:
1. Read any card's `attributes.number` field to get the set total.
2. Confirm that many distinct numbers 1..N exist as entity files in the set
   directory.
3. Cross-reference the full checklist against an authoritative source (Bulbapedia,
   Pokémon TCG API, or Serebii) rather than assuming — some sets have secret rares
   numbered above the printed total (e.g. `103/102`).

**The API sometimes invents a sequential number for a card that isn't
printed with one at all — don't trust `attributes.number` blindly for
trailing basic Energy cards.** Sun & Moon's API data includes 9 basic
Energy cards (one of each type, including Fairy) at what look like
numbers 164-172, beyond its documented 163-card checklist. Bulbapedia's
own compiled printing history for these explicitly calls this a Sun &
Moon-era Basic Energy print "**unnumbered**" — the physical card carries
no collector number at all, and the API's sequential numbering is its own
invention for database bookkeeping, not something to reproduce. Excluded
these 9 from `sun-moon/` for exactly that reason (a card's number is this
category's primary identifier — don't fabricate one). This appears to be
a one-off tied to this specific print event, not a recurring pattern —
every other Sun & Moon-era set's genuine numeric-card count matched its
independently-documented community checklist exactly with no similar
excess, so don't assume it recurs without checking.

## Naming files

`<number>-<slugified-name>.yaml`, number zero-padded to the set's total digit
width, e.g. `004-charizard.yaml` for card `4/102` in a 102-card set. Reprints
of the same name within a set get disambiguated by number, which is already
unique.

## Rarity

`attributes.rarity` is enum-validated in `template.schema.json`. The enum
starts small (`Common`, `Uncommon`, `Rare`, `Rare Holo`, `Rare Holo ex`) and is
expected to grow — it is not meant to gate curation. If a card's real rarity
tier isn't in the enum yet, add it as part of the same PR: confirm the exact
label against an authoritative source (Bulbapedia, Pokémon TCG API, or
Serebii), then add that label to the `enum` array in `template.schema.json`
alongside the card file(s) that need it. Don't invent a label, and don't
reuse a near-miss enum value to dodge a schema edit (e.g. filing a `Rare Holo
GX` card as `Rare Holo ex`).

**`Rare Holo ex` is lowercase, and — despite an earlier note here predicting
otherwise — it's the SAME enum value for both the 2003-2007 `Pokémon-ex`
mechanic and the 2011+ `Pokémon-EX` mechanic.** The card's `name` field
still shows the real difference (space-separated lowercase `Chansey ex` vs.
hyphenated capitalized `Shaymin-EX`), and Bulbapedia's own card template
has a separate `class=EX` field to track the mechanic distinction — but the
`rarity` template parameter itself is `Rare Holo ex` (lowercase) for both,
confirmed via raw wikitext (`action=raw`, not rendered HTML/icon alt text,
which can be ambiguous when a page lists multiple printings) on 4
independent BW-era cards across 2 sets. The Pokémon TCG API instead returns
`"Rare Holo EX"` (capitalized) for these BW-era cards — don't trust that;
map it to the existing `Rare Holo ex` value, not a new one. Full-art
BW-era `-EX` reprints are a genuinely different, separate rarity: see
`Rare Ultra` below.

**Word order and case both matter, and existing precedent isn't automatically
correct.** Two rarity values in this enum were wrong before being
re-verified against Bulbapedia: `Holo Rare` (should be `Rare Holo` — reversed
word order) and `Rare Holo EX` (should be `Rare Holo ex` — wrong case). Both
went unnoticed through several PRs because "it's already in the enum" was
read as settled instead of re-verified — and a third value, `Rare Holo ☆`,
that looked equally suspect on the same pass turned out to already be
correct (confirmed independently on two cards from different sets). The
lesson isn't "assume existing values are wrong" — it's that *neither*
assumption (precedent is right / precedent is suspect) substitutes for
actually checking. If you're about to reuse an enum value instead of
confirming it fresh, verify it against Bulbapedia anyway.

**The API routinely drops the `Rare Holo` prefix from compound rarities.**
Confirmed so far: the API's `"Rare Prime"` should be `Rare Holo Prime`
(HeartGold & SoulSilver Series' Pokémon Prime mechanic), and its bare
`"LEGEND"` should be `Rare Holo LEGEND` (the same series' two-card LEGEND
Pokémon) — both verified independently on two cards each. This is the same
failure mode as `Rare Holo EX`/`Rare Holo ex`, just via omission instead of
casing: when the API gives a short/bare rarity string, check whether
Bulbapedia's actual infobox has a longer `Rare Holo <modifier>` form before
trusting the short one.

**`Rare Ultra`** (Black & White Series onward): the full-art secret-style
reprint of an already-numbered `-EX` Pokémon within the same set (e.g.
Entei-EX prints at both `13/108` as `Rare Holo ex` and again later in the
same set's numbering as `Rare Ultra`) — not a beyond-total secret rare,
still within the printed range. Matches the API's own casing; confirmed
via raw wikitext on 2 cards across 2 sets.

**`Rare Ace`** (Boundaries Crossed onward): "ACE SPEC" Trainer/Item cards
(max 1 per deck). Title case, NOT the API's all-caps `"Rare ACE"` —
confirmed via raw wikitext on 2 cards across 2 sets.

**`Rare BREAK`** (BREAKthrough onward): "BREAK Evolution" Pokémon (named
`<Pokémon> BREAK` in-game). Matches the API's casing exactly — confirmed
via raw wikitext on 2 cards across 2 sets, no correction needed.

**A single card's raw wikitext can itself be stale — cross-check against
the Rarity overview page's prose when they disagree.** Individual
Pokémon-GX cards' `{{rar|}}` template parameter often literally reads
`Ultra-Rare Rare` (confirmed on 2 different cards' base Sun & Moon-era
printings), which looks like a genuine value but isn't the intended one:
the Rarity overview page's own maintained prose states outright "Their
rarity is rare Holo GX." Individual card infoboxes aren't always kept in
sync with what a rarity is *supposed* to be called; when a raw-wikitext
value looks inconsistent with how the same rarity reads elsewhere (e.g.
via the API, or via other cards of the same mechanic), check the Rarity
overview page's dedicated prose for that mechanic before trusting a
single card's template value. Two independent raw-wikitext checks
verifies a value is *used*, not that it's *correct* — Bulbapedia is
maintained by editors, not machine-consistent.

**`Rare Holo GX`** (Sun & Moon onward): Pokémon-GX cards, including "Tag
Team" GX from Team Up onward. Matches the API's casing — confirmed via
the Rarity overview page's prose (see above), not just individual card
infoboxes, which are unreliable for this one specifically.

**`Rare Rainbow`** (Sun & Moon onward): secret "Rainbow Rare" full-art
reprints, mostly of Pokémon-GX. Matches the API exactly — confirmed via
raw wikitext.

**`Rare Prism Star`** (Ultra Prism onward): "Prism Star" (◇) cards, max 1
per deck. Matches the API and the Rarity overview page's prose exactly.

**`Rare Shining`** (Shining Legends only): a 2017 one-set revival of the
"Shining Pokémon" concept, but a GENUINELY DIFFERENT rarity from the
1999-2002 Neo Series' `Shining Holofoil` — don't conflate them just
because both eras name the cards "Shining <Pokémon>". Confirmed via raw
wikitext on 2 cards.

**`Rare Shiny` / `Rare Shiny GX`** (Hidden Fates' Shiny Vault only):
non-GX and GX secret reprints in the `SV1/SV94` sub-checklist. Matches
the API exactly — confirmed via raw wikitext on multiple cards. Also
genuinely different from both `Shining Holofoil` and `Rare Shining` —
three visually/conceptually similar but textually distinct "shiny
Pokémon" rarities now exist in this enum across three different eras;
don't collapse them into one just because they sound alike.

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
