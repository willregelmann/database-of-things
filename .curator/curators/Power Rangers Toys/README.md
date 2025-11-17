# Power Rangers Toys Curator

> **⚠️ COMPLIANCE WARNING**
>
> **Data Source:** GrnRngr.com (fan-run website)
>
> **Status:** ⚠️ Requires explicit permission
>
> **Issue:** No formal ToS or API. Website states it's "provided as a resource to all" but doesn't explicitly grant permission for automated scraping. Images are acknowledged to belong to respective copyright holders (Bandai America, Hasbro, etc.).
>
> **Current Approach:**
> - Using metadata only (item numbers, names, dates, manufacturers)
> - **NOT copying images** from GrnRngr directly
> - Need to source official product images from manufacturers or retailers
>
> **Required Actions:**
> - [ ] Contact GrnRngr webmaster (John Green) for explicit permission
> - [ ] Source images from official channels (Hasbro, Bandai America, retailers)
> - [ ] Document permission received before continuing imports
>
> See [compliance analysis document] for full details.

---

Autonomous data import system for Power Rangers toy collectibles from grnrngr.com.

## Overview

This curator automatically scrapes and imports Power Rangers toy data with a hierarchical structure:

```
Power Rangers (franchise)
├── Power Rangers Toys (collection) ← Master collection
│   ├── Power Rangers in Space (collection) ← TV series
│   │   ├── 3130 Morpher Assortment (collection) ← Toy line
│   │   │   ├── 3136 Astro Morpher (toy)
│   │   │   ├── 3137 Battlizer (toy)
│   │   │   └── 3138 Digimorpher (toy)
│   │   └── ...more toy lines...
│   └── ...more series...
└── ...other collections...
```

## Data Structure

### Hierarchy

**Four levels of organization:**

1. **Franchise** (`type: franchise`)
   - Power Rangers

2. **Master Collection** (`type: collection`)
   - Power Rangers Toys (contains all Power Rangers toy-related content)

3. **TV Series** (`type: collection`)
   - Power Rangers in Space, Ninja Storm, Operation Overdrive, etc.
   - Linked to: Power Rangers Toys collection
   - Represents the TV show the toys are based on

4. **Toy Lines** (`type: collection`)
   - 3130 Morpher Assortment, 2200 Mighty Morphin Power Rangers, etc.
   - Linked to: **BOTH** TV series AND Power Rangers Toys collection
   - Represents product assortments/releases from Bandai America

5. **Individual Toys** (`type: toy`)
   - 3138 Digimorpher, 2200 Jason Red Ranger, etc.
   - Linked to: Parent toy line only
   - The actual collectible items

### Metadata Structure

**Toy Lines** (collection):
```json
{
  "name": "3130 Morpher Assortment",
  "type": "collection",
  "external_ids": {
    "grnrngr_assortment": "3130"
  },
  "attributes": {
    "manufacturer": "Bandai America"
  },
  "source_url": "https://www.grnrngr.com/toys/power-rangers/in-space"
}
```

**Individual Toys**:
```json
{
  "name": "Digimorpher",
  "type": "toy",
  "year": 1998,
  "image_url": "/storage/v1/object/public/images/originals/uuid.jpg",
  "thumbnail_url": "/storage/v1/object/public/images/thumbnails/uuid.webp",
  "external_ids": {
    "grnrngr": "3138"
  },
  "attributes": {
    "manufacturer": "Bandai America"
  },
  "source_url": "https://www.grnrngr.com/toys/power-rangers/in-space"
}
```

**Key Design Decisions:**
- ✅ **Manufacturer in attributes** (not external_ids)
- ✅ **Item/assortment numbers in external_ids** (for deduplication)
- ✅ **Year at entity level** (universal field for filtering/sorting)
- ✅ **Pre-generated thumbnails** (for performance on free tier)
- ✅ **Dual-linking for toy lines** (browseable by series OR master collection)

## Scripts

### `fetch_data.py`

Scrapes toy data from grnrngr.com and organizes into toy lines.

**Usage:**
```bash
python3 scripts/fetch_data.py
```

**What it does:**
1. Iterates through configured season pages (`SEASON_TOYLINES` list)
2. Finds all `<h2>` headers (toy line assortments)
3. Extracts toy line metadata (assortment number, name, manufacturer, price)
4. Parses all `<li>` items under each assortment
5. Extracts individual toy data (item number, name, year, release date)
6. Saves to `fetched_data.json`

**Output format:**
```json
[
  {
    "series": "Power Rangers in Space",
    "assortment_number": "3130",
    "name": "3130 Morpher Assortment",
    "manufacturer": "Bandai America",
    "price": "$10.50",
    "source_url": "https://www.grnrngr.com/toys/power-rangers/in-space",
    "toys": [
      {
        "name": "Digimorpher",
        "item_number": "3138",
        "year": 1998,
        "release_date": "[Fall 1998]",
        "image_url": "https://www.grnrngr.com/toys/pictures/bandai/03138_1.jpg",
        "source_url": "https://www.grnrngr.com/toys/power-rangers/in-space"
      }
    ]
  }
]
```

### `import_items.py`

Imports fetched data into Supabase with proper hierarchy.

**Usage:**
```bash
# Requires environment variables:
export SUPABASE_URL="http://127.0.0.1:54321"
export SUPABASE_SERVICE_KEY="your-service-key"

python3 scripts/import_items.py
```

**What it does:**
1. Loads `fetched_data.json`
2. For each toy line:
   - Creates or finds TV series collection
   - Creates toy line collection
   - Links toy line to **both** series AND "Power Rangers Toys"
   - Imports individual toys under the toy line
3. Downloads external images → Supabase Storage
4. Generates 300x300 WebP thumbnails
5. Generates name embeddings for semantic search
6. Reports import statistics

**Deduplication:**
- Toy lines: By `external_ids.grnrngr_assortment`
- Individual toys: By `external_ids.grnrngr`

## Configuration

### Environment Variables

**Required for import:**
- `SUPABASE_URL` - Supabase API URL
- `SUPABASE_SERVICE_KEY` - Service role key (for admin operations)

**Optional:**
- Create `secrets.env` in curator directory with:
  ```bash
  SUPABASE_URL=http://127.0.0.1:54321
  SUPABASE_SERVICE_KEY=your-key-here
  ```

### Season List

Edit `SEASON_TOYLINES` in `scripts/fetch_data.py` to add/remove seasons:

```python
SEASON_TOYLINES = [
    "/toys/power-rangers/mighty-morphin",
    "/toys/power-rangers/zeo",
    "/toys/power-rangers/in-space",
    # ... add more seasons here
]
```

## Running the Curator

### Full Import

```bash
# 1. Fetch data from website
cd ".curator/curators/Power Rangers Toys/scripts"
python3 fetch_data.py

# 2. Review fetched data
head -100 ../fetched_data.json

# 3. Import to database
python3 import_items.py
```

### Partial Import (One Season)

```python
from fetch_data import GrnRngrScraper
import json

scraper = GrnRngrScraper()
toy_lines = scraper.scrape_season_page('/toys/power-rangers/in-space')

with open('test_data.json', 'w') as f:
    json.dump(toy_lines, f, indent=2)
```

## Changelog

### v2.0 - Hierarchical Structure (2025-11)

**BREAKING CHANGES:**
- Complete restructuring of data hierarchy
- Changed from flat toy list to nested toy line structure
- Updated metadata schema (manufacturer in attributes, IDs in external_ids)

**Additions:**
- Toy line (assortment) extraction and organization
- Dual-linking: toy lines appear under both series AND master collection
- Pre-generated thumbnail support
- Semantic search embedding generation
- Image localization to Supabase Storage

**Fixes:**
- Corrected year extraction (now pulls from actual data, not defaulting to 1993)
- Fixed h2/h3 tag confusion in scraper
- Proper handling of div elements between headers and lists
- Removed redundant `attributes` from toys (only manufacturer retained)

### v1.0 - Initial Version

- Basic scraping from grnrngr.com
- Flat toy import directly under series
- External image URLs (no localization)

## Troubleshooting

### Fetch Issues

**Problem:** `Found 0 toy lines`
- **Cause:** Website structure changed
- **Fix:** Inspect HTML with browser DevTools, update header tag selector in `scrape_season_page()`

**Problem:** Missing toys under toy line
- **Cause:** UL not found after H2
- **Fix:** Check `find_next()` vs `find_next_sibling()` usage

### Import Issues

**Problem:** `SUPABASE_URL and SUPABASE_SERVICE_KEY must be set`
- **Fix:** Run `./bin/supabase status` and set environment variables

**Problem:** Duplicate key errors
- **Cause:** Toy already exists with same `external_ids.grnrngr`
- **Expected:** Skipped items are logged, not errors

**Problem:** Image download failures
- **Cause:** External URLs changed or unavailable
- **Impact:** Falls back to external URL (not localized)

## Database Queries

### Find Toys by Year

```sql
SELECT name, year, source_url
FROM entities
WHERE type = 'toy' AND year = 1998
ORDER BY name;
```

### View Toy Line Contents

```sql
SELECT e.name, e.type, e.year
FROM entities e
JOIN relationships r ON r.to_id = e.id
WHERE r.from_id = (
  SELECT id FROM entities
  WHERE name = '3130 Morpher Assortment'
)
AND r.type = 'contains'
ORDER BY e.name;
```

### Check Dual-Linking

```sql
-- Toy lines should have 2 parents (series + master collection)
SELECT
  e.name as toy_line,
  COUNT(r.from_id) as parent_count,
  STRING_AGG(e_parent.name, ', ') as parents
FROM entities e
LEFT JOIN relationships r ON r.to_id = e.id AND r.type = 'contains'
LEFT JOIN entities e_parent ON r.from_id = e_parent.id
WHERE e.external_ids ? 'grnrngr_assortment'
GROUP BY e.id, e.name
HAVING COUNT(r.from_id) != 2;  -- Should return 0 rows if all correct
```

## Future Improvements

- [ ] Add variant tracking (1st Edition, Shadowless, etc.)
- [ ] Support for Japanese/International releases
- [ ] Automatic price tracking over time
- [ ] eBay integration for market values
- [ ] Barcode/UPC tracking
- [ ] Box/packaging image support
- [ ] Instruction manual PDFs
