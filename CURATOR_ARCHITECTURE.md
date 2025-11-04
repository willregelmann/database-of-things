# Curator Agent Architecture Plan

**Status**: Draft for Review
**Date**: November 2, 2025
**Version**: 0.1

## Executive Summary

This document outlines the architecture for a **curator agent system** that manages the import and organization of collectible data at massive scale. Each curator agent is responsible for a single top-level collection (e.g., Pokemon TCG, Marvel Comics, Power Rangers toys) and autonomously:

- Discovers optimal data sources and scraping strategies
- Determines required metadata and organizational structure
- Creates collection-specific scripts and workflows
- Learns from successes and failures
- Runs on schedules or manual triggers
- Manages secrets for API access

The system is built on **DeepAgents** (LangChain's agent framework) with **LangGraph** for workflows, **LangGraph Store** for persistent memory, and integrates with our existing **Supabase** infrastructure and **collection-agnostic utilities** (thumbnail generation, entity management, etc.).

---

## Table of Contents

1. [Research Findings](#research-findings)
2. [System Architecture](#system-architecture)
3. [Curator Agent Design](#curator-agent-design)
4. [Memory & Learning System](#memory--learning-system)
5. [Scheduling & Triggers](#scheduling--triggers)
6. [Secrets Management](#secrets-management)
7. [Collection-Agnostic Utilities](#collection-agnostic-utilities)
8. [Data Flow](#data-flow)
9. [Implementation Phases](#implementation-phases)
10. [Open Questions](#open-questions)

---

## Research Findings

### DeepAgents Framework

**What is DeepAgents?**
- Python framework built on LangGraph by LangChain AI
- Designed for complex, multi-step agent tasks
- Release 0.2 (October 2025) with pluggable backend abstraction

**Core Capabilities:**
1. **Planning Tool** (`write_todos`) - Break down complex tasks, track progress
2. **Filesystem Interface** - Virtual file system (ls, read_file, write_file, edit_file) for context management
3. **Subagent Spawning** (`task` tool) - Create specialized subagents for isolation
4. **Long-term Memory** - LangGraph Store for persistent memory across threads

**Architecture:**
- Modular middleware: TodoListMiddleware, FilesystemMiddleware, SubAgentMiddleware
- Customizable: models, system prompts, tools, subagent configurations
- Default model: claude-sonnet-4-5-20250929

### LangGraph Store (Memory)

**Persistent Memory Across Threads:**
- Data survives across different conversation sessions
- Multiple backend implementations:
  - `InMemoryStore` - Development/testing
  - `PostgresStore` - Production (recommended)
  - `MongoDBStore` - Alternative (via langgraph-store-mongodb)
- Supports semantic search with embedding functions
- Independent from checkpointer API

**Integration with DeepAgents:**
```python
# Enable long-term memory in DeepAgents
agent = create_agent(
    use_longterm_memory=True,
    store=PostgresStore(connection_string="...")
)
```

### LangGraph Cron Scheduling

**Automated Runs:**
- Built into LangGraph Platform
- Cron expression-based scheduling
- Background execution (doesn't interfere with manual runs)
- SDK-based configuration

**Use Cases:**
- Daily/weekly imports from APIs
- Periodic scraping for new items
- Scheduled data validation/cleanup

**Example:**
```python
# Schedule curator to run daily at 8 PM
client.cron.create(
    assistant_id="pokemon-tcg-curator",
    schedule="0 20 * * *",  # Cron expression
    input={"mode": "incremental_update"}
)
```

### Secrets Management

**Options Available:**
1. **Environment Variables** - Local development (.env files)
2. **LangGraph Platform UI** - Deployment environment variables
3. **LangSmith Workspace Secrets** - Centralized key storage
4. **Cloud Secret Managers** - AWS Secrets Manager, HashiCorp Vault, Azure Key Vault

**Best Practice:**
- Development: `.env` files (not committed)
- Production: LangGraph Platform UI or LangSmith workspace secrets
- Enterprise: Cloud secret managers for centralized management

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Platform / Cloud                       │
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
│  - Base prompt (initialization instructions)                       │
│  - Long-term memory (LangGraph Store)                              │
│  - Virtual filesystem (scripts, configs, notes)                    │
│  - Planning & todo tracking                                        │
│  - Subagent spawning capability                                    │
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
│  - Error handling & retry logic                                    │
│  - Incremental vs full sync strategies                             │
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
│  Supabase:                     LangGraph Store (PostgreSQL):       │
│  - entities table              - Curator memory                     │
│  - relationships table         - Learning history                   │
│  - Storage (images)            - Workflow templates                 │
│                                - Success/failure patterns            │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Agent Framework** | DeepAgents (Python) | Core agent capabilities |
| **Workflow Engine** | LangGraph | Collection-specific workflows |
| **Memory** | LangGraph Store (PostgreSQL) | Persistent agent memory |
| **Scheduling** | LangGraph Platform Cron | Automated runs |
| **Secrets** | LangSmith Workspace Secrets | API credentials |
| **Database** | Supabase (PostgreSQL) | Collectible data |
| **Storage** | Supabase Storage | Images (originals + thumbnails) |
| **Observability** | LangSmith | Traces, debugging, evaluation |
| **Utilities** | Node.js scripts | Collection-agnostic operations |

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
7. **Learning** - Remember what works and what doesn't
8. **Adaptation** - Update strategies based on failures/changes

### Initialization

**User provides base prompt:**

```python
# Example: Initializing Pokemon TCG Curator
pokemon_curator = create_curator(
    collection_id="pokemon-tcg",
    base_prompt="""
    You are the curator for Pokemon Trading Card Game collectibles.

    Your goal is to catalog every Pokemon TCG card ever printed, organized by:
    - Era (e.g., Wizards of the Coast, Pokemon USA, Pokemon Company International)
    - Series (e.g., Base, Gym, Neo)
    - Set (e.g., Base Set, Jungle, Fossil)

    Known data sources:
    - pokemontcg.io API (primary, well-structured)
    - tcgplayer.com (pricing, market data)
    - bulbapedia.com (comprehensive reference)

    You should:
    1. Start with pokemontcg.io API for basic card data
    2. Enrich with pricing from tcgplayer
    3. Fill gaps with Bulbapedia scraping
    4. Create subcollections for each expansion set
    5. Track card variants (1st edition, shadowless, etc.)

    Remember: Quality over speed. Validate data before inserting.
    """,
    secrets={
        "POKEMONTCG_API_KEY": "env(POKEMONTCG_API_KEY)",
        "TCGPLAYER_API_KEY": "env(TCGPLAYER_API_KEY)"
    }
)
```

### DeepAgent Configuration

```python
# Curator as DeepAgent
from deepagents import create_agent
from langgraph.store import PostgresStore

curator_agent = create_agent(
    model="claude-sonnet-4-5-20250929",

    # System prompt combines base prompt + agent instructions
    system_prompt=base_prompt + """

    You have access to:
    - Planning tools (write_todos, mark_complete)
    - Virtual filesystem (write scripts, save configs)
    - Subagent spawning (for specialized tasks)
    - Long-term memory (remember successful strategies)
    - Collection utilities (thumbnail generation, entity creation)

    Your workflow:
    1. Plan the import (break into todos)
    2. Write/update collection-specific scripts to your filesystem
    3. Execute imports using those scripts
    4. Record successes/failures in long-term memory
    5. Adapt strategies based on learnings
    """,

    # Enable all DeepAgent features
    use_longterm_memory=True,
    use_filesystem=True,
    use_subagents=True,
    use_planning=True,

    # Memory backend
    store=PostgresStore(
        connection_string=LANGRAPH_STORE_CONNECTION_STRING,
        namespace=f"curator-{collection_id}"
    ),

    # Collection-specific tools
    tools=[
        # Collection-agnostic utilities
        create_entity_tool,
        create_relationship_tool,
        download_and_thumbnail_tool,

        # Data source tools (dynamic based on collection)
        fetch_from_api_tool,
        scrape_webpage_tool,
        validate_data_tool,
    ]
)
```

### Agent Capabilities

**Planning & Execution:**
```python
# Agent can create todos
agent.write_todos([
    "Fetch all sets from pokemontcg.io API",
    "For each set, fetch all cards",
    "Download card images and generate thumbnails",
    "Create entities and relationships in Supabase",
    "Validate data completeness"
])

# Track progress
agent.mark_complete("Fetch all sets from pokemontcg.io API")
```

**Filesystem (Script Generation):**
```python
# Agent can write collection-specific scripts
agent.write_file("workflows/import-from-pokemontcg-api.py", """
import requests
from utils.entity_manager import create_entity
from utils.image_handler import download_and_thumbnail

def import_set(set_id):
    # Fetch from API
    response = requests.get(
        f"https://api.pokemontcg.io/v2/sets/{set_id}",
        headers={"X-Api-Key": get_secret("POKEMONTCG_API_KEY")}
    )
    set_data = response.json()

    # Create set entity
    set_entity = create_entity({
        "type": "collection",
        "name": set_data["name"],
        "attributes": {
            "release_date": set_data["releaseDate"],
            "total_cards": set_data["total"]
        }
    })

    # Import cards...
""")

# Agent can execute scripts via subagent
agent.task("Run the import script for Base Set",
          script="workflows/import-from-pokemontcg-api.py",
          args={"set_id": "base1"})
```

**Memory (Learning):**
```python
# Agent stores learnings
agent.memory.store({
    "key": "strategy-pokemontcg-api",
    "value": {
        "approach": "Use pokemontcg.io API for bulk import",
        "success_rate": 0.98,
        "failures": ["Timeout on set xy12", "Missing images for promo cards"],
        "lessons": [
            "API rate limit: 1000 requests/hour - batch calls",
            "Promo cards need manual scraping from Bulbapedia",
            "Always validate image URLs before downloading"
        ],
        "last_used": "2025-11-02T15:30:00Z"
    }
})

# Agent retrieves learnings
past_strategies = agent.memory.search("pokemontcg API import strategy")
```

---

## Memory & Learning System

### Memory Types

**1. Short-term Memory (Thread State)**
- Current import session context
- Active todos and progress
- Temporary variables
- Managed by LangGraph checkpointer

**2. Long-term Memory (LangGraph Store)**
- Successful import strategies
- Failed approaches and why
- Data source metadata (API endpoints, rate limits)
- Organizational decisions (how to structure subcollections)
- Script versions and effectiveness

### Memory Schema

**Strategy Memories:**
```json
{
  "namespace": "curator-pokemon-tcg",
  "key": "strategy-import-base-set",
  "value": {
    "collection": "pokemon-tcg",
    "subcollection": "base-set",
    "approach": "pokemontcg.io API bulk import",
    "created_at": "2025-11-01T10:00:00Z",
    "last_updated": "2025-11-02T15:30:00Z",
    "executions": 5,
    "success_rate": 0.98,
    "avg_runtime_seconds": 120,
    "failures": [
      {
        "date": "2025-11-02T12:00:00Z",
        "error": "API rate limit exceeded",
        "resolution": "Added exponential backoff retry logic"
      }
    ],
    "lessons_learned": [
      "Rate limit: 1000 req/hr",
      "Batch size: 100 cards optimal",
      "Thumbnail generation adds ~30s per 100 cards"
    ]
  }
}
```

**Data Source Memories:**
```json
{
  "key": "datasource-pokemontcg-api",
  "value": {
    "url": "https://api.pokemontcg.io/v2",
    "type": "REST API",
    "authentication": "API key in header",
    "rate_limit": "1000 requests/hour",
    "reliability": 0.99,
    "last_checked": "2025-11-02T15:00:00Z",
    "endpoints": {
      "sets": "/sets",
      "cards": "/cards",
      "types": "/types"
    },
    "quirks": [
      "Promo cards often missing images",
      "Japanese sets use different ID format",
      "Older sets (pre-2003) have incomplete data"
    ]
  }
}
```

**Organizational Memories:**
```json
{
  "key": "structure-pokemon-tcg",
  "value": {
    "hierarchy": [
      "Era (Wizards/PUSA/Pokemon Company)",
      "Series (Base, Neo, EX, etc.)",
      "Set (Base Set, Jungle, etc.)",
      "Card (individual cards)"
    ],
    "relationship_types": {
      "card-to-set": "contains",
      "set-to-series": "contains",
      "series-to-era": "contains",
      "variant-to-base": "variant_of"
    },
    "metadata_requirements": {
      "card": ["name", "number", "rarity", "hp", "attacks", "artist"],
      "set": ["name", "release_date", "total_cards", "symbol"],
      "series": ["name", "start_date", "end_date"]
    }
  }
}
```

### Learning Loop

```python
def execute_import_with_learning(curator, import_task):
    # 1. Retrieve relevant memories
    past_strategies = curator.memory.search(
        f"strategy for {import_task.collection}"
    )

    # 2. Plan based on past learnings
    curator.plan_import(
        task=import_task,
        past_strategies=past_strategies
    )

    # 3. Execute
    result = curator.execute_import()

    # 4. Record outcome
    curator.memory.store({
        "key": f"execution-{import_task.id}",
        "value": {
            "task": import_task,
            "strategy_used": result.strategy,
            "success": result.success,
            "errors": result.errors,
            "runtime": result.runtime,
            "items_imported": result.count,
            "timestamp": datetime.now()
        }
    })

    # 5. Update strategy memory
    if result.success:
        curator.memory.update(
            f"strategy-{result.strategy}",
            increment_success_count=True,
            add_lesson=result.insights
        )
    else:
        curator.memory.update(
            f"strategy-{result.strategy}",
            add_failure={
                "error": result.error,
                "attempted_fix": result.attempted_fix
            }
        )
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
        "check_for_new_sets": True,
        "update_prices": True
    }
)

# Weekly full validation
client.cron.create(
    assistant_id="pokemon-tcg-curator",
    schedule="0 3 * * 0",  # 3 AM Sunday
    input={
        "mode": "validation",
        "check_data_quality": True,
        "regenerate_missing_thumbnails": True
    }
)
```

**2. Manual Triggers**
```python
# Manual trigger with runtime instructions
client.runs.create(
    assistant_id="pokemon-tcg-curator",
    thread={
        "metadata": {
            "trigger_type": "manual",
            "initiated_by": "user-123"
        }
    },
    input={
        "mode": "custom",
        "instructions": "Import only the new 'Scarlet & Violet' series",
        "specific_sets": ["sv1", "sv2", "sv3"]
    }
)
```

**3. Event-Driven Triggers**
```python
# Triggered by external events (future enhancement)
# Example: Pokemon Company announces new set
webhook_handler.on("new_set_announced", lambda event: {
    client.runs.create(
        assistant_id="pokemon-tcg-curator",
        input={
            "mode": "new_set_import",
            "set_id": event.set_id,
            "release_date": event.release_date
        }
    )
})
```

### Runtime Instructions

Curators can receive optional instructions at runtime:

```python
# Base prompt remains same, but runtime adds specifics
curator.run(
    base_instructions="You are the Pokemon TCG curator...",
    runtime_instructions="""
    Priority: Import the new 'Temporal Forces' set (sv5).

    Special considerations:
    - This set has dual-type cards - capture both types
    - Some cards have alternate art - create variant relationships
    - Pre-release promos are already available - import those first

    Timeline: Complete within 24 hours
    """,
    secrets=curator.secrets,
    resume_from=None  # Start fresh, or provide checkpoint ID
)
```

---

## Secrets Management

### Architecture

```
User Defines Secrets         LangGraph Platform
      ↓                              ↓
 .env (local dev)      Deployment Environment Vars
      ↓                              ↓
      └──────────────┬───────────────┘
                     ↓
            LangSmith Workspace
          (Centralized Storage)
                     ↓
              Curator Agents
              Access at Runtime
```

### Implementation

**1. Local Development**
```bash
# .env file (not committed)
POKEMONTCG_API_KEY=abc123...
TCGPLAYER_API_KEY=def456...
GRNRNGR_SCRAPER_TOKEN=ghi789...
SUPABASE_SERVICE_KEY=jkl012...
```

**2. Production Deployment**
```python
# When deploying curator to LangGraph Platform
deployment = client.deployments.create(
    graph=curator_graph,
    env_vars={
        "POKEMONTCG_API_KEY": "...",  # Set via UI or API
        "TCGPLAYER_API_KEY": "...",
        "SUPABASE_SERVICE_KEY": "..."
    }
)
```

**3. Centralized in LangSmith**
```python
# Store in LangSmith workspace (shared across curators)
langsmith.secrets.create({
    "SUPABASE_URL": "https://cogxqhlogmagvgicaccg.supabase.co",
    "SUPABASE_SERVICE_KEY": "...",  # Used by all curators
})

# Collection-specific secrets
langsmith.secrets.create({
    "POKEMONTCG_API_KEY": "...",  # Only Pokemon curator
})
```

**4. Access in Curator**
```python
# Curator retrieves secrets at runtime
def get_secret(key: str) -> str:
    """Get secret from environment or LangSmith"""
    # Try environment first (local dev)
    if key in os.environ:
        return os.environ[key]

    # Fall back to LangSmith (production)
    return langsmith.secrets.get(key)

# Use in workflows
api_key = get_secret("POKEMONTCG_API_KEY")
response = requests.get(
    "https://api.pokemontcg.io/v2/sets",
    headers={"X-Api-Key": api_key}
)
```

### Secrets Rotation

```python
# When API keys need rotation
def rotate_secret(curator_id: str, secret_key: str, new_value: str):
    # Update in LangSmith
    langsmith.secrets.update(secret_key, new_value)

    # Notify curator (if running)
    client.threads.update(
        thread_id=curator.active_thread_id,
        metadata={"secret_rotated": secret_key}
    )

    # Log rotation
    curator.memory.store({
        "key": f"secret-rotation-{secret_key}",
        "value": {
            "rotated_at": datetime.now(),
            "reason": "Scheduled rotation",
            "affected_workflows": ["import-from-api"]
        }
    })
```

---

## Collection-Agnostic Utilities

### Existing Utilities (Already Built)

✅ **Thumbnail Generation** (`scripts/thumbnails/`)
- `generate-thumbnails.js` - Create WebP thumbnails
- `backfill-thumbnails.js` - Batch processing with progress tracking
- Auto-detects Supabase credentials from CLI

### Utilities to Build

**Entity Manager** (`scripts/toolkit/entity-manager.js`)
```javascript
// Create entity with validation
export async function createEntity({
    type,
    name,
    year,
    country,
    language,
    image_url,
    thumbnail_url,
    attributes
}) {
    // Validate required fields
    if (!type || !name) {
        throw new Error("type and name are required");
    }

    // Insert to Supabase
    const { data, error } = await supabase
        .from('entities')
        .insert({
            id: crypto.randomUUID(),
            type,
            name,
            year,
            country,
            language,
            image_url,
            thumbnail_url,
            attributes,
            created_at: new Date(),
            updated_at: new Date()
        })
        .select()
        .single();

    if (error) throw error;
    return data;
}
```

**Image Handler** (`scripts/toolkit/image-handler.js`)
```javascript
import { generateThumbnailFromBuffer } from '../thumbnails/generate-thumbnails.js';

export async function downloadAndStoreImage(url, entityId) {
    // Download image
    const response = await fetch(url);
    const imageBuffer = await response.buffer();

    // Generate thumbnail
    const thumbnailBuffer = await generateThumbnailFromBuffer(imageBuffer);

    // Upload both to Supabase Storage
    const originalPath = `originals/${entityId}.jpg`;
    const thumbnailPath = `thumbnails/${entityId}.webp`;

    await supabase.storage.from('images').upload(originalPath, imageBuffer);
    await supabase.storage.from('images').upload(thumbnailPath, thumbnailBuffer);

    return {
        image_url: `/storage/v1/object/public/images/${originalPath}`,
        thumbnail_url: `/storage/v1/object/public/images/${thumbnailPath}`
    };
}
```

**Relationship Builder** (`scripts/toolkit/relationship-builder.js`)
```javascript
export async function createRelationship({
    from_id,
    to_id,
    type,
    order = null,
    attributes = {}
}) {
    const { data, error } = await supabase
        .from('relationships')
        .insert({
            id: crypto.randomUUID(),
            from_id,
            to_id,
            type,
            order,
            attributes,
            created_at: new Date()
        })
        .select()
        .single();

    if (error) throw error;
    return data;
}
```

**Progress Tracker** (`scripts/toolkit/progress-tracker.js`)
```javascript
// Track import progress with resume capability
export class ProgressTracker {
    constructor(curator_id, import_id) {
        this.curator_id = curator_id;
        this.import_id = import_id;
        this.checkpoint_file = `checkpoints/${curator_id}-${import_id}.json`;
    }

    async save(state) {
        await fs.writeFile(
            this.checkpoint_file,
            JSON.stringify(state, null, 2)
        );
    }

    async load() {
        if (await fs.exists(this.checkpoint_file)) {
            return JSON.parse(await fs.readFile(this.checkpoint_file));
        }
        return null;
    }

    async markComplete(item_id) {
        const state = await this.load() || { completed: [] };
        state.completed.push(item_id);
        await this.save(state);
    }
}
```

### Tool Interface for Curators

Curators call these utilities via LangChain tools:

```python
from langchain.tools import tool

@tool
def create_entity_with_images(
    name: str,
    type: str,
    image_url: str,
    attributes: dict
) -> dict:
    """
    Create entity and handle image download/thumbnail generation.

    This is a high-level utility that:
    1. Downloads the image from image_url
    2. Generates a thumbnail
    3. Uploads both to Supabase Storage
    4. Creates the entity with both URLs

    Returns the created entity with image_url and thumbnail_url populated.
    """
    # Call Node.js utility via subprocess
    result = subprocess.run([
        "node",
        "scripts/toolkit/create-entity-with-images.js",
        "--name", name,
        "--type", type,
        "--image-url", image_url,
        "--attributes", json.dumps(attributes)
    ], capture_output=True)

    return json.loads(result.stdout)
```

---

## Data Flow

### End-to-End Import Flow

```
1. Trigger (Cron or Manual)
   ↓
2. Curator Agent Activates
   - Loads base prompt
   - Retrieves long-term memory (past strategies)
   - Receives runtime instructions (if manual)
   ↓
3. Planning Phase
   - Agent uses write_todos to break down task
   - Checks memory for successful strategies
   - Decides: API import? Scraping? Hybrid?
   ↓
4. Script Generation/Retrieval
   - Agent writes new script OR
   - Retrieves existing script from filesystem
   - Adapts based on runtime instructions
   ↓
5. Execution (via Subagent)
   - Spawns subagent for isolated execution
   - Subagent calls collection-agnostic utilities:
     * Fetch data from source (API/scraper)
     * Download images
     * Generate thumbnails (existing script!)
     * Create entities
     * Build relationships
   - Progress tracked, resumable
   ↓
6. Validation
   - Agent validates imported data
   - Checks for missing images, invalid relationships
   - Runs integrity checks
   ↓
7. Learning & Memory Update
   - Agent stores execution results
   - Updates strategy success rates
   - Records failures and lessons
   - Saves to LangGraph Store
   ↓
8. Cleanup & Reporting
   - Mark todos complete
   - Generate summary report
   - Update metadata (last import timestamp)
```

### Example: Pokemon TCG Import

```
User: "Import all Base Set cards"
   ↓
Pokemon TCG Curator receives task
   ↓
Agent retrieves memory:
   - "pokemontcg.io API is reliable for Base Set"
   - "Rate limit: 1000 req/hr"
   - "Thumbnail generation: ~30s per 100 cards"
   ↓
Agent creates plan:
   [ ] Fetch Base Set metadata from API
   [ ] Fetch all 102 cards in set
   [ ] Download card images (102 images)
   [ ] Generate thumbnails (batch of 102)
   [ ] Create set entity
   [ ] Create card entities
   [ ] Create "contains" relationships
   ↓
Agent writes/updates script: workflows/import-pokemon-set.py
   ↓
Agent spawns subagent to execute script:
   - Calls pokemontcg.io API
   - Downloads images via image-handler utility
   - Generates thumbnails via existing script
   - Creates entities via entity-manager
   - Builds relationships via relationship-builder
   ↓
Subagent reports: 102/102 cards imported successfully
   ↓
Agent validates:
   - All 102 cards have images ✓
   - All 102 cards have thumbnails ✓
   - All cards linked to set ✓
   ↓
Agent updates memory:
   - strategy-import-base-set: success_rate = 1.0
   - Lesson: "Batch size 100 optimal for this API"
   - Last execution: 2025-11-02T16:00:00Z
   ↓
Agent marks all todos complete
   ↓
Reports to user: "Successfully imported 102 cards from Base Set"
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Build the infrastructure for curator agents

**Deliverables**:
1. ✅ Collection-agnostic utilities (toolkit)
   - Entity manager
   - Image handler (uses existing thumbnail generation)
   - Relationship builder
   - Progress tracker

2. ✅ LangGraph Store setup
   - PostgreSQL backend for memory
   - Namespace strategy for curators
   - Memory schema design

3. ✅ Secrets management
   - LangSmith workspace secrets
   - Credential access utilities
   - Documentation

4. ✅ DeepAgent template
   - Base agent configuration
   - Middleware setup (planning, filesystem, memory, subagents)
   - Tool definitions

**Success Criteria**:
- Utilities can create entities, download images, generate thumbnails
- Memory store successfully persists curator learnings
- Secrets are accessible from curators
- Template agent can plan, write scripts, spawn subagents

---

### Phase 2: Reference Implementation (Weeks 3-4)

**Goal**: Build Pokemon TCG curator as reference

**Deliverables**:
1. ✅ Pokemon TCG Curator agent
   - Base prompt with collection knowledge
   - Integration with pokemontcg.io API
   - Memory of successful import strategies

2. ✅ Collection-specific workflows
   - LangGraph graph for API import
   - LangGraph graph for web scraping (Bulbapedia fallback)
   - Error handling and retry logic

3. ✅ Organizational structure
   - Define hierarchy: Era → Series → Set → Card
   - Create subcollections for each expansion
   - Relationship types and metadata requirements

4. ✅ Testing
   - Import single set (Base Set)
   - Validate all 102 cards imported correctly
   - Verify thumbnails generated
   - Check relationships

**Success Criteria**:
- Pokemon TCG curator successfully imports Base Set
- Images and thumbnails all present
- Relationships correctly structured
- Agent learns from execution and updates memory
- Manual trigger works with runtime instructions

---

### Phase 3: Scaling & Scheduling (Weeks 5-6)

**Goal**: Scale to multiple curators and automate

**Deliverables**:
1. ✅ Additional curators
   - MMPR toys curator (scraping-based)
   - Marvel Comics curator (API-based)
   - Template for creating new curators

2. ✅ Cron scheduling
   - Daily incremental updates for Pokemon TCG
   - Weekly validation runs
   - Custom schedules per curator

3. ✅ Curator CLI
   - `curators list` - Show all curators
   - `curators run <id> --instructions "..."`
   - `curators status <id>` - Show progress
   - `curators resume <id>` - Resume interrupted

4. ✅ Monitoring & observability
   - LangSmith traces for all curator runs
   - Success/failure metrics
   - Performance tracking

**Success Criteria**:
- 3+ curators running independently
- Scheduled runs execute successfully
- CLI provides full control over curators
- Monitoring shows health of all curators

---

### Phase 4: Advanced Features (Weeks 7-8)

**Goal**: Enable full autonomy and optimization

**Deliverables**:
1. ✅ Adaptive learning
   - Curators optimize their strategies over time
   - Failure recovery with alternative approaches
   - Performance tuning based on runtime metrics

2. ✅ Cross-curator communication
   - Shared learnings (e.g., "Bulbapedia scraping best practices")
   - Resource coordination (avoid rate limits)
   - Data deduplication

3. ✅ Advanced workflows
   - Incremental vs full sync strategies
   - Data enrichment from multiple sources
   - Conflict resolution

4. ✅ Validation & integrity
   - Automated data quality checks
   - Missing data detection
   - Relationship integrity validation

**Success Criteria**:
- Curators improve success rates over multiple runs
- Curators share effective strategies
- Data quality high (>95% completeness)
- System handles 100K+ entities efficiently

---

## Open Questions

### For Discussion & Refinement

1. **Memory Persistence Strategy**
   - How long to retain strategy memories? (forever, or prune old ones?)
   - Should failed strategies be archived or deleted?
   - How to handle strategy versioning (script v1 vs v2)?

2. **Curator Initialization**
   - Who creates the base prompt? (User manually, or assistant-guided setup?)
   - Should there be a "curator setup wizard"?
   - How detailed should base prompts be?

3. **Conflict Resolution**
   - What if two curators try to create the same entity?
   - How to handle duplicate detection across collections?
   - Should there be a global "deduplication agent"?

4. **Resource Limits**
   - Rate limiting across curators (don't overwhelm Supabase)
   - Concurrent execution limits
   - Storage quotas per curator

5. **Error Recovery**
   - When curator fails, should it auto-retry or wait for manual intervention?
   - How many retries before giving up?
   - Should failures trigger alerts?

6. **Performance Optimization**
   - At what scale do we need batch operations?
   - Should thumbnail generation be async/queued?
   - Database indexing strategy for millions of entities

7. **Deployment**
   - Self-hosted LangGraph Platform or LangChain Cloud?
   - Cost implications at scale (LangSmith traces, storage)
   - Local development workflow

8. **Testing & Validation**
   - How to test curators before production?
   - Sandbox environment for new curators?
   - Rollback strategy if import corrupts data

9. **User Interface**
   - CLI-only or build web UI?
   - Real-time progress monitoring?
   - Manual intervention points (approve before import?)

10. **Schema Evolution**
    - What if Pokemon TCG structure changes (new card types)?
    - How do curators adapt to schema changes?
    - Migration strategy for existing data

---

## Next Steps

1. **Review this plan** - Discuss, refine, identify gaps
2. **Answer open questions** - Make architectural decisions
3. **Prioritize phases** - Adjust timeline based on needs
4. **Prototype Phase 1** - Build foundation utilities
5. **Validate with Pokemon TCG** - Reference implementation
6. **Iterate** - Learn and improve based on real usage

---

## Appendix: Resources

### Documentation
- [DeepAgents GitHub](https://github.com/langchain-ai/deepagents)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Store](https://docs.langchain.com/langgraph/store)
- [LangGraph Platform Cron Jobs](https://docs.langchain.com/langgraph-platform/cron-jobs)
- [LangSmith Secrets Management](https://docs.langchain.com/langsmith/secrets)

### Related Skills (Current Implementation)
- `pokemon-tcg-curator` (existing skill)
- `power-rangers-curator` (existing skill)
- `marvel-comics-curator` (existing skill)
- `collectibles-manager` (existing skill)

### Dependencies
- Python 3.10+
- DeepAgents: `pip install deepagents`
- LangGraph: `pip install langgraph`
- LangSmith SDK: `pip install langsmith`
- Node.js 18+ (for utilities)
- Supabase (already configured)
- PostgreSQL (for LangGraph Store)

---

**END OF ARCHITECTURE PLAN v0.1**

*Ready for review and refinement. Let's discuss! 🚀*
