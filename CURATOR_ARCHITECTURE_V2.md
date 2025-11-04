# Curator Agent Architecture Plan

**Status**: Ready for Implementation
**Date**: November 2, 2025
**Version**: 0.2 (Updated with user decisions)

## Changelog from v0.1

**Key Changes:**
- ✅ **Memory**: Switched from LangGraph Store to **Mem0** (automatic pruning, better performance)
- ✅ **Simplified**: Removed conflict resolution, resource limits, retry logic (not needed for v1)
- ✅ **Added**: Curator setup wizard
- ✅ **Added**: Real-time progress monitoring
- ✅ **Added**: Manual approval workflow for local development
- ✅ **Added**: Claude Code skill for curator development workflow
- ✅ **Deployment**: Self-hosted LangGraph Platform (confirmed)
- ✅ **Interface**: CLI-only (web UI deferred)

---

## Executive Summary

This document outlines the architecture for a **curator agent system** that manages the import and organization of collectible data at massive scale. Each curator agent is responsible for a single top-level collection (e.g., Pokemon TCG, Marvel Comics, Power Rangers toys) and autonomously:

- Discovers optimal data sources and scraping strategies
- Determines required metadata and organizational structure
- Creates collection-specific scripts and workflows
- Learns from successes (failures are deleted, not stored)
- Runs on schedules or manual triggers with optional runtime instructions
- Manages secrets for API access

The system is built on **DeepAgents** (LangChain's agent framework) with **LangGraph** for workflows, **Mem0** for intelligent persistent memory, and integrates with our existing **Supabase** infrastructure and **collection-agnostic utilities** (thumbnail generation, entity management, etc.).

---

## Table of Contents

1. [Architecture Decisions](#architecture-decisions)
2. [System Architecture](#system-architecture)
3. [Curator Agent Design](#curator-agent-design)
4. [Memory System (Mem0)](#memory-system-mem0)
5. [Curator Setup Wizard](#curator-setup-wizard)
6. [Scheduling & Triggers](#scheduling--triggers)
7. [Real-Time Progress Monitoring](#real-time-progress-monitoring)
8. [Manual Approval Workflow](#manual-approval-workflow)
9. [Secrets Management](#secrets-management)
10. [Collection-Agnostic Utilities](#collection-agnostic-utilities)
11. [Data Flow](#data-flow)
12. [Development Workflow (Claude Code Skill)](#development-workflow-claude-code-skill)
13. [Implementation Phases](#implementation-phases)

---

## Architecture Decisions

### Resolved Questions (From v0.1)

**1. Memory Persistence Strategy**
- ✅ Use **Mem0** with automatic pruning/decay
- ✅ **Delete** failed strategies (don't archive)
- ✅ **No version history** for scripts (latest only)

**2. Curator Initialization**
- ✅ User creates base prompt manually
- ✅ Provide **setup wizard** to guide prompt creation
- ✅ Base prompts are **fairly high-level** - should work even without collection-specific details

**3. Conflict Resolution**
- ✅ Not a concern for v1 (deferred)

**4. Resource Limits**
- ✅ Not a concern for v1 (deferred)

**5. Error Recovery**
- ✅ No auto-retry - just proceed normally on next scheduled/manual run
- ✅ No failure alerts

**6. Performance Optimization**
- ✅ Thumbnail generation stays **synchronous** (helps with rate limiting)
- ✅ Database indexing strategy **will be addressed** (only remaining performance concern)

**7. Deployment**
- ✅ **Self-hosted LangGraph Platform**
- ✅ Costs are not a concern

**8. Testing & Validation**
- ✅ Not a concern for v1 (deferred)

**9. User Interface**
- ✅ **CLI-only** (web UI deferred)
- ✅ **Real-time progress monitoring** (required)
- ✅ **Manual approval** for local dev, **not** in production

**10. Schema Evolution**
- ✅ Not a concern for v1 (deferred)

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│              LangGraph Platform (Self-Hosted)                       │
│  - Deployment infrastructure                                        │
│  - Cron scheduling                                                  │
│  - Environment variables / secrets                                  │
│  - Observability (LangSmith traces)                                 │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       Curator Agent Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Pokemon TCG  │  │    MMPR      │  │ Marvel Comics│ ...         │
│  │   Curator    │  │   Curator    │  │   Curator    │             │
│  │ (DeepAgent)  │  │ (DeepAgent)  │  │ (DeepAgent)  │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                      │
│  Each curator has:                                                  │
│  - Base prompt (user-provided via wizard)                          │
│  - Long-term memory (Mem0 with auto-pruning)                      │
│  - Virtual filesystem (scripts, configs)                           │
│  - Planning & todo tracking                                        │
│  - Subagent spawning capability                                    │
│  - Real-time progress reporting                                    │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  Collection-Specific Workflows                      │
│                        (LangGraph Graphs)                           │
│                                                                      │
│  Each curator creates/maintains workflows for:                     │
│  - API integration (pokemontcg.io, Marvel API, etc.)               │
│  - Web scraping (GRNRngr.com, etc.)                                │
│  - Data transformation & validation                                │
│  - Progress reporting (real-time updates)                          │
│  - Approval requests (local dev only)                              │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Collection-Agnostic Utility Layer                      │
│                                                                      │
│  ✅ Thumbnail generation (already built!)                          │
│  ✅ Supabase entity creation                                       │
│  ✅ Image download & storage                                       │
│  ✅ Relationship building                                          │
│  - Progress tracking & resume                                      │
│  - Validation & integrity checks                                   │
│  - Batch operations                                                │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Data Storage Layer                             │
│                                                                      │
│  Supabase (PostgreSQL):        Mem0 Memory Store:                  │
│  - entities table              - Curator strategies (auto-pruned)  │
│  - relationships table         - Data source metadata              │
│  - Storage (images)            - Organizational decisions           │
│                                - Script content (latest version)    │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Agent Framework** | DeepAgents (Python) | Core agent capabilities |
| **Workflow Engine** | LangGraph | Collection-specific workflows |
| **Memory** | **Mem0** | Intelligent persistent memory with auto-pruning |
| **Scheduling** | LangGraph Platform Cron | Automated runs |
| **Secrets** | LangSmith Workspace Secrets | API credentials |
| **Database** | Supabase (PostgreSQL) | Collectible data |
| **Storage** | Supabase Storage | Images (originals + thumbnails) |
| **Observability** | LangSmith | Traces, debugging, evaluation |
| **Utilities** | Node.js scripts | Collection-agnostic operations |
| **CLI** | Python Click or Typer | User interface |

---

## Curator Agent Design

### Core Responsibilities

Each curator agent is **explicitly assigned to a single collection** and is responsible for:

1. **Discovery** - Find the best data sources for its collection
2. **Strategy Development** - Determine optimal scraping/import approaches
3. **Metadata Definition** - Identify required fields and relationships
4. **Organizational Structure** - Define subcollections (e.g., Pokemon TCG expansions)
5. **Script Generation** - Create collection-specific workflows
6. **Execution** - Run imports on schedule or manual trigger
7. **Learning** - Remember what works, delete what doesn't
8. **Progress Reporting** - Real-time updates during execution
9. **Approval Requests** - Ask for approval in local dev (if enabled)

### DeepAgent Configuration

```python
from deepagents import create_agent
from mem0 import MemoryClient

curator_agent = create_agent(
    model="claude-sonnet-4-5-20250929",

    # System prompt from user (via wizard) + agent instructions
    system_prompt=user_base_prompt + """

    You have access to:
    - Planning tools (write_todos, mark_complete)
    - Virtual filesystem (write scripts, save configs)
    - Subagent spawning (for specialized tasks)
    - Long-term memory via Mem0 (remember successful strategies)
    - Collection utilities (thumbnail generation, entity creation)
    - Progress reporting (emit_progress for real-time updates)
    - Approval requests (request_approval in local dev mode)

    Your workflow:
    1. Check memory for past successful strategies
    2. Plan the import (break into todos)
    3. Write/update collection-specific scripts to filesystem
    4. Request approval if in local dev mode
    5. Execute imports using scripts, emit progress updates
    6. Record successes in memory, delete failures
    """,

    # Enable DeepAgent features
    use_longterm_memory=True,  # Uses Mem0
    use_filesystem=True,
    use_subagents=True,
    use_planning=True,

    # Memory client (Mem0)
    memory_client=MemoryClient(api_key=os.getenv("MEM0_API_KEY")),
    memory_user_id=f"curator-{collection_id}",

    # Collection-specific tools
    tools=[
        # Collection-agnostic utilities
        create_entity_tool,
        create_relationship_tool,
        download_and_thumbnail_tool,

        # Progress & approval
        emit_progress_tool,
        request_approval_tool,

        # Data source tools (dynamic)
        fetch_from_api_tool,
        scrape_webpage_tool,
        validate_data_tool,
    ]
)
```

---

## Memory System (Mem0)

### Why Mem0 Over LangGraph Store?

✅ **Automatic Pruning** - Built-in filtering & decay for outdated memories
✅ **Intelligent Scoring** - Relevance, importance, recency-based prioritization
✅ **Performance** - 26% better accuracy, 91% faster than OpenAI Memory
✅ **Category Protection** - Core memories can be protected from pruning
✅ **Native LangChain Integration** - Works seamlessly with DeepAgents

### Memory Categories

**Protected Categories** (never auto-pruned):
- `collection_structure` - Organizational hierarchy decisions
- `api_credentials` - Authentication methods and endpoints
- `metadata_schema` - Required fields for entities

**Auto-Pruned Categories** (based on recency/relevance):
- `strategy` - Import strategies (low-scoring ones removed automatically)
- `data_source` - Source reliability and quirks (stale ones pruned)
- `script` - Latest version of scripts (old versions deleted manually)

### Memory Operations

**Store successful strategy:**
```python
mem0.add(
    messages=[{
        "role": "assistant",
        "content": "Successfully imported 102 cards from Pokemon Base Set using pokemontcg.io API"
    }],
    user_id="curator-pokemon-tcg",
    metadata={
        "category": "strategy",
        "strategy_type": "api_import",
        "collection": "pokemon-tcg",
        "subcollection": "base-set",
        "success_rate": 1.0,
        "runtime_seconds": 120,
        "items_imported": 102
    }
)
```

**Delete failed strategy:**
```python
# Immediately delete failed attempts
mem0.delete(
    memory_id="failed-scraping-attempt-xyz",
    user_id="curator-pokemon-tcg"
)
```

**Retrieve relevant strategies:**
```python
# Mem0 automatically scores and ranks by relevance
relevant_strategies = mem0.search(
    query="How to import Pokemon TCG cards?",
    user_id="curator-pokemon-tcg",
    limit=5
)

# Use top-scoring strategy
best_strategy = relevant_strategies[0]
```

**Mem0 Auto-Pruning:**
- Happens automatically based on scoring
- Stale strategies with low relevance scores are removed
- Usage frequency affects retention
- No manual cleanup required!

---

## Curator Setup Wizard

### Interactive Setup Flow

When creating a new curator, user runs:

```bash
curators create
```

Wizard guides through:

**Step 1: Collection Identification**
```
What collection will this curator manage?
> Pokemon Trading Card Game

Collection ID (lowercase, hyphens):
> pokemon-tcg

Description (optional):
> Catalog all Pokemon TCG cards from 1996-present, organized by era/series/set
```

**Step 2: Data Sources (Optional)**
```
Do you have known data sources? [y/N]
> y

Enter API endpoints (one per line, empty line to finish):
> https://api.pokemontcg.io/v2
>

Enter websites to scrape (one per line, empty line to finish):
> https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_Trading_Card_Game_sets
>
```

**Step 3: Structure (Optional)**
```
Do you want to define the collection structure? [y/N]
> y

Define hierarchy (one level per line, empty to finish):
> Era
> Series
> Set
> Card
>

Example:
  Era: Wizards of the Coast
    Series: Base
      Set: Base Set
        Card: Charizard #4/102
```

**Step 4: Metadata Schema (Optional)**
```
Define required metadata for 'Card' entities? [y/N]
> y

Required fields (comma-separated):
> name, number, rarity, hp, type

Optional fields (comma-separated):
> attacks, artist, flavor_text
```

**Step 5: Base Prompt Generation**
```
Generating base prompt from your inputs...

===== Generated Base Prompt =====

You are the curator for Pokemon Trading Card Game collectibles.

Collection: Pokemon Trading Card Game
Description: Catalog all Pokemon TCG cards from 1996-present, organized by era/series/set

Known Data Sources:
- API: https://api.pokemontcg.io/v2
- Website: https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_Trading_Card_Game_sets

Collection Structure:
1. Era (top-level)
2. Series
3. Set
4. Card (leaf level)

Example Hierarchy:
Era: Wizards of the Coast
  └─ Series: Base
      └─ Set: Base Set
          └─ Card: Charizard #4/102

Required Metadata (Card):
- name
- number
- rarity
- hp
- type

Optional Metadata (Card):
- attacks
- artist
- flavor_text

Your Goal:
Discover the best strategies to import and organize this collection. Start with the provided data sources, but feel free to find additional sources if needed. Maintain the hierarchical structure and ensure all required metadata is captured.

Remember: Quality over speed. Validate data before inserting.

===================================

Would you like to:
1. Accept this prompt
2. Edit the prompt manually
3. Start over

> 1

✅ Curator 'pokemon-tcg' created successfully!

Next steps:
  curators run pokemon-tcg --dry-run
  curators status pokemon-tcg
```

**Step 6: Secrets Configuration (If APIs detected)**
```
Detected API endpoint: https://api.pokemontcg.io/v2

Does this API require authentication? [y/N]
> y

Secret key name (e.g., POKEMONTCG_API_KEY):
> POKEMONTCG_API_KEY

Secret value (will be stored in LangSmith):
> [hidden input]

✅ Secret saved to LangSmith workspace
```

---

## Scheduling & Triggers

### Execution Modes

**1. Scheduled (Cron)**
```python
# Daily incremental updates
client.cron.create(
    assistant_id="pokemon-tcg-curator",
    schedule="0 2 * * *",  # 2 AM daily
    input={
        "mode": "incremental",
        "emit_progress": True,  # Real-time updates
        "require_approval": False  # Production mode
    }
)
```

**2. Manual Trigger**
```bash
# CLI command
curators run pokemon-tcg \
    --instructions "Import only the new 'Scarlet & Violet' series" \
    --approve  # Enable approval workflow (local dev)
```

```python
# Via Python API
client.runs.create(
    assistant_id="pokemon-tcg-curator",
    input={
        "mode": "custom",
        "instructions": "Import Scarlet & Violet series",
        "emit_progress": True,
        "require_approval": True  # Local dev mode
    }
)
```

**3. Event-Driven (Future)**
- Deferred to later version

---

## Real-Time Progress Monitoring

### Progress Events

Curators emit progress events during execution:

```python
# Curator emits progress
emit_progress({
    "phase": "fetching",
    "message": "Fetching cards from Pokemon TCG API",
    "current": 50,
    "total": 102,
    "percentage": 49,
    "metadata": {
        "set_name": "Base Set",
        "api_endpoint": "/sets/base1/cards"
    }
})
```

### CLI Progress Display

```bash
$ curators run pokemon-tcg --watch

🚀 Starting Pokemon TCG Curator...

Phase: Planning
[████████████████░░░░░░░░] 80% | 4/5 todos complete
✓ Fetch Base Set metadata
✓ Fetch all cards in set
✓ Download card images
✓ Generate thumbnails
⏳ Create entities and relationships

Phase: Execution
[████████████░░░░░░░░░░░░] 50% | 51/102 cards processed
Current: Importing Charizard #4/102
Status: Downloading image... ✓
Status: Generating thumbnail... ✓
Status: Creating entity... ✓

Estimated time remaining: 2 minutes
```

### Progress API

```python
# Stream progress events
for progress in curator_client.stream_progress(run_id):
    print(f"[{progress.phase}] {progress.message}")
    print(f"Progress: {progress.percentage}%")

    if progress.phase == "approval_requested":
        # Handle approval (see next section)
        pass
```

---

## Manual Approval Workflow

### Local Development Only

When running with `--approve` flag:

```bash
curators run pokemon-tcg --approve
```

Curator requests approval at key decision points:

```bash
🚀 Starting Pokemon TCG Curator...

Phase: Planning
✓ Created plan with 5 todos

📋 Approval Requested
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision: Begin import of 102 cards from Base Set

Details:
  • Data Source: pokemontcg.io API
  • Strategy: Bulk API import
  • Estimated Runtime: ~3 minutes
  • Images to Download: 102
  • Thumbnails to Generate: 102
  • Entities to Create: 103 (1 set + 102 cards)

Approve? [y/N/details]
> details

Detailed Plan:
  1. Fetch set metadata (https://api.pokemontcg.io/v2/sets/base1)
  2. Fetch all cards (https://api.pokemontcg.io/v2/cards?q=set.id:base1)
  3. For each card:
     - Download image from card.images.large
     - Generate 300x300 WebP thumbnail
     - Create card entity with metadata
  4. Create set entity
  5. Link all cards to set via "contains" relationships

Approve? [y/N/abort]
> y

✅ Approved. Proceeding with import...
```

### Production Mode

In production (scheduled runs), `require_approval: False`:

```python
# No approval requests, runs fully autonomous
client.cron.create(
    assistant_id="pokemon-tcg-curator",
    schedule="0 2 * * *",
    input={
        "mode": "incremental",
        "require_approval": False  # Production mode
    }
)
```

---

## Secrets Management

### Simplified Approach

**Local Development:**
```bash
# .env file (not committed)
MEM0_API_KEY=mem0_key_...
POKEMONTCG_API_KEY=abc123...
SUPABASE_SERVICE_KEY=supabase_key_...
```

**Production (LangSmith Workspace):**
```python
# Store centrally in LangSmith
langsmith.secrets.create({
    "MEM0_API_KEY": "mem0_key_...",
    "SUPABASE_SERVICE_KEY": "...",  # Shared by all curators
    "POKEMONTCG_API_KEY": "...",     # Pokemon curator only
})
```

**Access in Curator:**
```python
def get_secret(key: str) -> str:
    # Try environment (local dev)
    if key in os.environ:
        return os.environ[key]
    # Fall back to LangSmith (production)
    return langsmith.secrets.get(key)
```

No rotation logic needed for v1.

---

## Collection-Agnostic Utilities

### Already Built ✅

**Thumbnail Generation** (`scripts/thumbnails/`)
- `generate-thumbnails.js`
- `backfill-thumbnails.js`
- Auto-detects Supabase credentials

### To Build

**Entity Manager** (`scripts/toolkit/entity-manager.js`)
```javascript
export async function createEntity({
    type, name, year, country, language,
    image_url, thumbnail_url, attributes
}) {
    // Validate & insert to Supabase
}
```

**Image Handler** (`scripts/toolkit/image-handler.js`)
```javascript
export async function downloadAndStoreImage(url, entityId) {
    // Download, generate thumbnail, upload both
    // Returns { image_url, thumbnail_url }
}
```

**Relationship Builder** (`scripts/toolkit/relationship-builder.js`)
```javascript
export async function createRelationship({
    from_id, to_id, type, order, attributes
}) {
    // Create relationship in Supabase
}
```

**Progress Tracker** (`scripts/toolkit/progress-tracker.js`)
```javascript
export class ProgressTracker {
    emit(phase, message, current, total, metadata) {
        // Emit progress event for real-time monitoring
    }
}
```

---

## Data Flow

### End-to-End Import Flow

```
1. Trigger (Manual with --approve flag)
   ↓
2. Curator Agent Activates
   - Loads user base prompt
   - Retrieves Mem0 memories (top strategies by score)
   - Receives runtime instructions
   ↓
3. Planning Phase
   - Uses write_todos to break down task
   - Checks Mem0 for successful past strategies
   - Decides approach (API/scraping/hybrid)
   - **EMITS PROGRESS**: "Planning complete, 5 todos created"
   ↓
4. Approval Request (Local Dev Only)
   - **REQUEST_APPROVAL** tool called
   - User reviews plan in CLI
   - User approves/rejects/requests details
   ↓
5. Script Generation/Retrieval
   - Writes new script OR retrieves from filesystem
   - Adapts based on runtime instructions
   - **EMITS PROGRESS**: "Script ready for execution"
   ↓
6. Execution (via Subagent)
   - Spawns subagent for isolated execution
   - Subagent calls utilities:
     * Fetch from API/scraper
     * Download images
     * Generate thumbnails (existing script!)
     * Create entities
     * Build relationships
   - **EMITS PROGRESS** after each batch:
     "Processed 50/102 cards (49%)"
   ↓
7. Validation
   - Validates imported data
   - Checks for missing images/relationships
   - **EMITS PROGRESS**: "Validation complete, 102/102 success"
   ↓
8. Memory Update
   - **STORES** success in Mem0:
     * Strategy metadata
     * Success rate
     * Runtime metrics
   - **DELETES** any failed attempts from Mem0
   - Mem0 automatically prunes old/low-scoring strategies
   ↓
9. Cleanup & Reporting
   - Marks todos complete
   - **EMITS PROGRESS**: "Import complete"
   - Returns summary to user
```

---

## Development Workflow (Claude Code Skill)

### Curator Development Skill

**Skill Name**: `curator-development`

**Use Cases:**
- "Create a new curator for Magic: The Gathering"
- "Test the Pokemon TCG curator locally"
- "Deploy curators to production"
- "Debug curator memory issues"

**Skill Provides:**

**1. Curator Creation**
```bash
# Guided wizard
curators create

# Or programmatic
curators create \
    --collection "Magic: The Gathering" \
    --collection-id "mtg" \
    --api "https://api.scryfall.com" \
    --prompt-file prompts/mtg-curator.txt
```

**2. Local Testing**
```bash
# Dry run with approval workflow
curators run mtg --dry-run --approve

# Watch progress in real-time
curators run mtg --watch --approve

# Resume from checkpoint
curators resume mtg --run-id abc123
```

**3. Memory Inspection**
```bash
# View curator memories
curators memory mtg --list

# Search memories
curators memory mtg --search "API import strategy"

# Delete specific memory
curators memory mtg --delete memory_abc123

# View Mem0 auto-pruning stats
curators memory mtg --stats
```

**4. Status & Monitoring**
```bash
# List all curators
curators list

# Show curator status
curators status mtg

# View recent runs
curators runs mtg --limit 10

# Stream live progress
curators watch mtg --run-id abc123
```

**5. Deployment**
```bash
# Deploy to self-hosted LangGraph Platform
curators deploy mtg --schedule "0 2 * * *"

# Update deployment
curators update mtg --schedule "0 3 * * *"

# Remove deployment
curators undeploy mtg
```

**6. Debugging**
```bash
# View LangSmith traces
curators traces mtg --run-id abc123

# Export memories for inspection
curators memory mtg --export memories.json

# View scripts in filesystem
curators filesystem mtg --list

# Read specific script
curators filesystem mtg --read workflows/import-set.py
```

### Skill Documentation

```markdown
# Curator Development Skill

## Overview
Develop, test, and deploy curator agents for collectible imports.

## Prerequisites
- LangGraph Platform (self-hosted) running
- Mem0 API key
- Supabase credentials
- Collection-agnostic utilities installed

## Workflow

### 1. Create Curator
```bash
curators create
# Follow wizard prompts
```

### 2. Test Locally
```bash
# Dry run with approval
curators run <id> --dry-run --approve

# Actual run
curators run <id> --approve --watch
```

### 3. Inspect & Debug
```bash
# Check memories
curators memory <id> --list

# View scripts
curators filesystem <id> --list

# Check traces
curators traces <id>
```

### 4. Deploy to Production
```bash
# Schedule daily runs
curators deploy <id> --schedule "0 2 * * *"
```

## Troubleshooting

**Curator not finding data sources**
- Check Mem0 memories: `curators memory <id> --search "data source"`
- Provide more detail in base prompt about known APIs

**Imports failing**
- View traces: `curators traces <id> --run-id <run>`
- Check failed memories were deleted: `curators memory <id> --stats`

**Mem0 auto-pruning too aggressive**
- Strategies are pruned based on relevance scores
- Frequently-used strategies are protected automatically
- Consider adding to "protected" category in code

## See Also
- CURATOR_ARCHITECTURE.md
- scripts/toolkit/ (collection-agnostic utilities)
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Build infrastructure for curator agents

**Deliverables**:
1. ✅ Collection-agnostic toolkit
   - Entity manager
   - Image handler (uses thumbnail generation)
   - Relationship builder
   - Progress tracker (with emit_progress)

2. ✅ Mem0 setup
   - API integration
   - Memory categories
   - Auto-pruning configuration
   - LangChain integration

3. ✅ Secrets management
   - LangSmith workspace secrets
   - Local .env fallback
   - get_secret() utility

4. ✅ DeepAgent template
   - Base configuration
   - Mem0 memory client
   - Tool definitions (including emit_progress, request_approval)

5. ✅ Curator CLI (basic)
   - `curators create` (wizard)
   - `curators list`
   - `curators run`
   - `curators status`

**Success Criteria**:
- Utilities create entities with thumbnails
- Mem0 stores and retrieves memories
- CLI wizard guides curator creation
- Template agent can plan, emit progress, request approval

---

### Phase 2: Reference Implementation (Weeks 3-4)

**Goal**: Build Pokemon TCG curator

**Deliverables**:
1. ✅ Pokemon TCG Curator
   - Base prompt (via wizard)
   - pokemontcg.io API integration
   - Mem0 memory of strategies

2. ✅ Real-time progress monitoring
   - emit_progress tool
   - CLI watch mode
   - Progress API

3. ✅ Manual approval workflow
   - request_approval tool
   - CLI approval interface
   - Production bypass (require_approval: false)

4. ✅ Testing
   - Import Base Set with approval
   - Verify all 102 cards + thumbnails
   - Check Mem0 memories stored
   - Confirm failed strategies deleted

**Success Criteria**:
- Pokemon curator imports Base Set successfully
- Real-time progress displays in CLI
- Approval workflow functions correctly
- Mem0 auto-prunes old strategies
- Manual trigger works with runtime instructions

---

### Phase 3: Scaling & Automation (Weeks 5-6)

**Goal**: Multiple curators, scheduling

**Deliverables**:
1. ✅ Additional curators
   - MMPR toys (scraping-based)
   - Marvel Comics (API-based)

2. ✅ Cron scheduling
   - Daily incremental (Pokemon)
   - Weekly validation
   - Per-curator schedules

3. ✅ Enhanced CLI
   - `curators deploy`
   - `curators memory`
   - `curators traces`
   - `curators filesystem`

4. ✅ Claude Code Skill
   - Curator development workflow documented
   - Commands for create/test/deploy/debug

**Success Criteria**:
- 3+ curators running independently
- Scheduled runs execute autonomously (no approval)
- CLI provides full control
- Skill documented and usable

---

### Phase 4: Optimization (Weeks 7-8)

**Goal**: Database performance at scale

**Deliverables**:
1. ✅ Database indexing
   - Composite indexes for common queries
   - Partial indexes for filtered lookups
   - Performance testing with 100K+ entities

2. ✅ Mem0 optimization
   - Category tuning (protected vs auto-pruned)
   - Scoring threshold adjustments
   - Pruning schedule configuration

3. ✅ Adaptive learning
   - Curators improve strategies over time
   - Failure recovery with alternative approaches
   - Performance tuning based on metrics

**Success Criteria**:
- Query performance <100ms for typical lookups
- Mem0 maintains optimal memory size
- Curators improve success rates over runs
- System handles 100K+ entities efficiently

---

## Summary of Simplifications from v0.1

**Removed** (Deferred to future versions):
- ❌ Conflict resolution between curators
- ❌ Resource limits and rate limiting
- ❌ Retry logic for failures
- ❌ Failure alerts
- ❌ Testing/validation sandbox
- ❌ Rollback strategy
- ❌ Schema evolution handling
- ❌ Cross-curator communication
- ❌ Event-driven triggers

**Added** (Based on user decisions):
- ✅ Curator setup wizard
- ✅ Real-time progress monitoring
- ✅ Manual approval workflow (local dev)
- ✅ Claude Code skill for development
- ✅ Mem0 with automatic pruning
- ✅ Database indexing strategy (only performance concern remaining)

**Confirmed**:
- ✅ Self-hosted LangGraph Platform
- ✅ CLI-only interface
- ✅ User creates base prompts
- ✅ High-level prompts (should work without collection specifics)
- ✅ Delete failed strategies (no archiving)
- ✅ No version history for scripts

---

**END OF ARCHITECTURE PLAN v0.2**

*Ready for Phase 1 implementation! 🚀*
