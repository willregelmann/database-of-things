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

**Terms of Service & Compliance:**
- What are the ToS requirements for this data source?
- Are there rate limits? Attribution requirements? Commercial use restrictions?
- Does the source allow automated access / API usage / web scraping?
- Are there any "free app only" or "non-commercial" restrictions?
- What attribution text should be displayed when showing this data?
- Are there specific linking requirements to source pages?

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

### 2. Research Terms of Service & Compliance

**CRITICAL:** Before generating any scripts, research the data source's Terms of Service.

**Steps:**
1. **Find ToS page:**
   - Look for `/terms`, `/tos`, `/legal`, `/api/terms` pages
   - Check API documentation for usage policies
   - Review developer portal guidelines

2. **Identify key requirements:**
   - Rate limits (requests per minute/hour/day)
   - Commercial use allowance (critical - DBoT has paid authentication services)
   - Attribution requirements (text to display, linking)
   - Restrictions (web scraping, automation, "free apps only")
   - API key requirements and registration process

3. **Use WebFetch to read ToS:**
   ```
   WebFetch the ToS page and ask:
   "What are the rate limits, commercial use restrictions, attribution requirements,
   and any prohibitions on automated access or web scraping?"
   ```

4. **Assess compliance:**
   - ✅ **Compliant:** Clear permission, no conflicts with DBoT's model
   - ⚠️ **Requires Review:** Some ambiguity, may need explicit permission
   - ❌ **Non-Compliant:** Explicit restrictions that conflict (e.g., "free apps only")

5. **Document findings:**
   - Add to README.md in "Terms of Service & Attribution" section
   - Include exact attribution text if required
   - Note any restrictions or special requirements
   - If non-compliant, STOP and inform user before generating scripts

**Red Flags:**
- "Free apps only" or "non-commercial use only" (conflicts with paid auth)
- "No web scraping" (must use API if available)
- "No automated access" (need explicit API permission)
- No ToS found for fan sites (requires explicit permission from owner)

**If non-compliant:**
- Document the issue clearly
- Suggest alternatives (different APIs, official sources, community contribution model)
- Do NOT generate scripts until compliance is resolved

### 3. Create Artifacts

Create directory: `.curator/curators/{name}/`

**README.md:**
```markdown
# {Name} Curator

Autonomous data import agent for {collection description} from {Data Source}.

## Overview

- **Collection:** {Collection Name} ({description})
- **Data Source:** {API or website URL}
- **Organization:** {flat/hierarchical structure}
- **Deduplication:** {external_id field} (`external_ids.{field_name}`)

## Terms of Service & Attribution

### Compliance Status
✅ Compliant | ⚠️ Requires Review | ❌ Non-Compliant

### Compliance Requirements
- **Rate Limits:** {requests per minute/hour/day}
- **Commercial Use:** {Allowed | Not Allowed | Requires License}
- **Attribution Required:** {Yes/No - specific text if yes}
- **Linking Requirements:** {Must link to source pages | Optional | None}
- **Restrictions:** {Any specific restrictions}

### Attribution Text
```
{Exact attribution text to display, e.g., "Data provided by Example API © 2025"}
```

### Compliance Notes
- {Any special considerations or requirements}
- {Contact information if permissions needed}
- {Review date for ToS changes}

## Setup

### 1. Get API Credentials

1. Visit {API website}
2. Create account
3. Get API key from {location}

### 2. Configure Secrets

```bash
cp secrets.env.example secrets.env
```

Edit `secrets.env`:
```bash
{API_KEY_NAME}=your_api_key_here
```

### 3. Test Fetch via MCP

Use Claude with MCP tools to test the fetch:

```
/curator:run "{Name}" --limit 10
```

Or via MCP tools directly in Claude Code:
```
mcp__database-of-things-local__run_curator_fetch(name="{Name}", options={"limit": 10})
mcp__database-of-things-local__validate_curator_data(name="{Name}")
```

## How It Works

### 1. Fetch (`fetch_data.py`)
- Authenticates with {API}
- Fetches {items} with metadata
- Outputs to `fetched_data.json` in v2 format

### 2. Import (via Claude + MCP)
- Deduplication using `external_ids.{field}`
- Entity creation with images
- Relationship linking
- Embedding generation

## Metadata Structure

### {Entity Type} (type: "{entity_type}")

**Fetched data format (graph structure):**

If your collection has hierarchy (e.g., Sets → Cards, Series → Issues):

```json
// Parent entity (set, series, collection)
{
  "name": "{Parent Name}",
  "type": "collection",
  "year": {year},
  "external_ids": {
    "{parent_id_field}": "{parent_id}"
  },
  "attributes": {
    "{attribute}": "{value}"
  }
}

// Child entity (card, issue, item)
{
  "name": "{Item Name}",
  "type": "{entity_type}",
  "year": {year},
  "external_ids": {
    "{item_id_field}": "{id}"
  },
  "image_url": "{url}",
  "source_url": "{url}",
  "parent": {
    "type": "collection",
    "external_ids": {
      "{parent_id_field}": "{parent_id}"
    }
  },
  "relationship": {
    "type": "contains",
    "order": {order_number}
  },
  "attributes": {
    "{attribute}": "{value}"
  }
}
```

If your collection is flat (no hierarchy), omit `parent` and `relationship` fields.

**Database entity:**
```json
{
  "name": "{Example Item}",
  "type": "{entity_type}",
  "year": {year},
  "image_url": "/storage/v1/object/public/images/originals/{uuid}.jpg",
  "thumbnail_url": "/storage/v1/object/public/images/thumbnails/{uuid}.webp",
  "external_ids": {
    "{field_name}": "{id}"
  },
  "attributes": {
    "{attribute}": "{value}"
  }
}
```

## Troubleshooting

### "API error: Invalid credentials"
- Check credentials in `secrets.env`
- Verify at {API website}

### "Rate limit exceeded"
- Wait or use --limit flag
- Current limit: {rate limit}

## See Also

- [Curator Best Practices](../../README.md)
- [{API} Documentation]({url})
```

**config.json:**
```json
{
  "curator_version": "2.0",
  "collection_name": "{Collection Name}",
  "data_source": "https://api.example.com/v1",
  "fetch": {
    "script": "scripts/fetch_data.py",
    "requires_api_key": true,
    "rate_limit_seconds": 0.1,
    "supports_filters": ["filter1", "filter2"]
  },
  "deduplication": {
    "strategy": "external_id",
    "field": "example_api_id",
    "fallback": "semantic",
    "semantic_threshold": 0.95
  },
  "entity_mapping": {
    "type": "card",
    "attributes": ["attribute1", "attribute2"]
  }
}
```

**scripts/fetch_data.py:**
```python
#!/usr/bin/env python3
"""Fetch {items} from {source}."""

import argparse
import os
import json
import requests
from datetime import datetime
from pathlib import Path

API_URL = "https://api.example.com/v1"
OUTPUT_FILE = Path(__file__).parent.parent / "fetched_data.json"

def fetch_items(api_key: str, limit: int = None, **filters):
    """Fetch items from API with pagination and rate limiting.

    Args:
        api_key: API authentication key
        limit: Maximum items to fetch (None = all)
        **filters: Curator-specific filters (expansion, theme, etc.)

    Returns:
        List of raw API responses
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    items = []
    page = 1

    while True:
        # CUSTOMIZE: Adjust pagination parameters for your API
        params = {"page": page, "pageSize": 100}

        # CUSTOMIZE: Add curator-specific filters
        # Example: if filters.get("expansion"):
        #     params["expansion"] = filters["expansion"]

        response = requests.get(
            f"{API_URL}/items",
            headers=headers,
            params=params
        )
        response.raise_for_status()

        data = response.json()
        # CUSTOMIZE: Adjust for your API's response structure
        batch = data.get("items", data.get("data", []))
        items.extend(batch)

        # Check limit
        if limit and len(items) >= limit:
            items = items[:limit]
            break

        # CUSTOMIZE: Check for more pages based on your API
        if not data.get("hasMore") and not data.get("next"):
            break

        page += 1

    return items

def normalize_item(raw_item: dict) -> dict:
    """Transform API response to standard fetched_data.json format.

    Args:
        raw_item: Raw item from API response

    Returns:
        Normalized item matching fetched_data.json schema
    """
    # CUSTOMIZE: Map your API fields to standard schema
    return {
        "name": raw_item["name"],
        "type": "card",  # CUSTOMIZE: "card", "figure", "game", etc.
        "external_id": raw_item.get("id"),
        "dedup_hint": {
            "strategy": "external_id",  # or "semantic"
            "field": "example_api_id",  # CUSTOMIZE: external_ids field name
            "fallback": "semantic"
        },
        "year": raw_item.get("year"),
        "language": raw_item.get("language"),  # ISO 639-1 code
        "country": raw_item.get("country"),    # ISO 3166-1 alpha-2
        "image_url": raw_item.get("image_url") or raw_item.get("imageUrl"),
        "source_url": f"{API_URL}/items/{raw_item.get('id')}",  # CUSTOMIZE
        "attributes": {
            # CUSTOMIZE: Domain-specific metadata only
            # Example for cards: "hp": raw_item.get("hp")
            # Example for games: "publisher": raw_item.get("publisher")
        }
    }

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description=f"Fetch items from {API_URL}"
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum items to fetch (default: all)'
    )
    # CUSTOMIZE: Add curator-specific filters
    # parser.add_argument('--expansion', help='Filter by expansion')
    # parser.add_argument('--theme', help='Filter by theme')
    # parser.add_argument('--rarity', help='Filter by rarity')

    args = parser.parse_args()

    # Load API key from environment
    api_key = os.getenv("API_KEY")  # CUSTOMIZE: Your API key env var name
    if not api_key:
        print("❌ Error: API_KEY not found in environment")
        print("Set it in .curator/curators/{name}/secrets.env")
        return 1

    # Extract filter arguments
    filters = {}
    # CUSTOMIZE: Add your filters
    # if args.expansion:
    #     filters["expansion"] = args.expansion

    # Fetch raw data
    print(f"Fetching items from {API_URL}...")
    if args.limit:
        print(f"Limit: {args.limit} items")
    if filters:
        print(f"Filters: {filters}")

    raw_items = fetch_items(api_key, args.limit, **filters)

    # Normalize to standard format
    print(f"Normalizing {len(raw_items)} items...")
    items = [normalize_item(item) for item in raw_items]

    # Create output in standard format
    output = {
        "format_version": "1.0",
        "metadata": {
            "curator": "{Collection Name}",  # CUSTOMIZE
            "source": API_URL,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "total_items": len(items),
            "filters_applied": {
                "limit": args.limit,
                **filters
            }
        },
        "items": items
    }

    # Save to file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✓ Fetched {len(items)} items → {OUTPUT_FILE}")
    return 0

if __name__ == "__main__":
    exit(main())
```

**Note:** Import is now handled by Claude via MCP tools. No import_items.py or validate.py scripts are generated.

### 4. Generate Working Fetch Script

**CRITICAL:** The fetch script must be:
- Complete and executable (~200 lines)
- Output standardized fetched_data.json format
- Handle pagination and rate limiting
- Install dependencies if missing (requests)
- Use environment variables for API keys
- Support --limit and curator-specific filters

**Customize based on:**
- User's answers about data sources
- Actual API/website structure
- Filter arguments discussed (--expansion, --theme, etc.)
- External ID field naming

### 5. Create Secrets Templates

Create **three** secrets template files for environment separation:

**`.curator/curators/{name}/secrets.env.example`** (Shared - API keys):
```bash
# {Name} Curator - Shared Configuration (All Environments)
# Copy to secrets.env and fill in your API key

# Data Source API Key
{API_KEY_VAR}=your_api_key_here

# Note: Collection IDs are environment-specific:
# - secrets.local.env (for local Supabase)
# - secrets.prod.env (for production Supabase)
```

**`.curator/curators/{name}/secrets.local.env.example`** (Local environment):
```bash
# {Name} Curator - Local Environment Configuration
# Copy to secrets.local.env and fill in your local collection ID

# Collection ID for local Supabase (http://127.0.0.1:54321)
# To get this ID:
# 1. Start local Supabase: ./bin/supabase start
# 2. Create collection: INSERT INTO entities (name, type) VALUES ('{Collection Name}', 'collection') RETURNING id;
# 3. Paste the UUID here:
COLLECTION_ID=00000000-0000-0000-0000-000000000000
```

**`.curator/curators/{name}/secrets.prod.env.example`** (Production environment):
```bash
# {Name} Curator - Production Environment Configuration
# Copy to secrets.prod.env and fill in your production collection ID

# Collection ID for production Supabase
# To get this ID:
# 1. Connect to production database
# 2. Create collection: INSERT INTO entities (name, type) VALUES ('{Collection Name}', 'collection') RETURNING id;
# 3. Paste the UUID here:
COLLECTION_ID=00000000-0000-0000-0000-000000000000
```

**Note:** The `.curator/.gitignore` already excludes all `secrets.*.env` files (without .example suffix) from git. Only commit the .example templates.

### 6. Offer Validation Test

After generating scripts, ask the user:

**"Would you like to test the curator via MCP before finalizing? (recommended)"**

Options:
- **Yes** - Test fetch and validate output format via MCP
- **No** - Skip to commit (user will test later)

**If user chooses Yes:**

1. **Test fetch via MCP:**
   ```
   Use mcp__database-of-things-local__run_curator_fetch(
     name="{name}",
     options={"limit": 5}
   )
   ```
   - MCP will execute the fetch script in the curator environment
   - Shows items_fetched count and sample data
   - Displays any errors encountered

2. **Validate via MCP:**
   ```
   Use mcp__database-of-things-local__validate_curator_data(
     name="{name}"
   )
   ```
   - Validates the fetched_data.json format
   - Checks format_version, metadata, and item structure
   - Returns warnings/errors if any

3. **Display sample items:**
   - Show 2-3 sample items from the MCP fetch response
   - Format as YAML for easy review
   - Verify:
     - Required fields present (name, type)
     - External IDs structure correct
     - Hierarchical relationships (parent/relationship) if applicable
     - Images present when expected

4. **Ask for confirmation:**
   "Does the data format look correct?"

   Options:
   - **Yes** - Proceed to commit (step 7)
   - **No** - Let user investigate/fix, then offer validation again

**If user chooses No:**
- Proceed directly to commit (step 7)
- Remind user they can test later with `/curator:run "{name}" --limit 10`

### 7. Commit the Curator

```bash
git add .curator/curators/{name}/
git commit -m "feat: add {name} curator (v2)

Discovery complete:
- Fetch script generated (standardized format)
- Deduplication strategy: {strategy}
- Data source: {source}
- Import handled by Claude via MCP tools"
```

## Important Notes

- Ask questions **one at a time** (Socratic method)
- **Research ToS compliance** before generating any scripts
- If source is non-compliant, **STOP** and suggest alternatives
- Generate **complete, working fetch script** (~200 lines)
- Output **standardized fetched_data.json format** (format_version: "1.0")
- Use **environment variables** for all secrets (API keys in secrets.env, collection IDs in secrets.{env}.env)
- **Test via MCP tools** - use run_curator_fetch and validate_curator_data
- **MCP-first workflow** - all curator operations should use MCP tools, not manual script execution
- Document ToS review date for future audits

## Critical Requirements for Fetch Script

The generated fetch_data.py MUST follow these patterns:

### REQUIRED

1. **Standardized Output Format**:
   - Output `fetched_data.json` with format_version "1.0"
   - Include complete metadata section (curator, source, fetched_at, total_items, filters_applied)
   - Each item must have: name (required), type (required), external_id (optional)
   - Include dedup_hint structure for each item

2. **Filter Arguments**:
   - Support `--limit` argument (standard)
   - Add curator-specific filters as needed (--expansion, --theme, --rarity, etc.)
   - Pass filters to API appropriately

3. **Field Mapping**:
   - Map API response to standard schema
   - Use dedicated fields: year, language, country, image_url, source_url
   - Put domain-specific metadata in attributes JSONB
   - Include external_id from source system

4. **Error Handling**:
   - Graceful handling of API errors
   - Rate limiting if required by ToS
   - Pagination for large datasets
   - Clear error messages

5. **Dependencies**:
   - Only require: requests, standard library
   - No Supabase client needed (Claude handles import)
   - No image processing needed (Claude handles via MCP)
   - No embedding generation needed (Claude handles via MCP)

### Customization Points

Mark these sections with **# CUSTOMIZE:** comments:
- API_URL constant
- API key environment variable name
- Pagination parameters
- Response structure parsing (items vs data field)
- Filter argument additions
- Entity type ("card", "figure", "game", etc.)
- External ID field name for dedup_hint
- Field mappings in normalize_item()
- Domain-specific attributes

This allows users to easily find and modify curator-specific logic.
