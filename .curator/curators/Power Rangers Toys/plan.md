# Power Rangers Toys Curator Plan

## Collection
- **Type:** Action figures, Zords, Megazords, playsets, and accessories
- **Parent Collection ID:** `d183e3a9-4eb7-40a5-b264-526b9a03ec30` (Power Rangers franchise)
- **Organization:** Hierarchical by series (MMPR → Zeo → Turbo → etc.)

## Data Sources
- **Primary:** RangerWiki (https://powerrangers.fandom.com)
- **Authentication:** None required (public wiki)
- **Method:** Web scraping with Beautiful Soup

## Target Structure

```
Power Rangers (franchise)
├── Mighty Morphin Power Rangers (series)
│   ├── Red Ranger Action Figure (toy)
│   ├── Megazord (toy)
│   └── ...
├── Power Rangers Zeo (series)
│   ├── Gold Ranger Action Figure (toy)
│   └── ...
└── ...
```

## Import Workflow

1. **Fetch series list** from RangerWiki's toy category pages
2. **For each series:**
   - Create series entity if doesn't exist
   - Link series to Power Rangers franchise with "contains" relationship
3. **Scrape toy listings** for each series
4. **Parse toy data:**
   - Name, year, type (figure/zord/megazord/playset)
   - Image URL
   - Description
5. **Deduplicate** using composite key: `name + series + year`
6. **Import to database:**
   - Create entity for each toy
   - Link to series with "contains" relationship

## Deduplication Strategy

- **Key:** Composite of `name + series + year`
- **Method:** Check if entity exists with matching name, linked to series, with matching year
- **Rationale:** Same toy name can appear in different series or years (re-releases, variants)

## Data Model

**Series entity:**
```json
{
  "type": "series",
  "name": "Mighty Morphin Power Rangers",
  "year": 1993,
  "attributes": {
    "description": "The original Power Rangers series",
    "abbreviation": "MMPR"
  }
}
```

**Toy entity:**
```json
{
  "type": "toy",
  "name": "Red Ranger Action Figure",
  "year": 1993,
  "image_url": "https://...",
  "external_ids": {
    "rangerwiki": "Red_Ranger_Action_Figure"
  },
  "attributes": {
    "toy_type": "action_figure",
    "character": "Red Ranger",
    "manufacturer": "Bandai",
    "description": "5-inch articulated figure"
  }
}
```

## Technical Notes

- RangerWiki uses MediaWiki structure, may need to parse infoboxes
- Rate limiting: 1 request per second to be respectful
- Images hosted on Fandom CDN, can be linked directly or downloaded to Supabase storage
- Some toy pages may have incomplete data - import what's available
