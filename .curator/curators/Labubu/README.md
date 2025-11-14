# Labubu Curator

Autonomous importer for Pop Mart Labubu figures from THE MONSTERS series.

## Overview

This curator fetches and imports Labubu figures from [PopMart World](https://www.popmartworld.com), a fan-operated archive of Pop Mart collections (similar to Rebrickable for LEGO).

**Scope:** Official Pop Mart releases from THE MONSTERS series, including collaborations

**Organization:** Hierarchical (Series → Figures)

## Quick Start

1. **Configure secrets**

```bash
cd .curator/curators/Labubu
cp secrets.env.example secrets.env
# Edit secrets.env and set COLLECTION_ID
```

2. **Create main collection entity** (if not exists)

```sql
INSERT INTO entities (name, type) VALUES ('THE MONSTERS', 'collection');
-- Copy the returned UUID to COLLECTION_ID in secrets.env
```

3. **Fetch data**

```bash
# Load both global and curator-specific secrets
set -a && source ../../secrets.env && source secrets.env && set +a

# Fetch all Labubu series
python3 scripts/fetch_data.py
```

4. **Test with dry run**

```bash
python3 scripts/import_items.py --dry-run
```

5. **Import to database**

```bash
python3 scripts/import_items.py
```

## Usage

### Fetch Data

```bash
# Fetch all series
python3 scripts/fetch_data.py

# Fetch specific series only
python3 scripts/fetch_data.py --series "Art Series"

# Fetch limited number of series (testing)
python3 scripts/fetch_data.py --limit 3
```

### Import Items

```bash
# Dry run (no database changes)
python3 scripts/import_items.py --dry-run

# Live import
python3 scripts/import_items.py
```

### Validate Data

```bash
# Check consistency after import
python3 scripts/validate.py
```

## Data Structure

### Series (Collections)
- Type: `collection`
- Example: "Art Series", "Camping Series", "Coca Cola Series"
- Metadata: Release date, size range
- Created automatically during import

### Figures (Entities)
- Type: `figure`
- Example: "Mona Lisa", "Hiking", "Girl with a Pearl Earring"
- Images localized to Supabase storage
- Thumbnails generated (300x300 WebP)
- Embeddings for semantic search
- Series relationship captured via `contains` relationship

### Relationships
- Series → Figures (`contains` relationship)
- Main Collection → Series (`contains` relationship)
- Supports many-to-many (figures can appear in multiple series)

## Deduplication

**Strategy:** External ID with semantic search fallback

1. **Primary:** Check `external_ids->>'popmartworld_slug'` (custom slug: `series-name-figure-name`)
2. **Fallback:** Semantic search on "Series Name - Figure Name" (95% similarity threshold)
3. **On duplicate:** Update parent relationships (figures can belong to multiple series)

## Metadata Schema

### External IDs
```json
{
  "popmartworld_slug": "art-series-mona-lisa",
  "popmartworld_series_url": "/collection/art-series"
}
```

### Attributes
```json
{}
```

Attributes are intentionally left empty. Series information is captured via relationships.

## Data Source

**PopMart World** (https://www.popmartworld.com)
- Fan-operated archive of Pop Mart collections
- No API (web scraping required)
- Rate limited: 2 requests/second
- Coverage: Comprehensive catalog of THE MONSTERS series

## Re-running

Safe to re-run curator to add new releases:
- Existing figures are detected by external ID
- Relationships updated if figures move between series
- New series and figures added automatically
- Images only downloaded if missing

## Troubleshooting

**"COLLECTION_ID not found"**
- Create main collection entity first (see Quick Start step 2)

**"SUPABASE_URL not found"**
- Load global secrets: `set -a && source ../../secrets.env && set +a`

**Web scraping fails**
- PopMart World may have changed their HTML structure
- Check fetch_data.py and update selectors if needed

**Missing images/thumbnails**
- Run import again - only missing images will be downloaded
- Check Supabase storage bucket permissions

## Files

- `plan.md` - Curator design and approach
- `config.json` - Configuration and metadata
- `secrets.env.example` - Template for secrets
- `scripts/fetch_data.py` - Web scraper for PopMart World
- `scripts/import_items.py` - Database importer with deduplication
- `scripts/validate.py` - Data consistency validator

## Notes

- Web scraping is respectful (2 req/sec rate limit)
- PopMart World is a community archive (similar to Rebrickable)
- All images localized to Supabase storage
- Semantic search enabled via embeddings
- Secret figures marked with `is_secret: true`
