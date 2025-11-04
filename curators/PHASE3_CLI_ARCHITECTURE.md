# Phase 3: CLI-Based Conversational Curator System

## Vision

Transform the autonomous curator into a conversational CLI tool where:
1. User provides minimal intent ("Import Elden Ring merchandise")
2. System discovers sources autonomously
3. System proposes schema → user approves/adjusts
4. System proposes workflow → user approves/adjusts
5. Curator is created and stored
6. User runs curator on-demand

## User Experience

### Initialization (Conversational)

```bash
$ curators init --instructions "Import Elden Ring merchandise"

🔍 Discovering data sources for "Elden Ring merchandise"...

Found 3 potential sources:
  1. Bandai Namco Official Store
     https://store.bandainamcoent.eu/games/brands/elden-ring/
     ✓ Official, high quality
     ✓ 66 products

  2. Amazon Marketplace
     https://amazon.com/s?k=elden+ring+merchandise
     ⚠ Mixed quality
     ✓ 500+ products

  3. Etsy Handmade
     https://etsy.com/search?q=elden+ring
     ⚠ Unofficial
     ✓ 200+ products

Which sources? [1,2,3 or comma-separated]: 1

📋 Analyzing Bandai Namco Store...

💡 Recommended Collection Schema:

Root Collection: "Elden Ring Merchandise"
└─ Type: collection
└─ Attributes: {brand: "Elden Ring", publisher: "Bandai Namco"}

Subcollections:
├─ "Elden Ring Figurines"
│  └─ Types: vinyl figures, plush toys, statues
│  └─ ~25 items expected
│
├─ "Elden Ring Accessories"
│  └─ Types: lamps, blankets, goblets
│  └─ ~15 items expected
│
├─ "Elden Ring Apparel"
│  └─ Types: jackets, shirts, hoodies
│  └─ ~10 items expected
│
└─ "Elden Ring Board Games"
   └─ Types: base game, expansions
   └─ ~16 items expected

Product Attributes:
  - name (text)
  - price (number)
  - price_currency (text, default: EUR)
  - sku (text)
  - availability (enum: in_stock, preorder, out_of_stock)
  - source_category (text)
  - image_url (text)

Approve this schema? [y/n/adjust]: y

⚙️  Proposed Workflow Plan:

Phase 1: Discovery
  ✓ Fetch product listing pages (estimated 4 pages)
  ✓ Extract product URLs and metadata

Phase 2: Extraction
  ✓ Parse product cards using CSS selectors
  ✓ Extract: name, price, SKU, images, category
  ✓ Download and store images to Supabase Storage

Phase 3: Categorization
  ✓ Categorize by keywords (figurine, accessory, apparel, game)
  ✓ Map to appropriate subcollections

Phase 4: Import
  ✓ Create entities with relationships
  ✓ Link products to category collections

Estimated time: 2-3 minutes
Estimated cost: $0.02 (LLM calls)

Approve workflow? [y/n/adjust]: y

✅ Curator Created!

Curator ID: c7e9f3a4-8b2d-4f1a-9e3f-5d6c7e8f9a0b
Name: elden-ring-curator
Collection: Elden Ring Merchandise (433f570a-...)

Workflow saved to: s3://curator-artifacts/c7e9f3a4.../workflow.json
Schema saved to: s3://curator-artifacts/c7e9f3a4.../schema.json

Ready to run: curators run elden-ring-curator
```

### Execution (Simple)

```bash
$ curators run elden-ring-curator

🚀 Running elden-ring-curator...

Loading workflow from S3...
✓ Workflow loaded

Phase 1: Discovery
[████████████████████] 100% | 4/4 pages

Phase 2: Extraction
[████████████████████] 100% | 66/66 products

Phase 3: Categorization
  ✓ Figurines: 25
  ✓ Accessories: 15
  ✓ Apparel: 10
  ✓ Board Games: 16

Phase 4: Import
[████████████████████] 100% | 66/66 imported

✅ Run Complete!

Imported: 66 products
Duration: 2m 34s
Cost: $0.018

Results saved to: s3://curator-artifacts/.../runs/run-{id}/results.json
```

### Subsequent Runs (with modifications)

```bash
$ curators run elden-ring-curator --instructions "Only import figurines under €50"

🚀 Running elden-ring-curator with custom instructions...

Applying filters:
  - Category: figurines only
  - Price: max €50

[████████████████████] 100% | 18/25 figurines

✅ Imported 18 products (7 filtered by price)
```

### List & Manage

```bash
$ curators list

Active Curators:
  1. elden-ring-curator (c7e9f3a4...)
     Collection: Elden Ring Merchandise
     Last run: 2 hours ago (66 products)

  2. pokemon-tcg-curator (8f1a2b3c...)
     Collection: Pokemon Trading Cards
     Last run: 3 days ago (10,450 cards)

$ curators info elden-ring-curator

Curator: elden-ring-curator
ID: c7e9f3a4-8b2d-4f1a-9e3f-5d6c7e8f9a0b
Collection: Elden Ring Merchandise (433f570a...)

Sources:
  - Bandai Namco Store

Schema:
  4 subcollections
  66 products imported

Runs:
  - run-1: 2 hours ago (66 products)
  - run-2: 1 week ago (62 products, 4 new)

$ curators delete elden-ring-curator

⚠️  This will delete the curator but not the collection.
Are you sure? [y/n]: y

✅ Deleted elden-ring-curator
```

## Architecture

### Database Schema

```sql
-- New table for curator metadata
CREATE TABLE curators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    collection_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    instructions TEXT,  -- Original user instructions
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_run_at TIMESTAMP,
    total_runs INTEGER DEFAULT 0
);

-- Optionally: Run history (or store in S3)
CREATE TABLE curator_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curator_id UUID REFERENCES curators(id) ON DELETE CASCADE,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status TEXT, -- running, completed, failed
    products_imported INTEGER,
    custom_instructions TEXT,
    results_url TEXT  -- S3 URL
);
```

### S3 Storage Structure

```
s3://curator-artifacts/
└─ {curator_id}/
   ├─ metadata.json              # Curator config
   ├─ schema.json                # Approved collection schema
   ├─ workflow.json              # Approved workflow plan
   │
   ├─ discovery/
   │  ├─ sources.json            # Discovered sources
   │  └─ analyses/
   │     └─ {source_hash}.json   # Source analysis
   │
   ├─ generated/
   │  ├─ scrapers/
   │  │  └─ scraper_v1.py       # Generated code
   │  └─ workflows/
   │     └─ workflow_v1.json     # LangGraph workflow
   │
   └─ runs/
      └─ {run_id}/
         ├─ logs.json            # Execution logs
         ├─ results.json         # Import results
         └─ artifacts/           # Any run-specific files
```

### CLI Structure

```
curators/
├─ cli/
│  ├─ __init__.py
│  ├─ main.py                   # Entry point
│  ├─ commands/
│  │  ├─ init.py               # curators init
│  │  ├─ run.py                # curators run
│  │  ├─ list.py               # curators list
│  │  ├─ info.py               # curators info
│  │  └─ delete.py             # curators delete
│  │
│  ├─ conversation/
│  │  ├─ source_discovery.py   # Find data sources
│  │  ├─ schema_builder.py     # Build schema with user
│  │  └─ workflow_planner.py   # Plan workflow with user
│  │
│  └─ storage/
│     ├─ s3_client.py           # S3 operations
│     └─ curator_store.py       # Curator CRUD
│
└─ setup.py                      # Install as CLI tool
```

### Installation

```bash
# Install as CLI tool
pip install -e .

# Now available as `curators` command
curators --help
```

## Key Components

### 1. Source Discovery Agent

```python
class SourceDiscoveryAgent:
    """Discovers data sources from user intent."""

    async def discover(self, instructions: str) -> List[Source]:
        # Use LLM to understand intent
        # Search web for potential sources
        # Analyze each source
        # Rank by quality/relevance
        return ranked_sources
```

### 2. Schema Builder (Conversational)

```python
class SchemaBuilder:
    """Builds collection schema with user approval."""

    async def propose_schema(
        self,
        sources: List[Source],
        instructions: str
    ) -> Schema:
        # Analyze sources
        # Generate schema proposal
        # Present to user
        # Loop until approved
        return approved_schema
```

### 3. Workflow Planner

```python
class WorkflowPlanner:
    """Plans execution workflow with user approval."""

    async def plan_workflow(
        self,
        schema: Schema,
        sources: List[Source]
    ) -> Workflow:
        # Generate workflow steps
        # Estimate time/cost
        # Present to user
        # Loop until approved
        return approved_workflow
```

### 4. S3 Storage Manager

```python
class S3StorageManager:
    """Manages curator artifacts in S3."""

    async def save_curator(
        self,
        curator_id: str,
        schema: Schema,
        workflow: Workflow,
        metadata: Dict
    ):
        # Upload to S3
        # Store metadata in DB

    async def load_curator(
        self,
        curator_id: str
    ) -> Curator:
        # Load from S3 and DB
        return curator
```

## Benefits

1. **Simpler UX**: User provides intent, system does everything
2. **Transparent**: User approves schema and workflow
3. **Persistent**: Curators stored in DB, artifacts in S3
4. **Reusable**: Run same curator multiple times
5. **Flexible**: Can modify with run-specific instructions
6. **Discoverable**: System finds sources autonomously
7. **Conversational**: User can adjust proposals

## Implementation Phases

### Phase 3A: CLI Infrastructure ✅
- [ ] CLI entry point with Click/Typer
- [ ] Database migration for `curators` table
- [ ] S3 client setup (Supabase Storage)
- [ ] Basic CRUD operations

### Phase 3B: Conversational Init 🎯
- [ ] Source discovery agent
- [ ] Schema builder with approval loop
- [ ] Workflow planner with approval loop
- [ ] Storage integration

### Phase 3C: Execution
- [ ] Run command
- [ ] Load curator from storage
- [ ] Execute workflow
- [ ] Save results

### Phase 3D: Management
- [ ] List command
- [ ] Info command
- [ ] Delete command
- [ ] Run history

## Next Steps

1. Create CLI package structure
2. Implement `curators` table migration
3. Build Source Discovery Agent
4. Build Schema Builder (conversational)
5. Build Workflow Planner
6. Connect everything

Ready to build this! 🚀
