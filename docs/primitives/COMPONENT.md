# Component

A **component** is an entity that's physically part of an item, but is not
itself a member of a collection someone completes. It's structurally
identical to an [item](ITEM.md) — same YAML shape — but referenced and
filed differently. See [COLLECTION.md](COLLECTION.md) for the ownership
semantics a component deliberately does *not* share.

## Ownership semantics

**Owning every component of an item doesn't constitute owning the item** —
unlike owning every item in a collection, which does constitute owning the
collection (see [COLLECTION.md](COLLECTION.md)). A LEGO set's
minifigures are components: someone who acquired all of a set's
minifigures loose hasn't acquired the set. This is the entire reason a
component is a distinct primitive rather than just another item.

## Identity

A component is catalogued exactly like any other entity — its own YAML
file, `id`/`name`/`type`, the same optional fields (`date`, `attributes`,
`image.source_url`, `tags`) as an item. Nothing about a component's own
file marks it as a component; what makes it one is that some item's
top-level `components` field points at it.

## Where it lives: the components bucket

A component is filed in a **components bucket** — a directory whose name
is prefixed with `_` (e.g. `lego/<theme>/_minifigs/`), nested *inside* the
collection it belongs to rather than in a sibling top-level tree. This
keeps exactly one directory anywhere asserting "this is the Star Wars
theme" — a sibling tree would need its own `star-wars/` folder kept in
sync with the sets side, with nothing enforcing that they match.

- **A components bucket doesn't get its own `_collection.yaml`.** The
  leading underscore already marks it as "structural, not a normal peer"
  — extending the same convention `_collection.yaml` itself established.
  The validator doesn't require one; nothing ever references the bucket
  directory itself, since components are referenced individually, by
  their own `id`.
- It still needs a `CLAUDE.md`/`template.schema.json` (own or inherited)
  like any directory holding entity files — a category whose components
  have genuinely different attributes from its items (a minifig's
  BrickLink number vs. a set's own numbering) writes its own
  `template.schema.json` for the bucket rather than reusing the parent's.
- Bootstrapping a brand-new bucket (and its schema, if distinct from its
  parent's) is a human/PR-level change — the `collections-mcp` tool
  surface only populates an already-scaffolded bucket, the same way
  `upsert_collection` refuses to author new curation conventions for a
  brand-new category.

## Referencing a component

An item points at its components via a top-level `components` field, an
array of `id`s:

```yaml
components:
  - a42e702b-e52b-4247-8ed6-103ed31a340b
  - 53708aaf-cb2a-41c7-b03a-bc95d651f563
```

- **By `id`, never by path** — a component's file can move (re-filed
  under a different theme, a bucket reorganized) without breaking
  anything that points at it.
- **Duplicate `id`s are allowed** — unlike `tags`, where a duplicate is an
  error. Repeating an `id` represents owning more than one of that
  component (e.g. a set that includes two identical minifigs).
- The validator enforces referential integrity — every `components` entry
  must resolve to a real `id` somewhere in the catalog — but doesn't
  require the component to already exist before the referencing item does,
  within the same PR.
- Don't retrofit `components` onto every item that happens to include
  extra parts — add it where a curator has actually catalogued the
  specific components, and leave a category's existing summary-count
  attribute (e.g. LEGO's `attributes.minifigCount`) in place for items
  whose specific components aren't catalogued yet. Partial coverage beats
  none.

## Reused components

The same component can recur across many items over time (e.g. a LEGO
minifig reprinted across dozens of sets). File it once, under whichever
collection it first appeared in; every other item that includes it just
references the same `id` — regardless of which collection's bucket it
physically lives in.

## Tooling

`list_components(collection_id, bucket)` and
`upsert_component(collection_id, bucket, component)` — addressed via the
owning collection's existing `id` plus a bucket name, not a separate id
scheme for the bucket itself. `get_item_details` works on a component's
`id` exactly as it does for a plain item. `get_collection_details`'s
`componentBuckets` field lists the bucket names a collection owns, for
discovery without guessing.

## Worked example

LEGO Star Wars: `lego/star-wars/_minifigs/sw0028-astromech-droid-r2-d2.yaml`
is a component (a minifig), referenced from
`lego/star-wars/episode-iv/7140-x-wing-fighter.yaml`'s `components` field.
See
[`collections/model-kits/lego/CLAUDE.md`](../../collections/model-kits/lego/CLAUDE.md)
for the full LEGO-specific convention.
