# Model Kits — curation hints

## What belongs here

Build-it-yourself kits assembled from molded parts into one specific,
non-reconfigurable model — Gunpla (Bandai's Gundam model kits), and
similarly-conventioned scale-model lines (Tamiya, Revell, Airfix, etc., not
yet curated). The defining trait is single-use assembly: parts are
cut/glued/snap-fit following one fixed instruction path into one model, not
a reusable general-purpose building system.

**Not construction toys — `lego/` is parked here temporarily.** LEGO is a
reusable, general-purpose brick system (the same piece goes into any set, or
a builder's own creation), which is a genuinely different kind of
collectible from a single-use scale kit. It's filed under this family for
now as a practical starting point rather than standing up a whole separate
domain family for one line — expect it to move to its own family (e.g.
`construction-toys/`) once a second brick/construction-system line shows up
to justify the split. Don't take `lego/`'s presence here as precedent for
"any assemble-it-yourself product belongs in `model-kits/`" — the family's
actual definition is single-use kits, and LEGO doesn't meet it.

## Directory structure

```
model-kits/
  CLAUDE.md
  template.schema.json          # generic fallback; each line overrides it
  _collection.yaml               # this domain family's own entity record
  <line>/
    CLAUDE.md                    # line-specific conventions — required
    template.schema.json         # line-specific attributes — required
    _collection.yaml
    ...                          # line's own internal structure
```

Each line (Gunpla, LEGO, ...) is a full top-level collection in its own
right — numbering schemes, manufacturers, and attributes differ by line.
Follow the shape of [`gunpla/CLAUDE.md`](gunpla/CLAUDE.md) or
[`lego/CLAUDE.md`](lego/CLAUDE.md) as worked examples, and see the root
[`collections/README.md`](../README.md) for how directory position
determines parentage.

## Adding a new line

1. Create `model-kits/<line>/`.
2. Write its `CLAUDE.md` — identification scheme, naming convention,
   completeness-checking approach, known pitfalls.
3. Write its `template.schema.json` — don't reuse another line's attributes
   as-is; verify against manufacturer listings or a fan database rather
   than guessing.
4. Write its `_collection.yaml` (`type: collection`, plus a `description`).
5. Run the validator before opening a PR.
