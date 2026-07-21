# POP MART — curation hints

## Directory structure

```
pop-mart/
  CLAUDE.md
  template.schema.json          # generic fallback; every IP shares this shape
  _collection.yaml               # the whole "POP MART" figures line
  <ip>/
    _collection.yaml             # the IP, e.g. "The Monsters", "Molly", "Dimoo"
    <series>/
      _collection.yaml           # one blind-box series within that IP
      <slugified-design-name>.yaml
```

Three levels, not two like Funko Pop — POP MART's catalog is organized as
**IP → series → design**, where an IP is a character world created by one
artist (or artist duo) under license or exclusive agreement to POP MART, and
a series is one blind-box release within that IP (a fixed set of designs
sold together, usually 6, 8, 9, or 12 regular designs plus one secret).

**Naming IP directories: use POP MART's own IP name, not a flagship
character's name.** This is a common trap — **Labubu is a character within
the "The Monsters" IP, not its own IP.** POP MART's IP/Artist Zone and every
major fan database (thetoypool.com) list "THE MONSTERS" as the IP; Labubu
never appears as a standalone entry. File Labubu-headlined series under
`the-monsters/`, not a `labubu/` directory. The same caution applies broadly
— confirm the actual IP name (POP MART's IP/Artist Zone, or a fan database's
IP-level page) before creating a new IP directory, rather than assuming a
popular character's own name is the IP name.

**Naming series directories**: lowercase, hyphenated, matching the series'
own marketed name (e.g. `have-a-seat`, `exciting-macaron`, `big-into-
energy`).

## What belongs here

Standalone blind-box figures and vinyl-plush hybrids — POP MART's core
collectible format, sold as a numbered/named series with a fixed design
lineup. **Excluded from this category** (same figures-only scope as the
rest of [`../CLAUDE.md`](../CLAUDE.md)):

- **MEGA-scale figures** (100%/400% oversized releases, e.g. MEGA SPACE
  MOLLY) — sold individually, not as blind boxes, with their own separate
  numbering/format. A distinct sibling collection if curated (e.g.
  `figures/pop-mart-mega/`), the same relationship as Funko Pop
  Rides/Town to plain Funko Pop (see
  [`../funko/pop/CLAUDE.md`](../funko/pop/CLAUDE.md)).
- **Pure plush** (soft-only, no vinyl parts) — a `plush/` concern if
  curated, not here.
- **Keychains, pendants, and other accessories** — not standalone figures.
- **Playsets, scene sets, and non-figure home goods** (mugs, stationery,
  etc.) — merchandise, not figures.

**Vinyl-plush hybrids are in scope, not excluded.** Some series (e.g. "Have
a Seat") use a vinyl face on a plush/fabric body — this is still part of
POP MART's core numbered blind-box figure catalog, sold and numbered
alongside solid-vinyl series, not a separate "plush toy line" the way
Bluey's soft plush is. Record the construction via `attributes.format`
rather than excluding it.

## No official global numbering

POP MART does not print a persistent catalog number on figures or boxes the
way Funko does with its "Pop! No." — identification research turned up no
evidence of one at the IP, series, or individual-design level. Identify a
figure by **IP + series name + design name** only. Fan databases (e.g. The
Toy Pool) sometimes impose their own internal numbering for their site's
purposes — don't mistake that for an official POP MART number.

## Secret designs

Every series typically ships with one secret/hidden design pulled at a
stated rarity (commonly 1-in-72 or 1-in-144, printed on the box back) in
addition to its regular lineup. Record it as a normal entity file in the
series directory, with `attributes.secret: true` and, when POP MART states
it, `attributes.secret_odds` (e.g. `"1-in-72"`) — don't fold the secret into
a regular design's file or skip filing it.

## Collection records

Give each `<ip>/_collection.yaml` a short `description` naming its
designer/artist when that credit is confirmed by more than one source (see
Common pitfalls below on conflicting attributions) — match the tone of
existing records elsewhere in this category. Give each
`<series>/_collection.yaml` a `description` plus `date` (the series' release
date — POP MART's own announcements, e.g. official X/Twitter posts, are
usually the most precise source).

## Manufacturer

`attributes.manufacturer` is `POP MART International Group Limited` across
every IP and series unless a specific release credits a different legal
entity — check the packaging/listing rather than assuming.

## Sourcing

POP MART's own site (popmart.com) is a client-rendered SPA — its product
pages don't expose data to a plain HTTP fetch, so cross-check with POP
MART's official social announcements (X/Twitter product-launch posts) and
fan databases: [The Toy Pool](https://thetoypool.com/pop-mart/) (structured
IP/series checklists), [Coleka](https://coleka.com/) (~3,600 catalogued
figures), and dedicated collector guide sites (e.g. labubu.city,
labubucollector.com for The Monsters specifically). Cross-reference at
least two independent sources per series before filing — POP MART has no
single authoritative catalog API the way Pokémon TCG does.

## Common pitfalls

- Don't name an IP directory after its most famous character — see Naming
  IP directories above (Labubu → `the-monsters/`, not `labubu/`).
- Designer/artist attribution is contested for some IPs in secondary
  sources (e.g. Skullpanda's designer is credited inconsistently across
  sites) — only record a designer credit in an IP's `description` once
  confirmed by more than one source; otherwise leave it out rather than
  guessing.
- Fan collector-guide sites sometimes version their own write-ups as "V2"
  etc. for a series — that's the site's own content versioning, not part of
  POP MART's official product name. Use POP MART's own product/announcement
  name for `name`, not a fan site's guide title.
- Don't treat a Pop! No.-style number as existing here — see No official
  global numbering above.
- Convention-exclusive and regional-exclusive releases exist (e.g. SDCC
  lottery exclusives) — record via `attributes.exclusive_to`, verified
  per-release rather than assumed.
