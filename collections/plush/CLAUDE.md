# Plush — curation hints

## What belongs here

Stuffed/plush toys sold as collectible product lines — branded plush with
their own identification scheme, naming, or series/squad identity
(Squishmallows, Beanie Babies, Jellycat, etc.). Not a one-off promotional
plush with no product line behind it.

**A plush line is curated whole — a sub-brand doesn't leave the family for
being made of something else.** Squishmallows' own Squish-A-Longs are 1"
squeezable *plastic* figures, not plush at all, and they still belong here:
they carry the Squishmallows name, use its characters, and are collected by
the same people tracking the plush line. Splitting them into
`figures-and-models/` on a materials test would mean a Squishmallows
collector has to know which family each sub-brand was sorted into, which is
precisely the knowledge a catalog should be saving them.

This mirrors the rule
[`../figures-and-models/CLAUDE.md`](../figures-and-models/CLAUDE.md) already
applies in the other direction — "a line is curated whole, don't slice one
line by object type," which is why a Power Rangers Zord or role-play morpher
stays with its figure line. **The unit is the product line, not the
material.**

Two limits keep this from swallowing the boundary:

- **It only extends a line already curated here.** A sub-brand of
  Squishmallows qualifies; an unrelated plastic toy line from the same
  manufacturer does not — Jazwares also makes plenty that has nothing to do
  with a plush line, and that isn't a `plush/` concern.
- **A line whose *whole* identity is non-plush belongs to whichever family
  fits it**, however squishy it is. This is about not fragmenting one line,
  not about claiming new ones.

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

1. Confirm the line belongs here at all before scaffolding it — but judge it
   by **which line it extends, not what it's made of** (see "What belongs
   here" above). A non-plush sub-brand of a line already curated here stays
   here; an unrelated line from the same manufacturer doesn't.
2. Create `plush/<line>/`. A sub-brand of an existing line is a **sibling**,
   not a nested directory — `plush/squishmallows-squish-a-longs/`, not
   `plush/squishmallows/squish-a-longs/` — since each keeps its own
   restarting numbering (see
   [`squishmallows/CLAUDE.md`](squishmallows/CLAUDE.md)).
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
