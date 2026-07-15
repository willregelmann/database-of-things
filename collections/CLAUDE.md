# Collections — curation hints

Cross-cutting guidance for curating anything under `collections/` — domain
family, category, or nested set alike. This applies everywhere in the tree;
family- and category-specific `CLAUDE.md` files (e.g.
[`trading-card-games/CLAUDE.md`](trading-card-games/CLAUDE.md),
[`trading-card-games/pokemon-tcg/CLAUDE.md`](trading-card-games/pokemon-tcg/CLAUDE.md))
add game/category-specific detail on top of this — they don't replace it.

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
