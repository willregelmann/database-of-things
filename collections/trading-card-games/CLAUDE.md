# Trading Card Games — curation hints

## What belongs here

Collectible card games with a structured ruleset (deck-building, matches,
official expansions/sets) — Pokémon TCG, Magic: The Gathering, Yu-Gi-Oh!, and
similar. Not single-purpose novelty card sets (those get their own domain
family elsewhere in `collections/`).

## Directory structure

```
trading-card-games/
  CLAUDE.md
  template.schema.json          # generic fallback; each game overrides it
  _collection.yaml               # this domain family's own entity record
  <game>/
    CLAUDE.md                    # game-specific conventions — required
    template.schema.json         # game-specific attributes — required
    _collection.yaml
    ...                          # game's own internal structure
```

Each game is a full top-level collection in its own right, not a thin
subdirectory — it needs its own `CLAUDE.md` and `template.schema.json` since
card attributes, numbering, and pitfalls vary by game. Follow the shape of
[`pokemon-tcg/CLAUDE.md`](pokemon-tcg/CLAUDE.md) as a worked example, and see
the root [`collections/README.md`](../README.md) for how directory position
determines parentage.

## Adding a new game

1. Create `trading-card-games/<game>/`.
2. Write its `CLAUDE.md` — identification scheme, naming convention,
   completeness-checking approach, known pitfalls. Don't inherit this
   family's `template.schema.json` as-is; write attributes specific to the
   game (see `pokemon-tcg/template.schema.json`).
3. Write its `_collection.yaml` (`type: collection`, plus a `description`).
4. Run the validator before opening a PR.
