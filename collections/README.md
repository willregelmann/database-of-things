# collections/

This directory is the canonical, file-based source of truth for DBoT's
collectibles data. See `docs/dbot-target-architecture.md` for the full design.

## Layout

```
collections/
  <domain-family>/             # broad grouping, e.g. trading-card-games
    CLAUDE.md                  # what belongs in this family, shared hints
    template.schema.json       # generic fallback; categories override it
    _collection.yaml           # this family's own entity record
    <category>/
      CLAUDE.md                 # curation hints for this category
      template.schema.json      # JSON Schema for item `attributes`
      _collection.yaml          # this collection's own entity record
      <set>/
        _collection.yaml        # nested collection; inherits CLAUDE.md + template
                                 # from the nearest ancestor unless it has its own
        <item>.yaml
```

Domain families exist to keep `collections/` itself from growing one entry
per specific collection — group related categories (all trading card games,
all coins, etc.) under one family directory. A category that doesn't fit any
existing family yet can sit directly under `collections/`, or start a new
family — see [`trading-card-games/CLAUDE.md`](trading-card-games/CLAUDE.md)
for a worked example of a family.

- Every directory that represents a collection (domain family, category, or
  nested set) needs a `_collection.yaml`.
- `CLAUDE.md` and `template.schema.json` are only required where a directory's
  conventions differ from its parent's — a nested set normally inherits both from
  its category.
- Every entity file (`_collection.yaml` included) needs `id` (a UUID, generated
  once, never reused), `name`, and `type`.
- **Parent membership is derived from directory position — don't add a
  `collection:`/`parent_collection:` field.** An item's parent is whatever
  directory it's in; a nested collection's parent is whatever directory *it's*
  in. Moving a file (`git mv`) re-parents it; there's no separate reference to
  keep in sync. The validator rejects these fields if it finds them.

## Validating

```bash
cd tools/collections-validate
npm install   # first time only
npm run validate
```

CI runs this on every PR that touches `collections/**`.

## Adding entries

Use the `collections-curate` skill (`.claude/skills/collections-curate/`) — it
resolves the right template/`CLAUDE.md`, generates a UUID, writes the file in the
right place, and runs the validator before you open a PR.
