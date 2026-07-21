# Figures — curation hints

## What belongs here

Character figure **lines**, curated whole. Figures are the anchor — action
figures, chibi (Nendoroid), scale, vinyl (Funko Pop), blind-box designer
(Pop Mart), diorama (Re-Ment) — but if an item shipped as part of the line,
it's in whatever kind of object it is: the figures plus their companion
**vehicles**, **playsets and locations**, and **role-play pieces** (weapons,
morphers, and the like). Membership is about being part of the line, not about
what category of object the item is — **don't slice a single line by object
type.**

This deliberately pulls in companion pieces that on their own would look like
another family's concern. A vehicle, or a **scale-model-style build**, released
as part of a figure line belongs here with its line — don't route it to
[`../model-kits/`](../model-kits/CLAUDE.md) just because it's a vehicle or a
kit-like object. The product line is the unit, not the object.

What's out isn't an object category; it's things that aren't the figure line:

- **Separate non-figure merchandise** — apparel, stationery, homeware, food
  and other consumables. A franchise's t-shirts or erasers are a different
  product line, not its figure line (see [`re-ment/CLAUDE.md`](re-ment/CLAUDE.md)
  and [`funism/CLAUDE.md`](funism/CLAUDE.md) for the same carve-out).
- **Standalone plush lines** — their own top-level family,
  [`plush/`](../plush/CLAUDE.md).
- **One-off items with no product line behind them** — a single promotional
  statue or prop that isn't part of a released line.

`figures/` is a sibling of the other collecting-domain families (`plush/`,
`model-kits/`, `trading-card-games/`, ...). The boundary with them is which
product line an item belongs to, not what the item physically is.

## How the tree is organized: manufacturer/brand first, franchise via tags

The directory tree under `figures/` encodes **one** axis: the
manufacturer/brand that makes the item. Franchise/IP is **not** a directory
axis — it's carried by `tags/franchises/` entities (see
[`../CLAUDE.md`](../CLAUDE.md#tags)). Keeping the two separate is what makes
every directory level mean the same thing.

**A top-level directory here is the customer-facing brand under which the
line is sold** — the entity whose own storefront/site presents it, not
necessarily the deepest legal manufacturer. A brand's individual product
lines nest beneath it:

```
figures/
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
   `figures/<brand>/<line>/`. Create the `<brand>/` umbrella (`_collection.yaml`
   + `CLAUDE.md`) if it doesn't exist yet. A line that is its own top-level
   brand goes directly at `figures/<line>/`.
2. Write the line's `CLAUDE.md` — identification scheme, naming convention,
   known pitfalls (variant/re-release numbering is common in this domain —
   check for it explicitly rather than assuming a line is flatly numbered).
3. Write its `template.schema.json` — don't reuse another line's attributes
   as-is; verify against manufacturer listings or a fan database (e.g.
   MyFigureCollection) rather than guessing.
4. Write its `_collection.yaml` (`type: collection`, plus a `description`).
5. Run the validator before opening a PR.
