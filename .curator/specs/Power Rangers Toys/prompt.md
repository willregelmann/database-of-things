# Power Rangers Toys Curator

Fetch Power Rangers toy data from grnrngr.com and import it into the database.

## Data Source

GrnRngr (https://www.grnrngr.com) — a fan-maintained Power Rangers collector reference.

No API key required. Use `User-Agent: Power Rangers Collector Database Bot (Educational/Personal Project)`.

Toy listings by season: `https://www.grnrngr.com/toys/power-rangers/{season_slug}`

## Seasons

| Slug | Full Name |
|---|---|
| mighty-morphin | Mighty Morphin Power Rangers |
| zeo | Power Rangers Zeo |
| turbo | Power Rangers Turbo |
| in-space | Power Rangers in Space |
| lost-galaxy | Power Rangers Lost Galaxy |
| lightspeed-rescue | Power Rangers Lightspeed Rescue |
| time-force | Power Rangers Time Force |
| wild-force | Power Rangers Wild Force |
| ninja-storm | Power Rangers Ninja Storm |
| dino-thunder | Power Rangers Dino Thunder |
| spd | Power Rangers SPD |
| mystic-force | Power Rangers Mystic Force |
| operation-overdrive | Power Rangers Operation Overdrive |
| jungle-fury | Power Rangers Jungle Fury |
| rpm | Power Rangers RPM |
| samurai | Power Rangers Samurai |
| megaforce | Power Rangers Megaforce |
| dino-charge | Power Rangers Dino Charge |
| ninja-steel | Power Rangers Ninja Steel |
| beast-morphers | Power Rangers Beast Morphers |
| dino-fury | Power Rangers Dino Fury |
| cosmic-fury | Power Rangers Cosmic Fury |

## Hierarchy

```
Power Rangers Toys (top-level collection — this is COLLECTION_ID)
└── Season (collection)  e.g. "Mighty Morphin Power Rangers"
    └── Toy (action_figure)  e.g. "Red Ranger 5" Action Figure"
```

## Page Structure

Each season page has:
- `<h2>` headers for assortment groups (e.g. "5" Action Figures", "Deluxe Zords")
- Under each `<h2>`: a `<ul>` list of items
- Each `<li>` contains: item number, name, year in brackets `[1993]`, and optional links (View Photo, Browse eBay, etc.)

**Parse each `<li>`**:
1. Extract item number (leading digits before the name)
2. Clean the name: strip item number, remove `[year]` brackets, `<small>` annotations, "View Photo", "Browse eBay", "Buy Item", "Instructions (PDF)" links
3. Extract year from `[Fall 1993]` or `[1993]` pattern
4. Find "View Photo" link href for the image URL — if present, that's the direct image URL; if not, try `https://www.grnrngr.com/toys/pictures/bandai/{item_number:05d}.jpg`

## Entity Schemas

### Season (type: "collection", category: "figures")

```json
{
  "name": "Mighty Morphin Power Rangers",
  "type": "collection",
  "category": "figures",
  "source_url": "https://www.grnrngr.com/toys/power-rangers/mighty-morphin",
  "external_ids": {
    "grnrngr_season_slug": "mighty-morphin"
  }
}
```

Season parent = COLLECTION_ID.

### Toy (type: "action_figure", category: "figures")

```json
{
  "name": "Red Ranger 5\" Action Figure",
  "type": "action_figure",
  "category": "figures",
  "year": 1993,
  "image_url": "https://www.grnrngr.com/toys/pictures/bandai/00001.jpg",
  "source_url": "https://www.grnrngr.com/toys/power-rangers/mighty-morphin",
  "external_ids": {
    "grnrngr_item_number": "1"
  },
  "attributes": {
    "manufacturer": "Bandai America"
  },
  "parent": {
    "type": "collection",
    "external_ids": { "grnrngr_season_slug": "mighty-morphin" }
  }
}
```

## Rate Limiting

Wait 1 second between page fetches. The site is fan-run — be respectful.

## Import

Season first, then toys:

```
entities_upsert(collection_id=COLLECTION_ID, items=[season_entity, ...toys])
```
