# Power Rangers — curation hints

## Directory structure

```
power-rangers/
  CLAUDE.md
  template.schema.json          # shared attributes across every PR toy line
  _collection.yaml               # the whole "Power Rangers" toy brand
  mighty-morphin/
    CLAUDE.md                    # this line's own numbering/pitfalls
    _collection.yaml
    figures/                     # + zords/, vehicles/, weapons/, playsets/
      _collection.yaml
      <number>-<slugified-name>.yaml
```

Each U.S. toy release era (Mighty Morphin, Zeo, Turbo, In Space, ... Hasbro's
Lightning Collection) is its own line, nested here the same way FireLink
nests `<game>/` under its brand — see
[`../firelink/CLAUDE.md`](../firelink/CLAUDE.md). `mighty-morphin/`,
`zeo/`, `turbo/`, and `in-space/` are curated so far.

## Full toy line, not figures-only

Unlike every other line in `collectible-figures/`, a Power Rangers toy line
is curated in full — figures alongside its companion Zords/Megazords,
vehicles, playsets, and weapons/role-play accessories — because the
manufacturer releases and numbers all of these together as one product
line; splitting them across categories would fragment a single collector's
checklist. This is a documented exception to the parent category's default
figures-only scope — see [`../CLAUDE.md`](../CLAUDE.md). Each item's coarse
`type` (`figure`, `zord`, `vehicle`, `weapon`, `playset`) determines which
subdirectory it lives in within its line.

## Manufacturer varies by era

Bandai America produced the U.S. toy lines from the original 1993 Mighty
Morphin series through the early 2000s; Hasbro has held the license since
2019 (Beast Morphers onward, including the Lightning Collection). Always
verify `attributes.manufacturer` for the era/line you're curating rather
than assuming Bandai.

## Identifying items

Each era used its own numbering scheme (e.g. Bandai's internal
catalog/assortment numbers for Mighty Morphin; Hasbro's Lightning
Collection uses its own separate numbering). See the specific line's own
`CLAUDE.md` for how that era's numbers work — don't assume they carry over
between eras.
