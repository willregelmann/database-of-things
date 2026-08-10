# Collection

A **collection** is a directory that groups other entities — nested
collections or items. Every domain family, category, series, and set
under `collections/` is a collection. This is the "container" primitive;
see [ITEM.md](ITEM.md) for the "member" primitive.

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
- **`name`** — display name of the collection.
- **`type`** — always `collection`, every `_collection.yaml`'s entity-kind
  marker.

This shape — every field below included — is enforced by
[`schemas/collection.schema.json`](../../schemas/collection.schema.json);
everything else in this file is the prose walkthrough of what that schema
allows and why.

## Optional fields

- **`date`** — when the collection was *first* released, at whatever
  precision the source supports (`"1999"`, `"1999-06"`, or
  `"1999-06-30"`). For a grouping collection (a series, a product line),
  roll this up from its earliest already-sourced child rather than
  re-deriving it independently. Domain-family directories (the broad
  top-level groupings directly under `collections/`) don't get a `date`
  at all — they're organizational buckets, not things that were released.
- **`ongoing`** — whether new items are still being produced for the
  collection. Most collections are closed (a finished set, a discontinued
  line) and omit or set this `false`; a currently-releasing series (e.g.
  Pokémon TCG as a whole, or its still-expanding Mega Evolution series)
  sets it `true`.
- **`description`** — prose context: release history, scope, what the
  collection spans.
- **`image`** — URL of the collection's own official logo/brand mark,
  from an authoritative source, only when one genuinely exists and
  belongs to the entity itself, not a franchise it's merely licensed
  from.
- **`tags`** — ids referencing [tag](TAG.md) entities for cross-cutting
  groupings a collection's directory position doesn't already express
  (see `collections/CLAUDE.md`, "Tags").
- **`attributes`** — category-specific structured data about the
  collection record itself, validated against the nearest
  `../../collection-attributes.schema.json` (own or inherited) — e.g. a
  trading-card set's `total_cards` (see
  [`collections/trading-cards/collection-attributes.schema.json`](../../collections/trading-cards/collection-attributes.schema.json)).
  This is where a category-specific field belongs now, not loose at the
  top level. It still has to carry information the hierarchy doesn't:
  Pokémon TCG once stamped `category: Trading Card Games` onto every
  `_collection.yaml` in the category, which said nothing directory
  position didn't already, and it has since been removed rather than
  moved into `attributes`.

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

## Inheritance

`CLAUDE.md` and `../../item-attributes.schema.json` are resolved by walking
up from a collection's own directory to the nearest ancestor that has one —
a nested set normally inherits both from its category rather than repeating
them. `../../collection-attributes.schema.json` (governing this collection's
own `attributes`, see above) resolves the same way, but independently — a
directory can inherit one without the other, since an item's attribute
shape and a collection record's attribute shape are unrelated data.

**`tags` inherits differently — by accumulation, not nearest-ancestor.**
CLAUDE.md/schema resolution stops at the first ancestor that has one; a
collection's `tags`, by contrast, implicitly apply to every nested
collection and item below it, all the way down, regardless of how many
levels deep. See [`collections/CLAUDE.md`](../../collections/CLAUDE.md#tags)
for the tag-vs-`attributes` heuristic this difference drives.
