# Plush — curation hints

## What belongs here

Stuffed/plush toys sold as collectible product lines — branded plush with
their own identification scheme, naming, or series/squad identity
(Squishmallows, Beanie Babies, Jellycat, etc.). Not a one-off promotional
plush with no product line behind it.

## Directory structure

```
plush/
  CLAUDE.md
  template.schema.json          # generic fallback; each product line overrides it
  _collection.yaml               # this domain family's own entity record
  <line>/
    CLAUDE.md                    # line-specific conventions — required
    template.schema.json         # line-specific attributes — required
    _collection.yaml
    ...                          # line's own internal structure
```

Each product line (Squishmallows, etc.) is a full top-level collection in its
own right — identification schemes, manufacturers, and attributes differ by
line. Follow the shape of
[`squishmallows/CLAUDE.md`](squishmallows/CLAUDE.md) as a worked example, and
see the root [`collections/README.md`](../README.md) for how directory
position determines parentage.

## Adding a new product line

A line arrives in **two phases — scaffold it first, author its conventions
when it actually has items.** See
[`../CLAUDE.md`](../CLAUDE.md#scaffolding-a-new-collection) for the rule and
why it works this way; the phases below are this family's version of it.

**Phase 1 — scaffold.** No new conventions needed; anyone (or any automated
curation pass) can do this.

1. Confirm the line belongs here at all before scaffolding it. Plush
   manufacturers also sell small **plastic** collectibles under
   plush-adjacent branding — those aren't a `plush/` concern even when the
   name matches a plush line. Check the product's actual construction, not
   its branding.
2. Create `plush/<line>/`.
3. Write its `_collection.yaml` (`type: collection`, plus a `description`).
   The line inherits this family's `CLAUDE.md` and `template.schema.json` for
   now.
4. Run the validator before opening a PR.

**Phase 2 — author its conventions.** Required before the first item is filed
under the line.

5. Write its `CLAUDE.md` — identification scheme, naming convention, known
   pitfalls (many plush lines mix a global catalog number with sub-lines that
   restart their own numbering — check for this explicitly rather than
   assuming a line is flatly numbered).
6. Write its `template.schema.json` — don't reuse another line's attributes
   as-is; verify against manufacturer listings or a well-maintained fan
   database rather than guessing.
7. Run the validator before opening a PR.
