# Collectible Figures — curation hints

## What belongs here

Standalone character figures — poseable chibi figures (Nendoroid), poseable
action figures (figma), static scale figures, and similar product lines sold
as individually numbered or titled collectibles. Not one-off statues/props
with no product line behind them.

**Exception: inseparable toy lines.** A small number of toy lines bundle
character figures together with companion vehicles, combining robots,
playsets, and role-play weapons/accessories under one numbered product line
and one packaging identity — splitting the figures out into this category
while routing vehicles/zords/playsets elsewhere would fragment a single
collector's checklist across unrelated parts of the tree. When a line's own
identity is inseparable from its full toy range (e.g. Power Rangers — see
[`bandai/power-rangers/CLAUDE.md`](bandai/power-rangers/CLAUDE.md)), curate
the whole numbered line rather than only the poseable figures. This is a
judgment call made per-line, not a general loosening of the figures-only rule
— document the reasoning in that line's own `CLAUDE.md`.

## How the tree is organized: manufacturer/brand first, franchise via tags

The directory tree under `collectible-figures/` encodes **one** axis: the
manufacturer/brand that makes the figure. Franchise/IP is **not** a directory
axis — it's carried by `tags/franchises/` entities (see
[`../CLAUDE.md`](../CLAUDE.md#tags)). Keeping the two separate is what makes
every directory level mean the same thing.

**A top-level directory here is the customer-facing brand under which the
line is sold** — the entity whose own storefront/site presents it, not
necessarily the deepest legal manufacturer. A brand's individual product
lines nest beneath it:

```
collectible-figures/
  good-smile/                    # customer-facing brand (Good Smile Company)
    nendoroid/                    # one of its lines
    figma/                        # another (Max Factory, sold under Good Smile)
  funko/
    pop/
  bandai/
    gashapon/
    power-rangers/                # a franchise sold under Bandai's own name
```

- **Cut at the customer-facing brand, not the deepest legal parent.** figma
  is made by Max Factory (a Good Smile subsidiary) but listed on the Good
  Smile Company storefront, so it's `good-smile/figma/`. Sister/subsidiary
  brands fold into the parent that presents them (Banpresto → `bandai/`).
- **A brand with only one line curated still gets its own directory** when
  it's a real manufacturer that plausibly sells others — the directory is a
  stable home for future siblings, not redundant nesting. Worked example:
  [`good-smile/nendoroid/CLAUDE.md`](good-smile/nendoroid/CLAUDE.md) under
  the [`good-smile/`](good-smile/CLAUDE.md) umbrella.

**Franchise may appear as a line-level directory under a manufacturer** — e.g.
`bandai/power-rangers/`, `re-ment/pokemon/` — where the franchise is
functioning as *that maker's* product line. It is never a **top-level** axis
of its own, and cross-cutting franchise discovery always comes from the tag,
never from a franchise directory sitting at the root.

### When a franchise spans manufacturers

Two shapes, decided by whether the franchise's toys carry their own unifying
product-line brand:

- **No unifying brand — sold under each maker's own name → split by
  manufacturer.** Power Rangers toys were made by Bandai (1993–early 2000s)
  and Hasbro (2019 on), each under its own name. They split into
  `bandai/power-rangers/` and `hasbro/power-rangers/`, reunified by a shared
  `power-rangers` franchise tag. While only one manufacturer's toys are
  curated, the tag isn't added yet — the directory already expresses the
  franchise; the tag earns its place once the second manufacturer's
  directory exists and the franchise genuinely spans both.
- **Its own unifying brand → stays top-level under that brand.**
  [`firelink/`](firelink/CLAUDE.md) is a licensed label whose products carry
  the "FireLink" brand even though different manufacturers produce different
  series — so it's a single top-level directory, no split. The brand name,
  not the maker, is the constant.

## Adding a new product line

1. Identify the customer-facing brand and place the line under it:
   `collectible-figures/<brand>/<line>/`. Create the `<brand>/` umbrella
   (`_collection.yaml` + `CLAUDE.md`) if it doesn't exist yet. A line that is
   its own top-level brand goes directly at `collectible-figures/<line>/`.
2. Write the line's `CLAUDE.md` — identification scheme, naming convention,
   known pitfalls (variant/re-release numbering is common in this domain —
   check for it explicitly rather than assuming a line is flatly numbered).
3. Write its `template.schema.json` — don't reuse another line's attributes
   as-is; verify against manufacturer listings or a fan database (e.g.
   MyFigureCollection) rather than guessing.
4. Write its `_collection.yaml` (`type: collection`, plus a `description`).
5. Run the validator before opening a PR.
