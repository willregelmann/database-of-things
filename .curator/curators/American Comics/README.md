# American Comics Curator

Autonomous data import agent for curated American comic book series from Metron API.

## Overview

- **Collection:** American Comics (curated series from Marvel, DC, Image, and other publishers)
- **Data Source:** Metron API (metron.cloud)
- **Organization:** Series → Issues (two-level hierarchy)
- **Deduplication:** Metron Issue ID (`external_ids.metron_id`)

## Setup

### 1. Get Metron API Credentials

1. Visit https://metron.cloud/
2. Create a free account
3. Your username and password are your API credentials

### 2. Configure Secrets

Copy the example file and add your credentials:

```bash
cp secrets.env.example secrets.env
```

Edit `secrets.env` and add your Metron credentials:

```bash
METRON_USERNAME=your_username
METRON_PASSWORD=your_password
```

### 3. Test Fetch (Small Batch)

Test with a small batch using the `--limit` flag:

```bash
cd ".curator/curators/American Comics"
source secrets.env

# Fetch 10 issues from Monstress for testing
python3 scripts/fetch_data.py --series "Monstress" --limit 10
```

Or use the default test mode (fetches Monstress without limit):

```bash
python3 scripts/fetch_data.py
```

This will create `fetched_data.json` with the fetched issues.

### 4. Run Import via Claude

Use the curator-run command or natural language:

```bash
/curator:run "American Comics"
```

Or simply:
```
Import the American Comics collection
```

Claude will:
- Execute fetch_data.py
- Use semantic search to check for duplicates
- Create series collection entities
- Create comic issue entities with metadata
- Localize cover images to Supabase storage
- Generate embeddings for semantic search
- Link issues to series with proper ordering

### 5. Expand Collection

The fetch script supports flexible filtering via command-line arguments:

```bash
# Fetch multiple specific series
python3 scripts/fetch_data.py --series "Monstress" --series "Saga" --series "Invincible"

# Fetch all series from a publisher
python3 scripts/fetch_data.py --publisher "Image Comics"

# Combine with limit for testing
python3 scripts/fetch_data.py --publisher "Image Comics" --limit 50
```

**Claude/MCP Integration:**
When using `/curator:run`, Claude can pass filters to the fetch script:
- Specify series names: `--series "Monstress" --series "Saga"`
- Specify publisher: `--publisher "Image Comics"`
- Use limit for testing: `--limit 100`

## Import Strategy

The fetch script is flexible and supports different import strategies:

### Curated Series Import
- Specify series by name: `--series "Monstress" --series "Saga"`
- Best for personal collections or specific titles
- No rate limits enforced by Metron

### Publisher Import
- Fetch all series from a publisher: `--publisher "Image Comics"`
- Useful for comprehensive publisher collections
- Can be combined with `--limit` for testing

### Testing and Incremental Import
- Use `--limit N` to fetch only N issues total
- Allows testing API connection and data quality
- Can run incrementally to build collection over time

## How It Works

### 1. Fetch (`fetch_data.py`)

- Authenticates with Metron API using username/password via mokkari library
- Accepts command-line arguments:
  - `--series "Name"`: Fetch specific series (repeatable)
  - `--publisher "Name"`: Fetch all series from publisher
  - `--limit N`: Limit total issues fetched
- For each series:
  1. Search for series by name (optionally with publisher/year filters)
  2. Fetch all issues for that series
  3. For each issue, fetch full details including credits
- Extracts:
  - Issue ID, name, number
  - Series name and ID
  - Publication year
  - Publisher name
  - Writers and artists (from credits)
  - Cover image URL
  - Source URL for attribution
- Outputs to `fetched_data.json` in v2 format (with metadata wrapper)

### 2. Import (via Claude + MCP)

Claude uses MCP tools to:
1. Load fetched_data.json
2. Check for duplicates using `external_ids.metron_id`
3. Create or get series collection entities
4. For each comic issue:
   - Generate UUID
   - Localize cover image to Supabase storage
   - Generate 300x300 WebP thumbnail
   - Create embedding for semantic search
   - Create entity with proper metadata
   - Link to series with `order` = issue number

## Metadata Structure

### Comic Issues (type: "comic")

**Fetched data format:**
```json
{
  "id": 60339,
  "name": "Monstress #1",
  "series_name": "Monstress",
  "series_id": 4733,
  "issue_number": "1",
  "year": 2015,
  "publisher": "Image Comics",
  "writers": ["Marjorie Liu"],
  "artists": ["Sana Takeda"],
  "image_url": "https://static.metron.cloud/media/issue/...",
  "source_url": "https://metron.cloud/issue/60339/"
}
```

**Database entity:**
```python
{
  "name": "Monstress #1",
  "type": "comic",
  "year": 2015,
  "image_url": "/storage/v1/object/public/images/originals/{uuid}.jpg",
  "thumbnail_url": "/storage/v1/object/public/images/thumbnails/{uuid}.webp",
  "name_embedding": [...],  # 384-dim vector for semantic search
  "source_url": "https://metron.cloud/issue/60339/",
  "external_ids": {
    "metron_id": "60339"  # For deduplication
  },
  "attributes": {
    "series_name": "Monstress",
    "series_id": 4733,
    "issue_number": "1",
    "publisher": "Image Comics",
    "writers": ["Marjorie Liu"],
    "artists": ["Sana Takeda"]
  }
}
```

### Series (type: "collection")

```python
{
  "name": "Monstress",
  "type": "collection",
  "year": 2015,
  "attributes": {
    "publisher": "Image Comics",
    "metron_series_id": 4733
  }
}
```

## Relationships

- **American Comics collection** `contains` **Series**
- **Series** `contains` **Issues** (with `order` = issue number)

This allows:
- Browse all series: query relationships from American Comics collection
- Browse issues in series: query relationships from series (ordered by issue number)
- Find specific issue: search by name or semantic search

## Troubleshooting

### "Error: METRON_USERNAME and METRON_PASSWORD must be set"
- Check your credentials in `secrets.env`
- Verify you've sourced the file: `source secrets.env`
- Create account at https://metron.cloud/

### "Series not found in Metron"
- Verify series name, publisher, and year in `TARGET_SERIES`
- Try searching manually on metron.cloud
- Check for spelling variations or alternate titles

### "Image localization failed"
- Check Supabase storage is configured
- Verify `images` bucket exists
- Check network connectivity to Metron's CDN

### "Embedding model download"
- First run downloads `all-MiniLM-L6-v2` model (~80MB)
- Model is cached locally for future runs
- Requires internet connection on first run

## Data Quality

Based on test import of Monstress series:
- **Total comics**: 50+ issues
- **With images**: ~100% (Metron has excellent image coverage)
- **With years**: ~100% (cover dates reliably extracted)
- **With writers**: ~95% (most issues have credits)

## See Also

- [Metron API Documentation](https://metron.cloud/docs/api_v1.html)
- [Mokkari Python Library](https://github.com/Metron-Project/mokkari)
- [Curator Best Practices](../../README.md)
- [Image Localization](../../lib/image_utils.py)
