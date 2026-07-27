# Comics & Manga — curation hints

## What belongs here

Periodical comics and manga — Western comics and manga live together here
because they're the same kind of collectible (a serialized publication
bought a part at a time) sold through the same shops, and a growing number
of publishers put out both.

The **primary collectible unit differs by tradition**, and that's a
per-series fact, not a directory-level one:

- **Western comics — the single issue.** Not collected editions (trade
  paperbacks, deluxe hardcovers, compendiums); those repackage issues that
  already exist as entities here, so they're a separate future concern
  rather than duplicate entities.
- **Manga — the tankōbon volume**, not the individual magazine chapter.
  Most manga serializes chapter by chapter in a magazine first, but those
  chapters generally aren't collected individually the way Western issues
  are. Not light novels or dōjinshi — those are a separate future concern
  rather than folded in here.

Use `type: issue` or `type: volume` on the entity accordingly. The
distinction is recorded in the data, not in directory position.

## Model the English-language edition

For anything published in Japanese first, **catalog the English-language
edition, not the original Japanese one** — same convention as Pokémon TCG
cataloging English/US card sets rather than their Japanese originals (see
[`trading-card-games/pokemon-tcg/CLAUDE.md`](../trading-card-games/pokemon-tcg/CLAUDE.md)).
Volume numbers, titles, and dates all follow the English release; note the
original Japanese publisher and serialization in the series'
`_collection.yaml` description for context, but don't create separate
entities for Japanese tankōbon.

If a series has never had an English release, that's a gap to flag rather
than a reason to catalog the Japanese edition instead — ask a maintainer
before deviating from this.

## Directory structure

```
comics-and-manga/
  CLAUDE.md
  template.schema.json          # generic fallback; each series overrides it
  _collection.yaml
  <publisher>/
    _collection.yaml
    <series>/
      CLAUDE.md                  # series-specific conventions — required
      template.schema.json       # series-specific attributes — required
      _collection.yaml
      <issue-or-volume>.yaml
```

**The top level under `comics-and-manga/` is always a publisher** — never a
genre, imprint-within-a-publisher, era, medium, or anything else. Publisher
is its own directory level (not folded into series) because series names
aren't guaranteed unique across publishers, and because a flat list of
series would blow past the ~100-nested-collections guideline in
[`../CLAUDE.md`](../CLAUDE.md) long before the catalog is meaningfully
complete. Follow the shape of
[`image/monstress/CLAUDE.md`](image/monstress/CLAUDE.md) as a worked
example.

**For manga, the publisher is the English-language licensor** (VIZ Media,
Yen Press, Seven Seas, Kodansha USA, …) — consistent with modelling the
English edition, and the only publisher that's a stable property of the
edition being catalogued. The original Japanese publisher belongs in the
series' `_collection.yaml` description, not in the directory tree.

A license can move between English publishers over the life of a series (a
relicense, a new omnibus edition from someone else). When that happens,
file the series under the publisher of the edition being catalogued and say
so in the series' own `CLAUDE.md` — the same way Western series that change
imprints are handled. Don't split one series across two publisher
directories without a maintainer's sign-off.

## Adding a new series

1. Create `<publisher>/<series>/` (create `<publisher>/` too if it doesn't
   exist yet — it only needs a `_collection.yaml`, no `CLAUDE.md`/schema of
   its own unless it has series that need different conventions).
2. Write the series' `CLAUDE.md` — numbering scheme (confirm whether it's
   continuous or resets, and check for spin-offs/miniseries with separate
   numbering before assuming a flat structure), identification approach,
   known pitfalls. For manga, also cover how the
   Japanese-publisher-vs-English-licensor distinction plays out for that
   series, including any relicense or omnibus re-release.
3. Write `template.schema.json` — don't reuse another series' attributes
   as-is; verify against the actual series (credits, format) rather than
   assuming they match.
4. Write `_collection.yaml`.
5. Run the validator before opening a PR.
