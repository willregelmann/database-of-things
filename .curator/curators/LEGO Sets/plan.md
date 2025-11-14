# LEGO Sets Curator Plan

## Collection
- **Type:** LEGO sets
- **Collection ID:** Runtime parameter (set via environment variable)
- **Organization:** Hierarchical (Theme → Sets)

## Data Sources
- **Primary:** Rebrickable API v3 (https://rebrickable.com/api/v3/lego/sets/)
- **Authentication:** API key (free registration at rebrickable.com)
- **Coverage:** Comprehensive LEGO database with 800,000+ parts, daily updates

## Import Workflow
1. **Lookup Theme** - Query `/lego/themes/` to get theme ID from theme name
   - Search for matching theme by name
   - Extract `theme_id` for filtering
2. **Fetch Sets** - Query `/lego/sets/?theme_id={id}` for sets in theme
   - Paginate with `page_size=1000` (max)
   - Runtime parameter: `THEME_NAME` environment variable
3. **Parse** - Extract set metadata (name, year, pieces, images)
4. **Deduplicate** - Check by `set_num` in `external_ids`
5. **Localize Images** - Download `set_img_url` and store in Supabase storage with thumbnails
6. **Generate Embeddings** - Create semantic search vectors for set names
7. **Import** - Create entities with relationships to theme collection
8. **Maintain** - Update relationships when re-running (items can move themes)

## Deduplication
- **Primary Key:** `set_num` (Rebrickable set identifier, e.g., "10497-1")
- **Strategy:** Check `external_ids->>'rebrickable_set_num'` before creating
- **On Duplicate:** Update parent relationship (set can belong to new theme/subtheme)

## Entity Schema

### Dedicated Columns
- `name` - Set name (e.g., "Galaxy Explorer")
- `type` - "lego_set"
- `year` - Release year
- `image_url` - Localized box art image (Supabase storage)
- `thumbnail_url` - 300x300 WebP thumbnail
- `source_url` - Rebrickable set page URL

### External IDs
```json
{
  "rebrickable_set_num": "10497-1",  // Rebrickable set_num (primary key)
  "rebrickable_theme_id": "186"      // Theme ID for reference
}
```

### Attributes (Minimal)
```json
{
  "pieces": 1254
}
```

## Runtime Configuration

The curator accepts a theme filter at runtime:

```bash
export THEME_NAME="Space"  # Or "Star Wars", "City", "Technic", etc.
python3 scripts/fetch_data.py
python3 scripts/import_items.py
```

This allows importing different themes without modifying code.

## Notes

- **Theme Collections:** Create theme collection entities manually before running curator
- **Hierarchical Structure:** Theme (collection) → Sets (lego_set entities)
- **Image Storage:** All images localized to Supabase storage with thumbnails
- **Semantic Search:** Embeddings enable "find sets like X" queries
- **Re-run Safe:** Deduplication prevents duplicates, relationship updates maintain integrity
