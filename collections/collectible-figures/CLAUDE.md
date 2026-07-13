# Collectible Figures — curation hints

## What belongs here

Standalone character figures — poseable chibi figures (Nendoroid), poseable
action figures (Figma), static scale figures, and similar product lines sold
as individually numbered or titled collectibles. Not one-off statues/props
with no product line behind them.

## Directory structure

```
collectible-figures/
  CLAUDE.md
  template.schema.json          # generic fallback; each product line overrides it
  _collection.yaml               # this domain family's own entity record
  <line>/
    CLAUDE.md                    # line-specific conventions — required
    template.schema.json         # line-specific attributes — required
    _collection.yaml
    ...                          # line's own internal structure
```

Each product line (Nendoroid, Figma, etc.) is a full top-level collection in
its own right — numbering schemes, manufacturers, and attributes differ by
line. Follow the shape of [`nendoroids/CLAUDE.md`](nendoroids/CLAUDE.md) as a
worked example, and see the root [`collections/README.md`](../README.md) for
how directory position determines parentage.

## Adding a new product line

1. Create `collectible-figures/<line>/`.
2. Write its `CLAUDE.md` — identification scheme, naming convention, known
   pitfalls (variant/re-release numbering is common in this domain — check
   for it explicitly rather than assuming a line is flatly numbered).
3. Write its `template.schema.json` — don't reuse another line's attributes
   as-is; verify against manufacturer listings or a fan database (e.g.
   MyFigureCollection) rather than guessing.
4. Write its `_collection.yaml` (`type: collection`, plus a `description`).
5. Run the validator before opening a PR.
