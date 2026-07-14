# Collections — curation hints

Cross-cutting guidance for curating anything under `collections/` — domain
family, category, or nested set alike. This applies everywhere in the tree;
family- and category-specific `CLAUDE.md` files (e.g.
[`trading-card-games/CLAUDE.md`](trading-card-games/CLAUDE.md),
[`trading-card-games/pokemon-tcg/CLAUDE.md`](trading-card-games/pokemon-tcg/CLAUDE.md))
add game/category-specific detail on top of this — they don't replace it.

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
