# Curator System

Autonomous data import agents for the collectibles database. Each curator handles a specific collection or data source.

## Overview

Curators are self-contained import systems that:
- Fetch data from external sources (APIs, web scraping)
- Transform and validate data
- Import items into the database with proper relationships
- Handle deduplication, image localization, and embedding generation
- Run autonomously with minimal human intervention

## Directory Structure

```
.curator/
├── README.md                        # This file
├── lib/                             # Shared utilities for all curators
│   ├── image_utils.py              # Image downloading, thumbnails, storage
│   └── embedding_utils.py          # Semantic search embedding generation
├── templates/                       # Template scripts for new curators
│   ├── fetch_data.py.template
│   └── import_items.py.template
└── curators/
    └── {Collection Name}/           # One directory per curator
        ├── README.md               # Curator documentation
        ├── config.json             # Configuration
        ├── plan.md                 # Import plan and strategy
        ├── secrets.env.example     # Environment variables template
        ├── fetched_data.json       # Output from fetch script
        └── scripts/
            ├── fetch_data.py       # Fetch data from source
            ├── import_items.py     # Import to database
            └── validate.py         # Validation (optional)
```

## Best Practices

These patterns emerged from real curator implementations and should be followed by all new curators.

### 1. Use Shared Libraries (REQUIRED)

**Always use** `.curator/lib/` utilities instead of reimplementing:

```python
# At the top of import_items.py
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))
from image_utils import ImageLocalizer
from embedding_utils import EmbeddingGenerator

# In your importer class
class MyImporter:
    def __init__(self, supabase):
        self.supabase = supabase
        self.image_localizer = ImageLocalizer(supabase)
        self.embedding_generator = EmbeddingGenerator()
```

**Why**: Consistent behavior, tested code, automatic improvements benefit all curators.

### 2. Localize All Images (REQUIRED)

**Never use external image URLs directly.** Always download to Supabase storage:

```python
def import_item(self, item_data):
    # Generate entity ID upfront (needed for storage paths)
    entity_id = str(uuid.uuid4())

    # Localize image with automatic thumbnail generation
    external_url = item_data.get("image_url")
    if external_url:
        image_url, thumbnail_url = self.image_localizer.localize_image(
            external_url,
            entity_id
        )

        # Fallback to external URL if localization fails
        if not image_url:
            print(f"  ⚠️  Image localization failed, using external URL")
            image_url = external_url
    else:
        image_url = None
        thumbnail_url = None
```

**What it does**:
- Downloads original → `/storage/v1/object/public/images/originals/{uuid}.jpg`
- Generates 300x300 WebP thumbnail → `/storage/v1/object/public/images/thumbnails/{uuid}.webp`
- Returns paths for both

**Benefits**:
- No broken external links
- Pre-generated thumbnails (90-95% size reduction)
- Consistent URL structure
- Works on Supabase Free Tier
- Automatic retry logic for flaky URLs

**Storage Structure**:
```
images/
  originals/
    {uuid}.jpg           # Full resolution (200-500 KB)
    {uuid}.png
  thumbnails/
    {uuid}.webp          # 300x300 WebP (20-50 KB, ~90% savings)
```

### 3. Generate Embeddings During Import (REQUIRED)

**Always generate embeddings** for semantic search:

```python
# Generate embedding for entity name
name_embedding = self.embedding_generator.generate_embedding(name)

# Store in entity
entity_data = {
    "name": name,
    "name_embedding": name_embedding,  # 384-dim vector
    # ... other fields
}
```

**Model Details**:
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Dimensions: 384
- Model size: ~80MB (one-time download, cached locally)
- Inference speed: ~5ms per text
- Quality: Optimized for short texts

**Why**: Enables semantic search immediately ("fire dragon pokemon" finds Charizard), no backfill needed.

### 4. Follow Metadata Schema (REQUIRED)

Use the correct fields based on the database schema:

**Dedicated Columns** (use these first):
```python
entity_data = {
    # REQUIRED
    "name": "Charizard",              # Display name
    "type": "card",                   # Entity type (card, toy, figure, etc.)

    # UNIVERSAL FIELDS (optional but recommended)
    "year": 1999,                     # For filtering/sorting
    "country": "US",                  # ISO 3166-1 alpha-2
    "language": "en",                 # ISO 639-1

    # IMAGES
    "image_url": "/storage/...",      # Supabase storage path (NOT external URL)
    "thumbnail_url": "/storage/...",  # Pre-generated thumbnail

    # METADATA
    "source_url": "https://...",      # Attribution/source page URL
    "name_embedding": [...],          # 384-dim vector for semantic search
}
```

**External IDs** (for deduplication):
```python
"external_ids": {
    "pokemontcg_io": "base1-4",       # External system IDs only
    "tcgplayer": "base1-4",
    "grnrngr": "3138"                 # Item/product numbers
}
```

**Attributes** (everything else):
```python
"attributes": {
    "manufacturer": "Bandai America",  # Domain-specific metadata
    "hp": 120,
    "description": "A fire-type Pokemon",
    "additional_images": [...]
}
```

**CRITICAL RULES**:
- ✅ Manufacturer → `attributes` (domain-specific, not universal)
- ✅ Item/product numbers → `external_ids` (for deduplication)
- ✅ Year → dedicated column (universal field for filtering/sorting)
- ✅ Language → dedicated column (ISO 639-1 code)
- ❌ **NEVER** put data in `attributes` if a dedicated column exists
- ❌ **NEVER** use external URLs for `image_url` (localize first)

### 5. Deduplicate via External IDs (REQUIRED)

**Always check** before creating entities:

```python
def check_exists(self, external_id: str, id_field: str) -> Optional[str]:
    """Check if entity exists by external ID."""
    if not external_id:
        return None

    result = self.supabase.table("entities").select("id").eq(
        f"external_ids->>{id_field}",  # JSONB path query
        external_id
    ).execute()

    if result.data:
        return result.data[0]["id"]
    return None

# Usage in import
existing_id = self.check_exists(item_number, "grnrngr")
if existing_id:
    print(f"  Skip: {name} (item #{item_number} already exists)")
    return False, "Skipped (duplicate)"
```

**Benefits**:
- Safe re-runs of import scripts
- Incremental imports (only new items)
- No duplicate entities
- Idempotent operations

### 6. Maintain Relationships (REQUIRED)

**Curators maintain collections over time**, not just create them. When you find an existing entity during import, you should **update its relationships** instead of skipping it.

**Problem**: Collection hierarchies change (e.g., flat → hierarchical restructuring). Existing items may be linked to old parent entities.

**Solution**: When an entity exists, update its parent relationships:

```python
def update_parent_relationship(self, entity_id: str, new_parent_id: str, entity_name: str) -> str:
    """
    Update entity's parent relationship when hierarchy changes.

    Critical for maintaining collections during restructuring.
    """
    # Find current parent relationships
    existing_rels = self.supabase.table("relationships").select("id,from_id").eq(
        "to_id", entity_id
    ).eq("type", "contains").execute()

    # Delete old parent relationships
    for rel in existing_rels.data:
        self.supabase.table("relationships").delete().eq("id", rel["id"]).execute()

    # Create new relationship to correct parent
    try:
        self.supabase.table("relationships").insert({
            "from_id": new_parent_id,
            "to_id": entity_id,
            "type": "contains"
        }).execute()
        return f"Updated parent: {entity_name} → new parent"
    except Exception as e:
        # Relationship might already exist
        if '409' in str(e) or 'unique' in str(e).lower():
            return f"Re-linked: {entity_name} (relationship already exists)"
        raise

# Usage in import
def import_item(self, item_data: Dict, parent_id: str) -> Tuple[bool, str]:
    """Import item with relationship maintenance."""
    name = item_data["name"]
    external_id = item_data.get("id")

    # Check if entity already exists
    existing_id = self.check_exists(external_id, "external_system")
    if existing_id:
        # MAINTAIN MODE: Update relationship if parent changed
        message = self.update_parent_relationship(existing_id, parent_id, name)
        return True, message  # Return success, not skip!

    # CREATE MODE: Create new entity
    entity_id = str(uuid.uuid4())
    # ... rest of creation logic
```

**Track created vs updated**:

```python
def import_all(self, items: list) -> Tuple[int, int, int]:
    """Import with separate tracking for created and updated."""
    created = 0
    updated = 0
    failed = 0

    for item in items:
        success, message = self.import_item(item, parent_id)

        if success:
            # Distinguish between created and updated
            if "Updated parent" in message or "Re-linked" in message:
                updated += 1
            else:
                created += 1
        else:
            failed += 1

    print(f"Created: {created}, Updated: {updated}, Failed: {failed}")
    return created, updated, failed
```

**Real-world example**: Power Rangers Toys curator had 2,419 toys linked to old series collections. After adding toy line entities, re-running the import updated all relationships:
- Before: 682 empty toy lines, 2,419 toys linked to series
- After: 0 empty toy lines, 2,419 toys re-linked to toy lines
- Result: Collection maintained with correct hierarchy

**Why**: Collections evolve. Curators should maintain them, not just create them once.

### 7. Cache Entity Lookups (RECOMMENDED)

For bulk imports with hierarchical data, **cache** repeated lookups:

```python
class MyImporter:
    def __init__(self, supabase):
        self.supabase = supabase
        self.series_cache = {}      # Cache series entities
        self.collection_cache = {}  # Cache collection entities
        self.image_localizer = ImageLocalizer(supabase)
        self.embedding_generator = EmbeddingGenerator()

    def get_or_create_series(self, series_name: str, year: Optional[int] = None) -> str:
        """Get or create series, with caching to avoid repeated queries."""
        # Check cache first
        cache_key = f"{series_name}_{year}"
        if cache_key in self.series_cache:
            return self.series_cache[cache_key]

        # Query database
        query = self.supabase.table("entities").select("id").eq("name", series_name).eq("type", "collection")
        if year:
            query = query.eq("year", year)
        result = query.execute()

        if result.data:
            series_id = result.data[0]["id"]
        else:
            # Create new series
            series_id = self.create_series(series_name, year)

        # Cache for next time
        self.series_cache[cache_key] = series_id
        return series_id
```

**Why**: Avoids N+1 queries during imports (10x-100x faster for large datasets).

### 8. Auto-Install Dependencies (REQUIRED)

**Always auto-install** missing packages at script startup:

```python
#!/usr/bin/env python3
"""Import script with auto-dependency installation."""

import sys

# Auto-install dependencies if missing
try:
    import requests
    from bs4 import BeautifulSoup
    from supabase import create_client
    from PIL import Image
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages",
        "requests", "beautifulsoup4", "supabase", "pillow", "lxml"
    ])
    import requests
    from bs4 import BeautifulSoup
    from supabase import create_client
    from PIL import Image
```

**Why**: Reduces friction, scripts work on first run, no manual pip installs needed.

### 9. Hierarchical Relationships (REQUIRED)

Follow **parent→child** direction for all relationship types:

**Standard Patterns**:
```python
# Collection contains items
self.supabase.table("relationships").insert({
    "from_id": collection_id,  # Parent
    "to_id": item_id,          # Child
    "type": "contains"
}).execute()

# Variant points to base item
self.supabase.table("relationships").insert({
    "from_id": variant_id,     # Variant
    "to_id": base_item_id,     # Base
    "type": "variant_of"
}).execute()

# Component is part of whole
self.supabase.table("relationships").insert({
    "from_id": component_id,   # Part
    "to_id": whole_id,         # Whole
    "type": "part_of"
}).execute()
```

**Advanced: Dual-Linking** (for multi-level hierarchies)

Link intermediate levels to both parent AND root collection:

```python
# Example: Toy line linked to BOTH series AND master collection

# Link to specific series (for browsing by show)
self.supabase.table("relationships").insert({
    "from_id": series_id,
    "to_id": toy_line_id,
    "type": "contains"
}).execute()

# Also link to master collection (for browsing all toys)
self.supabase.table("relationships").insert({
    "from_id": master_collection_id,
    "to_id": toy_line_id,
    "type": "contains"
}).execute()
```

**Why**: Enables flexible browsing (filter by specific series OR view all items in master collection).

### 10. Ordered Relationships (OPTIONAL)

Use the `order` column for sortable collections:

```python
self.supabase.table("relationships").insert({
    "from_id": collection_id,
    "to_id": item_id,
    "type": "contains",
    "order": 42  # Position in collection (e.g., card number)
}).execute()
```

**IMPORTANT**: The `relationships` table has **NO** `attributes` column (removed in migration `20251024195010`). All relationship metadata must use dedicated columns like `order`.

### 11. Error Handling and Progress (REQUIRED)

**Show clear progress** during imports:

```python
def import_all_items(self, items: list):
    """Import all items with progress tracking."""
    imported = 0
    skipped = 0

    total = len(items)
    for i, item in enumerate(items, 1):
        success, message = self.import_item(item)
        print(f"  [{i}/{total}] {message}")

        if success:
            imported += 1
        else:
            skipped += 1

    print(f"\n✓ Complete: {imported} imported, {skipped} skipped")
    return imported, skipped
```

**Handle failures gracefully**:

```python
try:
    # Download and localize image
    if external_url:
        print(f"    📥 Downloading image...")
        image_url, thumbnail_url = self.image_localizer.localize_image(
            external_url,
            entity_id
        )

        if not image_url:
            # Fallback to external URL if localization failed
            print(f"    ⚠️  Image localization failed, using external URL")
            image_url = external_url
            thumbnail_url = None

except Exception as e:
    print(f"    ⚠️  Error during import: {e}")
    # Continue with import, just skip problematic parts
```

**Progress indicators**:
- Use emojis for visual clarity (📥 downloading, 📤 uploading, ✓ success, ⚠️ warning)
- Show counters: `[42/150]`
- Report final statistics

## Creating a New Curator

### Option 1: Use the Init Skill (Recommended)

```bash
/curator:init "Collection Name"
```

The skill will:
1. Ask Socratic questions about your collection and data sources
2. Generate complete working scripts following all best practices
3. Create all necessary files and documentation
4. Set up proper deduplication and metadata handling

### Option 2: Manual Creation

1. **Create directory**: `.curator/curators/{Collection Name}/`

2. **Copy templates**:
   ```bash
   cp .curator/templates/*.template .curator/curators/{Name}/scripts/
   # Rename and customize
   ```

3. **Document your approach**:
   - `plan.md`: Import strategy, hierarchy, deduplication
   - `README.md`: Collection-specific notes and lessons learned
   - `config.json`: Configuration and data sources

4. **Create scripts** following all best practices above

5. **Test locally** before committing

## Running a Curator

### Using the Run Command (Recommended)

```bash
/curator:run "Collection Name"
```

The run skill will:
- Validate curator exists
- Load configuration and secrets
- Execute fetch → import → validate workflow
- **Autonomously debug and fix errors**
- Report final results with statistics

### Manual Execution

```bash
cd ".curator/curators/Collection Name/scripts"

# Load environment
source ../secrets.env

# Fetch data from source
python3 fetch_data.py

# Review fetched data (optional)
head -50 ../fetched_data.json
jq '.[0]' ../fetched_data.json  # Inspect first item

# Import to database
python3 import_items.py

# Validate results (optional)
python3 validate.py
```

## Environment Variables

All curators should use these standard environment variables:

```bash
# Supabase (from ./bin/supabase status)
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_KEY=your-service-role-key-from-supabase-status

# Collection
COLLECTION_ID=uuid-from-database

# Optional: API credentials
API_KEY=your-api-key-here
API_SECRET=your-secret-here
```

**Security**:
- Store secrets in `secrets.env` (never commit to git)
- Provide `secrets.env.example` as template
- `.curator/.gitignore` should include `secrets.env`

## Testing and Validation

### Before First Run

1. **Test fetch script** on small dataset:
   ```python
   # In fetch_data.py, add limit during development
   items = fetch_items(limit=10)  # Test with 10 items first
   ```

2. **Validate data structure**:
   ```bash
   python3 fetch_data.py
   jq '.[0] | keys' fetched_data.json  # See available fields
   jq 'length' fetched_data.json       # Count items
   ```

3. **Test import** with subset:
   ```python
   # In import_items.py, limit during testing
   items = load_fetched_data()[:10]  # Import only 10 items
   ```

### Dry Run Mode

Test curator scripts without writing to the database.

**Usage:**
```bash
cd ".curator/curators/{Collection Name}"
source secrets.env
export FETCH_LIMIT=10  # Limit for testing
python3 scripts/fetch_data.py
python3 scripts/import_items.py --dry-run
```

**What it does:**
- ✅ Runs all import logic (parsing, validation, hierarchy building)
- ✅ Validates image URLs are accessible (HEAD request)
- ✅ Skips: Database writes, image downloads, embedding generation
- ✅ Outputs: YAML summary + complete JSON file

**Output:**
- Terminal: YAML summary with hierarchy (limited to first 3 entities)
- File: `dry_run_results.json` with complete results

**Use cases:**
- Test new curator after init
- Validate data structure before full import
- Debug hierarchy issues
- Check image accessibility

### After Import

1. **Check counts**:
   ```sql
   -- Count entities by type
   SELECT type, COUNT(*) FROM entities GROUP BY type;

   -- Count items in collection
   SELECT COUNT(*) FROM relationships
   WHERE from_id = 'collection-uuid' AND type = 'contains';
   ```

2. **Verify images and thumbnails**:
   ```sql
   SELECT name, image_url, thumbnail_url
   FROM entities
   WHERE type = 'toy'
     AND image_url IS NOT NULL
   LIMIT 10;

   -- Check for missing thumbnails
   SELECT COUNT(*) FROM entities
   WHERE image_url IS NOT NULL
     AND thumbnail_url IS NULL;
   ```

3. **Test semantic search**:
   ```sql
   -- Text-based semantic search
   SELECT * FROM search_by_text('fire dragon pokemon', 'card', 10);

   -- Check embedding coverage
   SELECT COUNT(*) FROM entities WHERE name_embedding IS NOT NULL;
   ```

## Troubleshooting

### Common Issues

**Missing Dependencies**:
```bash
# Auto-install should handle this, but if manually needed:
pip install --break-system-packages requests beautifulsoup4 supabase pillow sentence-transformers lxml
```

**Supabase Not Running**:
```bash
./bin/supabase start
./bin/supabase status  # Verify all services healthy
```

**Image Upload Fails (409 Conflict)**:
- Normal if re-running imports
- Image already exists in storage
- ImageLocalizer handles this gracefully
- Not an error, will skip and continue

**Embedding Generation Slow on First Run**:
- First run downloads ~420MB model (one-time)
- Cached in `~/.cache/torch/sentence_transformers/`
- Subsequent runs are fast (~5ms per text)
- This is expected behavior

**Duplicate Items Created**:
- Check your deduplication logic
- Ensure `external_ids` are set correctly
- Query duplicates:
  ```sql
  SELECT external_ids->>'your_field', COUNT(*)
  FROM entities
  GROUP BY external_ids->>'your_field'
  HAVING COUNT(*) > 1;
  ```

### Debugging Failed Imports

1. **Read the full error message** (don't skip stack traces!)

2. **Check environment variables**:
   ```bash
   echo $SUPABASE_URL
   echo $SUPABASE_SERVICE_KEY
   echo $COLLECTION_ID
   # None should be empty
   ```

3. **Test database connection**:
   ```python
   from supabase import create_client
   supabase = create_client(supabase_url, supabase_key)
   result = supabase.table("entities").select("count", count="exact").limit(1).execute()
   print(f"✓ Database accessible: {result.count} total entities")
   ```

4. **Inspect fetched data**:
   ```bash
   jq '.[0] | keys' fetched_data.json           # See structure
   jq 'map(.name) | unique | length' fetched_data.json  # Check uniqueness
   jq '.[0]' fetched_data.json                  # First item details
   ```

5. **Check Supabase Storage**:
   ```bash
   # View bucket via Studio UI
   open http://127.0.0.1:54323
   # → Storage → images → check originals/ and thumbnails/
   ```

## Examples

See existing curators for reference implementations:

### Power Rangers Toys
`.curator/curators/Power Rangers Toys/`

**Demonstrates**:
- Web scraping with BeautifulSoup
- Hierarchical structure (franchise → series → toy lines → toys)
- Image localization with alternate URL patterns
- Dual-linking pattern (toy lines linked to both series AND master collection)
- Complete documentation with lessons learned
- Embedding generation for all entities
- Proper metadata schema usage

**Key Files**:
- `README.md` - Complete documentation
- `scripts/fetch_data.py` - Web scraping patterns
- `scripts/import_items.py` - Full import with all best practices

Each curator's README documents specific patterns and lessons learned from that implementation.

## Contributing

When creating a new curator:

1. ✅ **Follow all best practices** listed above (especially REQUIRED items)
2. ✅ **Use shared libraries** (`ImageLocalizer`, `EmbeddingGenerator`)
3. ✅ **Document your approach** in curator's README
4. ✅ **Test with small dataset** before full import
5. ✅ **Commit working scripts** (no placeholders or TODOs)
6. ✅ **Add lessons learned** to your README

**If you discover a new pattern or fix a common issue**, update this document so future curators benefit.

## Future Improvements

Potential enhancements to the curator system:

- [ ] Incremental update detection (import only new/changed items)
- [ ] Parallel image downloads (ThreadPoolExecutor)
- [ ] Automatic data quality reports (missing fields, image coverage, etc.)
- [ ] Retry logic with exponential backoff for flaky APIs
- [ ] Rate limiting middleware for APIs
- [ ] Delta imports (compare with existing data, update only changes)
- [ ] Automated testing framework for curators
- [ ] CLI tool for curator management (`curator new`, `curator run`, `curator validate`)
- [ ] Batch embedding generation for better performance
- [ ] Image format optimization (auto-convert HEIC, handle SVG, etc.)
