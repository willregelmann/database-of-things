# Marvel Comics Curator Plan

## Collection
- **Type:** Individual comic book issues
- **Collection ID:** `4201e80e-f081-4035-9dea-415f918a0881`
- **Organization:** Two-level hierarchy (Series → Issues)
- **Scope:** All Marvel universes, first printings only

## Data Sources
- **Primary:** Marvel API (developer.marvel.com)
- **Authentication:** API key required (public + private key)
- **Rate Limit:** 3000 requests/day
- **Endpoint:** `https://gateway.marvel.com/v1/public/comics`

## Import Workflow

1. **Fetch data from Marvel API**
   - Paginate through all comics (100 per page)
   - Extract series, issue number, title, creators, cover images
   - Respect rate limits (3000 requests/day)
   - Save to `fetched_data.json`

2. **Parse and transform**
   - Extract series name from comic data
   - Parse issue number
   - Extract creators (writers, artists)
   - Get cover image URL

3. **Deduplicate using Marvel API ID**
   - Check `external_ids.marvel_api` before creating
   - Skip if issue already exists
   - Update relationships if parent series changed

4. **Import to database**
   - Create or get series collection entity
   - Create comic issue entity with proper metadata
   - Localize cover images to Supabase storage
   - Generate embeddings for semantic search
   - Link issue to series with `order` = issue number

5. **Link to collection**
   - Link series to Marvel Comics collection
   - Link issues to series (using `order` for issue number)

## Deduplication
- **Key:** Marvel API `id` field
- **Strategy:** Exact match on `external_ids.marvel_api`
- **Fallback verification:** Series name + issue number

## Metadata Schema

### Comic Issues (type: "comic")
**Dedicated columns:**
- `name`: Full title (e.g., "Amazing Spider-Man (1963) #121")
- `year`: Publication year
- `image_url`: Localized cover image
- `thumbnail_url`: Localized thumbnail

**External IDs:**
- `marvel_api`: Marvel's numeric ID (primary key for deduplication)

**Attributes:**
- `writers`: Array of writer names
- `artists`: Array of artist names
- `issue_number`: Issue number (for display)
- `series_name`: Series title (for reference)

### Series (type: "collection")
**Dedicated columns:**
- `name`: Series name (e.g., "Amazing Spider-Man (1963)")
- `year`: Start year of series

**Attributes:**
- `start_year`: Year series began
- `end_year`: Year series ended (if applicable)

## Import Strategy

**Phase 1: Testing (subset)**
- Fetch 100-500 issues from popular series
- Validate data quality and image localization
- Test deduplication and relationship management

**Phase 2: Incremental (ongoing)**
- Fetch 3000 issues per day (API limit)
- Run daily to gradually build collection
- Track progress in fetched_data.json

**Phase 3: Maintenance**
- Weekly updates for new releases
- Backfill missing data
- Update cover images if improved versions available

## Rate Limit Handling

Marvel API allows 3000 requests/day:
- Each page of comics = 1 request (100 comics per page)
- Each series lookup = 1 request
- Budget: ~2900 comic pages/day = ~290,000 comics/day (unlikely to hit)
- Conservative: Fetch in batches of 1000 issues, pause between batches
