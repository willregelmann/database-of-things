# Bluey Poseable Figures — curation hints

## Format

Fully articulated (moving arms and torso) figures, roughly 2.5-3" tall —
larger and more detailed than the hard-plastic Mini Figures (see
[`../mini-figures/CLAUDE.md`](../mini-figures/CLAUDE.md)). Sold in two kinds
of pack, both using the same figure scale:

- **Multi-packs** — several named figures together, e.g. the "Bluey &
  Family Figure 4-Pack" (Bluey, Bingo, Bandit, Chilli) or themed 2-Packs
  ("Pool Time", "Grannies").
- **Story Starter packs** — a single figure plus one episode-themed
  accessory (e.g. "Bandit & Unicorse", "Muffin & Crown") and a mini postcard
  from the show.

Record which via `attributes.pack_type`.

## Directory shape

A multi-pack's box is the collectible unit — it's an **item** (`type:
pack`), not a collection, even though several figures ship inside it:
owning every figure from a pack loose doesn't mean owning the pack. Each
figure inside is a **component** (see root
[`collections/CLAUDE.md`](../../../../CLAUDE.md), "Components"), filed in the
`_figures/` bucket sitting alongside the pack items, and referenced from the
pack's own `components` field:

```
poseable-figures/
  CLAUDE.md
  template.schema.json
  _collection.yaml
  _figures/                       # components bucket — no _collection.yaml
    template.schema.json           # figure-specific attributes (accessory)
    family-4-pack-bluey.yaml
    family-4-pack-bingo.yaml
    ...
  family-4-pack.yaml               # type: pack, components: [...]
  bandit-unicorse.yaml             # Story Starter — still a plain item
```

Fields that describe the pack as a whole (`attributes.manufacturer`,
`attributes.series`) live on the pack item; fields that vary per figure
(`attributes.accessory` — a costume/prop specific to that sculpt) live on
the figure component. Don't duplicate `attributes.pack_name`/`pack_type`
onto components — the pack item's own `name` and `type: pack` already say
that; `image` isn't duplicated onto components either unless a figure
genuinely has its own distinguishing photo (rare — most releases only have
one photo, of the whole pack).

A Story Starter pack contains exactly one figure — the pack *is* the
figure, so it stays a single plain item (`type: figure`, named for the
character, e.g. `bandit-unicorse.yaml`) rather than being split into a
pack item plus a one-entry `_figures/` component. Don't retrofit this
split onto Story Starters.

## No printed catalog number

Neither pack type prints a collector/catalog number — identify by the
pack's own marketed name (the pack item's `name`, e.g. `"Bluey & Family
Figure 4-Pack"`, or `attributes.pack_name` for a Story Starter, e.g.
`"Bandit & Unicorse"`) plus the character(s) depicted. Retailer SKUs
(Amazon/Target item numbers) are not Moose Toys catalog numbers — don't
record them as `attributes.number`.

## Naming files

Multi-pack: slugified pack name directly under `poseable-figures/` (e.g.
`family-4-pack.yaml`), with each figure inside filed at
`_figures/<pack-slug>-<character-slug>.yaml` (e.g.
`_figures/family-4-pack-bluey.yaml`) — the pack-slug prefix disambiguates
the same character recurring across many packs' buckets. Story Starter:
slugified pack name directly (`bandit-unicorse.yaml`).
