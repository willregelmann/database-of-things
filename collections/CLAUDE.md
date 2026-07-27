# Collections — curation hints

Cross-cutting guidance for curating anything under `collections/` — domain
family, category, or nested set alike. This applies everywhere in the tree;
family- and category-specific `CLAUDE.md` files (e.g.
[`trading-cards/CLAUDE.md`](trading-cards/CLAUDE.md),
[`trading-cards/pokemon-tcg/CLAUDE.md`](trading-cards/pokemon-tcg/CLAUDE.md))
add game/category-specific detail on top of this — they don't replace it.

## Collectibles, not products

**The entity is the collectible — the individual physical thing someone owns
and points at. One card, one figure, one issue. Not the product it was sold
as.** A product is a commercial unit: a sealed booster pack, a three-figure
multipack, a boxed starter set, a regional SKU. The catalog is a record of
what collectors collect, and nobody collects a UPC.

The operative test: **deduplicate on physical uniqueness, not on product
identity.**

- **Two entries are the same entity when the objects are physically
  indistinguishable** — however many products they shipped in, and however
  many barcodes those products carried. A figure sold both single-boxed and
  in a gift set is one entity, not two. The same card pulled from a booster
  pack or a tin is one card.
- **Two entries are different entities when the objects themselves differ**
  in a way a collector distinguishes — a different paint application, foil
  treatment, colorway, or printed number. This holds even when the product
  and its barcode are unchanged, which is exactly why Squishmallows records a
  dash-suffixed colorway and Funko records a variant suffix.

What follows from it:

- **Packaging is never a directory tier.** How something was distributed
  isn't a property of the thing. Yu-Gi-Oh!'s sets group cleanly by "Booster
  Pack / Structure Deck / Starter Deck" and the catalog deliberately doesn't
  use that split, because it describes the sealed package rather than the
  card — see
  [`trading-cards/yu-gi-oh/CLAUDE.md`](trading-cards/yu-gi-oh/CLAUDE.md).
- **A retail bundle isn't a collectible, and isn't `components` either.**
  When a multipack contains figures that are themselves the collectibles,
  file the figures — the bundle is a purchase, not a thing to own. Contrast a
  LEGO set, where the set *is* the collectible and its minifigures are
  genuine components (see Components below). The test is the one stated
  there: owning every component doesn't amount to owning the item. Owning
  every figure from a multipack does amount to owning what the multipack
  offered, which is how you know it was only packaging.
- **A container gets its own entity only when the container is itself
  collected.** A boxed set with its own identity qualifies; a blister card
  doesn't.

**Where the line falls between "a variant" and "the same thing" is a
per-category call**, and it's what a category's `CLAUDE.md` exists to settle
— a print-run difference that matters enormously in one line is noise in
another. This principle says which question to ask, not what the answer is.
Answer it in the category's own `CLAUDE.md` before filing at scale, because
changing it later means re-cutting every file in the collection.

## Tree shape

Every path through `collections/` has the same shape:

```
<category>/<brand>[/<line>[/<subline>…]]/<item>
```

- **category** — the domain family directly under `collections/`
  (`trading-cards/`, `figures-and-models/`, `plush/`, `comics-and-manga/`,
  `video-games/`). DBoT's own grouping, not a thing that was released — which
  is why a category gets no `date` (see Dates below).
- **brand** — required. **What counts as a brand differs by category, and
  that's deliberate**: the manufacturer in `figures-and-models/` (`bandai`,
  `funko`), the publisher in `comics-and-manga/` (`dark-horse`, `viz-media`),
  the game in `trading-cards/` (`pokemon-tcg`), the plush brand itself in
  `plush/` (`squishmallows`). Each category's own `CLAUDE.md` states which,
  and generally means the *customer-facing* brand rather than the deepest
  legal parent — figma is `good-smile/figma/`, not filed under Max Factory.
- **line** — optional. A named product line within the brand
  (`good-smile/nendoroid/`, `bandai/gunpla/`).
- **subline** — optional, and **may repeat** (`bandai/gunpla/mg/`,
  `pokemon-tcg/mega-evolution-series/<set>/`).
- **item** — the leaf entity file. It sits at whatever depth its collection
  is; items directly under a brand are normal when that brand has no line
  tier.

### Sanity check on the brand tier

**A brand directory is always a name someone owns and puts on the product —
never a descriptive grouping.** Every brand directory in the catalog satisfies
this today, across three different kinds of mark, all legitimate:

- a **corporate name** — `bandai/`, `nintendo/`, `marvel/`, `viz-media/`
- a **product or retail brand** — `squishmallows/`, `pokemon-center/`,
  `firelink/`
- a **title mark** — `magic-the-gathering/`, `pokemon-tcg/`, `yu-gi-oh/`

Use it as a diagnostic when a new brand directory is proposed: **if the name
isn't something an owner puts on the product, it's a category, not a brand.**
Either it belongs one level up as a domain family, or the tier is invented and
shouldn't exist — the same failure the "brand-defined or community-standard"
rule below catches from the other direction.

The test is ownership and appearance on the product, **not trademark
registration.** Registration is evidence, not the requirement: it varies by
jurisdiction, lapses, and would wrongly exclude an individual artist selling a
line under their own name, a doujinshi circle, or a defunct line whose mark
has expired. All of those are legitimate brand directories.

**Worked example — the same franchise across three positions.** "Pokémon"
appears at the brand tier twice and the line tier once:
`trading-cards/pokemon-tcg/`, `plush/pokemon-center/`, and
`figures-and-models/re-ment/pokemon/`. All three are correct, because they're
three *different* marks — a game, a retail brand, and Re-Ment's own line name
— while the franchise itself is carried by a `tags/franchises/` tag and lives
nowhere in the tree.

Note the third one is at the **line** tier, not the brand tier, and that's the
distinction to hold on to: a franchise name is fine as a line under a
manufacturer (`re-ment/pokemon/`, `bandai/power-rangers/`) where it names that
maker's own product line — see
[`figures-and-models/CLAUDE.md`](figures-and-models/CLAUDE.md). A bare
franchise name at the **brand** tier is the misplacement, because the franchise
isn't what the seller's name on the box is. Cross-cutting franchise discovery
comes from the tag either way.

Two rules govern the optional tiers.

**A tier must be named by the brand or standard in the collecting community
— never invented by DBoT to make a category look symmetrical.** Pokémon TCG
has a real series tier above its sets, so its sets sit at
`pokemon-tcg/<series>/<set>/`; Magic has no equivalent, so its sets sit
directly at `magic-the-gathering/<set>/`. That asymmetry is correct. Don't
manufacture a tier for tidiness, and don't collapse one that genuinely
exists.

Depth follows from that test rather than from a fixed limit.
`figures-and-models/bandai/power-rangers/in-space/figures/` runs four tiers
deep under its category and every one of them earns it: Bandai the brand,
Power Rangers the line it sold under its own name, In Space the season, and
the figure/zord/weapon/vehicle split the way that line is conventionally
divided. Components buckets (`_zords/`) sit outside this shape entirely —
they aren't browsable tiers (see Components below).

**Don't split a brand across sibling directories.** Everything a brand sells
belongs under its one directory, subdivided by line. Sibling directories
sharing a brand-name prefix — `squishmallows-squish-a-longs/` next to
`squishmallows/` — are the shape to avoid: that's hierarchy encoded in a
filename instead of in the tree, and it scatters one brand across a
category's top level.

**This holds even when a line isn't the same kind of object as its brand.**
Squishmallows' Squish-A-Longs are 1" squeezable *plastic* figures, not plush
at all, and they still belong at `plush/squishmallows/squish-a-longs/`.
Filing them by material would mean a Squishmallows collector has to know
which category each sub-brand got sorted into — exactly the knowledge a
catalog should be saving them. The same principle runs the other way in
[`figures-and-models/CLAUDE.md`](figures-and-models/CLAUDE.md): "a line is
curated whole — don't slice one line by object type," which is why a Power
Rangers Zord or role-play morpher stays with its figure line. **The unit is
the brand, not the material.**

The limit: this keeps *one brand* together, it doesn't pull in neighbours. An
unrelated line from the same manufacturer isn't covered — Jazwares makes
plenty that has nothing to do with Squishmallows — and a brand whose whole
identity belongs to another category goes there instead.

## Collection shape

**A collection should usually contain either nested collections or items,
rarely both at the same level.** A category's own directory is typically all
sub-collections (series, sets, product lines); a set's directory is
typically all items (cards, figures). `_collection.yaml` doesn't count
toward this either way — it's the directory's own entity record, not a
child of it.

This is a soft rule, not a hard split. A directory that genuinely needs a
small, distinctly-scoped sub-collection (its own dated/sourced identity)
alongside the rest of its plain items is a legitimate exception — don't
force an artificial collections-only tier on top just because this
guideline exists. But treat mixing as the exception that needs a reason,
not the default shape to reach for.

**A collection should rarely exceed 1000 items or 100 nested collections.**
Past that size, a directory listing stops being useful for orientation, and
it usually means there's a missing intermediate grouping — Pokémon TCG's
series → expansion → card split exists precisely so no single directory
ever holds every card in the game. If a category is approaching either
threshold, look for a natural subdivision already present in the source
material (an official series, era, or product-line boundary) before just
piling everything into one directory.

The legitimate exception: a collection that the source material itself
defines as one indivisible unit — a single expansion's own checklist, sized
by its actual print run rather than by a grouping choice DBoT made —
shouldn't be artificially split just to dodge this guideline. Treat 1000/100
as a prompt to look for a real missing grouping level, not a hard ceiling to
engineer around when no natural one exists.

## Scaffolding a new collection

**A new line, series, or game arrives in two phases: scaffold it first,
author its own conventions when it actually has items.** Each family's
`CLAUDE.md` spells this out in its own "Adding a new …" section; this is the
shared rule behind them.

- **Phase 1 — scaffold.** Create the directory and its `_collection.yaml`,
  nothing else. It inherits the nearest ancestor's `CLAUDE.md` and
  `template.schema.json`, which is all the validator requires — it checks for
  them "own or inherited," walking up the tree. **An itemless
  `_collection.yaml` is a legitimate, useful record**: it says "this line
  exists and hasn't been curated yet," which is strictly better than the
  catalog silently implying it doesn't exist. Don't hold a known-missing
  line out of the tree because nobody has worked out its identification
  scheme yet, and don't gate the scaffold on shipping items alongside it.
- **Phase 2 — author its conventions.** Before the **first item** is filed
  under it, the line needs its own `CLAUDE.md` (identification scheme, naming
  convention, known pitfalls) and `template.schema.json`. The one exception
  is a tier whose parent `CLAUDE.md` already documents its conventions
  explicitly — POP MART's IP directories inherit
  [`figures-and-models/pop-mart/CLAUDE.md`](figures-and-models/pop-mart/CLAUDE.md)
  by design and never need their own.

**Why this order.** A line's identification scheme is much easier to write
correctly while holding real product data than in the abstract — authored
speculatively, it tends to be contradicted by the first ten items that
actually arrive. The reverse order also has a track record here:
`bandai/gunpla/` and `bandai/gashapon/` both received fully-authored
`CLAUDE.md` and `template.schema.json` up front and still contain **zero
items**, while `re-ment/pokemon/` (462 items), `pop-mart/skullpanda/` (263),
and `dark-horse/hellboy/` have run correctly on inherited conventions for
their whole existence. Requiring the authoring step up front mostly succeeded
at keeping real data out.

Phase 2 is deferred, not optional — a line accumulating items under inherited
conventions it has outgrown is a real defect, just a later one than an empty
directory.

## Dates

The optional top-level `date` field records when an entity was **first**
released — always a quoted string, since an unquoted `YYYY-MM-DD` gets parsed
as a YAML timestamp instead of a string. Use whatever precision the source
actually supports, don't pad it out:

- `date: "1999"` — year only, when that's the best precision the source gives.
- `date: "1999-06"` — year and month.
- `date: "1999-06-30"` — full release date, when a reliable per-item or
  per-expansion source exists (e.g. Pokémon TCG's expansion release dates).

Don't fabricate precision that isn't in the source — a card known only to
have shipped "in 1999" stays `date: "1999"` rather than guessing a month.

**This applies at every level, not just leaf items — an ongoing or
multi-part collection (a series, a product line, a publisher) gets a date
too, using its *first* release rather than a range.** A grouping collection's
`date` should match whichever of its own children has the earliest already-
sourced date (e.g. a card series' date matches its first expansion; a
figure line's date matches its first-released figure) — don't re-derive it
from a separate source when a child's date already establishes it. If no
child is dated precisely enough yet (or the entity's true first release
isn't reliably sourceable — e.g. a licensed brand with several unfiled
product lines), leave `date` off rather than guessing; that's a gap to
close later, not something to fabricate now.

**Exception: domain-family directories** (the broad top-level groupings
directly under `collections/`, e.g. `trading-cards/`,
`comics-and-manga/`) don't get a `date` — they're DBoT's own organizational
buckets for grouping related categories, not things that were themselves
released.

## Descriptions

Some entities — in practice almost always `_collection.yaml` records, not leaf
items — carry an optional top-level `description`: a short summary of what the
collection, series, or set is. Two rules govern it, and they exist to keep the
whole catalog cleanly redistributable under CC0 (see the repo's
[`LICENSE-DATA`](../LICENSE-DATA)).

- **Write original prose — never paste or lightly reword source text.** State
  facts freely (release dates, mechanics, notable items, who produced it), but
  the *wording* must be your own synthesis. Copying a description from
  Bulbapedia, a Fandom/wiki page, a manufacturer's marketing copy, or a
  retailer listing imports that source's copyright and license — e.g.
  Bulbapedia is CC BY-NC-SA, whose non-commercial + share-alike terms are
  incompatible with this project's CC0 data license. Facts carry no such
  license; original expression over those facts is the project's own and can be
  released under CC0. Descriptions written by an AI curator satisfy this as long
  as they're genuine synthesis, not regurgitated source prose.
- **Keep it factual and brief — a few sentences.** A description orients a
  reader on what the grouping is and why it's distinct; it isn't a place for
  exhaustive detail (that's what `source_url` links and per-item data are for)
  or for promotional/editorializing tone. When there's nothing non-obvious to
  say beyond what the name and hierarchy already convey, leave `description`
  off rather than padding it.

## Tags

The optional top-level `tags` field is a flat array of **ids**, each
referencing a tag entity under [`tags/`](../tags/) — a sibling of
`collections/`, not a part of it, since a tag is cross-cutting by nature
(see [`tags/CLAUDE.md`](../tags/CLAUDE.md) and
[`docs/primitives/TAG.md`](../docs/primitives/TAG.md) for the full tag
primitive reference). Tags close a gap directory position can't: the main
case is a franchise/IP that spans multiple, unrelated categories — a
Pokémon-themed Squishmallow, Funko Pop, Nendoroid, and Re-Ment figure all
sit in completely different parts of the tree, so nothing about their
directory position lets someone find "everything Pokémon" across the
catalog. Referencing the same `tags/franchises/pokemon.yaml` entity from
all four closes that gap.

```yaml
tags:
  - 175817b0-ba6b-49ca-90a9-f0777b4149e4   # tags/franchises/pokemon.yaml
```

**Reusing an existing tag is as cheap as it's always been** — look up its
id under `tags/` and reference it. **Adding a genuinely new tag means
creating its entity file first** (under the right namespace, e.g.
`tags/franchises/`), then referencing that id — there's no more freeform
ad hoc string tagging. Duplicate ids within one entity's `tags` list are
still an error (unlike `components`, where a duplicate is meaningful); the
validator also enforces that every id resolves to a real `tags/` entity.

**Franchise is always recorded via `tags`, never as a structured
`attributes` field, even within a single line where it doesn't cross
categories.** Funko Pop, for instance, resets its box-printed "line"
independent of franchise, so nearly every figure carries a franchise tag
(see
[`figures-and-models/funko/pop/CLAUDE.md`](figures-and-models/funko/pop/CLAUDE.md))
— not just the cross-category crossover cases. Keeping franchise in one
place means a search for "everything Pokémon" never has to also check a
per-category attribute that might hold the same information.

**Don't over-tag — same philosophy as not adding speculative `attributes`.**
A tag only earns its place if it captures a grouping that's genuinely useful
and isn't already available some other way:

- **Don't restate the hierarchy — but franchise is the deliberate
  exception.** In general a tag shouldn't duplicate what directory position
  already expresses. Franchise is the one axis that must stay tag-derivable
  regardless, because the directory tree *deliberately* doesn't carry it
  (the figure families organize by manufacturer, not franchise — see
  [`figures-and-models/CLAUDE.md`](figures-and-models/CLAUDE.md)). So a franchise search should
  resolve from tags alone, never from also scanning the tree. Record
  franchise **at the highest level where it's uniformly true**:
  - When a whole collection is one franchise, tag that collection's
    `_collection.yaml` — e.g. `figures-and-models/bandai/power-rangers/_collection.yaml`,
    or `trading-cards/pokemon-tcg/` — **not** every item inside it. A
    franchise search resolves an item by walking up to its nearest
    franchise-tagged ancestor collection.
  - When a collection mixes franchises, tag the individual **items** — e.g.
    a lone Power Rangers Funko Pop among many franchises in
    `figures-and-models/funko/pop/television/`.
  - Don't tag *both* an item and an ancestor collection that already carries
    the same franchise — that duplicate *is* the restatement to avoid.
- **Don't duplicate a tag into a structured `attributes` field**, and vice
  versa — pick one home for a given piece of information and search it there.
- **Don't invent tags for hypothetical future searches — except franchise.**
  For every other kind of tag, add it when it reflects a grouping that's real
  and useful today, not because it might be handy if someone eventually wants
  to filter by it. A **franchise** tag is different: create it the first time
  that franchise appears in the catalog, even when it currently resolves to a
  single collection or a single item. Gating a franchise tag on whether it
  already spans two collections makes coverage depend on curation order, and
  that's not hypothetical — the catalog ran for months with ~22,000 Pokémon
  items of which only 76 were franchise-searchable, because the tag had only
  ever been applied in the one line where someone happened to notice it
  crossing categories. A franchise tag resolving to one collection today
  isn't speculative; it's the same franchise anyone would search for,
  recorded once now instead of retrofitted across thousands of files later.
- **Keep the list short — rarely more than 5 tags on a single entity.** A
  couple of high-value tags beats an exhaustive set of loosely-related
  keywords; if nothing crosses the hierarchy in a useful way, leave `tags`
  off entirely rather than reaching for something to put there. An entity
  that genuinely spans several independent cross-cutting groupings at once
  (e.g. a crossover collab piece tied to two franchises plus a
  seasonal/exclusive-release status) can legitimately go over 5 — treat that
  as a rare, deliberate case, not a target to build up to.

See [`tags/CLAUDE.md`](../tags/CLAUDE.md) for how to add a new tag entity
(namespace, naming, display-name conventions).

## Logos

When adding or editing a collection's own `_collection.yaml` — at any level,
not just expansion/set records — check whether it has a real official logo
or brand mark, and if so add `image.source_url` pointing to it, the same way
set-level records already do (see
[`trading-cards/pokemon-tcg/CLAUDE.md`](trading-cards/pokemon-tcg/CLAUDE.md)
for the worked example). Take the URL from an authoritative source (the
rights-holder's own assets, or a well-maintained reference like Wikimedia
Commons) rather than guessing or hand-constructing one, and verify it
actually resolves before considering the entry done.

Don't invent a logo where none exists — many groupings (e.g. retroactive
"series" groupings that were never marketed under one banner) have no
official logo at all. Leave `image` off rather than substituting a fan-made
or unrelated image.

Hold the line on "authoritative and clean": a real logo spotted only
embedded in a marketing photo or webpage banner (mixed with character art,
other logos, or UI chrome) isn't the same as a standalone asset — don't crop
or hand-construct one to force a fit. Leave `image` off and treat it as a
sourcing gap instead.

**The logo must belong to the entity itself, not a franchise it's merely
based on or licensed from.** A merchandise line themed around a video game
isn't the same entity as the game — pointing its `image` at the game's own
trademarked logo implies that mark represents the merchandise, which it
doesn't (contrast with e.g. the Pokémon TCG collection, whose logo is
correct precisely because that collection *is* the Pokémon TCG, not a
product based on it). If the entity has no logo of its own, leave `image`
off rather than substituting the thing it's licensed from.

## Components

Some items are physically made up of other, independently-catalogable
things — a LEGO set includes several minifigures, a board game includes
miniatures, a vinyl box set includes prints. Those parts are **components**,
not items in their own right: **owning every component of an item doesn't
constitute owning the item, unlike owning every item in a collection, which
does constitute owning the collection.** A person who somehow acquired all
four minifigures from a LEGO set loose hasn't acquired the set.

A component is catalogued exactly like any other entity — its own YAML file
with `id`/`name`/`type`, filed wherever it naturally belongs in the tree
(see the category's own `CLAUDE.md` for where that is). What makes it a
component is that some other item's top-level `components` field points at
it:

```yaml
components:
  - a42e702b-e52b-4247-8ed6-103ed31a340b
  - 53708aaf-cb2a-41c7-b03a-bc95d651f563
```

- **Reference by `id`, never by path.** A component's file can move (a
  minifig re-filed under a different theme, a set migrated into a new
  subtheme) without breaking anything that points at it — the same reason
  `id` is "generated once, never reused" everywhere else in this format.
- **Duplicate `id`s in one `components` list are allowed** — unlike `tags`,
  where a duplicate is an error. Repeating an id represents owning more than
  one of that component (e.g. a set that includes two identical minifigs).
- The validator checks every `components` entry resolves to a real `id`
  somewhere in the catalog, but doesn't require the component to already
  exist before the referencing item does within the same PR.
- **A directory whose name is prefixed with `_` (other than the
  `_collection.yaml` file itself) is a components bucket, not a browsable
  collection someone completes — it doesn't get its own `_collection.yaml`,
  and the validator doesn't require one.** This convention predates
  components (`_collection.yaml` already used a leading underscore to mean
  "structural, not a normal peer") — extending the same marker to a
  directory name means a components bucket doesn't need an entity record
  of its own just to satisfy the validator, since nothing ever references
  the bucket itself; components are referenced individually, by their own
  `id`. It still needs `CLAUDE.md`/`template.schema.json` (own or
  inherited) like any directory holding entity files. See the category's
  own `CLAUDE.md` for the actual directory convention (e.g.
  [`figures-and-models/lego/CLAUDE.md`](figures-and-models/lego/CLAUDE.md) for LEGO
  minifigures).
- Don't retrofit `components` onto every item that happens to include
  extra parts — add it where a curator has actually catalogued the specific
  components, and leave a category's existing summary-count attribute (e.g.
  LEGO's `attributes.minifigCount`) in place for items whose specific
  components aren't catalogued yet. Partial coverage beats none.
