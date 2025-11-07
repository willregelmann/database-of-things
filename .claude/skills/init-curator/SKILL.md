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
"""Import fetched items into Supabase."""

import os
import json
from supabase import create_client

FETCHED_FILE = "fetched_data.json"

def load_fetched_data():
    """Load data from fetch script."""
    with open(FETCHED_FILE) as f:
        return json.load(f)

def import_to_database(items, collection_id):
    """Import items to Supabase."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")

    supabase = create_client(supabase_url, supabase_key)

    imported = 0
    skipped = 0

    for item in items:
        # Check if exists (deduplication)
        existing = supabase.table("entities").select("id").eq(
            "external_ids->>example_api", item["id"]
        ).execute()

        if existing.data:
            print(f"  Skip: {item['name']} (exists)")
            skipped += 1
            continue

        # Create entity
        entity = supabase.table("entities").insert({
            "name": item["name"],
            "type": "card",  # or appropriate type
            "external_ids": {"example_api": item["id"]},
            "attributes": item,
            "image_url": item.get("imageUrl")
        }).execute()

        entity_id = entity.data[0]["id"]

        # Link to collection
        supabase.table("relationships").insert({
            "from_id": collection_id,
            "to_id": entity_id,
            "type": "contains"
        }).execute()

        print(f"  ✓ Imported: {item['name']}")
        imported += 1

    return imported, skipped

def main():
    collection_id = os.getenv("COLLECTION_ID")
    if not collection_id:
        raise ValueError("COLLECTION_ID not found in environment")

    print("Loading fetched data...")
    items = load_fetched_data()

    print(f"Importing {len(items)} items...")
    imported, skipped = import_to_database(items, collection_id)

    print(f"\n✓ Complete: {imported} imported, {skipped} skipped")

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

### 4. Create secrets.env Template

Create `.curator/curators/{name}/secrets.env.example`:

```bash
# API Keys and Secrets
API_KEY=your_api_key_here

# Supabase (usually from .env.local in project root)
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_KEY=your_service_key

# Collection
COLLECTION_ID=uuid-from-database
```

**Add to .gitignore:**
```bash
echo "secrets.env" >> .curator/.gitignore
```

### 5. Commit the Curator

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
