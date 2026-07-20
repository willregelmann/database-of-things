# Bandai — curation hints

## What belongs here

Bandai's figure lines and the licensed toy ranges Bandai manufactured,
organized one nested collection per line. Two kinds of child live here, and
they're both legitimate:

- **Bandai's own branded lines** — e.g. [`gashapon/`](gashapon/CLAUDE.md),
  Bandai's capsule-toy business.
- **Franchise toy ranges Bandai produced under license** — e.g.
  [`power-rangers/`](power-rangers/CLAUDE.md). Here the directory name is a
  franchise, but it sits under `bandai/` because Bandai is the
  customer-facing maker whose name is on the toys. The franchise itself is
  cross-cutting and is (or will be) carried by a `tags/franchises/` tag, not
  by directory position — see the parent [`../CLAUDE.md`](../CLAUDE.md).

**A franchise that spans manufacturers splits by manufacturer.** Bandai
America produced the U.S. Power Rangers toy line from 1993 into the early
2000s; Hasbro has held the license since 2019. Only the Bandai eras belong
under `bandai/power-rangers/`; Hasbro's (the Lightning Collection onward)
would live under a sibling `hasbro/power-rangers/`, with a shared
`power-rangers` franchise tag reunifying the two once both exist. Don't file
Hasbro-era Power Rangers here.

## Directory structure

```
bandai/
  CLAUDE.md
  _collection.yaml               # Bandai itself
  <line>/                         # e.g. "gashapon", "power-rangers"
    CLAUDE.md
    template.schema.json
    _collection.yaml
    ...
```

## Sub-brands (not yet needed)

Bandai sells collector figures through named sub-brands — Tamashii Nations
(S.H.Figuarts, Chogokin) and Banpresto (World Collectable Figure, Ichiban
Kuji) among them. None are curated yet. When the first one is, decide then
whether it earns an intermediate level (`bandai/tamashii-nations/sh-figuarts/`)
or flattens (`bandai/sh-figuarts/`) — add the sub-brand tier only once more
than one line sits under it, per the "don't build a grouping tier with a
single child" guidance in [`../../CLAUDE.md`](../../CLAUDE.md).
