# Comics — curation hints

## What belongs here

Published comic book series — single issues as the primary collectible
unit, organized by publisher. Not collected editions (trade paperbacks,
deluxe hardcovers, compendiums) — those repackage issues that already exist
as entities here, so they're a separate future concern rather than
duplicate entities.

## Directory structure

```
comics/
  CLAUDE.md
  template.schema.json          # generic fallback; each series overrides it
  _collection.yaml
  <publisher>/
    _collection.yaml
    <series>/
      CLAUDE.md                  # series-specific conventions — required
      template.schema.json       # series-specific attributes — required
      _collection.yaml
      <issue>.yaml
```

**The top level under `comics/` is always a publisher** — never a genre,
imprint-within-a-publisher, era, or anything else. Publisher is its own
directory level (not folded into series) because series names aren't
guaranteed unique across publishers. Follow the shape of
[`image/monstress/CLAUDE.md`](image/monstress/CLAUDE.md) as a worked
example.

## Adding a new series

1. Create `<publisher>/<series>/` (create `<publisher>/` too if it doesn't
   exist yet — it only needs a `_collection.yaml`, no `CLAUDE.md`/schema of
   its own unless it has series that need different conventions).
2. Write the series' `CLAUDE.md` — numbering scheme (confirm whether it's
   continuous or resets, and check for spin-offs/miniseries with separate
   numbering before assuming a flat structure), identification approach,
   known pitfalls.
3. Write `template.schema.json` — don't reuse another series' attributes
   as-is; verify against the actual series (credits, format) rather than
   assuming they match.
4. Write `_collection.yaml`.
5. Run the validator before opening a PR.
