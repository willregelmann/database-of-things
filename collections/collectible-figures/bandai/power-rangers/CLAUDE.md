# Power Rangers — curation hints

## Directory structure

```
power-rangers/
  CLAUDE.md
  template.schema.json          # shared attributes across every PR toy line
  _collection.yaml               # Bandai's Power Rangers toy line
  mighty-morphin/
    CLAUDE.md                    # this line's own numbering/pitfalls
    _collection.yaml
    figures/                     # + zords/, _zords/, vehicles/, weapons/, playsets/
      _collection.yaml
      <number>-<slugified-name>.yaml
```

Each Bandai-era toy release (Mighty Morphin, Zeo, Turbo, In Space) is its own
line, nested here the same way FireLink nests `<game>/` under its brand — see
[`../../firelink/CLAUDE.md`](../../firelink/CLAUDE.md). `mighty-morphin/`,
`zeo/`, `turbo/`, and `in-space/` are curated so far.

**Only Bandai's eras belong here.** Hasbro has held the Power Rangers license
since 2019 (Beast Morphers, the Lightning Collection, ...); those are a
different manufacturer's product and live under a sibling
`hasbro/power-rangers/`, reunified with this line by a shared `power-rangers`
franchise tag rather than by directory position. This split — and why Power
Rangers is a franchise directory under a manufacturer at all — is documented
in the Bandai umbrella [`../CLAUDE.md`](../CLAUDE.md) and the category
[`../../CLAUDE.md`](../../CLAUDE.md).

## Full toy line, not figures-only

Unlike every other line in `collectible-figures/`, a Power Rangers toy line
is curated in full — figures alongside its companion Zords/Megazords,
vehicles, playsets, and weapons/role-play accessories — because the
manufacturer releases and numbers all of these together as one product
line; splitting them across categories would fragment a single collector's
checklist. This is a documented exception to the parent category's default
figures-only scope — see [`../../CLAUDE.md`](../../CLAUDE.md). Each item's coarse
`type` (`figure`, `zord`, `vehicle`, `weapon`, `playset`) determines which
subdirectory it lives in within its line.

## Zords as components

Some Megazords are physically molded from multiple individually-named Zords
packaged together in one box — Bandai/Hasbro never sold these individual
pieces separately, so cataloguing them as their own items in `zords/` would
misrepresent something a collector could complete on its own. These are
**components** (see [`../../../CLAUDE.md`](../../../CLAUDE.md), "Components") of
the combined product, catalogued in a `_zords/` bucket nested inside each
line, alongside that line's own `zords/`:

```
mighty-morphin/
  zords/                     # standalone/combining Zord products, each its own SKU
    2220-megazord.yaml
  _zords/                    # pieces bundled inside one of the above, never sold alone
    tyrannosaurus-dinozord.yaml
```

- **Per-line, not per-brand** — matching `zords/` itself already being
  scoped to one era rather than shared across the whole `power-rangers/`
  brand.
- **No catalog `number` unless the source documents one of its own.**
  Unlike LEGO minifigures (which always carry a BrickLink/Brickset number —
  see [`../../../model-kits/lego/CLAUDE.md`](../../../model-kits/lego/CLAUDE.md)),
  Bandai generally never assigned these bundled-only pieces a catalog
  number — leave `attributes.number` off rather than inventing one or
  reusing the parent Megazord's number. Record one only if a source
  genuinely documents a distinct number for the piece.
- **Naming files**: `<slugified-name>.yaml` — no number prefix, absent a
  real number to sort by.
- **Only add where actually verified.** Don't retrofit `components` onto
  every Megazord that might combine from parts — populate it where a
  curator has confirmed the specific pieces via a reliable source, and
  leave items without confirmed sub-zords alone. A single Zord that doesn't
  combine from separately-named pieces (Titanus, Dragonzord, Tor) has
  nothing to put here.
- A Megazord references its pieces via the top-level `components` field,
  same as any other component:
  ```yaml
  components:
    - <id of tyrannosaurus-dinozord>
    - <id of mastodon-dinozord>
  ```

## Manufacturer

Every line here is a Bandai America release — the U.S. toy lines from the
original 1993 Mighty Morphin series through the early 2000s. Hasbro's license
era (2019 onward) is deliberately not in this directory (see "Directory
structure" above). Still verify `attributes.manufacturer` against the actual
release rather than hardcoding it, since Bandai used more than one legal
entity/co-brand over the line's run.

## Identifying items

Each Bandai era used its own numbering scheme (e.g. Bandai's internal
catalog/assortment numbers for Mighty Morphin). See the specific line's own
`CLAUDE.md` for how that era's numbers work — don't assume they carry over
between eras.
