---
name: marvel-comics-curator
description: Curate Marvel Comics collections using the official Marvel Comics API. Use when importing comic series and issues with rich metadata including creators, publication dates, and cover images (66,480+ comics, 15,990+ series).
---

# Marvel Comics Curator

## Overview

Curate your Marvel Comics collection using the official Marvel Comics API. This skill discovers comic series and issues, manages the collection hierarchy, and keeps your database synchronized with Marvel's comprehensive comic metadata.

**Perfect for collectibles tracking**: 66,480+ comics, 15,990+ series, with rich metadata including creators, publication dates, and high-quality cover images.

**Works with**: `collectibles-manager` skill for database operations.

**Marvel Comics Entity ID**: `5b3a5e40-ddd1-4163-8032-c805c4a7a667`

## Database Schema

### Hierarchy Structure

```
Marvel Comics (franchise)
  └─ [Series Name] (collection)
      └─ [Series Name] #[Issue] (comic_issue)
          └─ [Variant covers] (comic_issue, variant relationship)
```

### Entity Types

**1. Franchise Entity** (`franchise`)
- **Name**: "Marvel Comics"
- **Year**: 1939
- **Attributes**: `publisher`, `description`

**2. Series/Collection Entity** (`collection`)
- **Name**: Series title with year (e.g., "Doomwar (2010)")
- **Year**: Start year of series
- **Country**: "US"
- **Image**: Series cover image URL
- **External IDs** (in `external_ids` column):
  - `marvel_series_id`: Marvel API series ID
- **Attributes** (in `attributes` column):
  - `publisher`: "Marvel Comics"

**3. Comic Issue Entity** (`comic_issue`)
- **Name**: Full issue title (e.g., "Doomwar (2010) #1")
- **Year**: Publication year
- **Country**: "US"
- **Image**: Cover image URL
- **External IDs** (in `external_ids` column):
  - `marvel_comic_id`: Marvel API comic ID
- **Attributes** (in `attributes` column):
  - `publisher`: "Marvel Comics"
  - `writer`: Primary writer's name

### Key Schema Principles

✅ **External IDs in dedicated column**: All API IDs live in the `external_ids` JSONB column, not nested in `attributes`

✅ **Minimal attributes**: Only store what matters for collectors - publisher and primary writer

✅ **Standard columns used**: `name`, `year`, `country`, `image_key` handle core metadata

✅ **Deduplication by external ID**: Use `marvel_series_id` and `marvel_comic_id` for checking if entities already exist

### Relationships

- **Franchise → Series**: `contains` relationship from "Marvel Comics" to series
- **Series → Issue**: `contains` relationship from series to individual issues
- **Issue → Variant**: `variant` relationship from base issue to variant covers

## Marvel API Configuration

### Authentication

The Marvel API requires MD5 hash authentication:

**Required credentials** (in `.env`):
```
MARVEL_COMICS_API_PUBLIC_KEY=your_public_key
MARVEL_COMICS_API_PRIVATE_KEY=your_private_key
```

**Authentication parameters**:
- `apikey`: Public key
- `ts`: Timestamp
- `hash`: MD5(ts + private_key + public_key)

### Available Endpoints

- **`/comics`**: Individual comic issues (66,480 available)
- **`/series`**: Comic series/collections (15,990 available)
- **`/characters`**: Marvel characters (1,564 available)
- **`/creators`**: Writers, artists, editors (6,562 available)
- **`/events`**: Major storyline events
- **`/stories`**: Story components

### API Limits

- Default limit: 20 results per request
- Maximum limit: 100 results per request
- Use pagination with `offset` parameter for larger datasets

## Scripts

### `test_marvel_api.py`

Explore the Marvel API and understand available data.

```bash
python3 test_marvel_api.py
```

**Features**:
- Tests API authentication
- Explores comics, series, characters, creators
- Shows sample data from each endpoint
- Validates credentials

### `import_comic.py`

Import specific comic series and issues.

```bash
# Import a specific issue
python3 import_comic.py "Doomwar" --issues 1

# Import multiple issues
python3 import_comic.py "Amazing Spider-Man" --start-year 1999 --issues 1,2,3

# Select specific series result if multiple matches
python3 import_comic.py "Spider-Man" --series-index 2 --issues 1-10
```

**Parameters**:
- `series_title`: Name of the series to search for
- `--start-year`: Filter series by start year (optional)
- `--issues`: Comma-separated list of issue numbers to import
- `--series-index`: Which search result to use (default: 0, first result)

**Features**:
- Automatically creates "Marvel Comics" franchise if needed
- Searches for series by title
- Shows multiple options if ambiguous
- Imports only specified issue numbers
- Deduplicates using external IDs
- Stores simplified metadata following schema

**What it does**:
1. Searches Marvel API for series matching title
2. Creates/finds "Marvel Comics" franchise entity
3. Creates series as `collection` entity
4. Creates each issue as `comic_issue` entity
5. Detects variants (titles with parentheses after issue number)
6. Links regular issues to series with `contains` relationship
7. Links variants to base issues with `variant` relationship
8. Stores external IDs in `external_ids` column
9. Stores minimal attributes: publisher and writer

## Usage Examples

### Import a Complete Mini-Series

```bash
# Import all issues of Doomwar (2010)
python3 import_comic.py "Doomwar" --issues 1,2,3,4,5,6
```

### Import First Issue of Long-Running Series

```bash
# Import Amazing Spider-Man (1999) #1
python3 import_comic.py "Amazing Spider-Man" --start-year 1999 --issues 1
```

### Handle Multiple Series with Same Name

```bash
# List all "Spider-Man" series
python3 import_comic.py "Spider-Man"

# Then select the correct one (e.g., series #2 in results)
python3 import_comic.py "Spider-Man" --series-index 2 --issues 1
```

## Query Examples

### Find all Marvel series

```sql
SELECT name, year
FROM entities
WHERE type = 'collection'
  AND external_ids ? 'marvel_series_id'
ORDER BY year DESC, name;
```

### Find all issues in a series

```sql
SELECT
    i.name as issue,
    i.year,
    i.attributes->>'writer' as writer
FROM entities s
JOIN relationships r ON r.from_id = s.id
JOIN entities i ON i.id = r.to_id
WHERE s.name = 'Doomwar (2010)'
  AND r.type = 'contains'
ORDER BY i.name;
```

### Find comics by writer

```sql
SELECT name, year
FROM entities
WHERE type = 'comic_issue'
  AND attributes->>'writer' = 'Jonathan Maberry'
ORDER BY year DESC, name;
```

### Get full hierarchy

```sql
WITH RECURSIVE hierarchy AS (
  SELECT id, name, type, 0 as level
  FROM entities
  WHERE name = 'Marvel Comics'

  UNION ALL

  SELECT e.id, e.name, e.type, h.level + 1
  FROM entities e
  JOIN relationships r ON r.to_id = e.id
  JOIN hierarchy h ON r.from_id = h.id
  WHERE r.type = 'contains'
)
SELECT
  REPEAT('  ', level) || name as hierarchy,
  type
FROM hierarchy
ORDER BY level, name;
```

## Common Operations

### Add a new series

```bash
python3 import_comic.py "Series Name" --issues 1
```

### Update existing series with new issues

```bash
# Import additional issues (duplicates are skipped)
python3 import_comic.py "Series Name" --issues 2,3,4
```

### Check if series exists

```sql
SELECT id, name
FROM entities
WHERE external_ids->>'marvel_series_id' = '9240';
```

## API Response to Database Mapping

### Series Data

**Marvel API Response**:
```json
{
  "id": 9240,
  "title": "Doomwar (2010)",
  "startYear": 2010,
  "endYear": 2010,
  "thumbnail": {
    "path": "http://i.annihil.us/u/prod/marvel/i/mg/b/80/4badb21d6821b",
    "extension": "jpg"
  }
}
```

**Database Storage**:
```sql
INSERT INTO entities (type, name, year, country, image_key, external_ids, attributes)
VALUES (
  'collection',
  'Doomwar (2010)',
  2010,
  'US',
  'http://i.annihil.us/u/prod/marvel/i/mg/b/80/4badb21d6821b.jpg',
  '{"marvel_series_id": "9240"}'::jsonb,
  '{"publisher": "Marvel Comics"}'::jsonb
);
```

### Comic Issue Data

**Marvel API Response**:
```json
{
  "id": 29948,
  "title": "Doomwar (2010) #1",
  "issueNumber": 1,
  "creators": {
    "items": [
      {"name": "Jonathan Maberry", "role": "writer"},
      {"name": "Will Conrad", "role": "penciller"}
    ]
  },
  "dates": [
    {"type": "onsaleDate", "date": "2010-02-17T00:00:00+0000"}
  ],
  "thumbnail": {
    "path": "http://i.annihil.us/u/prod/marvel/i/mg/4/10/5a2990f8184b9",
    "extension": "jpg"
  }
}
```

**Database Storage**:
```sql
INSERT INTO entities (type, name, year, country, image_key, external_ids, attributes)
VALUES (
  'comic_issue',
  'Doomwar (2010) #1',
  2010,
  'US',
  'http://i.annihil.us/u/prod/marvel/i/mg/4/10/5a2990f8184b9.jpg',
  '{"marvel_comic_id": "29948"}'::jsonb,
  '{"publisher": "Marvel Comics", "writer": "Jonathan Maberry"}'::jsonb
);
```

## Notes

- **External IDs**: Always stored in the dedicated `external_ids` column (JSONB), never in `attributes`
- **Deduplication**: Check `external_ids` column for marvel_series_id or marvel_comic_id before creating
- **Image URLs**: Stored directly as provided by API (not localized to storage yet)
- **Writer attribution**: Only primary writer stored in attributes
- **Country**: Always "US" for Marvel Comics
- **Variants**: Automatically detected by parentheses in title (e.g., "#4 (HEROIC AGE VARIANT)") and linked to base issue with `variant` relationship

## Future Enhancements

- [x] Import variant covers with `variant` relationships (✅ Complete)
- [ ] Localize cover images to Supabase storage
- [ ] Import character appearances
- [ ] Track collection status (owned/wanted)
- [ ] Bulk import entire series
- [ ] Sync with Marvel API for updates
