---
name: init-curator
description: Initialize a new curator through interactive discovery session
---

# Initialize Curator

You are designing a curator for a collectibles database. New curators are **prompt-based** — Claude collects the data directly using web research, with no Python fetch scripts required.

## Process

### 1. Ask Questions (One at a Time)

Use Socratic method:

**Collection Scope:**
- What items belong in this collection?
- How are they organized? (flat list, hierarchical, multi-parent graph)

**Data Sources:**
- Where does the data live? (website, API, wiki)
- What's the URL?
- Is there a structured API, or is it a scrape?

**Terms of Service & Compliance:**
- What are the ToS requirements for this data source?
- Are there rate limits? Attribution requirements? Commercial use restrictions?
- Does the source allow automated access / scraping?

**Deduplication:**
- What makes items unique? (product number, name+year, external ID)

**Attributes & Metadata:**
- What fields matter beyond name, year, image?
- Examples: for figures (line, scale, accessories), for cards (rarity, number, artist)

**Scope Boundaries:**
- What should be excluded? (promos, international exclusives, variants)
- Any ambiguous cases worth calling out explicitly?

### 2. Research Terms of Service & Compliance

**CRITICAL:** Before creating the curator, research the data source's ToS.

1. WebFetch the ToS/API docs page
2. Look for: rate limits, commercial use restrictions, attribution requirements, scraping prohibitions
3. Assess:
   - ✅ **Compliant** — clear permission, no conflicts
   - ⚠️ **Requires Review** — ambiguous, may need explicit permission
   - ❌ **Non-Compliant** — explicit restrictions (e.g. "free apps only", "no automated access")
4. If non-compliant, **STOP** and inform the user before proceeding

**Red flags:**
- "Non-commercial use only" (DBoT has paid auth)
- "No web scraping" or "no automated access" without API
- Fan sites with no stated license (need explicit permission)

### 3. Create Curator Directory

Create `.curator/specs/{Name}/` with these files:

---

**`config.json`:**
```json
{
  "curator_version": "2.0",
  "type": "agent",
  "collection_name": "{Collection Name}",
  "data_source": "{primary URL}",
  "deduplication": {
    "strategy": "external_id",
    "field": "{external_id_field}",
    "fallback": "semantic",
    "semantic_threshold": 0.95
  },
  "entity_mapping": {
    "type": "{item|collection}",
    "category": "{trading_card_games|figures|comics|video_games|buildables}"
  }
}
```

Use `"strategy": "semantic"` with no `"field"` if the source has no stable IDs.

---

**`prompt.md`** — the curator's instructions. Be specific and complete; this is what Claude reads when running the curator.

```markdown
# {Collection Name} Curator

## What to Collect
{Clear description of scope — what's in and what's out}

## Primary Source
{URL} — {brief description of what's there and how it's organized}

## Collection Structure
{Hierarchy: e.g. "Series → Year → Items" or "flat list of items"}
{How parent/child relationships should be created}

## How to Find Items
1. {Step-by-step navigation instructions}
2. {Where item lists are, how to paginate}
3. {Where images live}

## Fields to Extract per Item
- name: {where to find it}
- year: {where to find it}
- image_url: {where to find it}
- source_url: {item page URL pattern}
- external_ids: { "{field}": "{how to find the ID}" }
- attributes: { "{field}": "{description}" }

## What to Skip
- {Explicit exclusions}
- {Edge cases and how to handle them}

## Terms of Service & Attribution
- **Compliance:** ✅ Compliant / ⚠️ Requires Review
- **Rate Limits:** {e.g. "1 request/second"}
- **Attribution:** {required text, or "none required"}
- **Notes:** {any special requirements}
```

---

**`secrets.local.env.example`:**
```bash
# {Name} Curator — Local Environment
# Copy to secrets.local.env and fill in your collection ID

# Collection ID for local Supabase (http://127.0.0.1:54321)
COLLECTION_ID=00000000-0000-0000-0000-000000000000
```

**`secrets.prod.env.example`:**
```bash
# {Name} Curator — Production Environment
# Copy to secrets.prod.env and fill in your collection ID

COLLECTION_ID=00000000-0000-0000-0000-000000000000
```

Only add a `secrets.env.example` (shared API keys) if the source requires an API key.

---

### 4. Tell the User What to Do Next

```
Created: .curator/specs/{Name}/

Next steps:
1. Copy and fill in secrets:
     cp secrets.local.env.example secrets.local.env
     # Edit with your local COLLECTION_ID

2. Run a test import:
     /curator:run "{Name}" --limit 10

3. Review results, then run without --limit to import everything.
```

## Important Notes

- Ask questions **one at a time**
- **Research ToS compliance** before creating the curator
- The `prompt.md` should be specific enough that Claude can run it without asking clarifying questions
- No Python scripts are generated — Claude handles research and import directly
- Existing script-based curators (`type: "script"`) are unaffected
