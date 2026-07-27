---
name: json-schema
description: Author, change, or debug the per-collection schema.json files that validate item attributes. Covers JSON Schema draft-07 as this repo actually runs it (Ajv 8, strict off, attributes-only, merge inheritance) plus the traps that make a constraint silently do nothing. Use when adding a template for a new collection, tightening or loosening an existing one, or diagnosing a schema error from the validator. For the separate envelope-shape schemas (id/name/date/image/tags — not attributes), see /schemas/{item,collection,tag}.schema.json instead; this skill doesn't cover those.
---

# JSON Schema in this repo

Every `../../../schema.json` is a [JSON Schema draft-07](https://json-schema.org/specification-links#draft-7)
document, compiled by [Ajv 8](https://ajv.js.org/) in
[`tools/collections-validate/validate.mjs`](../../../tools/collections-validate/validate.mjs)
and run in CI on every PR touching `collections/**`.

`collections/README.md` and `docs/primitives/COLLECTION.md` cover *where*
templates live and how they're resolved. This skill covers what they can
express, how this particular runtime behaves, and how to change one without
breaking the hundreds of files it governs.

## The five facts that aren't obvious

**1. A template validates `attributes` and nothing else.** The validator
calls `schema(data.attributes)` — the top-level `id`/`name`/`type`/`date`/
`tags`/`components` fields are validated separately, by the envelope schemas
under `/schemas/` (`item.schema.json`, `collection.schema.json`,
`tag.schema.json`) plus a little hand-written JS, not by a category's own
`schema.json`. Declaring `name` or `date` in a category template does
nothing useful; it constrains `attributes.name`, a different field.
Conversely, a file with no `attributes:` key at all skips this validation
entirely — including `_collection.yaml`, which never has `attributes` and so
never goes through this mechanism (it's checked against
`schemas/collection.schema.json` instead, a different, non-attributes
schema).

**2. Nearest-ancestor resolution is merge, not replace.** `validate.mjs`
walks down the tree carrying the merged schema *object* (not just a compiled
function), and layers a directory's own `schema.json` on top whenever one
exists — `properties` merge shallowly (a child's definition for a shared key
wins), `required` unions (a child can add a requirement, never drop an
inherited one), and `additionalProperties` takes the nearest declared value,
evaluated against the already-merged `properties`. This is what lets a
family-level template *recommend* an attribute (declare it, don't require
it) and have that recommendation reach items in every nested collection —
e.g. `comics-and-manga/schema.json` recommends `writer`/`artist`, and a
series several levels down with its own `additionalProperties: false`
template still accepts them, because by the time that check runs they're
already part of its merged `properties`. `collections-mcp`'s
`get_collection_context` mirrors this: it returns the whole `schemaChain`
(root to nearest), the same way it already did for `claudeChain`, not just
the nearest file.

**3. `format` works, but is rarely used here.** `ajv-formats` is installed
and applied to the same Ajv instance every category template compiles
against, so `"format": "uuid"` and `"format": "uri"` are genuinely
enforced if you use them — but house style (below) reaches for `pattern`
instead for anything attribute-shaped, so you won't see `format` in most
templates. (Don't be fooled by `figures-and-models/pop-mart/schema.json`:
its `format` is an *attribute named* `format`, with an enum of its own — a
property name, not the keyword.)

**4. `strict: false` means a mistyped keyword is silently ignored.**
`"requires"` instead of `"required"`, `"additionalProperty"` instead of
`"additionalProperties"` — Ajv accepts the schema and the constraint just never
fires. Nothing warns you; the file count in CI just doesn't change. A mistyped
*value* does fail loudly (`"type": "strng"` and `"required": "number"` both
throw at compile), so the risk is concentrated in keyword names. **Always
confirm a new constraint by making a file violate it on purpose and watching
the validator fail.**

**5. `pattern` is an unanchored partial match.** `"pattern": "[0-9]+"` accepts
`"abc123"`. Every numbering pattern in this repo anchors with `^…$`; keep doing
that.

Two more worth knowing:

- A malformed template **crashes the validator** instead of producing a
  validation error — `JSON.parse` and `ajv.compile` are uncaught, so you get a
  stack trace naming nothing useful. If `npm run validate` blows up rather than
  listing errors, suspect the template you just edited.
- There's no attributes-level root fallback anymore — a directory with no
  `schema.json` anywhere in its ancestry simply has nothing to merge, which
  is fine as long as nothing under it ever sets `attributes` (true of e.g. a
  domain-family directory that holds only nested collections, or a
  `tags/` namespace, whose entities never have `attributes` at all). The
  validator only complains if a real file sets `attributes` with no
  governing schema anywhere above it — that's the actual invariant, not
  "every directory needs one."

## Tooling

`scripts/schema-scope.mjs` answers the three questions worth answering before
editing. Runs from anywhere in the repo (it needs
`tools/collections-validate/node_modules` — `npm install` there once):

```bash
node .claude/skills/json-schema/scripts/schema-scope.mjs which <path>
# → which template + CLAUDE.md govern this file/dir, own or inherited, and
#   prints the template

node .claude/skills/json-schema/scripts/schema-scope.mjs scope <path>
# → every entity file that template governs, by directory, with counts —
#   the blast radius of any change

node .claude/skills/json-schema/scripts/schema-scope.mjs keys <path> [--max=N]
# → every `attributes` key across the governed items: how many files carry it
#   (100% = a `required` candidate), its types, and its value distribution
#   (small distinct-value count = an `enum` candidate)
```

`<path>` may be a directory, an item `.yaml`, or a `../../../schema.json`.

## Changing an existing template

1. **`scope`** it. A template change is retroactive — every governed file is
   re-validated. `funko/pop` governs 715 item files; `pokemon-tcg` governs
   20,121.
2. **`keys`** it. Write the constraint against the data that exists, not
   against what you expect. An `enum` derived from a value distribution is
   correct by construction; one derived from memory strands the long tail.
3. Edit. Keep the house style below.
4. `cd tools/collections-validate && npm run validate`. Read the full error
   list, not the first line — `allErrors: true` reports every failure.
5. If you *tightened* anything, verify the new rule actually fires (fact 4):
   temporarily break one governed file, confirm the validator names it, revert.

When a tightening turns up genuine violations, fix the data if it's wrong —
but if the data is right and the schema was too narrow, widen the schema. An
`enum` that doesn't cover a real rarity/variant is a schema bug, not a data
bug.

## Writing a template for a new collection

Only at phase 2 — when the line is about to receive its first item, not when
it's scaffolded (see `collections/CLAUDE.md`, "Adding a new …"). Until then it
inherits, which is what the validator wants.

House style, matching every existing template:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "<Line name> attributes",
  "type": "object",
  "properties": {
    "number": { "type": "string", "pattern": "^[0-9]{1,5}$" },
    "variant": { "type": "string", "enum": ["Common", "Chase"] }
  },
  "required": ["number"],
  "additionalProperties": false
}
```

- `$schema` draft-07, `title` naming the line, `type: "object"` — all 35
  existing templates do this, no exceptions.
- **`additionalProperties: false` for a real line's template.** It's what turns
  a typo'd key into a CI failure instead of an invisible orphan field, and the
  validator has a custom message for it that names the offending key. The
  permissive `additionalProperties: true` stubs are family-level fallbacks only.
- Collector and catalog numbers stay **strings**, not integers — `"004"`,
  `"4/102"`, `"TG12"` all need to round-trip verbatim, and the file slug is
  derived from them. Genuine quantities are a different case and are correctly
  integers (`sitting-cuties` types `series` as `{"type": "integer",
  "minimum": 1}`).
- `required` only for what genuinely exists on every item (`keys` tells you).
  Optional-but-declared is the normal case.
- Never declare `id`/`name`/`type`/`date`/`tags` — those are top-level fields,
  not attributes (fact 1).

Templates here use a deliberately small slice of the vocabulary: `type`,
`properties`, `required`, `enum`, `pattern`, `additionalProperties`, one
`minimum`. No `$ref`, `allOf`/`anyOf`/`oneOf`, `definitions`, or conditionals
appear anywhere in the tree. That's a fine default — reach for more only when
an attribute genuinely needs it, and see [`reference.md`](reference.md) for
what draft-07 offers and which parts are load-bearing under this runtime.

## Debugging a validator error

- `attributes has undeclared key "X"` — `additionalProperties: false` fired.
  Either the key is a typo (fix the file) or it's legitimate (declare it in the
  governing template — run `which` to find which one that is, it's often an
  ancestor, not the file's own directory).
- `attributes is missing required key "X"` — the file lacks a `required` key.
- `attributes/foo must be equal to one of the allowed values` — an `enum`
  miss. Check whether the value is wrong or the enum is incomplete.
- `attributes/foo must match pattern "…"` — confirm the pattern is anchored
  and that the value is quoted in YAML (an unquoted `4/102` still parses as a
  string, but unquoted numerics like `004` do not — they become integers and
  fail `type: "string"`).
- Stack trace instead of an error list — malformed template JSON.

## Reference

- [`reference.md`](reference.md) — draft-07 keywords, what each is worth here
- [json-schema.org](https://json-schema.org/) — the specification
- [Draft-07 release notes](https://json-schema.org/draft-07/json-schema-release-notes)
- [Ajv options](https://ajv.js.org/options.html) — the `strict` behavior above
