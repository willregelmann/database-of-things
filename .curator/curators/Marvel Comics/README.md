# Marvel Comics Curator

Autonomous data import agent for Marvel Comics individual issues from the Marvel API.

## Overview

- **Collection:** Marvel Comics (individual issues, all universes, first printings)
- **Data Source:** Marvel API (developer.marvel.com)
- **Organization:** Series → Issues (two-level hierarchy)
- **Deduplication:** Marvel API ID (`external_ids.marvel_api`)

## Setup

### 1. Get Marvel API Keys

1. Visit https://developer.marvel.com
2. Sign up for a free account
3. Create an application to get your API keys:
   - **Public Key** (shown in dashboard)
   - **Private Key** (shown in dashboard)

### 2. Configure Secrets

Copy the example file and add your keys:

```bash
cp secrets.env.example secrets.env
```

Edit `secrets.env` and add your Marvel API keys:

```bash
MARVEL_PUBLIC_KEY=your_actual_public_key
MARVEL_PRIVATE_KEY=your_actual_private_key
```

The Supabase credentials should be copied from your project's `.env.local` file.

### 3. Test Fetch (Small Batch)

Start with a small batch to test the API connection:

```bash
cd ".curator/curators/Marvel Comics"
source secrets.env
export FETCH_LIMIT=10  # Fetch only 10 comics for testing
python3 scripts/fetch_data.py
```

This will create `fetched_data.json` with 10 comics.

### 4. Test Import

Import the fetched comics:

```bash
source secrets.env
python3 scripts/import_items.py
```

Check the database to verify:
- Comics are created with proper metadata
- Cover images are localized to Supabase storage
- Thumbnails are generated
- Series collections are created
- Issues are linked to series with correct order

### 5. Full Import

Once testing succeeds, remove the limit to fetch more comics:

```bash
source secrets.env
unset FETCH_LIMIT  # Remove limit
python3 scripts/fetch_data.py  # Fetches up to 3000 requests/day
python3 scripts/import_items.py
```

## Import Strategy

### Phase 1: Initial Testing
- Fetch 10-100 comics
- Verify data quality
- Check image localization
- Test deduplication

### Phase 2: Incremental Import
- Marvel API rate limit: 3000 requests/day
- Each request gets 100 comics
- Can fetch ~290,000 comics/day (theoretical max)
- Practical: Fetch in batches of 1000-5000 comics

### Phase 3: Maintenance
- Run weekly to fetch new releases
- Re-run import to update existing comics (will skip duplicates)
- Backfill missing data as needed

## How It Works

### 1. Fetch (`fetch_data.py`)

- Authenticates with Marvel API using MD5 hash of timestamp + private + public keys
- Paginates through comics (100 per page)
- Filters for individual issues only (no graphic novels, variants)
- Extracts:
  - Comic ID, title, issue number
  - Series name and publication year
  - Writers and artists
  - Cover image URL
  - Source URL for attribution

### 2. Import (`import_items.py`)

- Groups comics by series
- Creates series collection entities (or reuses existing)
- For each comic:
  - **Deduplication:** Checks `external_ids.marvel_api`
  - **If exists:** Updates parent relationship (maintain mode)
  - **If new:**
    - Generates UUID
    - Localizes cover image to Supabase storage
    - Generates 300x300 WebP thumbnail
    - Creates embedding for semantic search
    - Creates entity with proper metadata
    - Links to series with `order` = issue number

## Metadata Structure

### Comic Issues (type: "comic")

**Dedicated columns:**
```python
{
  "name": "Amazing Spider-Man (1963) #121",  # Full title
  "type": "comic",
  "year": 1973,  # Publication year
  "image_url": "/storage/v1/object/public/images/originals/{uuid}.jpg",
  "thumbnail_url": "/storage/v1/object/public/images/thumbnails/{uuid}.webp",
  "name_embedding": [...],  # 384-dim vector for semantic search
  "source_url": "https://www.marvel.com/comics/issue/..."
}
```

**External IDs:**
```python
{
  "marvel_api": "12345"  # Marvel's numeric ID (for deduplication)
}
```

**Attributes:**
```python
{
  "writers": ["Gerry Conway"],
  "artists": ["Gil Kane", "John Romita Sr."],
  "issue_number": 121,
  "series_name": "Amazing Spider-Man (1963)"
}
```

### Series (type: "collection")

```python
{
  "name": "Amazing Spider-Man (1963)",
  "type": "collection",
  "year": 1963,  # Start year
  "attributes": {
    "start_year": 1963
  }
}
```

## Relationships

- **Marvel Comics collection** `contains` **Series**
- **Series** `contains` **Issues** (with `order` = issue number)

This allows:
- Browse all series: query relationships from Marvel Comics collection
- Browse issues in series: query relationships from series (ordered by issue number)
- Find specific issue: search by name or semantic search

## Troubleshooting

### "API error: Invalid credentials"
- Check your Marvel API keys in `secrets.env`
- Verify keys at https://developer.marvel.com

### "Rate limit exceeded"
- Marvel API allows 3000 requests/day
- Wait 24 hours or reduce `FETCH_LIMIT`

### "Image localization failed"
- Check Supabase storage is configured
- Verify `images` bucket exists
- Check network connectivity to Marvel's image CDN

### "Embedding model download"
- First run downloads `all-MiniLM-L6-v2` model (~80MB)
- Model is cached locally for future runs
- Requires internet connection on first run

## Advanced Usage

### Fetch Specific Date Range

Edit `fetch_data.py` and modify the API params:

```python
params.update({
    "dateRange": "2020-01-01,2024-12-31"  # YYYY-MM-DD format
})
```

### Fetch Specific Series

Edit `fetch_data.py` and add series filter:

```python
params.update({
    "series": "12345"  # Series ID from Marvel API
})
```

### Re-import with Updates

Simply re-run the import script. It will:
- Skip comics that already exist (deduplication)
- Update relationships if series changed
- Add new comics found in `fetched_data.json`

## See Also

- [Marvel API Documentation](https://developer.marvel.com/docs)
- [Curator Best Practices](../../README.md)
- [Image Localization](../../lib/image_utils.py)
- [Embedding Generation](../../lib/embedding_utils.py)
