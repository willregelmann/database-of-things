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

1. Create `plush/<line>/`.
2. Write its `CLAUDE.md` — identification scheme, naming convention, known
   pitfalls (many plush lines mix a global catalog number with sub-lines that
   restart their own numbering — check for this explicitly rather than
   assuming a line is flatly numbered).
3. Write its `template.schema.json` — don't reuse another line's attributes
   as-is; verify against manufacturer listings or a well-maintained fan
   database rather than guessing.
4. Write its `_collection.yaml` (`type: collection`, plus a `description`).
5. Run the validator before opening a PR.
