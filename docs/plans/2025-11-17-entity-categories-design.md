# Entity Categories Design

**Date:** 2025-11-17
**Status:** Approved

## Overview

Add a single `category` field to entities for primary classification (e.g., "trading card games", "figures", "comics"). This supports filtering and search faceting across collections while leaving room for future multi-tag support.

## Goals

- Enable browsing items by category across different collections
- Provide search facets to narrow results
- Replace ad-hoc type classifications with formal category vocabulary
- Keep tags available for future multi-label feature

## Design Decisions

### Schema

**Add category column to entities table:**

```sql
-- Create enum type
CREATE TYPE category_type AS ENUM (
  'trading_card_games',
  'figures',
  'comics',
  'video_games',
  'buildables'
);

-- Add column to entities
ALTER TABLE entities ADD COLUMN category category_type;

-- Create partial index for filtering
CREATE INDEX idx_entities_category ON entities(category)
WHERE category IS NOT NULL;
```

**Key properties:**
- Column is nullable - allows entities without category during import
- Partial index (WHERE category IS NOT NULL) - saves space, only indexes categorized entities
- Enum provides strong typing and prevents typos
- Both items and collections can have categories

### Data Migration

Migrate existing entity type data from attributes JSONB:

```sql
UPDATE entities SET category = CASE
  WHEN type = 'collection' THEN NULL  -- Collections start uncategorized
  ELSE CASE
    WHEN attributes->>'type' = 'card' THEN 'trading_card_games'
    WHEN attributes->>'type' IN ('action_figure', 'figure') THEN 'figures'
    WHEN attributes->>'type' = 'comic' THEN 'comics'
    WHEN attributes->>'type' = 'video_game' THEN 'video_games'
    WHEN attributes->>'type' = 'lego_set' THEN 'buildables'
    ELSE NULL
  END
END;
```

**Category mappings:**
- `card` → `'trading_card_games'`
- `action_figure`, `figure` → `'figures'`
- `comic` → `'comics'`
- `video_game` → `'video_games'`
- `lego_set` → `'buildables'`

### API Exposure

**GraphQL:**

```graphql
# Filter entities by category
query {
  entitiesCollection(
    filter: { category: { eq: trading_card_games } }
  ) {
    edges {
      node {
        id
        name
        type
        category
      }
    }
  }
}

# Get all available categories via introspection
query {
  __type(name: "category_type") {
    enumValues {
      name
    }
  }
}
```

**SQL Helper Function:**

```sql
CREATE FUNCTION get_categories() RETURNS TEXT[] AS $$
  SELECT array_agg(enumlabel::text ORDER BY enumsortorder)
  FROM pg_enum WHERE enumtypid = 'category_type'::regtype;
$$ LANGUAGE sql IMMUTABLE;
```

**MCP Tool:**

Add `list_categories()` tool:
```python
@mcp.tool()
def list_categories() -> list[str]:
    """Get all available category values"""
    result = supabase.rpc('get_categories').execute()
    return result.data
```

### Curator Integration

**Fetch data format:**
Curators can optionally specify category in `fetched_data.json`:

```json
{
  "name": "Charizard",
  "category": "trading_card_games",
  "external_ids": {...}
}
```

**MCP create_entity update:**
Add optional `category` parameter:

```python
create_entity(
  name="Charizard",
  type="item",
  category="trading_card_games",  # Optional
  ...
)
```

## Implementation

**Migration file:** `20251117XXXXXX_add_category_to_entities.sql`

**Steps:**
1. Create `category_type` enum
2. Add `category` column to entities (nullable)
3. Migrate existing data from attributes JSONB
4. Create partial index on category
5. Add `get_categories()` helper function

**MCP Server updates:**
1. Add optional `category` parameter to `create_entity` tool
2. Add `list_categories()` tool
3. Update tool documentation

## Future Extensions

### Adding New Categories
Requires migration to alter enum:
```sql
ALTER TYPE category_type ADD VALUE 'new_category';
```

### Multi-Tag Support
When ready to add multiple tags per entity:
- Add `tags` JSONB array column, OR
- Create separate `entity_tags` junction table
- `category` remains primary classification
- `tags` provides additional facets

### Display Names
For user-friendly labels ("Trading Card Games" vs "trading_card_games"):
- Simple mapping in application layer, OR
- Create `categories` reference table with display_name, icon, description

### Hierarchical Categories
If needed:
- Create categories table with parent_id self-reference
- Enables "Games → Card Games → Trading Card Games" hierarchy

## Edge Cases

- NULL category allowed (uncategorized items during import)
- Collections can be categorized or not
- Index only covers non-NULL values (performance optimization)
- Backwards compatible - existing code continues to work

## Backwards Compatibility

- Existing code unaffected (category is optional)
- Old entity type data in attributes JSONB preserved for reference
- Can remove attributes->>'type' in future cleanup migration
