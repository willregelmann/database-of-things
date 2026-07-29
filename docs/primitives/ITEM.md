# Item

An **item** is a leaf entity — the actual collectible: a card, a LEGO set,
a figure. It's the primitive a collection is made of; see
[COLLECTION.md](COLLECTION.md) for the container primitive.

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
  everything else in this format references an item by — nothing references an
  item by path.
- **`name`** — display name of the item.
- **`type`** — whatever noun accurately names the thing (`card`, `set`,
  `plush`, `minifig`, ...), not a fixed enum. A category introduces
  whatever value fits its own collectibles.

This shape — every field below included — is enforced by
[`schemas/item.schema.json`](../../schemas/item.schema.json); everything
else in this file is the prose walkthrough of what that schema allows and
why.

## Optional fields

- **`date`** — the item's own release date, same format/precision rules
  as a collection's (see [COLLECTION.md](COLLECTION.md)).
- **`description`** — prose context. Original synthesis only, never
  pasted or lightly reworded source text.
- **`attributes`** — category-specific structured data, validated against
  the nearest `../../item-attributes.schema.json` (piece count, rarity, illustrator,
  ...). This is where domain-specific detail lives; everything else in an
  item's top-level shape is cross-cutting and format-wide.
- **`image`** — URL of the item's own image, from an authoritative
  source (or a retailer/marketplace photo, as a documented fallback when
  no authoritative source exists).
- **`tags`** — ids referencing [tag](TAG.md) entities for cross-cutting
  groupings (see `collections/CLAUDE.md`, "Tags") — the main case is a
  franchise/IP spanning multiple, unrelated categories.
- **`variants`** — physically distinct variants of this item, each its
  own sub-entity (see "Variants," below).

## Variants

Some items exist in physically distinct forms that are otherwise the
same collectible — a print or colorway difference rather than a
different card, figure, or set. `variants` holds these as an array of
sub-entities, each with its own required `id` and `name`:

```yaml
id: 181bd056-a11c-43a6-998b-254c2a5d7cb3
name: Charizard
type: card
date: "1999-01-09"
attributes:
  number: "4/102"
  rarity: Rare Holo
  illustrator: Mitsuhiro Arita
image: https://images.pokemontcg.io/base1/4_hires.png
variants:
  - id: 6341e5c7-c4dc-4907-8bed-8a866482f213
    name: 1st Edition
  - id: 25958570-46a9-4b8b-80c3-4b18f5b9e785
    name: Shadowless
  - id: 4d4afd61-a2c1-42c5-a3ad-09534ce8c5ec
    name: Unlimited
```

- Every other field (`date`, `attributes`, `image`, `tags`, ...) is
  optional on a variant and may be treated as inherited from the parent
  item when omitted — only add a field when the variant's own value
  actually differs.
- A variant cannot itself have variants — nesting is capped at one
  level.
- Use `variants` for a physical print/colorway difference, not for
  unrelated collectibles that happen to share a name; those are
  separate items. See `collections/CLAUDE.md` for where that line falls.

## Parent membership

An item's parent collection is whichever directory it's filed in — no
`collection:`/`parent_collection:` field. `git mv` between directories to
re-parent it; nothing else needs to change to reflect the move, since
that's by `id` and survives the move automatically for exactly this reason.

## Naming files

`<slugified-name>.yaml`, or `<canonical-number>-<slugified-name>.yaml`
(zero-padded to the collection's total digit width) when the collection has
a canonical numbering scheme. See the category's own `CLAUDE.md` for the
specifics — which field is canonical, how to slugify, disambiguation rules.