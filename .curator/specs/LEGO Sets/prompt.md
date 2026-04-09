# LEGO Sets Curator

Fetch LEGO sets from the Rebrickable API and import them into the database.

## Credentials

- `REBRICKABLE_API_KEY` from `secrets.env`
- Auth header: `Authorization: key {api_key}`

## Data Source

Rebrickable (https://rebrickable.com) — comprehensive LEGO database with every set ever released.

Key endpoints:
- `GET https://rebrickable.com/api/v3/lego/themes/?page_size=1000` — list all themes (paginated)
- `GET https://rebrickable.com/api/v3/lego/sets/?theme_id={id}&page_size=500&ordering=year` — sets for a theme

## Hierarchy

```
LEGO Sets (top-level collection — this is COLLECTION_ID)
└── Theme (collection)  e.g. "Star Wars", "City", "Technic"
    └── Set (lego_set)  e.g. "Millennium Falcon", "Police Station"
```

## What to Import

Themes are the top-level grouping (Star Wars, City, Creator, Technic, etc.). When given a specific theme name, fetch that theme's sets. For broad imports, start with the most popular themes.

**Theme lookup**: The themes endpoint returns all themes. Find the one matching the requested name (case-insensitive). Theme IDs are stable — use `rebrickable_theme_id` for deduplication.

## Entity Schemas

### Theme (type: "collection", category: "buildables")

```json
{
  "name": "Star Wars",
  "type": "collection",
  "category": "buildables",
  "external_ids": {
    "rebrickable_theme_id": "171"
  }
}
```

Theme parent = COLLECTION_ID.

### Set (type: "lego_set", category: "buildables")

```json
{
  "name": "Millennium Falcon",
  "type": "lego_set",
  "category": "buildables",
  "year": 2017,
  "image_url": "https://cdn.rebrickable.com/media/sets/75192-1/...",
  "source_url": "https://rebrickable.com/sets/75192-1/",
  "external_ids": {
    "rebrickable_set_num": "75192-1"
  },
  "attributes": {
    "pieces": 7541
  },
  "parent": {
    "type": "collection",
    "external_ids": { "rebrickable_theme_id": "171" }
  },
  "order": 2017
}
```

Fields from API response:
- `set_num` → `external_ids.rebrickable_set_num`
- `name` → `name`
- `year` → `year` and `order`
- `num_parts` → `attributes.pieces`
- `set_img_url` → `image_url`
- `set_url` → `source_url`

## Pagination

Sets endpoint paginates. Check `next` field — keep fetching until null. Use `page_size=500` to minimize requests.

## Import

Send theme first, then sets in batches of 250:

```
entities_upsert(collection_id=COLLECTION_ID, items=[theme_entity])
entities_upsert(collection_id=COLLECTION_ID, items=[...sets batch 1...])
```
