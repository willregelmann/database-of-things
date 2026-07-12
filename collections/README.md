# collections/

This directory is the canonical, file-based source of truth for DBoT's
collectibles data. See `docs/dbot-target-architecture.md` for the full design.

## Layout

```
collections/
  <category>/
    AGENTS.md                 # curation hints for this category
    template.schema.json      # JSON Schema for item `attributes`
    _collection.yaml          # this collection's own entity record
    <set>/
      _collection.yaml        # nested collection; inherits AGENTS.md + template
                               # from the nearest ancestor unless it has its own
      <item>.yaml
```

- Every directory that represents a collection (top-level or nested) needs a
  `_collection.yaml`.
- `AGENTS.md` and `template.schema.json` are only required where a directory's
  conventions differ from its parent's — a nested set normally inherits both from
  its category.
- Every entity file (`_collection.yaml` included) needs `id` (a UUID, generated
  once, never reused), `name`, and `type`.

## Validating

```bash
cd tools/collections-validate
npm install   # first time only
npm run validate
```

CI runs this on every PR that touches `collections/**`.

## Adding entries

Use the `collections-curate` skill (`.claude/skills/collections-curate/`) — it
resolves the right template/`AGENTS.md`, generates a UUID, writes the file in the
right place, and runs the validator before you open a PR.
