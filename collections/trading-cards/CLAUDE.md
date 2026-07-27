# Trading Cards — curation hints

## What belongs here

Collectible cards sold in sets — anything printed as a card and collected as
a set belongs here, whether or not it's playable:

- **Trading card games** with a structured ruleset (deck-building, matches,
  official expansions) — Pokémon TCG, Magic: The Gathering, Yu-Gi-Oh!.
- **Sports cards** — Topps, Panini, Upper Deck, and similar.
- **Non-sport card sets** — Garbage Pail Kids, Marvel Universe, movie and TV
  tie-in sets, and other one-off or seasonal card releases.

The distinction that used to gate this family (playable game vs. novelty
card set) is no longer a boundary — it's a property of the individual line,
recorded in that line's own `_collection.yaml` and `CLAUDE.md`. It does
still shape the internal structure, though: see below.

Not card-shaped things that aren't collected as card sets — a board game's
component deck belongs with the product it ships in, not here.

## Directory structure

```
trading-cards/
  CLAUDE.md
  template.schema.json          # generic fallback; each line overrides it
  _collection.yaml               # this domain family's own entity record
  <line>/
    CLAUDE.md                    # line-specific conventions — required
    template.schema.json         # line-specific attributes — required
    _collection.yaml
    ...                          # line's own internal structure
```

Each line is a full top-level collection in its own right, not a thin
subdirectory — it needs its own `CLAUDE.md` and `template.schema.json` since
card attributes, numbering, and pitfalls vary by line. See the root
[`collections/README.md`](../README.md) for how directory position
determines parentage.

**How deep a line nests depends on how much it publishes.** An ongoing TCG
needs intermediate grouping levels to stay under the size guidelines in
[`../CLAUDE.md`](../CLAUDE.md) — Pokémon TCG uses series → expansion → card,
which is why no single directory holds every card in the game. A line that
released one set, or one set per year, doesn't need that machinery; a flat
set → card layout is correct for it. Follow
[`pokemon-tcg/CLAUDE.md`](pokemon-tcg/CLAUDE.md) as the worked example of
the deep case, and don't manufacture a series tier for a line that has no
real one.

## Adding a new line

1. Create `trading-cards/<line>/`.
2. Write its `CLAUDE.md` — identification scheme, naming convention,
   completeness-checking approach, known pitfalls. Say whether the line is a
   playable game or a non-game set, and what its intermediate grouping
   levels (if any) are. Don't inherit this family's `template.schema.json`
   as-is; write attributes specific to the line (see
   `pokemon-tcg/template.schema.json`).
3. Write its `_collection.yaml` (`type: collection`, plus a `description`).
4. Run the validator before opening a PR.
