# Variants Table Design

**Date:** 2025-11-12
**Status:** Approved

## Problem Statement

Variants in the current pure graph model are stored as entities with `variant_of` relationships. However, variants are conceptually different from other entities because they **cannot exist standalone** - they are always dependent on a base item. This dependency is unique among relationship types in the system.

Moving variants to a dedicated table provides conceptual clarity and enforces the required parent relationship at the schema level.

## Design Overview

Create a new `variants` table separate from `entities`, with mandatory foreign key to base entity. Variants will have their own identity (`id`, `name`) but always reference a parent entity via `variant_of`.

## Schema Design

### New Variants Table

```sql
CREATE TABLE variants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  variant_of UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  image_url TEXT,
  thumbnail_url TEXT,
  attributes JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key properties:**
- `variant_of` is NOT NULL - variants MUST have a base entity
- CASCADE delete - if base entity deleted, variants automatically removed
- Follows entity table conventions (image_url, thumbnail_url, attributes JSONB)
- Minimal schema - only essential fields, rest in attributes

### Indexes

```sql
CREATE INDEX idx_variants_variant_of ON variants(variant_of);
CREATE INDEX idx_variants_attributes ON variants USING GIN(attributes);
```

Critical for:
- Querying all variants of a base item (primary use case)
- Filtering variants by attribute metadata

## GraphQL Integration

### Computed Field on Entities

Add PostgreSQL function to expose variants as a field on entities:

```sql
CREATE OR REPLACE FUNCTION entity_variants(entity_row entities)
RETURNS SETOF variants AS $$
  SELECT * FROM variants WHERE variant_of = entity_row.id
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION entity_variants IS
  '@graphql({"totalCount": {"enabled": true}})';
```

### Query Examples

**Query entity with variants:**
```graphql
query {
  entitiesCollection(filter: {name: {eq: "Charizard"}}) {
    edges {
      node {
        id
        name
        image_url
        entity_variants {
          id
          name
          image_url
          thumbnail_url
          attributes
        }
      }
    }
  }
}
```

**Query variants directly:**
```graphql
query {
  variantsCollection(filter: {variant_of: {eq: "uuid-here"}}) {
    edges {
      node {
        id
        name
        variant_of
        attributes
      }
    }
  }
}
```

## Migration Strategy

### Database Migration

**Approach:** Start fresh with empty variants table.

- Create variants table with indexes
- Add GraphQL function for `entity_variants` computed field
- **No data migration** - existing variant entities remain as-is
- No breaking changes to existing queries

### Curator Updates

**Approach:** Gradual rollout (Option 2).

- Do NOT update existing curators immediately
- Keep existing curators working as-is
- Add variant support to one proof-of-concept curator first (Pokemon TCG)
- Roll out to other curators after validation

**Curator implementation pattern:**
```python
def create_variant(base_entity_id, variant_name, image_url, attributes):
    result = supabase.table("variants").insert({
        "variant_of": base_entity_id,
        "name": variant_name,
        "image_url": image_url,
        "thumbnail_url": generate_thumbnail_path(image_url),
        "attributes": attributes
    }).execute()
    return result.data[0]["id"]
```

## Testing & Rollout

### Testing Steps

1. **Schema validation**
   - Apply migration to local dev environment
   - Verify GraphQL schema includes `entity_variants` field
   - Test CRUD operations on variants table

2. **GraphQL testing**
   - Create variants via REST API
   - Query entities with variants
   - Filter variants by JSONB attributes
   - Test cascade delete (delete entity → variants should disappear)

3. **Proof of concept**
   - Update Pokemon TCG curator with variant support
   - Import cards with variants (1st Edition, Shadowless, etc.)
   - Validate variants appear correctly in GraphQL queries
   - Document pattern for other curators

### Rollout Plan

1. Create and test migration locally
2. Update CLAUDE.md documentation (schema section, query examples)
3. Update curator templates to show variant support as optional pattern
4. Test with Pokemon TCG curator
5. Once stable, roll out to other curators as needed

## Backward Compatibility

- Existing `variant_of` relationships in relationships table remain valid
- Old variant entities (stored as entities) are not affected
- No breaking changes to existing queries
- System supports both old and new variant approaches during transition

## Trade-offs

**Benefits:**
- Conceptual clarity - variants are distinct from standalone entities
- Schema-enforced dependency - variants cannot exist without base entity
- Cleaner queries - direct table access instead of relationship joins
- GraphQL convenience - `entity.variants` instead of relationship traversal

**Trade-offs:**
- Breaks "pure graph" philosophy (no longer just entities + relationships)
- Dual variant systems during transition (old relationship-based + new table-based)
- Curator updates required to use new system
- Migration path for existing variant data deferred (started fresh)

## Future Considerations

- Migrate existing variant entities to variants table (optional)
- Consider similar treatment for components (`part_of` relationships)?
- Semantic search support for variant names
- Variant-specific metadata validation
