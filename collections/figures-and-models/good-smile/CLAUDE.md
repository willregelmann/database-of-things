# Good Smile Company — curation hints

## What belongs here

Good Smile Company's character figure lines, organized one nested collection
per product line. Curated so far:

- [`nendoroid/`](nendoroid/CLAUDE.md) — poseable chibi-style figures, one
  continuous catalog number since 2006.
- [`figma/`](figma/CLAUDE.md) — highly articulated action figures (Max
  Factory, a Good Smile subsidiary listed under the Good Smile Company
  storefront), one continuous number since 2008.

figma is placed here rather than under its manufacturing subsidiary Max
Factory because Good Smile Company is the customer-facing brand that presents
and sells it — the same "cut at the customer-facing brand" rule the parent
[`../CLAUDE.md`](../CLAUDE.md) documents.

## Directory structure

```
good-smile/
  CLAUDE.md
  _collection.yaml               # Good Smile Company itself
  <line>/                         # e.g. "nendoroid", "figma"
    CLAUDE.md
    template.schema.json
    _collection.yaml
    ...                          # the line's own internal structure
```

Each line owns its numbering, attributes, and pitfalls — don't assume one
line's conventions carry to another. Nendoroid spin-off lines (Nendoroid
Doll, Nendoroid More, Nendoroid Petit) are their own lines and would be
siblings here (`good-smile/nendoroid-doll/`, ...), not nested inside
`nendoroid/` — see [`nendoroid/CLAUDE.md`](nendoroid/CLAUDE.md).
