# Collections — curation hints

Cross-cutting guidance for curating anything under `collections/` — domain
family, category, or nested set alike. This applies everywhere in the tree;
family- and category-specific `CLAUDE.md` files (e.g.
[`trading-card-games/CLAUDE.md`](trading-card-games/CLAUDE.md),
[`trading-card-games/pokemon-tcg/CLAUDE.md`](trading-card-games/pokemon-tcg/CLAUDE.md))
add game/category-specific detail on top of this — they don't replace it.

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
directly under `collections/`, e.g. `trading-card-games/`, `comics/`) don't
get a `date` — they're DBoT's own organizational buckets for grouping
related categories, not things that were themselves released.

## Tags

The optional top-level `tags` field is a flat array of lowercase, hyphenated
strings (`tags: [pokemon, halloween]`) for cross-cutting groupings that don't
map to directory position. The main case: a franchise/IP that spans multiple,
unrelated categories — a Pokémon-themed Squishmallow, Funko Pop, Nendoroid,
and Re-Ment figure all sit in completely different parts of the tree, so
nothing about their directory position lets someone find "everything
Pokémon" across the catalog. A shared `tags: [pokemon]` closes that gap.

**Franchise is always recorded via `tags`, never as a structured
`attributes` field, even within a single line where it doesn't cross
categories.** Funko Pop, for instance, resets its box-printed "line"
independent of franchise, so nearly every figure carries a franchise tag
(see
[`collectible-figures/funko-pop/CLAUDE.md`](collectible-figures/funko-pop/CLAUDE.md))
— not just the cross-category crossover cases. Keeping franchise in one
place means a search for "everything Pokémon" never has to also check a
per-category attribute that might hold the same information.

**Don't over-tag — same philosophy as not adding speculative `attributes`.**
A tag only earns its place if it captures a grouping that's genuinely useful
and isn't already available some other way:

- **Don't restate the hierarchy.** A card in `pokemon-tcg/` doesn't need
  `tags: [pokemon]` — its category already says that. Tags exist for
  groupings the *directory position doesn't* express, not to duplicate it.
- **Don't duplicate a tag into a structured `attributes` field**, and vice
  versa — pick one home for a given piece of information and search it there.
- **Don't invent tags for hypothetical future searches.** Add a tag when it
  reflects a grouping that's real and useful today, not because it might be
  handy if someone eventually wants to filter by it.
- **Keep the list short — rarely more than 5 tags on a single entity.** A
  couple of high-value tags beats an exhaustive set of loosely-related
  keywords; if nothing crosses the hierarchy in a useful way, leave `tags`
  off entirely rather than reaching for something to put there. An entity
  that genuinely spans several independent cross-cutting groupings at once
  (e.g. a crossover collab piece tied to two franchises plus a
  seasonal/exclusive-release status) can legitimately go over 5 — treat that
  as a rare, deliberate case, not a target to build up to.

Format matches the repo's existing slug convention (lowercase, hyphenated,
e.g. `star-wars` not `Star Wars`) so tags stay consistent and easy to
search/group by.

## Logos

When adding or editing a collection's own `_collection.yaml` — at any level,
not just expansion/set records — check whether it has a real official logo
or brand mark, and if so add `image.source_url` pointing to it, the same way
set-level records already do (see
[`trading-card-games/pokemon-tcg/CLAUDE.md`](trading-card-games/pokemon-tcg/CLAUDE.md)
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
  [`model-kits/lego/CLAUDE.md`](model-kits/lego/CLAUDE.md) for LEGO
  minifigures).
- Don't retrofit `components` onto every item that happens to include
  extra parts — add it where a curator has actually catalogued the specific
  components, and leave a category's existing summary-count attribute (e.g.
  LEGO's `attributes.minifigCount`) in place for items whose specific
  components aren't catalogued yet. Partial coverage beats none.
