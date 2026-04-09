# Pokemon TCG Curator

Fetch Pokemon Trading Card Game data from the official pokemon-tcg-data GitHub repository and import it into the database.

## Data Sources

All data comes from raw GitHub JSON — no API key required.

- **Sets list**: `https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/sets/en.json`
- **Cards for a set**: `https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/cards/en/{set_id}.json`

## Hierarchy

```
Pokemon TCG (top-level collection, already exists — this is COLLECTION_ID)
└── Series (collection)  e.g. "Scarlet & Violet", "Sword & Shield", "Original Series"
    └── Set (collection)  e.g. "Base Set", "Paldea Evolved"
        └── Card (card)  e.g. "Charizard 004/102"
```

## Incremental Fetch Strategy

**Always check what's already imported before fetching cards.** This avoids re-downloading large sets that are already complete.

1. Fetch `sets/en.json` — this is fast (~1 request, ~200 sets)
2. For each set, use `entity_find` with `key=pokemontcg_io_set`, `value={set_id}` to check if it exists in the DB
3. **Skip sets that already exist** unless the user asked to re-import a specific set
4. For new sets only, fetch `cards/en/{set_id}.json` and import

If `--limit N` is passed, stop after N cards total (useful for testing).
If `--set "Name"` is passed, only process that one set regardless of whether it exists.

## Entity Schemas

### Series (type: "collection", category: "trading_card_games")

```json
{
  "name": "Scarlet & Violet",
  "type": "collection",
  "category": "trading_card_games",
  "year": 2023,
  "external_ids": {
    "pokemontcg_io_series": "scarlet-and-violet"
  }
}
```

Series `external_ids.pokemontcg_io_series` = series name lowercased, spaces→hyphens, "&"→"and".
Year = earliest release year among sets in the series.
Series parent = COLLECTION_ID (top-level Pokemon TCG collection).

### Set (type: "collection", category: "trading_card_games")

```json
{
  "name": "Paldea Evolved",
  "type": "collection",
  "category": "trading_card_games",
  "year": 2023,
  "image_url": "https://images.pokemontcg.io/sv2/logo.png",
  "source_url": "https://pokemontcg.io/sets/sv2",
  "external_ids": {
    "pokemontcg_io_set": "sv2"
  },
  "attributes": {
    "total_cards": 279,
    "printed_total": 193,
    "release_date": "2023-06-09"
  },
  "parent": {
    "type": "collection",
    "external_ids": { "pokemontcg_io_series": "scarlet-and-violet" }
  }
}
```

Set image: use `set_data.images.logo` if available.

### Card (type: "card", category: "trading_card_games")

```json
{
  "name": "Charizard ex 199/193",
  "type": "card",
  "category": "trading_card_games",
  "year": 2023,
  "image_url": "https://images.pokemontcg.io/sv2/199_hires.png",
  "source_url": "https://pokemontcg.io/card/sv2-199",
  "external_ids": {
    "pokemontcg_io": "sv2-199"
  },
  "attributes": {
    "rarity": "Special Illustration Rare",
    "artist": "nagimiso"
  },
  "parent": {
    "type": "collection",
    "external_ids": { "pokemontcg_io_set": "sv2" }
  },
  "order": 199
}
```

**Card name format**: `{card.name} {number}/{printedTotal}` — e.g. "Charizard 004/102".
- If `number` is numeric, zero-pad to 3 digits: `int(number)` → `f"{n:03d}"`
- If `number` is non-numeric (e.g. "SV001", "TG01"), use as-is: `f"{name} {number}/{printedTotal}"`

Card image: use `card.images.large` if available (high-res), fall back to `card.images.small`.

`order`: parse `card.number` as int if possible, otherwise omit.

## Import

Batch into `entities_upsert` calls — collections first, then cards in batches of 250.

Send all series + sets as one initial batch, then cards in groups by set or by 250-item chunks.

```
entities_upsert(
  collection_id = COLLECTION_ID,
  items = [...],
  skip_duplicates = true,
  localize_images = true
)
```

## Scope Notes

- English cards only (`sets/en.json`, `cards/en/`)
- Do not import price data (tcgplayer prices, cardmarket prices) — these change constantly
- Do not create Variant entities for reverse holos — the source data doesn't reliably distinguish them
- Promo sets (set IDs like "swshp", "svp") are valid — include them
