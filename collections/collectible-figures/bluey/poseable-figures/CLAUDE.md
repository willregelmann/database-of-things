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

A multi-pack is a small collection in its own right (its box is the
collectible unit, several figures inside) — give it its own directory with
a `_collection.yaml` and one entity file per figure, the same pattern as a
Re-Ment volume (see [`../../re-ment/CLAUDE.md`](../../re-ment/CLAUDE.md)).
A Story Starter pack contains exactly one figure — file it directly as a
single entity (named for the pack, e.g. `bandit-unicorse.yaml`) rather than
creating a one-item collection directory for it, per the root
[`collections/CLAUDE.md`](../../../CLAUDE.md) collection-shape guidance.

## No printed catalog number

Neither pack type prints a collector/catalog number — identify by the
pack's own marketed name (`attributes.pack_name`, e.g. `"Bluey & Family
Figure 4-Pack"`, `"Bandit & Unicorse"`) plus the character(s) depicted.
Retailer SKUs (Amazon/Target item numbers) are not Moose Toys catalog
numbers — don't record them as `attributes.number`.

## Naming files

Multi-pack directory: slugified pack name (e.g. `family-4-pack/`), with each
figure inside named for its character (`bluey.yaml`, `bingo.yaml`). Story
Starter: slugified pack name directly (`bandit-unicorse.yaml`).
