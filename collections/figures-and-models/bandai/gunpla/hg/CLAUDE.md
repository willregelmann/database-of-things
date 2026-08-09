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
```

Confirmed but **not yet populated** (raw wiki page count before redirect
dedup — true unique counts will be lower, HGUC's 546→330 and HGGS's
149→84 are rough dedup-ratio guides): HG00/Gundam 00 (138), HGGTO/08th MS
Team-Thunderbolt era (124), HGI-BO/Iron-Blooded Orphans (120), HGCE/
Cosmic Era current-era (101), HGAGE/Gundam AGE (80), HGBF/Build Fighters
(65), HGAC/After Colony-Wing (36), HGBD/Build Divers (30), HGFC/Future
Century-G Gundam (26), plus ~9 smaller ones (HGGT, HGAW, HGI-BA, HGBC,
HGRG, HGGB, HGCC, HGM, HGGU) at 1-13 raw pages each.

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
count; HGUC's 546 raw pages resolved to 330 real unique kits, HGGS's 149
resolved to 84.

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
sub-line has these — HGGS had none.

**A malformed infobox `image =` value can be a full `[[File:...|thumb]]`
wikilink instead of a bare filename** — one HGUC kit
(`RX-78-3 Gundam + MS-09RS Rick Dom`) had this, and the standard
`[[...|X]]`-strips-to-`X` cleanup used everywhere else in this project
silently extracted the literal word "thumb" instead of the filename.
Worth a sanity check (does the resolved "filename" look like a real
image filename?) rather than assuming every infobox follows the plain
`image = Some-File.jpg` format.

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
