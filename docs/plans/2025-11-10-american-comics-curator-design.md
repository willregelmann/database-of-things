# American Comics Multi-Collection Curator Design

**Date:** 2025-11-10
**Status:** Approved for Implementation

## Overview

A multi-collection curator for American comic books organized by publisher, similar to how the video games curator organizes by platform. Replaces the Marvel-only curator after Marvel API deprecation.

## Problem Statement

The existing Marvel Comics curator relied on the Marvel API at developer.marvel.com, which appears to be deprecated (redirects to marvel.com with 301). Need a replacement data source that:

- Covers multiple publishers (not just Marvel)
- Has a sustainable, open API
- Provides comprehensive metadata and cover images
- Supports both curated imports and bulk imports

## Solution: Metron API

**Data Source:** Metron (metron.cloud)
- Community-driven, open-source comic book database
- REST API with Python wrapper (Mokkari)
- Creative Commons licensed data
- Free with reasonable rate limits
- Covers all major publishers: Marvel, DC, Image, Dark Horse, IDW, etc.

## Architecture

### Collection Hierarchy

Three-level hierarchy similar to video games curator:

```
Publisher Collections (top-level, independent)
├── Marvel Comics
│   ├── DOOMWAR (series collection)
│   │   ├── DOOMWAR #1 (comic entity)
│   │   ├── DOOMWAR #2
│   │   └── ...
│   ├── Loki: Agent of Asgard (series collection)
│   └── Ms. Marvel (2014) (series collection)
├── Image Comics
│   ├── Monstress (series collection)
│   ├── Saga (series collection)
│   └── The Walking Dead (series collection)
└── DC Comics
    └── Batman (2011) (series collection)
```

**Key Points:**
- Each publisher is an independent top-level collection
- No parent "American Comics" collection
- Series are nested collections within publishers
- Individual issues are comic entities

### Relationships

```
Publisher Collection (e.g., "Marvel Comics")
  └─ contains → Series Collection (e.g., "DOOMWAR")
       └─ contains → Comic Issue (e.g., "DOOMWAR #1")
                     └─ order = 1  ← Issue number
```

**Relationship Details:**
1. **Publisher → Series**: `contains` relationship, no order
2. **Series → Issue**: `contains` relationship with `order` column = issue number
   - Enables proper sorting: `ORDER BY order ASC`
   - Handles decimal issues (e.g., #12.1 → order: 12.1)

## Metadata Schema

### Comic Issues (type: "comic")

**Dedicated Columns:**
- `name`: Full title (e.g., "Monstress #1")
- `year`: Publication year
- `image_url`: Localized cover image path
- `thumbnail_url`: Localized thumbnail path
- `source_url`: Metron URL for attribution

**External IDs:**
```json
{
  "metron": "12345"
}
```

**Attributes:**
```json
{
  "publisher": "Image",
  "writers": ["Marjorie Liu"],
  "artists": ["Sana Takeda"]
}
```

### Series Collections (type: "collection")

**Dedicated Columns:**
- `name`: Series name with year (e.g., "Monstress (2015)")
- `year`: Start year

**Attributes:**
```json
{
  "publisher": "Image",
  "writers": ["Marjorie Liu"],
  "artists": ["Sana Takeda"]
}
```

### Publisher Collections (type: "collection")

**Dedicated Columns:**
- `name`: Publisher name (e.g., "Marvel Comics")
- `image_url`: Publisher logo (optional)

**Attributes:** _(empty)_

## Deduplication Strategy

- **Issues:** Check `external_ids.metron` before creating
- **Series:** Match by name (with year if specified)
- **Publishers:** Match by exact name

## Implementation Phases

### Phase C: Curated Series (Initial)

**Goal:** Import 10 hand-picked modern popular series to validate system

**Target Series:**
```python
TARGET_SERIES = [
    # User's personal collection
    {"name": "DOOMWAR", "publisher": "Marvel", "year": 2010},
    {"name": "Loki: Agent of Asgard", "publisher": "Marvel", "year": 2014},
    {"name": "Monstress", "publisher": "Image", "year": 2015},

    # Popular modern series
    {"name": "Saga", "publisher": "Image", "year": 2012},
    {"name": "The Walking Dead", "publisher": "Image", "year": 2003},
    {"name": "Invincible", "publisher": "Image", "year": 2003},
    {"name": "Ms. Marvel", "publisher": "Marvel", "year": 2014},
    {"name": "Hawkeye", "publisher": "Marvel", "year": 2012},
    {"name": "Batman", "publisher": "DC", "year": 2011},
    {"name": "Descender", "publisher": "Image", "year": 2015},
]
```

**Benefits:**
- Fast validation of data quality
- Tests multi-publisher functionality
- Immediate useful collection
- Easy to debug and iterate

### Phase A: Single Publisher (Expansion)

**Goal:** Import all series from one publisher (e.g., all Marvel)

**Changes:**
- Add `--publisher` flag to fetch script
- Remove hardcoded `TARGET_SERIES` list
- Fetch all series from Metron for specified publisher
- Add `--limit` flag for testing subsets

**Example:**
```bash
python3 fetch_data.py --publisher Marvel --limit 50
```

### Phase B: Multi-Publisher (Full Import)

**Goal:** Import everything from all major publishers

**Changes:**
- Add `--all-publishers` flag
- Iterate through: Marvel, DC, Image, Dark Horse, IDW, Boom, Dynamite, etc.
- Handle rate limiting with batching/pausing
- Track progress for resumability

## Import Workflow

### 1. Fetch Script (`fetch_data.py`)

```python
# Phase C implementation
for series_config in TARGET_SERIES:
    # Search Metron for series
    series = metron.series(
        name=series_config["name"],
        publisher=series_config["publisher"],
        year=series_config.get("year")
    )

    # Fetch all issues
    issues = metron.issues(series_id=series.id)

    # Save to fetched_data.json
```

**Output:** `fetched_data.json` with all series and issues

### 2. Import Script (`import_items.py`)

```python
# Load fetched data
data = load_fetched_data()

# Group by publisher → series
grouped = group_by_publisher_and_series(data)

for publisher_name, series_list in grouped.items():
    # Find or create publisher collection
    publisher = find_or_create_publisher(publisher_name)

    for series_name, issues in series_list.items():
        # Find or create series collection
        series = find_or_create_series(series_name, publisher)

        for issue_data in issues:
            # Check deduplication
            if exists_by_metron_id(issue_data["metron_id"]):
                continue  # Skip existing

            # Create new issue
            issue = create_issue(
                issue_data,
                localize_image=True,
                generate_thumbnail=True
            )

            # Link to series with order
            link_to_series(series, issue, order=issue_data["number"])
```

### 3. Re-run Capability

- Safe to run multiple times (deduplication prevents duplicates)
- Can add new series to `TARGET_SERIES` and re-run
- Maintains existing data, only adds new content

## Data Source Integration

### Metron API via Mokkari

**Installation:**
```bash
pip install mokkari
```

**Authentication:**
- Requires Metron account (free)
- API credentials stored in `secrets.env`

**Usage Example:**
```python
import mokkari

# Initialize client
m = mokkari.api(
    username="your_username",
    passwd="your_password"
)

# Search for series
series = m.series_list(params={"name": "DOOMWAR"})

# Get all issues
issues = m.issues_list(params={"series_id": series[0].id})
```

**Rate Limits:**
- Not aggressively limited (community-friendly)
- Built-in pagination support
- Automatic retry on errors

## Image Handling

**Cover Images:**
- Download from Metron CDN
- Localize to Supabase storage: `/storage/v1/object/public/images/originals/{uuid}.jpg`
- Generate 300x300 WebP thumbnails: `/storage/v1/object/public/images/thumbnails/{uuid}.webp`

**Missing Covers:**
- Some issues may not have cover images in Metron
- Import without image (null `image_url`)
- Can backfill from other sources later

## Success Criteria

### Phase C Complete When:
- [x] 10 target series fully imported
- [x] All 3 publishers created (Marvel, Image, DC)
- [x] Cover images localized and thumbnails generated
- [x] Series-issue relationships correct with proper ordering
- [x] Deduplication working (re-run doesn't create duplicates)

### Phase A Complete When:
- [ ] All series from one publisher imported
- [ ] `--publisher` and `--limit` flags working
- [ ] Rate limiting handled gracefully

### Phase B Complete When:
- [ ] All major publishers imported
- [ ] Progress tracking/resumability working
- [ ] Collection useful for end users

## Migration from Marvel API Curator

**Changes to existing curator:**
1. Rename directory: `Marvel Comics` → `American Comics`
2. Replace fetch script with Metron integration
3. Update import script for multi-publisher support
4. Keep existing `plan.md` and `README.md` as reference
5. Archive old Marvel API code

**Data Migration:**
- Existing Marvel comics data can stay (won't conflict)
- New imports will deduplicate against existing data
- Can manually link old Marvel issues to new publisher collection

## Open Questions

None - design is complete and approved.

## References

- Metron: https://metron.cloud/
- Mokkari Python wrapper: https://github.com/Metron-Project/mokkari
- Video games curator (reference implementation): `.curator/curators/NTSC Video Games/`
