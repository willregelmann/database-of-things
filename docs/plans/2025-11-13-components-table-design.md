# Components Table Design

**Date:** 2025-11-13
**Status:** Approved

## Problem Statement

Components (physical pieces that can be removed/lost from collectible items) are currently tracked using `part_of` relationships in the relationships table. However, components share the same conceptual dependency as variants - they **cannot exist standalone** and are always dependent on a parent item.

Moving components to a dedicated table provides:
- Conceptual clarity (components are distinct from global catalog entities)
- Schema-enforced dependency (components cannot exist without parent)
- Quantity tracking (critical for completeness verification)
- Automatic hiding from global searches

## Use Cases

**Primary use case:** Track physical components for completeness verification
- Toys with removable pieces (e.g., Megazord with 5 individual Zords)
- Board games with tokens, cards, dice
- Action figures with accessories
- Model kits with parts

**Key requirement:** Components don't need global catalog visibility - they're only relevant when viewing their parent item ("does my Megazord have all 5 pieces?").

## Design Overview

Create a new `components` table separate from `entities`, with mandatory foreign key to parent entity. Components will have their own identity (`id`, `name`) but always reference a parent via `component_of`.

**Key addition beyond variants pattern:** Quantity tracking for bulk items (e.g., "50 wooden tokens").

## Schema Design

### New Components Table

```sql
CREATE TABLE components (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  component_of UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  quantity INTEGER DEFAULT 1,
  "order" INTEGER,
  image_url TEXT,
  thumbnail_url TEXT,
  attributes JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key properties:**
- `component_of` is NOT NULL - components MUST belong to a parent entity
- CASCADE delete - if parent deleted, components automatically removed
- `quantity` defaults to 1 for unique pieces, set higher for bulk items (e.g., 50 tokens)
- `order` is nullable - use when presentation order matters (assembly instructions), ignore otherwise
- `image_url` and `thumbnail_url` nullable - useful for complex pieces, skip for generic tokens
- `attributes` JSONB for future metadata (condition notes, materials, physical specs)
- Minimal schema - only essential fields, rest in attributes

**Design decisions:**
- **Flat structure only** - Components cannot have sub-components (YAGNI - can add nesting later if needed)
- **Unique per parent** - Each component belongs to exactly one parent (NOT NULL FK, no sharing across items)
- **Optional ordering** - Some items benefit from ordered display, others don't need it
- **Optional images** - Photos help for complex pieces, unnecessary for generic tokens

### Indexes

```sql
CREATE INDEX idx_components_component_of ON components(component_of);
CREATE INDEX idx_components_order ON components("order") WHERE "order" IS NOT NULL;
CREATE INDEX idx_components_attributes ON components USING GIN(attributes);
```

**Purpose:**
- `idx_components_component_of`: Primary use case - query all components of an item
- `idx_components_order`: Partial index for ordered display (only non-null values, follows relationships pattern)
- `idx_components_attributes`: Future JSONB queries (condition tracking, physical specs)

## GraphQL Integration

### Computed Field on Entities

Add PostgreSQL function to expose components as a field on entities:

```sql
CREATE OR REPLACE FUNCTION entity_components(entity_row entities)
RETURNS SETOF components AS $$
  SELECT * FROM components
  WHERE component_of = entity_row.id
  ORDER BY COALESCE("order", 999999), name
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION entity_components IS
  '@graphql({"totalCount": {"enabled": true}})';
```

**Ordering logic:** Components with explicit `order` values appear first (sorted numerically), then unordered components appear after (sorted alphabetically). This ensures ordered components display in sequence while unordered ones just appear at the end.

### Query Examples

**Query entity with components:**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "megazord-uuid"}}) {
    edges {
      node {
        id
        name
        image_url
        entity_components {
          id
          name
          quantity
          order
          image_url
          thumbnail_url
          attributes
        }
      }
    }
  }
}
```

**Query components directly:**
```graphql
query {
  componentsCollection(filter: {component_of: {eq: "item-uuid"}}) {
    edges {
      node {
        id
        name
        quantity
        order
        attributes
      }
    }
  }
}
```

## Migration Strategy

### Database Migration

**Approach:** Start fresh with empty components table (same as variants).

- Create components table with indexes
- Add GraphQL function for `entity_components` computed field
- **No data migration** - existing `part_of` relationships remain as-is
- No breaking changes to existing queries

### Curator Updates

**Approach:** Gradual rollout.

- Do NOT update existing curators immediately
- Keep existing curators using `part_of` relationships
- Add component support to curators as needed (when importing items with removable pieces)
- Document pattern in curator utilities

**Curator implementation pattern:**
```python
def add_component(parent_entity_id, component_name, quantity=1, order=None, image_url=None):
    result = supabase.table("components").insert({
        "component_of": parent_entity_id,
        "name": component_name,
        "quantity": quantity,
        "order": order,
        "image_url": image_url,
        "thumbnail_url": generate_thumbnail_path(image_url) if image_url else None,
        "attributes": {}
    }).execute()
    return result.data[0]["id"]
```

## Testing & Rollout

### Testing Steps

1. **Schema validation**
   - Apply migration to local dev environment
   - Verify GraphQL schema includes `entity_components` field
   - Test CRUD operations on components table

2. **GraphQL testing**
   - Create components via REST API (with varying quantities)
   - Query entities with components
   - Test ordering (explicit order values vs. null)
   - Test cascade delete (delete entity → components should disappear)

3. **Quantity tracking**
   - Insert components with quantity=1 (unique pieces)
   - Insert components with quantity>1 (bulk items like tokens)
   - Verify queries return correct quantities

### Rollout Plan

1. Create and test migration locally
2. Update CLAUDE.md documentation:
   - Add components table to Database Architecture section
   - Mark `part_of` as deprecated in Relationship Types
   - Add component query examples to Common SQL Queries
3. Update curator utilities (optional helper functions)
4. Add components as needed when importing items with removable pieces

## Backward Compatibility

- Existing `part_of` relationships in relationships table remain valid
- Old component entities (stored as entities) are not affected
- No breaking changes to existing queries
- System supports both old and new component approaches during transition

## Trade-offs

**Benefits:**
- Conceptual clarity - components are distinct from global catalog entities
- Schema-enforced dependency - components cannot exist without parent
- Automatic hiding from searches - components don't clutter entity searches
- Quantity tracking - critical for completeness verification ("do I have all 50 tokens?")
- Cleaner queries - direct table access instead of relationship joins
- GraphQL convenience - `entity.components` instead of relationship traversal

**Trade-offs:**
- Breaks "pure graph" philosophy (no longer just entities + relationships)
- Dual component systems during transition (old `part_of` + new table)
- Curator updates required to use new system
- Migration path for existing component data deferred (start fresh)

## Future Considerations

- Migrate existing `part_of` relationships to components table (optional)
- Metadata patterns for condition tracking on vintage items
- Component-specific validation in curator utilities
- Semantic search support for component names (if needed)
- Nested components if use cases emerge (currently flat only)
