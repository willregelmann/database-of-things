# American Comics Curator

Fetch comic book series and issues from the Metron API and import them into the database.

## Credentials

- `METRON_USERNAME` and `METRON_PASSWORD` from `secrets.env`
- API uses HTTP Basic Auth: `Authorization: Basic base64(username:password)`

## Data Source

Metron (https://metron.cloud) — a community-maintained comic book database.

Key endpoints (all return paginated JSON):
- `GET https://metron.cloud/api/series/?name={name}` — search series by name
- `GET https://metron.cloud/api/series/{id}/` — series details (includes publisher)
- `GET https://metron.cloud/api/issue/?series_id={id}&page={n}` — issues in a series (paginated, 100/page)
- `GET https://metron.cloud/api/issue/{id}/` — full issue details (includes credits, cover image)

## Hierarchy

```
American Comics (top-level collection — this is COLLECTION_ID)
└── Series (collection)  e.g. "Monstress", "Saga", "Deadly Class"
    └── Issue (comic)   e.g. "Monstress #1", "Saga #25"
```

## What to Import

The scope is **American non-mainstream comics** — indie, Image, Dark Horse, BOOM!, IDW, Vault, AfterShock, etc. Not Marvel or DC (too large, handled separately if ever).

Good starting points:
- Award-winning series (Eisner, Harvey winners)
- Image Comics catalog
- Fan favorites: Saga, Monstress, Deadly Class, The Walking Dead, Invincible, Wytches, Black Science

When given a specific publisher or series name, fetch that. Otherwise, start with a curated list of notable series.

## Entity Schemas

### Series (type: "collection", category: "comics")

```json
{
  "name": "Monstress",
  "type": "collection",
  "category": "comics",
  "year": 2015,
  "source_url": "https://metron.cloud/series/{id}/",
  "external_ids": {
    "metron_series_id": "1234"
  },
  "attributes": {
    "publisher": "Image Comics"
  }
}
```

Series parent = COLLECTION_ID.

### Issue (type: "comic", category: "comics")

```json
{
  "name": "Monstress #1",
  "type": "comic",
  "category": "comics",
  "year": 2015,
  "image_url": "https://static.metron.cloud/media/issue/...",
  "source_url": "https://metron.cloud/issue/{id}/",
  "external_ids": {
    "metron_id": "45678"
  },
  "attributes": {
    "issue_number": "1",
    "publisher": "Image Comics",
    "writers": ["Marjorie Liu"],
    "artists": ["Sana Takeda"]
  },
  "parent": {
    "type": "collection",
    "external_ids": { "metron_series_id": "1234" }
  },
  "order": 1
}
```

**Issue name format**: `{series_name} #{number}` — e.g. "Saga #25".

**Credits**: Extract from `issue.credits` array. Each credit has `creator` (name string) and `role` (array of role objects with `name`). Classify:
- Writers: roles containing "writer" or "plotter"
- Artists: roles containing "artist", "pencil", "ink", or "color"

**Image**: Use `issue.image` (converts to string URL).

**Order**: Parse issue number as int if possible, otherwise omit.

## Pagination

Issues endpoint paginates at 100/page. Check `next` field in response — keep fetching until `next` is null.

## Import

Batch series first, then issues in groups of 250:

```
entities_upsert(collection_id=COLLECTION_ID, items=[...series...])
entities_upsert(collection_id=COLLECTION_ID, items=[...issues batch 1...])
entities_upsert(collection_id=COLLECTION_ID, items=[...issues batch 2...])
```

## Rate Limits

Metron asks for reasonable usage. Add a short delay (0.5s) between requests when fetching many issues.
