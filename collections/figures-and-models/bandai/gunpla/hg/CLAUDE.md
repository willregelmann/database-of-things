# HG (High Grade) — curation hints

Like SD (see [`../sd/CLAUDE.md`](../sd/CLAUDE.md)), HG is not one line — it's
an umbrella over dozens of **independently numbered timeline sub-lines**,
confirmed via research before filing anything (see the top-level
[`../CLAUDE.md`](../CLAUDE.md)'s warning about this). Full-scope research
(2026-08-08) found roughly 20 real sub-lines totaling ~1,480 raw wiki pages
— by far the largest grade in the Gunpla family, bigger than every other
grade combined. Populated so far:

```
hg/
  CLAUDE.md
  _collection.yaml
  hguc/    # High Grade Universal Century — 330 kits, the original/largest sub-line
  hggs/    # High Grade Gundam SEED (original 2002-2010s era) — 84 kits
  hgce/    # High Grade Cosmic Era (newer current-era SEED prefix) — 55 kits
  hg00/    # High Grade Gundam 00 — 74 kits
  hggto/   # High Grade Gundam The Origin — 62 kits
  hgibo/   # High Grade Iron-Blooded Orphans — 63 kits
  hgage/   # High Grade Gundam AGE — 41 kits
  hgbf/    # High Grade Build Fighters — 38 kits
```

Confirmed but **not yet populated** (raw wiki page count before redirect
dedup — true unique counts will be lower, prior sub-lines' dedup ratios
are a rough guide): HGAC/After Colony-Wing (36), HGBD/Build Divers (30),
HGFC/Future Century-G Gundam (26), plus ~9 smaller ones (HGGT, HGAW,
HGI-BA, HGBC, HGRG, HGGB, HGCC, HGM, HGGU) at 1-13 raw pages each.

**HGGS and HGCE are two separate sub-lines despite both covering the
Cosmic Era/SEED timeline** — confirmed by checking their category members
directly. HGGS is the original 2002-2010s SEED-era HG line; HGCE is a
distinct, newer prefix used for current-era SEED kits (SEED Freedom-tie-in
releases, sports-team collabs, etc.). Don't merge them into one directory
just because they cover the same in-universe timeline.

## Sourcing: verify the wiki category name, it's rarely the short prefix

`Category:HGUC`, `Category:HG00`, etc. **do not exist** — the wiki
categorizes by spelled-out name (`Category:High Grade Universal Century`,
`Category:High Grade Gundam 00`, ...). The `allpages&apprefix=<PREFIX> `
method (same as every other grade) is the reliable way to enumerate a
sub-line's real kit pages by the prefix that actually appears in kit
titles — **always resolve with `redirects=1`** before trusting a raw
count.

**A prefix's own letters don't reliably tell you what it stands for —
verify via the infobox `Classification` field.** HGGTO's raw category
size suggested "08th MS Team"/"Thunderbolt" era at first glance; its
kits' own `Classification = High Grade Gundam The Origin` field showed
it's actually the *Mobile Suit Gundam: The Origin* prequel line. Don't
guess a sub-line's real scope from its prefix alone.

**MediaWiki's anonymous API caps `titles=` at 50 values per call** — chunk
at 20 (same as every other grade's fetch script) rather than requesting
all of a sub-line's titles in one call; a raw multi-title `curl` without
chunking silently returns a `toomanyvalues` error instead of data.

**Watch for `/Variants` navigational subpages** — a kit's own
`<title>/Variants` subpage (e.g. `HGUC RX-0 Unicorn Gundam (Destroy
Mode)/Variants`) is a list page linking to sibling releases, not a
product itself; it resolves as a "real" page under `redirects=1` but has
no infobox and must be excluded from the item set. Also a good place to
cross-reference for kits missing from the main `allpages` sweep — HGUC's
did surface 25 additional candidate titles this way, though all turned
out to be either duplicates already captured or genuine redlinks (kits
referenced but with no page written yet), not real gaps. Not every
sub-line has these — most (HGGS, HG00, HGI-BO, HGAGE) have none, and
where present they usually surface nothing new (HGGTO's 2), though HGBF's
one turned up 8 genuine redlinks (deferred, not fabricated).

**A malformed infobox `image =` value can be a full `[[File:...|thumb]]`
wikilink instead of a bare filename** — one HGUC kit
(`RX-78-3 Gundam + MS-09RS Rick Dom`) had this, and the standard
`[[...|X]]`-strips-to-`X` cleanup used everywhere else in this project
silently extracted the literal word "thumb" instead of the filename.
Worth a sanity check (does the resolved "filename" look like a real
image filename?) rather than assuming every infobox follows the plain
`image = Some-File.jpg` format.

**Unreleased-kit markers vary per sub-line — grep for more than one
pattern, and always confirm the page's OWN template rather than trusting
a bare keyword hit.** Three known so far: `{{Canceled}}`/
`{{Template:Canceled}}` (see [`../pg/CLAUDE.md`](../pg/CLAUDE.md)),
"Under Consideration" (see [`../rg/CLAUDE.md`](../rg/CLAUDE.md)), and
`{{PollsDoesNotGuarantee}}` (HGCE — a fan-census poll result never
produced). A bare "canceled"/"unreleased" keyword hit is often just
boilerplate "Variants" section text about a *different*, sibling kit
being canceled (HG00 had 7 of these false positives against 1 real one)
— check for the page's own template, not just a keyword match anywhere
on the page.

**Infobox template naming has at least six variants now — don't stop
adding to the regex after the first few.** On top of `Plamo Infobox`,
`Plamo_Infobox`, `Gunpla_Infobox`, and `Template:Plamo Infobox`
(documented in [`../mg/CLAUDE.md`](../mg/CLAUDE.md)), HGBF turned up a
sixth: `{{B-Club_Infobox}}` (Bandai's limited/garage-kit sub-brand). A
page with no infobox under the usual patterns may just need one more
variant added, not be a real gap.

**A sub-line's own infobox `Scale` and `Classification` fields can have
outright typos/copy-paste errors** — HGGS had one kit labeled `1/44`
(should be `1/144`, no such Gunpla scale exists) and another labeled
`Classification = High Grade Universal Century` despite being a Cosmic
Era unit (a copy-pasted infobox, not a real cross-grade kit) — see
`hggs/CLAUDE.md`. Skim the scale/classification distribution for
obviously-wrong outliers before trusting a bulk field extraction
wholesale.

Every other convention (flat directory per sub-line, `<slugified-name>.yaml`
no number prefix, no `variants` sub-entities, unreleased/`{{Canceled}}`
kit checks) follows [`../rg/CLAUDE.md`](../rg/CLAUDE.md),
[`../eg/CLAUDE.md`](../eg/CLAUDE.md), [`../pg/CLAUDE.md`](../pg/CLAUDE.md),
and [`../sd/CLAUDE.md`](../sd/CLAUDE.md) — see each sub-line's own
`CLAUDE.md` for its specific numbers and quirks.
