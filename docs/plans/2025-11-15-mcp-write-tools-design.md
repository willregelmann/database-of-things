# MCP Write Tools & Curator Integration Design

**Date:** 2025-11-15
**Status:** Approved
**Context:** Extend MCP server with write operations and integrate with curator system

## Background

Currently:
- MCP server has 5 read-only tools for querying the database
- Curators are Python scripts using Supabase client directly
- Both systems have separate environment handling (local/prod)

## Problem

Curators use generated Python scripts that Claude invokes, but this doesn't leverage Claude's intelligence for:
- Deduplication decisions
- Error recovery
- Interactive problem-solving
- Relationship inference

## Solution

**Hybrid Architecture:** Python scripts fetch data from external APIs (mechanical), Claude uses MCP write tools to intelligently write to database.

### Core Principles

1. **Simple, composable tools** - Not "smart" combined operations
2. **Intelligent orchestration** - Claude decides when/how to use tools
3. **Transparent errors** - Structured error responses with recovery suggestions
4. **Environment safety** - Explicit opt-in for production writes
5. **No transactions** - Claude handles partial failures intelligently

## Architecture

### Unified MCP Server

Single `database-of-things` MCP server with three capability groups:

**Read Tools (existing):**
- `search_collectibles` - Semantic search
- `get_entity` - Entity details
- `browse_collection` - Collection contents
- `get_variants` - Variant lookup
- `get_components` - Component lookup

**Write Tools (new - 13 tools):**

**Entity Operations:**
- `create_entity(name, type, attributes, ...)` → entity_id
- `update_entity(entity_id, fields)` → success
- `delete_entity(entity_id)` → success

**Relationship Operations:**
- `create_relationship(from_id, to_id, type, order?)` → relationship_id
- `delete_relationship(from_id, to_id, type)` → success

**Variant Operations:**
- `create_variant(variant_of, name, attributes)` → variant_id
- `update_variant(variant_id, fields)` → success

**Component Operations:**
- `create_component(component_of, name, quantity, order, attributes)` → component_id

**Image Operations:**
- `create_image(entity_id|variant_id|component_id, image_url, thumbnail_url, is_primary)` → image_id

**Embedding Operations:**
- `generate_embedding(entity_id)` → success
- `bulk_generate_embeddings(entity_ids[])` → {success_count, failed[], errors}

**Curator Tools (new - 5 tools):**
- `list_curators()` → {name, path, has_fetch_script, environment}[]
- `get_curator_config(name)` → {plan, config, collection_id, data_source}
- `run_curator_fetch(name, options?)` → {status, items_fetched, data, errors}
- `validate_curator_data(name, data)` → {valid, warnings, errors}
- `get_curator_stats(name)` → {total_items, last_import, items_in_collection}

## Data Flow

### Curator Workflow Example: Pokemon TCG Base Set

**Step 1: Fetch (Python)**
```bash
python3 .curator/curators/Pokemon TCG/scripts/fetch_data.py
# → writes fetched_data.json with 102 cards
```

**Step 2: Process (Claude + MCP)**
```
Claude reads JSON, then:

1. collection_id = create_entity({name: "Base Set", type: "collection"})
2. For each card:
   a. results = search_collectibles("Charizard Base Set", type="card")
   b. If similarity > 0.95:
        create_relationship(results[0].id, collection_id, "contains")
   c. Else:
        entity_id = create_entity({name: "Charizard", type: "card", ...})
        create_relationship(entity_id, collection_id, "contains")
        create_image(entity_id, image_url)
3. bulk_generate_embeddings([all_new_entity_ids])
4. Report: "Imported 95 new cards, updated 7 relationships"
```

### Why This Works

**Claude's Intelligence:**
- Asks user about ambiguous duplicates (90-95% similarity)
- Adapts when API data is incomplete
- Handles errors gracefully with context
- Reports progress naturally

**Python's Strengths:**
- Mechanical API pagination and rate limiting
- Format conversion (CSV/XML → clean JSON)
- Reliable, testable data extraction

## Error Handling

### Structured Error Responses

```typescript
// Success
{ success: true, entity_id: "uuid" }

// Error
{
  success: false,
  error: "Entity with name 'Charizard' already exists",
  error_code: "DUPLICATE_ENTITY",
  details: { existing_id: "uuid", similarity: 0.98 }
}
```

### Error Codes

- `DUPLICATE_ENTITY` - Exact name match exists
- `INVALID_UUID` - Malformed ID
- `NOT_FOUND` - Referenced entity doesn't exist
- `MISSING_REQUIRED_FIELD` - Required parameter missing
- `RELATIONSHIP_EXISTS` - Duplicate relationship
- `CIRCULAR_REFERENCE` - Would create cycle
- `IMAGE_DOWNLOAD_FAILED` - Could not fetch image
- `EMBEDDING_GENERATION_FAILED` - Vector generation error

### Recovery Strategy

Claude handles errors intelligently:
- `DUPLICATE_ENTITY` → Search for existing, use that ID
- `IMAGE_DOWNLOAD_FAILED` → Log warning, continue without image
- `CIRCULAR_REFERENCE` → Ask user before proceeding
- Others → Report to user, skip item

## Transactions & Atomicity

**No automatic transactions or rollbacks.**

**Rationale:**
- Partial success is often useful (entity exists even without relationship)
- Claude makes intelligent recovery decisions
- Simpler server implementation
- Matches natural thinking: "Created entity, now linking it..."

**Benefits:**
- Report granular progress: "Created 100 entities, 97 relationships (3 failed)"
- User can fix failures manually or retry specific items
- Claude decides: keep partial state? retry? ask user?

**Mitigation for orphans:**
- Add `find_orphaned_entities()` tool for cleanup (future)

## Environment Handling

### Multi-Environment MCP Servers

```json
{
  "mcpServers": {
    "database-of-things-local": {
      "env": {
        "SUPABASE_URL": "http://127.0.0.1:54321",
        "SUPABASE_ANON_KEY": "local-key"
      }
    },
    "database-of-things-prod": {
      "env": {
        "SUPABASE_URL": "${SUPABASE_PROD_URL}",
        "SUPABASE_ANON_KEY": "${SUPABASE_PROD_ANON_KEY}"
      }
    }
  }
}
```

### Tool Prefix Determines Environment

```typescript
// Local writes
mcp__database-of-things-local__create_entity(...)
→ writes to http://127.0.0.1:54321

// Production writes
mcp__database-of-things-prod__create_entity(...)
→ writes to https://yourproject.supabase.co
```

### Safety Mechanisms

1. **Default to local** - Safer for development
2. **Production confirmation** - First prod write triggers: "⚠️ Writing to PRODUCTION. Type 'yes' to confirm"
3. **Read-only mode** - `SUPABASE_PROD_READ_ONLY=true` disables prod writes
4. **Dry run** - `create_entity({..., dry_run: true})` previews without writing

### Curator Workflow

```bash
# Development
source .env.local  # or just use defaults
claude
# Use -local tools

# Production
source .env.prod
claude
# Use -prod tools, get confirmation prompt
```

## Implementation Plan

### Phase 1: Core Write Tools (Week 1)
- Entity CRUD (create, update, delete)
- Relationship CRUD
- Basic error handling
- Manual testing

### Phase 2: Extended Write Tools (Week 1)
- Variant operations
- Component operations
- Image operations
- Embedding generation
- Sample curator workflow testing

### Phase 3: Curator Integration (Week 2)
- Curator discovery tools
- `run_curator_fetch` tool
- `validate_curator_data` tool
- End-to-end test with Pokemon TCG curator

### Phase 4: Safety & Polish (Week 2)
- Production write confirmations
- Dry run mode
- Read-only mode flag
- Comprehensive error codes
- Documentation updates

### Phase 5: Rollout (Week 3)
- Update remaining curators
- Migration guide for curator authors
- Update CLAUDE.md with new patterns

## Deliverables

- `mcp-server/src/tools/write/` - Write operation tools
- `mcp-server/src/tools/curator/` - Curator workflow tools
- Updated `.mcp.json` with environment defaults
- Migration guide for existing curators
- Updated documentation

## Testing Approach

- Manual testing with real curators during development
- Real usage feedback drives iteration
- No automated tests initially

## Success Metrics

- Claude can run complete curator workflows using only MCP tools
- Deduplication decisions are intelligent (asks user when uncertain)
- Error recovery is graceful (partial success reported)
- Environment switching is safe (confirmation required)

## Future Enhancements

- Bulk operation optimizations (if needed)
- Transaction support (if partial failures become problematic)
- Orphan cleanup tools
- Audit logging for production writes
- Undo/rollback capabilities

## Alternatives Considered

### Separate curator-mcp-server
**Rejected:** Would require wrapping database tools, creating semantic conflicts. Single unified server is simpler.

### Smart combined operations (e.g., `add_to_collection`)
**Rejected:** Too many operation patterns in one tool. Simple, composable tools give Claude more control.

### Automatic transactions/rollback
**Rejected:** Partial success is often useful. Claude handles failures intelligently without automatic rollback.

### Python scripts call MCP tools directly
**Rejected:** Loses Claude's intelligence. Scripts become mechanical tool invocation without judgment.
