# Labubu Curator Plan

## Collection
- **Type:** Labubu figures (Pop Mart designer toys)
- **Collection ID:** Runtime parameter (set via environment variable)
- **Organization:** Hierarchical (Series → Figures)
- **Scope:** Official Pop Mart releases from THE MONSTERS series, including collaborations

## Data Sources
- **Primary:** PopMart World (https://www.popmartworld.com)
- **Type:** Fan-operated archive of Pop Mart collections
- **Coverage:** Comprehensive catalog of The Monsters (Labubu) series
- **Authentication:** None required (public website)
- **Note:** Similar to Rebrickable for LEGO, this is a community-driven archive

## Import Workflow
1. **Fetch Series List** - Scrape PopMart World for all Labubu/THE MONSTERS series
   - Extract series names, URLs, release dates, and metadata
   - Runtime parameter: Optional series name filter via command-line argument
2. **Fetch Figures** - For each series, scrape figure details
   - Regular figures (typically 12 per series)
   - Secret figures (typically 1 per series)
   - Extract names, images, sizes
3. **Parse** - Extract figure metadata (name, series, size, secret status)
4. **Deduplicate** - Check by custom slug in `external_ids`
5. **Localize Images** - Download images and store in Supabase storage with thumbnails
6. **Generate Embeddings** - Create semantic search vectors for "Series - Figure" names
7. **Import** - Create series collections and figure entities with relationships
8. **Maintain** - Update relationships when re-running (figures can appear in multiple series)

## Deduplication
- **Primary Key:** Custom slug (series + figure name, e.g., "art-series-mona-lisa")
- **Strategy:** Check `external_ids->>'popmartworld_slug'` before creating
- **Fallback:** Semantic search on "Series Name - Figure Name" for variations
- **On Duplicate:** Update parent relationship (figure can belong to multiple series)

## Entity Schema

### Series Entities (Collections)
- `name` - Series name (e.g., "Art Series", "Camping Series")
- `type` - "collection"
- `year` - Release year extracted from date
- `image_url` - Series cover image (if available)
- `thumbnail_url` - 300x300 WebP thumbnail
- `source_url` - PopMart World series page URL

### Figure Entities
- `name` - Figure name (e.g., "Mona Lisa", "Hiking")
- `type` - "figure"
- `year` - Release year (from series)
- `image_url` - Localized figure image (Supabase storage)
- `thumbnail_url` - 300x300 WebP thumbnail
- `source_url` - PopMart World series page URL

### External IDs
```json
{
  "popmartworld_slug": "art-series-mona-lisa",  // Custom slug for deduplication
  "popmartworld_series_url": "/collection/art-series"  // Series reference
}
```

### Attributes
```json
{}
```

**Note:** Attributes are intentionally left empty. Series information is captured via relationships, and additional metadata can be added later if needed.

## Runtime Configuration

The curator accepts optional series name filter as command-line argument:

```bash
# Fetch all Labubu series
python3 scripts/fetch_data.py
python3 scripts/import_items.py

# Fetch specific series only
python3 scripts/fetch_data.py --series "Art Series"
python3 scripts/import_items.py --dry-run

# Test with limited figures
python3 scripts/fetch_data.py --limit 20
```

This allows importing specific series or testing with limited data without modifying configuration.

## Notes

- **Series Collections:** Series collection entities are created automatically during import
- **Hierarchical Structure:** Series (collection) → Figures (figure entities)
- **Image Storage:** All images localized to Supabase storage with thumbnails
- **Semantic Search:** Embeddings enable "find figures like X" queries
- **Re-run Safe:** Deduplication prevents duplicates, relationship updates maintain integrity
- **Secret Figures:** Marked with `is_secret: true` in attributes for special handling
- **Multi-series Figures:** Some figures may appear in multiple series (handled via many-to-many relationships)
