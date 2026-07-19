# Manga — curation hints

## What belongs here

Japanese comic series — the **tankōbon volume** is the primary collectible
unit, not the individual magazine chapter. Most manga serializes chapter by
chapter in a magazine first, but those chapters generally aren't collected
individually the way Western comic issues are — see
[`comics/CLAUDE.md`](../comics/CLAUDE.md) for that separate, issue-based
convention. Not light novels or dōjinshi — those are a separate future
concern rather than folded in here.

**Model the English-language edition, not the original Japanese one** —
same convention as Pokémon TCG cataloging English/US card sets rather than
their Japanese originals (see
[`trading-card-games/pokemon-tcg/CLAUDE.md`](../trading-card-games/pokemon-tcg/CLAUDE.md)).
Volume numbers, titles, and dates all follow the English release; note the
original Japanese publisher/serialization in the series' `_collection.yaml`
description for context, but don't create separate entities for Japanese
tankōbon. If a series has never had an English release, that's a gap to
flag rather than a reason to catalog the Japanese edition instead — ask a
maintainer before deviating from this.

## Directory structure

```
manga/
  CLAUDE.md
  template.schema.json          # generic fallback; each series overrides it
  _collection.yaml               # this domain family's own entity record
  <series>/
    CLAUDE.md                    # series-specific conventions — required
    template.schema.json         # series-specific attributes — required
    _collection.yaml
    <volume>.yaml
```

**The top level under `manga/` is a series** — not a publisher, the way
`comics/` uses publisher as its top level. A manga series' original
Japanese publisher and its English-language licensor are different things
and can even change over the life of a series (a license can move to a new
publisher on re-release), so there's no single stable publisher to organize
by the way Western comics can. Publisher/licensor is instead a per-series
or per-volume detail, worked out in that series' own `CLAUDE.md` when it's
added — not a rule to fix here before any real series exists.

## Adding a new series

1. Create `manga/<series>/`.
2. Write its `CLAUDE.md` — volume numbering (confirm it's continuous and
   doesn't reset across arcs/seasons before assuming so), how to handle the
   Japanese-publisher-vs-English-licensor distinction for that series
   (including cases with more than one English edition over time — e.g. a
   relicense or an omnibus re-release), identification approach, known
   pitfalls.
3. Write its `template.schema.json` — don't reuse another series' attributes
   as-is; verify against the actual series (creator credits, format) rather
   than assuming they match.
4. Write its `_collection.yaml`.
5. Run the validator before opening a PR.
