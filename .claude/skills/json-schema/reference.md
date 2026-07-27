# draft-07 keyword reference, as this repo runs it

Runtime: [Ajv 8](https://ajv.js.org/) with `{ allErrors: true, strict: false }`
and `ajv-formats` installed, meta-schema
[`http://json-schema.org/draft-07/schema#`](https://json-schema.org/draft-07/schema).
Spec: [json-schema.org](https://json-schema.org/) ·
[draft-07 validation vocabulary](https://json-schema.org/draft-07/draft-handrews-json-schema-validation-01).

Schemas here always validate one object: an item's `attributes` map, parsed
from YAML by `js-yaml`. The "in this repo" column reflects both the runtime and
the fact that the instance is always that map.

## Core

| Keyword | Effect | In this repo |
| --- | --- | --- |
| `$schema` | Declares the dialect | Always `http://json-schema.org/draft-07/schema#`. All 35 templates. |
| `title` | Annotation only, never validates | Always `"<Line name> attributes"`. |
| `description` | Annotation only | Fine on individual properties; nothing reads it programmatically. |
| `type` | `"string"`, `"number"`, `"integer"`, `"boolean"`, `"object"`, `"array"`, `"null"`, or an array of those | Always `"object"` at the top. A bad value **throws at compile** — the validator crashes rather than reporting an error. |
| `properties` | Per-key subschemas; a key absent from the instance is simply not checked | The main body of every template. Merges across the ancestor chain (see the json-schema skill's fact 2, "merge not replace") — a family-level `properties` key still applies several directories down unless a more specific template redefines it. |
| `required` | Array of key names that must be present | Only for keys that genuinely appear on 100% of items — check with `schema-scope.mjs keys`. Must be an array; a bare string throws. Unions across the ancestor chain — a child can add a requirement, never drop an inherited one. |
| `additionalProperties` | `false` rejects undeclared keys; `true` (the default) allows them | `false` on every real line template — this is what catches typo'd keys. The nearest ancestor's own declared value wins (own value present → own value; not declared at all → inherit the parent's), evaluated against the *merged* `properties`, so a child needn't redeclare `false` itself once an ancestor already has it. `true` only on stubs meant to stay genuinely open. The validator prints a custom message naming the offending key. |

## Values

| Keyword | Effect | In this repo |
| --- | --- | --- |
| `enum` | Instance must equal one of the listed values | The workhorse for closed vocabularies: rarity, variant, format, condition. Derive it from `schema-scope.mjs keys`, never from memory — an incomplete enum blocks legitimate data. |
| `const` | Single allowed value | Unused. Equivalent to a one-element `enum`; either is fine. |
| `pattern` | ECMA-262 regex, **unanchored partial match** | Used for collector-number shapes. **Always anchor with `^…$`** — `"[0-9]+"` accepts `"abc123"`. JSON-escape backslashes (`"\\d"`), and prefer explicit classes over `\d`/`\w` for readability, as existing templates do. |
| `format` | Named semantic formats (`uuid`, `uri`, `date`…) | Actually enforced — `ajv-formats` is installed. Rarely used here anyway; house style reaches for `pattern` for attribute-shaped constraints instead. |
| `minLength` / `maxLength` | String length bounds | Unused; legitimate when a code has fixed width, though an anchored `pattern` usually says it better. |
| `minimum` / `maximum` / `exclusiveMinimum` / `exclusiveMaximum` / `multipleOf` | Numeric bounds | One use: `sitting-cuties` types `series` as `{"type": "integer", "minimum": 1}`. |

## Arrays and nesting

| Keyword | Effect | In this repo |
| --- | --- | --- |
| `items` | Subschema for array elements (draft-07: a single schema, or an array for tuple positions) | Unused in `collections/`; correct for any list-valued attribute. |
| `minItems` / `maxItems` / `uniqueItems` | Array size and duplicate constraints | Unused; `uniqueItems: true` is worth pairing with any list attribute. |
| `properties` nested inside a property | Object-valued attributes | Unused — attributes are flat here. If you nest, set `additionalProperties: false` on the inner object too; the outer one doesn't reach inside. |

## Composition and conditionals

All unused across the tree. Valid draft-07 and supported by Ajv, but weigh the
readability cost first — these templates are read by curators and agents far
more often than they're executed.

| Keyword | Effect | Note |
| --- | --- | --- |
| `allOf` | All subschemas must pass | Still unused *as a keyword* in these templates — cross-template inheritance is real here (see fact 2), but it's done by merging the parsed schema *objects* in JS before compiling, not via `allOf`. That sidesteps the classic draft-07 footgun this keyword has: `allOf` **does not merge `additionalProperties`** — a branch declaring a property doesn't make it "declared" for a sibling branch's `additionalProperties: false`. Worth knowing if you're ever tempted to reach for `allOf` directly in a template. |
| `anyOf` / `oneOf` | At least one / exactly one must pass | Errors get noisy: `allErrors` reports failures from every branch, so one bad file produces a wall of output. |
| `not` | Subschema must fail | — |
| `if` / `then` / `else` | Conditional application (draft-07 addition) | The clean way to express "if `variant` is Chase then `exclusive_to` is required". |
| `dependencies` | Key presence implies other keys or a subschema | Simpler than `if`/`then` for "X requires Y". |
| `$ref` / `definitions` | Reuse within or across documents | **Don't `$ref` another file.** Each template is compiled standalone against its own path with no `loadSchema`; a cross-file `$ref` won't resolve and will crash the validator. Internal `#/definitions/...` refs are safe. |

## YAML → JSON type mapping

The instance comes from `js-yaml`, so YAML's scalar rules decide the type the
schema sees:

| YAML in the file | Type the schema sees | Consequence |
| --- | --- | --- |
| `number: "004"` | string `"004"` | Correct for collector numbers. |
| `number: 004` | number `4` | Fails `type: "string"`, and the leading zeros are gone. |
| `number: 4/102` | string `"4/102"` | Unquoted is safe here, but quote it anyway for consistency. |
| `series: 3` | number `3` | Passes `type: "integer"`. |
| `foo: yes` / `no` | boolean | YAML 1.1 booleans — quote them if you mean the words. |
| `foo:` (empty) | `null` | Fails any `type` except `"null"`; omit the key instead. |

Top-level `date` has its own rule enforced in JavaScript, not by any schema: it
must be a **quoted** string in `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` form. See
`collections/CLAUDE.md`, "Dates".

## What the schema never sees

`id`, `name`, `type`, `date`, `tags`, `components`, `image` — all top-level
entity fields, validated by hand in
[`tools/collections-validate/validate.mjs`](../../../tools/collections-validate/validate.mjs)
(UUID format and uniqueness, tag referential integrity, ancestor-tag
duplication, component resolution). Adding a rule for any of them belongs in
that file, not in a template.
