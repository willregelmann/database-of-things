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
  hggto/   # High Grade Gundam The Origin (08th MS Team-Thunderbolt era) — 62 kits
  hgibo/   # High Grade Iron-Blooded Orphans — 63 kits
  hgage/   # High Grade Gundam AGE — 41 kits
  hgbf/    # High Grade Build Fighters — 38 kits
  hgac/    # High Grade After Colony (Gundam Wing) — 21 kits
  hgbd/    # High Grade Build Divers — 20 kits
  hgfc/    # High Grade Future Century (G Gundam) — 11 kits
  hggt/    # High Grade Gundam Thunderbolt — 6 kits
  hgaw/    # High Grade After War (Gundam X) — 7 kits
```

Confirmed but **not yet populated** (raw wiki page count before redirect
dedup — true unique counts will be lower per sub-line's own dedup ratio):
HGI-BA/Iron-Blooded Orphans Option/Weapon sets (12), HGBC/Build Custom
weapon & accessory sets (11), HGRG/Gundam Reconguista in G (7),
HGGB/G Gundam Beginning-Forever movie (5), HGCC/Turn A Gundam (3),
HGM/Neue Ziel (1), HGGU/Gundam Geminass (1).

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
resolved to 84. A sub-line's redirect dedup ratio varies widely — HGFC's
26 raw resolved to only 11 real kits (58% dedup, mostly from in-fiction
alias titles and spelling-variant pairs, not `/Variants` pages).

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

**Not every `/`-subpage is a `/Variants` list page, though — some are real
kits filed as subpages of their base kit's title.** HGGT had two
(`<base>/ONA Ver.`, `<base>/Bandit Flower Ver.`), each with a full
infobox, own `Release Date`, and own `image` — genuine distinct releases,
not navigational pages. The discriminator is always infobox presence, not
the `/` in the title. Renamed these to a parenthetical form for the `name`
field (matching every other bracketed-variant naming in this project)
since the wiki's own parenthetical alternate title for the same page was
just a redirect alias, not a separate missing kit.

**A malformed infobox `image =` value can be a full `[[File:...|thumb]]`
wikilink instead of a bare filename** — one HGUC kit
(`RX-78-3 Gundam + MS-09RS Rick Dom`) had this, and the standard
`[[...|X]]`-strips-to-`X` cleanup used everywhere else in this project
silently extracted the literal word "thumb" instead of the filename.
Worth a sanity check (does the resolved "filename" look like a real
image filename?) rather than assuming every infobox follows the plain
`image = Some-File.jpg` format.

**A second wiki-image placeholder filename exists**:
`Gunpla-Wiki-No-Image-Available.jpg` (HGBD), a sibling to the plain
`No-Image-Available.jpg` seen on HGUC — both are literal placeholder
strings the wiki uses in place of a real filename, not real files. Treat
any `image=` value containing "No-Image-Available" as empty and fall back
to the page's Stock Photos gallery.

**An infobox `image` filename can carry the wrong sub-line prefix without
being wrong** — HGAW's `GX-9900-DV Gundam X Divider` uses a file named
`HGUC-Gundam-X-Divider-box.jpg`, just a wiki upload-naming inconsistency;
the page's own title and category are unambiguously HGAW. Trust the
page's title/category over an inconsistent asset filename.

**Unreleased-kit markers vary per sub-line — grep for more than one
pattern.** On top of `{{Canceled}}`/`{{Template:Canceled}}` (see
[`../pg/CLAUDE.md`](../pg/CLAUDE.md)) and "Under Consideration" (see
[`../rg/CLAUDE.md`](../rg/CLAUDE.md)), HGCE turned up a third:
`{{PollsDoesNotGuarantee}}`, marking a fan-census poll result that was
never actually produced. None of these pages have a usable infobox, which
is what naturally excludes them from a parse pass keyed on infobox
presence — but don't assume "has no infobox" is itself sufficient
evidence something's unreleased without checking why it's missing one.

**A bare keyword hit for "unreleased"/"canceled" is very often a false
positive — always verify against the page's own infobox, never trust the
keyword alone.** Recurred on PG, HG00, HGAC, and HGFC: the match was
boilerplate Variants-section prose about a *different*, unrelated kit
(often a different grade entirely), not a marker on the page in question.

**A sub-line's own infobox `Scale`, `Classification`, and `Release Date`
fields can have outright typos/copy-paste errors** — HGGS had one kit
labeled `1/44` (should be `1/144`, no such Gunpla scale exists) and
another labeled `Classification = High Grade Universal Century` despite
being a Cosmic Era unit (a copy-pasted infobox, not a real cross-grade
kit) — see `hggs/CLAUDE.md`. HGBD's `GNX-803OG Ogre GN-X` infobox said
`Release Date = May 19, 2015`, flatly contradicted by the article's own
opening prose ("released in 2018") and by the line not existing before
2018 at all — corrected by hand. Skim for obviously-wrong outliers and
cross-check against surrounding prose before trusting a bulk field
extraction wholesale.

Every other convention (flat directory per sub-line, `<slugified-name>.yaml`
no number prefix, no `variants` sub-entities, unreleased/`{{Canceled}}`
kit checks) follows [`../rg/CLAUDE.md`](../rg/CLAUDE.md),
[`../eg/CLAUDE.md`](../eg/CLAUDE.md), [`../pg/CLAUDE.md`](../pg/CLAUDE.md),
and [`../sd/CLAUDE.md`](../sd/CLAUDE.md) — see each sub-line's own
`CLAUDE.md` for its specific numbers and quirks.
