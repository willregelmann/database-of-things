# Item

An **item** is a leaf entity — the actual collectible: a card, a LEGO set,
a figure. It's the primitive a collection is made of; see
[COLLECTION.md](COLLECTION.md) for the container primitive and
[COMPONENT.md](COMPONENT.md) for a related but distinct primitive.

## Identity

One YAML file per item, directly inside the collection directory it
belongs to (never `_collection.yaml`, which is the collection's own
record). Every item carries the same baseline as any entity:

```yaml
id: 3f4334f3-6a41-45fb-a1c1-dcf44566491e
name: Charizard
type: card
```

- **`id`** — a UUID, generated once, never reused. It's the anchor
  everything else in this format references an item by (see
  "Components," below) — nothing references an item by path.
- **`type`** — whatever noun accurately names the thing (`card`, `set`,
  `plush`, `minifig`, ...), not a fixed enum. A category introduces
  whatever value fits its own collectibles.

## Optional fields

- **`date`** — the item's own release date, same format/precision rules
  as a collection's (see [COLLECTION.md](COLLECTION.md)).
- **`attributes`** — category-specific structured data, validated against
  the nearest `template.schema.json` (piece count, rarity, illustrator,
  ...). This is where domain-specific detail lives; everything else in an
  item's top-level shape is cross-cutting and format-wide.
- **`image.source_url`** — the item's own image, from an authoritative
  source (or a retailer/marketplace photo, as a documented fallback when
  no authoritative source exists).
- **`tags`** — ids referencing [tag](TAG.md) entities for cross-cutting
  groupings (see `collections/CLAUDE.md`, "Tags") — the main case is a
  franchise/IP spanning multiple, unrelated categories.
- **`components`** — ids of the entities this item is physically made up
  of (see [COMPONENT.md](COMPONENT.md)). Not every item has this — a
  category may track a components summary count instead (e.g. LEGO's
  `attributes.minifigCount`) until specific components are catalogued.

## Parent membership

An item's parent collection is whichever directory it's filed in — no
`collection:`/`parent_collection:` field. `git mv` between directories to
re-parent it; nothing else needs to change to reflect the move, including
any `components` reference elsewhere, since that's by `id` and survives
the move automatically for exactly this reason.

## Naming files

`<slugified-name>.yaml`, or `<canonical-number>-<slugified-name>.yaml`
(zero-padded to the collection's total digit width) when the collection has
a canonical numbering scheme. See the category's own `CLAUDE.md` for the
specifics — which field is canonical, how to slugify, disambiguation rules.

## Tooling

`get_item_details` (by `id` — works the same whether the item sits in a
plain collection directory or is itself a component in a bucket, see
[COMPONENT.md](COMPONENT.md)), `upsert_item`, `rename_item`.
