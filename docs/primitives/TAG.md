# Tag

A **tag** is a cross-cutting label — a franchise/IP that spans multiple,
unrelated categories being the main case. It's the one primitive that
doesn't live under `collections/` at all: a tag applies *across* the
catalog, not to any one domain family or category, so it lives in a
sibling root, [`tags/`](../../tags/). See [COLLECTION.md](COLLECTION.md)
and [ITEM.md](ITEM.md) for the primitives it labels.

## Identity

One YAML file per tag, under `tags/<namespace>/` (e.g.
`tags/franchises/pokemon.yaml`). A tag carries the same baseline as any
entity — `id`, `name`, `type: tag` — and nothing else, by design: **one
standard schema for every namespace**, no per-namespace `attributes`.

```yaml
id: 175817b0-ba6b-49ca-90a9-f0777b4149e4
name: Pokémon
type: tag
```

- **`name` is the tag's proper display form** — `Pokémon`, not `pokemon`;
  `Assassin's Creed`, not `assassins-creed`. This is the only place that
  display form is recorded at all; the filename is just a slug for human
  browsability, never referenced by anything.
- Quote `name` in YAML whenever it contains a colon, apostrophe, or comma
  — `name: Magic: The Gathering` is a genuine parse error, not a style
  nit (a bare `: ` inside an unquoted scalar reads as a second mapping
  key).

## Namespaces

A namespace directory (`tags/franchises/`) is structurally the same kind
of node a domain family or category under `collections/` is — its own
`_collection.yaml`, inherited `CLAUDE.md`/`template.schema.json`. Only one
namespace exists so far (`franchises/`); a new one is added only when a
genuinely different kind of cross-cutting grouping shows up, not
speculatively.

## Referencing a tag

A collection or item points at its tags via a top-level `tags` field, an
array of `id`s — see [COLLECTION.md](COLLECTION.md) and [ITEM.md](ITEM.md).

```yaml
tags:
  - 175817b0-ba6b-49ca-90a9-f0777b4149e4
```

- **By `id`, always** — there is no freeform ad hoc string tagging.
  Reusing an existing tag is as cheap as it's always been (look up its
  `id`); adding a genuinely new one means creating its entity file first.
- **Duplicate ids in one `tags` list are an error** — unlike
  [`components`](COMPONENT.md), where a duplicate is meaningful (owning
  more than one of the same part), tagging the same thing twice never is.
- The validator enforces referential integrity on `tags` the same way it
  does on `components`, plus one additional check `components` doesn't
  have: every referenced id must resolve to an entity with `type: tag`
  specifically, not just any entity — catching a tag reference that
  accidentally points at a collection or item id.
- Don't over-tag: a tag only earns its place if it captures a grouping
  that's genuinely useful and isn't already expressed by directory
  position or a structured `attributes` field — see
  [`collections/CLAUDE.md`](../../collections/CLAUDE.md), "Tags," for the
  full curation guidance (when to tag, when not to, how many is too many).

## Tooling

Not yet exposed via `collections-mcp` — the tool surface currently
addresses `collections/` only. Curating a tag today means creating or
referencing its entity file directly.
