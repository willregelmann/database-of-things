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
map to directory position or to an existing structured `attributes` field.
The main case: a franchise/IP that spans multiple, unrelated categories — a
Pokémon-themed Squishmallow, Funko Pop, Nendoroid, and Re-Ment figure all sit
in completely different parts of the tree, so nothing about their directory
position lets someone find "everything Pokémon" across the catalog. A shared
`tags: [pokemon]` closes that gap.

**Don't over-tag — same philosophy as not adding speculative `attributes`.**
A tag only earns its place if it captures a grouping that's genuinely useful
and isn't already available some other way:

- **Don't restate the hierarchy.** A card in `pokemon-tcg/` doesn't need
  `tags: [pokemon]` — its category already says that. Tags exist for
  groupings the *directory position doesn't* express, not to duplicate it.
- **Don't restate a structured attribute.** Funko Pop already records
  `attributes.franchise` per figure (see
  [`collectible-figures/funko-pop/CLAUDE.md`](collectible-figures/funko-pop/CLAUDE.md)) —
  don't also add a `tags` entry that just repeats that value.
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
