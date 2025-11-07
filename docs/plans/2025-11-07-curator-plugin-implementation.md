# Curator Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Claude Code plugin that creates and executes autonomous curator agents for importing collectibles data.

**Architecture:** Two-phase system: (1) init-curator skill conducts Socratic discovery session and generates import plan/scripts, (2) run-curator skill autonomously executes the plan with full debugging capabilities.

**Tech Stack:** Claude Code plugin system (skills + slash commands), Python scripts for data fetching/importing, Supabase database.

---

## Task 1: Create Plugin Directory Structure

**Files:**
- Create: `.claude/plugins/collectibles-curator/plugin.json`
- Create: `.claude/plugins/collectibles-curator/README.md`
- Create: `.claude/commands/curator-init.md`
- Create: `.claude/commands/curator-run.md`
- Create: `.claude/commands/curator-status.md`

**Step 1: Create plugin metadata**

Create `.claude/plugins/collectibles-curator/plugin.json`:

```json
{
  "name": "collectibles-curator",
  "version": "1.0.0",
  "description": "Autonomous agents for importing collectibles data",
  "author": "Database of Things",
  "skills": [
    "init-curator",
    "run-curator"
  ]
}
```

**Step 2: Create plugin README**

Create `.claude/plugins/collectibles-curator/README.md`:

```markdown
# Collectibles Curator Plugin

Autonomous agents that import items into collectibles databases.

## Usage

### Initialize a Curator

```bash
/curator:init "Pokemon TCG"
```

Interactive discovery session that generates import plan and scripts.

### Run a Curator

```bash
/curator:run "Pokemon TCG"
```

Autonomously executes the import plan, debugging and fixing issues.

### Check Status

```bash
/curator:status "Pokemon TCG"
```

Shows collection stats and curator details.

## How It Works

1. **Discovery** - Socratic questioning to understand collection and data sources
2. **Generation** - Creates `plan.md` and Python scripts in `.curator/curators/{name}/`
3. **Execution** - Runs scripts autonomously, fixing errors and installing dependencies
4. **Reporting** - Summarizes imported items and issues resolved

## Directory Structure

```
.curator/
  curators/
    Pokemon TCG/
      plan.md           # Import strategy
      config.json       # Collection ID, settings
      scripts/
        fetch_data.py   # Fetch from API/website
        import_items.py # Import into database
        validate.py     # Optional validation
      secrets.env       # API keys (gitignored)
```
```

**Step 3: Create /curator:init command**

Create `.claude/commands/curator-init.md`:

```markdown
---
name: curator:init
description: Initialize a new curator with interactive discovery
---

Initialize a curator for importing collectibles data.

**Usage:**
```bash
/curator:init "Collection Name"
```

**Example:**
```bash
/curator:init "Pokemon TCG"
```

Launches interactive discovery session using the `init-curator` skill.
```

**Step 4: Create /curator:run command**

Create `.claude/commands/curator-run.md`:

```markdown
---
name: curator:run
description: Execute a curator plan to import items
---

Run a curator to autonomously import items.

**Usage:**
```bash
/curator:run "Collection Name"
```

**Example:**
```bash
/curator:run "Pokemon TCG"
```

Launches the `run-curator` skill to execute the import plan.
```

**Step 5: Create /curator:status command**

Create `.claude/commands/curator-status.md`:

```markdown
---
name: curator:status
description: Show curator statistics and status
---

Display curator and collection statistics.

**Usage:**
```bash
/curator:status "Collection Name"
```

**Example:**
```bash
/curator:status "Pokemon TCG"
```

Shows collection stats, plan summary, and recent activity.
```

**Step 6: Commit plugin structure**

```bash
git add .claude/plugins/collectibles-curator/ .claude/commands/curator-*.md
git commit -m "feat: create curator plugin structure

- Plugin metadata and README
- Slash commands: /curator:init, /curator:run, /curator:status
- Directory structure for skills (next task)"
```

---

## Task 2: Create init-curator Skill

**Files:**
- Create: `.claude/plugins/collectibles-curator/skills/init-curator/SKILL.md`

**Step 1: Create init-curator skill**

Create `.claude/plugins/collectibles-curator/skills/init-curator/SKILL.md`:

```markdown
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
```

**Step 2: Commit init-curator skill**

```bash
git add .claude/plugins/collectibles-curator/skills/init-curator/
git commit -m "feat: add init-curator skill

Interactive discovery session that:
- Asks Socratic questions about collection
- Generates import plan and working scripts
- Creates curator directory structure
- Commits result to git"
```

---

## Task 3: Create run-curator Skill

**Files:**
- Create: `.claude/plugins/collectibles-curator/skills/run-curator/SKILL.md`

**Step 1: Create run-curator skill**

Create `.claude/plugins/collectibles-curator/skills/run-curator/SKILL.md`:

```markdown
---
name: run-curator
description: Execute a curator plan autonomously to import collection items
---

# Run Curator

You execute curator plans to autonomously import items into collections.

## Your Task

### 1. Load Configuration

```bash
# Curator directory
CURATOR_DIR=".curator/curators/{name}"

# Load plan
cat "$CURATOR_DIR/plan.md"

# Load config
cat "$CURATOR_DIR/config.json"

# Load secrets into environment (if exists)
if [ -f "$CURATOR_DIR/secrets.env" ]; then
    source "$CURATOR_DIR/secrets.env"
fi
```

### 2. Execute Import Workflow

**Step 2a: Run fetch script**

```bash
cd "$CURATOR_DIR/scripts"
python fetch_data.py
```

**If it fails:**
- Read the error message
- Identify the issue (missing dependency, API error, parsing error)
- Fix it:
  - **Missing dependency:** `pip install {package}`
  - **Script bug:** Edit the script to fix the error
  - **API changed:** Update the script to match new API structure
- Retry until successful

**Step 2b: Run import script**

```bash
python import_items.py
```

**If it fails:**
- Identify the issue
- Fix the script or install dependencies
- Retry until successful

**Step 2c: Run validation (optional)**

```bash
python validate.py
```

Report any issues found.

### 3. Be Autonomous

You have **full access** to:
- Read - Inspect scripts, errors, data files
- Write - Fix broken scripts, update code
- Bash - Install dependencies, run commands
- WebFetch - Check API docs if needed

**Your job:** Make the import succeed, not just run scripts blindly.

**Common fixes:**
- `ModuleNotFoundError: No module named 'requests'` → `pip install requests`
- `JSONDecodeError` → Fix parsing logic in script
- `KeyError: 'items'` → API structure changed, update field access
- `ConnectionError` → Check API URL, retry with backoff

### 4. Report Results

After successful execution, summarize:

```
✓ Curator run complete: {name}

Fetched: {N} items from {source}
Imported: {M} new items
Skipped: {K} duplicates
Issues fixed:
  - Installed missing dependency: requests
  - Fixed API field name: items → data.items

Collection stats:
  Total items: {X}
  Last updated: {timestamp}
```

## Example Run

```bash
# Load curator
CURATOR=".curator/curators/Pokemon TCG"

# Load secrets
source "$CURATOR/secrets.env"

# Run fetch
cd "$CURATOR/scripts"
python fetch_data.py
# → ModuleNotFoundError: requests

# Fix: install dependency
pip install requests

# Retry fetch
python fetch_data.py
# → ✓ Fetched 152 items

# Run import
python import_items.py
# → ✓ Imported 152 items

# Validate
python validate.py
# → Collection: 152 items, 0 missing images
```

## Critical Principles

1. **Iterate until success** - Don't give up on first error
2. **Fix scripts** - Edit code when it's broken
3. **Install dependencies** - `pip install` as needed
4. **Adapt to changes** - Update scripts when APIs change
5. **Report clearly** - Summarize what was imported and fixed

You are not a passive script runner. You are an autonomous agent that makes imports succeed.
```

**Step 2: Commit run-curator skill**

```bash
git add .claude/plugins/collectibles-curator/skills/run-curator/
git commit -m "feat: add run-curator skill

Autonomous execution that:
- Loads plan and configuration
- Runs fetch/import scripts
- Debugs and fixes errors
- Installs missing dependencies
- Iterates until successful
- Reports results clearly"
```

---

## Task 4: Update .gitignore

**Files:**
- Modify: `.gitignore`
- Create: `.curator/.gitignore`

**Step 1: Ensure .curator directory is tracked but secrets aren't**

Add to `.gitignore`:

```gitignore
# Curator secrets
.curator/curators/*/secrets.env

# Curator temporary files
.curator/curators/*/fetched_data.json
.curator/curators/*/scripts/__pycache__/
.curator/curators/*/scripts/*.pyc
```

Create `.curator/.gitignore`:

```gitignore
# Secrets
curators/*/secrets.env

# Temporary data
curators/*/fetched_data.json
curators/*/scripts/__pycache__/
curators/*/scripts/*.pyc
```

**Step 2: Commit gitignore updates**

```bash
git add .gitignore .curator/.gitignore
git commit -m "chore: add curator gitignore rules

Ignore:
- secrets.env files
- fetched_data.json (temporary)
- Python cache files"
```

---

## Task 5: Test with Manual Curator Creation

**Files:**
- Test: Create a simple test curator manually to verify structure

**Step 1: Create test curator directory**

```bash
mkdir -p .curator/curators/Test
```

**Step 2: Create minimal plan.md**

Create `.curator/curators/Test/plan.md`:

```markdown
# Test Curator Plan

## Collection
- **Type:** Test items
- **Collection ID:** test-uuid
- **Organization:** Flat list

## Data Sources
- **Primary:** Manual test data

## Import Workflow
1. Echo test data
2. Print success message
```

**Step 3: Create minimal config.json**

Create `.curator/curators/Test/config.json`:

```json
{
  "collection_id": "test-uuid",
  "data_source": "test"
}
```

**Step 4: Create minimal test script**

Create `.curator/curators/Test/scripts/test.py`:

```python
#!/usr/bin/env python3
print("✓ Test curator works!")
print("Imported 5 test items")
```

**Step 5: Test running the script**

```bash
python .curator/curators/Test/scripts/test.py
```

Expected output:
```
✓ Test curator works!
Imported 5 test items
```

**Step 6: Remove test curator**

```bash
rm -rf .curator/curators/Test
```

**Step 7: Verify plugin files exist and are correct**

```bash
# Check slash commands exist
ls .claude/commands/curator-*.md

# Check plugin exists
ls .claude/plugins/collectibles-curator/plugin.json

# Check skills exist
ls .claude/plugins/collectibles-curator/skills/*/SKILL.md
```

Expected: All files present

---

## Task 6: Document Plugin Usage

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add curator plugin section to CLAUDE.md**

Add to `CLAUDE.md`:

```markdown
## Curator Plugin

Autonomous agents for importing collectibles data.

### Available Commands

- `/curator:init "Collection Name"` - Initialize new curator (interactive discovery)
- `/curator:run "Collection Name"` - Execute curator to import items
- `/curator:status "Collection Name"` - Show collection stats

### Example Usage

```bash
# Create curator
/curator:init "Pokemon TCG"
# → Interactive questions about collection and data sources
# → Generates plan and scripts in .curator/curators/Pokemon TCG/

# Run curator
/curator:run "Pokemon TCG"
# → Executes fetch and import scripts autonomously
# → Fixes errors, installs dependencies
# → Reports: "Imported 152 cards from pokemontcg.io"

# Check status
/curator:status "Pokemon TCG"
# → Collection: 152 cards, last updated 2 hours ago
```

### How It Works

1. **Discovery** (`/curator:init`) - Socratic questioning generates import plan and working scripts
2. **Execution** (`/curator:run`) - Autonomously runs scripts, debugging and fixing issues
3. **Results** - Reports imported items and issues resolved

Scripts are in `.curator/curators/{name}/scripts/` and can be edited manually if needed.
```

**Step 2: Commit documentation**

```bash
git add CLAUDE.md
git commit -m "docs: document curator plugin in CLAUDE.md

Added:
- Command reference
- Example usage
- How it works explanation"
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] `.claude/plugins/collectibles-curator/plugin.json` exists
- [ ] `.claude/plugins/collectibles-curator/README.md` exists
- [ ] `.claude/commands/curator-init.md` exists
- [ ] `.claude/commands/curator-run.md` exists
- [ ] `.claude/commands/curator-status.md` exists
- [ ] `.claude/plugins/collectibles-curator/skills/init-curator/SKILL.md` exists
- [ ] `.claude/plugins/collectibles-curator/skills/run-curator/SKILL.md` exists
- [ ] `.gitignore` includes curator secret patterns
- [ ] `.curator/.gitignore` exists
- [ ] `CLAUDE.md` documents curator plugin
- [ ] All changes committed to git

## Next Steps

After implementation:

1. Test `/curator:init` with a real collection (e.g., Pokemon TCG)
2. Verify it generates working scripts
3. Test `/curator:run` and ensure it can fix common errors
4. Iterate on skill prompts based on results

## Success Criteria

- Users can initialize curators through natural conversation
- Generated scripts work or can be fixed autonomously
- Curators successfully import items without manual intervention
- Users trust curators to debug and iterate
