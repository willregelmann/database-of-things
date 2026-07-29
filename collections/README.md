# collections/

This directory is the canonical, file-based source of truth for DBoT's
collectibles data. See [`../docs/primitives/`](../docs/primitives/) for the
data model it's built from — [`COLLECTION.md`](../docs/primitives/COLLECTION.md),
[`ITEM.md`](../docs/primitives/ITEM.md), and
[`TAG.md`](../docs/primitives/TAG.md).

> **License:** the data in this directory is released into the public domain
> under CC0 1.0 — see [`../LICENSE-DATA`](../LICENSE-DATA). Third-party
> trademarks and the images referenced by the `image` field are *not* covered;
> see [`../DISCLAIMER.md`](../DISCLAIMER.md).

## Layout

```
collections/
  <domain-family>/             # broad grouping, e.g. trading-cards
    CLAUDE.md                  # what belongs in this family, shared hints
    item-attributes.schema.json  # generic fallback; categories override it
    _collection.yaml           # this family's own entity record
    <category>/
      CLAUDE.md                 # curation hints for this category
      item-attributes.schema.json  # JSON Schema for item `attributes`
      _collection.yaml          # this collection's own entity record
      <set>/
        _collection.yaml        # nested collection; inherits CLAUDE.md + template
                                 # from the nearest ancestor unless it has its own
        <item>.yaml
```

Domain families exist to keep `collections/` itself from growing one entry
per specific collection — group related categories (all trading cards, all
coins, etc.) under one family directory. A category that doesn't fit any
existing family yet can sit directly under `collections/`, or start a new
family — see [`trading-cards/CLAUDE.md`](trading-cards/CLAUDE.md)
for a worked example of a family.

- Every directory that represents a collection (domain family, category, or
  nested set) needs a `_collection.yaml`.
- `CLAUDE.md` and `../item-attributes.schema.json` are only required where a directory's
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

Read the target directory's `CLAUDE.md` chain and nearest
`item-attributes.schema.json`, generate a fresh id with `uuidgen` (never reuse
or hand-pick one), write the file per the layout above, then run the
validator before you open a PR.
