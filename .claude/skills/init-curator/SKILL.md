---
name: init-curator
description: Initialize a new curator through interactive discovery session
---

# Initialize Curator

You are designing a curator agent for a collectibles database.

## Process

### 1. Ask Questions (One at a Time)

Use Socratic method like the brainstorming skill:

**Collection Scope:**
- What items belong in this collection?
- How are they organized? (flat list, hierarchical, multi-parent graph)

**Data Sources:**
- Where does data come from? (specific API, website to scrape, manual entry)
- What's the API endpoint or website URL?
- Is an API key required?

**Deduplication:**
- What makes items unique? (ID field, name+year, product number)
- How should duplicates be detected?

**Attributes & Metadata:**
- What attributes should we capture for each item?
- Examples: For video games (publisher, developers, platform), for cards (HP, rarity, card number)
- Should attributes be empty (relying only on relationships and external IDs)?
- Note: Dedicated columns (name, year, country, language, image_url, etc.) are already available

**Import Strategy:**
- Should this import incrementally or bulk fetch?
- What metadata is critical vs optional?

### 2. Create Artifacts

Create directory: `.curator/curators/{name}/`

**plan.md:**
```markdown
# {Name} Curator Plan

## Collection
- **Type:** {type of items}
- **Collection ID:** {uuid from database}
- **Organization:** {flat/hierarchical/graph}

## Data Sources
- **Primary:** {API or website URL}
- **Authentication:** {API key requirements}

## Import Workflow
1. Fetch data from {source}
2. Parse and transform
3. Deduplicate using {strategy}
4. Import to database
5. Link to collection

## Deduplication
- **Key:** {unique identifier field(s)}
- **Strategy:** {exact match / fuzzy / composite key}
```

**config.json:**
```json
{
  "collection_id": "uuid-here",
  "data_source": "https://api.example.com/v1",
  "requires_api_key": true,
  "dedup_field": "external_id"
}
```

**scripts/fetch_data.py:**
```python
#!/usr/bin/env python3
"""Fetch {items} from {source}."""

import os
import json
import requests
from pathlib import Path

API_URL = "https://api.example.com/v1"
OUTPUT_FILE = "fetched_data.json"

def fetch_items():
    """Fetch all items from API."""
    # Get API key from environment
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY not found in environment")

    headers = {"Authorization": f"Bearer {api_key}"}

    items = []
    page = 1

    while True:
        response = requests.get(
            f"{API_URL}/items",
            headers=headers,
            params={"page": page, "pageSize": 100}
        )
        response.raise_for_status()

        data = response.json()
        items.extend(data["items"])

        if not data.get("hasMore"):
            break
        page += 1

    return items

def main():
    print(f"Fetching items from {API_URL}...")
    items = fetch_items()

    # Save to file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(items, f, indent=2)

    print(f"✓ Fetched {len(items)} items → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
```

**scripts/import_items.py:**
```python
#!/usr/bin/env python3
"""Import fetched items into Supabase with image localization and embeddings."""

import argparse
import os
import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

# Auto-install dependencies if missing
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "supabase"
    ])
    from supabase import create_client, Client

# Add lib directory to path for shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))
from image_utils import ImageLocalizer
from embedding_utils import EmbeddingGenerator

FETCHED_FILE = "fetched_data.json"


class ItemImporter:
    """Import items to Supabase with best practices."""

    def __init__(self, supabase: Client, collection_id: str):
        self.supabase = supabase
        self.collection_id = collection_id
        self.image_localizer = ImageLocalizer(supabase)
        self.embedding_generator = EmbeddingGenerator()

        # Cache for parent entity lookups (if using hierarchies)
        self.parent_cache = {}

        # Track image validation results (for dry run)
        self.image_results = []

    def check_exists(self, external_id: str, id_field: str) -> Optional[str]:
        """Check if entity exists by external ID."""
        if not external_id:
            return None

        result = self.supabase.table("entities").select("id").eq(
            f"external_ids->>{id_field}",
            external_id
        ).execute()

        if result.data:
            return result.data[0]["id"]
        return None

    def update_parent_relationship(self, entity_id: str, new_parent_id: str, entity_name: str) -> str:
        """Update entity's parent relationship when hierarchy changes."""
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
            return f"Updated parent: {entity_name}"
        except Exception as e:
            # Relationship might already exist
            if '409' in str(e) or 'unique' in str(e).lower():
                return f"Re-linked: {entity_name} (relationship already exists)"
            raise

    def import_item(self, item_data: Dict) -> Tuple[bool, str]:
        """Import a single item with images and embeddings."""
        name = item_data.get("name")
        external_id = item_data.get("id")  # CUSTOMIZE: Your unique ID field

        # Check for duplicates
        existing_id = self.check_exists(external_id, "example_api")  # CUSTOMIZE: id_field
        if existing_id:
            # MAINTAIN MODE: Update relationship if parent changed
            message = self.update_parent_relationship(existing_id, self.collection_id, name)
            return True, message  # Return success, not skip!

        # Generate entity ID upfront (needed for storage paths)
        entity_id = str(uuid.uuid4())

        # Localize image if present
        image_url = None
        thumbnail_url = None
        external_image_url = item_data.get("imageUrl")  # CUSTOMIZE: field name

        if external_image_url:
            print(f"    Processing images for: {name}")

            # Capture validation result if in dry run
            if hasattr(self.image_localizer, 'image_validator') and self.image_localizer.image_validator:
                result = self.image_localizer.image_validator.validate_image(external_image_url)
                self.image_results.append(result)

            image_url, thumbnail_url = self.image_localizer.localize_image(
                external_image_url,
                entity_id
            )

            if not image_url:
                # Fallback to external URL if localization failed
                print(f"      ⚠️  Image localization failed, using external URL")
                image_url = external_image_url

        # Generate embedding for semantic search
        name_embedding = self.embedding_generator.generate_embedding(name)

        # Create entity with proper schema
        entity_data = {
            "id": entity_id,
            "name": name,
            "type": "card",  # CUSTOMIZE: "card", "toy", "figure", etc.
            "year": item_data.get("year"),  # Use dedicated column if available
            "language": item_data.get("language"),  # ISO 639-1 code
            "country": item_data.get("country"),  # ISO 3166-1 alpha-2
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "name_embedding": name_embedding,
            "source_url": item_data.get("sourceUrl"),
            "external_ids": {
                "example_api": external_id  # CUSTOMIZE: Your external system name
            },
            "attributes": {
                # CUSTOMIZE: Domain-specific metadata only
            }
        }

        # Remove None values
        entity_data = {k: v for k, v in entity_data.items() if v is not None}
        if entity_data.get("attributes"):
            entity_data["attributes"] = {k: v for k, v in entity_data["attributes"].items() if v is not None}
        else:
            entity_data["attributes"] = {}

        try:
            # Create entity
            self.supabase.table("entities").insert(entity_data).execute()

            # Link to collection
            self.supabase.table("relationships").insert({
                "from_id": self.collection_id,
                "to_id": entity_id,
                "type": "contains"
            }).execute()

            thumb_status = "with thumbnail" if thumbnail_url else "original only" if image_url else "no image"
            return True, f"✓ Imported: {name} - {thumb_status}"

        except Exception as e:
            return False, f"Error importing {name}: {str(e)}"

    def import_all(self, items: list) -> Tuple[int, int, int]:
        """Import all items with progress tracking."""
        created = 0
        updated = 0
        failed = 0

        total = len(items)
        for i, item in enumerate(items, 1):
            success, message = self.import_item(item)
            print(f"  [{i}/{total}] {message}")

            if success:
                # Distinguish between created and updated
                if "Updated parent" in message or "Re-linked" in message:
                    updated += 1
                else:
                    created += 1
            else:
                failed += 1

        return created, updated, failed


# NOTE: Configuration loading is now handled by load_environment_config() from curator_utils
# See the import_items.py template for usage:
#
# from curator_utils import load_environment_config
#
# CURATOR_NAME = "{Curator Name}"  # Use exact directory name
#
# def main():
#     parser.add_argument('--env', choices=['local', 'prod'], default='local')
#     args = parser.parse_args()
#
#     # Warn if using default
#     if not any(arg.startswith('--env') for arg in sys.argv):
#         print("⚠️  No --env specified, defaulting to local")
#
#     # Load environment-specific config
#     supabase_url, supabase_key, collection_id = load_environment_config(
#         CURATOR_NAME,
#         args.env
#     )


def load_fetched_data() -> list:
    """Load data from fetch script."""
    data_file = Path(__file__).parent.parent / FETCHED_FILE

    if not data_file.exists():
        print(f"Error: {FETCHED_FILE} not found")
        print("Run fetch_data.py first")
        sys.exit(1)

    with open(data_file) as f:
        return json.load(f)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Import items to Supabase database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate import without writing to database'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Item Importer")  # CUSTOMIZE: Collection name
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be written to database")
    print("=" * 60)
    print()

    # Load configuration
    supabase_url, supabase_key, collection_id = load_config()

    # Use mock or real client
    if args.dry_run:
        from dry_run_utils import MockSupabaseClient, ImageValidator, DryRunOutput
        supabase = MockSupabaseClient()
        image_validator = ImageValidator()
    else:
        supabase = create_client(supabase_url, supabase_key)
        image_validator = None

    # Load fetched data
    print("Loading fetched data...")
    items = load_fetched_data()
    print(f"Found {len(items)} items to import")
    print()

    # Import items
    if not args.dry_run:
        print("Loading embedding model: sentence-transformers/all-MiniLM-L6-v2")

    importer = ItemImporter(supabase, collection_id)

    # Pass validator to image localizer if present
    if image_validator:
        importer.image_localizer = ImageLocalizer(supabase, image_validator=image_validator)

    if not args.dry_run:
        print("✓ Model loaded\n")

    created, updated, failed = importer.import_all(items)

    print()
    print("=" * 60)

    # Generate dry run output
    if args.dry_run:
        output = DryRunOutput(supabase, importer.image_results)
        output.print_yaml(max_entities=3)
        output.save_json('dry_run_results.json')
        print(f"\n✓ Dry run complete. Full results saved to dry_run_results.json")
    else:
        print(f"✓ Complete:")
        print(f"  Created: {created}")
        print(f"  Updated (re-linked): {updated}")
        print(f"  Failed: {failed}")
        print(f"  Total processed: {created + updated}")

    print("=" * 60)


if __name__ == "__main__":
    main()
```

**scripts/validate.py:**
```python
#!/usr/bin/env python3
"""Validate imported data."""

import os
from supabase import create_client

def validate_collection(collection_id):
    """Check collection integrity."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    supabase = create_client(supabase_url, supabase_key)

    # Count items in collection
    result = supabase.table("relationships").select(
        "id", count="exact"
    ).eq("from_id", collection_id).eq("type", "contains").execute()

    total = result.count

    # Check for items missing images
    entities = supabase.table("relationships").select(
        "entities!relationships_to_id_fkey(id, name, image_url)"
    ).eq("from_id", collection_id).eq("type", "contains").execute()

    missing_images = [
        e["entities"]["name"]
        for e in entities.data
        if not e["entities"].get("image_url")
    ]

    print(f"Collection: {total} items")
    print(f"Missing images: {len(missing_images)}")

    if missing_images:
        print("\nItems without images:")
        for name in missing_images[:10]:
            print(f"  - {name}")
        if len(missing_images) > 10:
            print(f"  ... and {len(missing_images) - 10} more")

def main():
    collection_id = os.getenv("COLLECTION_ID")
    if not collection_id:
        raise ValueError("COLLECTION_ID required")

    validate_collection(collection_id)

if __name__ == "__main__":
    main()
```

### 3. Generate Working Scripts

**CRITICAL:** Scripts must be:
- Complete and executable
- Handle errors gracefully
- Install dependencies if missing
- Use environment variables for secrets
- Focus on DATA IMPORT (not just validation)

**Customize based on:**
- User's answers about data sources
- Actual API/website structure
- Deduplication strategy discussed

### 4. Create secrets.env Templates

Create **three** secrets files for environment separation:

**`.curator/curators/{name}/secrets.env.example`** (Shared config - API keys):
```bash
# {Name} Curator - Shared Configuration (All Environments)

# Data Source API Keys
API_KEY=your_api_key_here

# Note: Environment-specific configuration (Supabase credentials, Collection IDs)
# are in separate files:
# - secrets.local.env (for local development)
# - secrets.prod.env (for production)

# Optional: Runtime parameters (if needed)
# FETCH_LIMIT=10
```

**`.curator/curators/{name}/secrets.local.env.example`** (Local environment):
```bash
# {Name} Curator - Local Environment Configuration

# Collection ID for local Supabase
# Create collection entity first:
#   INSERT INTO entities (name, type) VALUES ('{Collection Name}', 'collection');
# Then paste the returned UUID here:
COLLECTION_ID=00000000-0000-0000-0000-000000000000
```

**`.curator/curators/{name}/secrets.prod.env.example`** (Production environment):
```bash
# {Name} Curator - Production Environment Configuration

# Collection ID for production Supabase
# Create collection entity first:
#   INSERT INTO entities (name, type) VALUES ('{Collection Name}', 'collection');
# Then paste the returned UUID here:
COLLECTION_ID=00000000-0000-0000-0000-000000000000
```

**Note:** Global Supabase credentials are in `.curator/secrets.local.env` and `.curator/secrets.prod.env`.
The `.curator/.gitignore` already excludes all `secrets.*.env` files from git.

### 5. Offer Dry Run Validation

After generating scripts, ask the user:

**"Would you like to test the curator with a dry run before finalizing? (recommended)"**

Options:
- **Yes** - Test with dry run before committing
- **No** - Skip to commit (user will test later)

**If user chooses Yes:**

1. **Check prerequisites:**
   ```bash
   # Verify all secrets files exist:
   # - .curator/secrets.local.env (global Supabase credentials)
   # - .curator/curators/<name>/secrets.env (API keys)
   # - .curator/curators/<name>/secrets.local.env (collection ID)
   # Check if FETCH_LIMIT should be set
   ```

2. **Run fetch script** (with small limit):
   ```bash
   cd .curator/curators/<name>
   export FETCH_LIMIT=10  # Small sample for testing
   python3 scripts/fetch_data.py
   ```
   - Show any errors encountered
   - Verify fetched_data.json was created

3. **Run dry run:**
   ```bash
   python3 scripts/import_items.py --dry-run --env=local
   ```
   - Show YAML summary output
   - Point user to dry_run_results.json for details
   - Note: --env flag defaults to local, but explicit is better

4. **Ask for confirmation:**
   "Does the hierarchy look correct?"

   Options:
   - **Yes** - Proceed to commit (step 6)
   - **No** - Abort, let user investigate issues
   - **Edit scripts** - Let user fix, then offer dry run again

**If user chooses No:**
- Proceed directly to commit (step 6)
- Remind user to test with `--dry-run` before real import

### 6. Commit the Curator

```bash
git add .curator/curators/{name}/
git commit -m "feat: add {name} curator

Discovery complete:
- Import plan documented
- Fetch/import scripts generated
- Deduplication strategy: {strategy}
- Data source: {source}"
```

## Important Notes

- Ask questions **one at a time** (Socratic method)
- Generate **complete, working code** (no placeholders)
- Scripts should **install dependencies** if missing
- Use **environment variables** for all secrets
- **Test the plan** mentally - would it actually work?

## Critical Requirements for Generated Scripts

All generated import scripts MUST follow these patterns (from `.curator/README.md`):

### REQUIRED

1. **Use Shared Libraries**:
   - Import `ImageLocalizer` from `.curator/lib/image_utils.py`
   - Import `EmbeddingGenerator` from `.curator/lib/embedding_utils.py`
   - Add lib directory to path: `sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))`

2. **Localize All Images**:
   - NEVER use external URLs directly in `image_url`
   - Always call `image_localizer.localize_image(external_url, entity_id)`
   - Generate `entity_id = str(uuid.uuid4())` BEFORE localizing images
   - Store both `image_url` and `thumbnail_url` in entity

3. **Generate Embeddings**:
   - Call `embedding_generator.generate_embedding(name)` for every entity
   - Store in `name_embedding` field
   - Initialize generator once in `__init__`, not per-item

4. **Follow Metadata Schema**:
   - Use dedicated columns: `year`, `language`, `country`, `image_url`, `thumbnail_url`
   - External IDs go in `external_ids` JSONB (for deduplication)
   - Domain-specific metadata goes in `attributes` JSONB
   - NEVER put universal fields in `attributes`

5. **Deduplicate via External IDs**:
   - Check `external_ids->>field_name` before creating entities
   - When duplicate found, UPDATE relationships instead of skipping
   - Track created vs updated counts separately

6. **Maintain Relationships (CRITICAL)**:
   - When entity exists, update its parent relationships
   - Delete old parent relationships, create new ones
   - Return success (not skip) when updating relationships
   - Track: created, updated, failed (not just imported/skipped)
   - Example: `update_parent_relationship(entity_id, new_parent_id, name)`

7. **Auto-Install Dependencies**:
   - Wrap imports in try/except
   - Use subprocess.check_call with `--break-system-packages`
   - Install: `supabase`, `requests`, `beautifulsoup4`, `pillow`, `lxml`

8. **Progress Tracking**:
   - Print `[i/total]` counters
   - Show success/skip/error for each item
   - Report final statistics

### Customization Instructions

When generating scripts, tell the user to customize:
- Entity type (`"card"`, `"toy"`, `"figure"`, etc.)
- External ID field name in `external_ids`
- Deduplication field name
- Year/language extraction (if available in source data)
- Relationship structure (flat vs hierarchical)

Refer user to `.curator/README.md` for complete best practices documentation.
