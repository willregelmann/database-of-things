# Collection

A **collection** is a directory that groups other entities — nested
collections, items, or (for a subset of collections) a components bucket.
Every domain family, category, series, and set under `collections/` is a
collection. This is the "container" primitive; see [ITEM.md](ITEM.md) for
the "member" primitive and [COMPONENT.md](COMPONENT.md) for a third,
non-owned primitive.

## Identity

A collection's entity record is `_collection.yaml`, one per directory —
domain family, category, series, set, any level. It carries the same
baseline as any entity — `id` (a UUID, generated once, never reused),
`name`, `type: collection` — plus whichever optional fields below apply.

```yaml
id: 177ba0d9-f7f0-44a2-aaa7-9bf014150cc9
name: LEGO
type: collection
description: >
  Officially released LEGO building sets, organized by theme and (where one
  exists) subtheme. Each theme is its own nested collection.
```

- **`id`** is the collection's stable identity. Nothing in this format
  references a collection by path — an item's parent is derived purely
  from directory position (see "Parent membership," below), and the only
  thing that addresses a collection at all is the `collections-mcp` tool
  surface, which does so exclusively by `id`.
- **A directory whose name is prefixed with `_`** (other than
  `_collection.yaml` itself) is not a collection — it's a components
  bucket (see [COMPONENT.md](COMPONENT.md)) and doesn't get a
  `_collection.yaml` of its own.

## Optional fields

- **`date`** — when the collection was *first* released, at whatever
  precision the source supports (`"1999"`, `"1999-06"`, or
  `"1999-06-30"`). For a grouping collection (a series, a product line),
  roll this up from its earliest already-sourced child rather than
  re-deriving it independently. Domain-family directories (the broad
  top-level groupings directly under `collections/`) don't get a `date`
  at all — they're organizational buckets, not things that were released.
- **`description`** — prose context: release history, scope, what the
  collection spans.
- **`image.source_url`** — the collection's own official logo/brand mark,
  from an authoritative source, only when one genuinely exists and
  belongs to the entity itself, not a franchise it's merely licensed
  from.
- **`tags`** — cross-cutting groupings a collection's directory position
  doesn't already express (see `collections/CLAUDE.md`, "Tags").
- Category-specific fields some categories add on top of this baseline
  (e.g. Pokémon TCG's `category: Trading Card Games` on every
  `_collection.yaml` in that category) — see the category's own
  `CLAUDE.md`.

## Parent membership

A collection's parent is whichever directory contains it — there is no
`collection:`/`parent_collection:` field, and the validator rejects one if
it finds it. Moving a directory (`git mv`) re-parents everything inside it;
nothing else needs to change.

## Shape: nested collections vs. items

A collection should usually contain either nested collections or items,
rarely both at the same level — a category's own directory is typically
all sub-collections (series, sets, product lines); a set's directory is
typically all items. This is a soft rule: a small, distinctly-scoped
exception is legitimate, but mixing should be the exception that needs a
reason, not the default shape.

A collection should rarely exceed 1000 items or 100 nested collections —
past that, look for a natural subdivision already present in the source
material (a series, era, or product-line boundary) rather than piling
everything into one directory.

## Ownership semantics

**Owning every item in a collection constitutes owning the collection.**
This is the defining trait that distinguishes a collection's items from a
component (see [COMPONENT.md](COMPONENT.md)): a component is part of an
item, not a member of a collection, and owning every component of an item
does *not* constitute owning that item.

## Inheritance

`CLAUDE.md` and `template.schema.json` are resolved by walking up from a
collection's own directory to the nearest ancestor that has one — a nested
set normally inherits both from its category rather than repeating them.

## Tooling

The `collections-mcp` tools address collections exclusively by `id`:
`choose_random_collection`, `get_collection_context`, `get_collection_details`
(includes `componentBuckets`, the names of any components buckets this
collection owns), `list_items`, `list_collections`, `upsert_collection`.
