# Variants Table Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add dedicated variants table to replace variant_of relationships, providing schema-enforced parent dependency and cleaner GraphQL queries.

**Architecture:** Create new `variants` table with mandatory foreign key to `entities`, add indexes for performance, create PostgreSQL function for GraphQL computed field `entity_variants`.

**Tech Stack:** PostgreSQL, Supabase, GraphQL (auto-generated via PostgREST)

---

## Task 1: Create Database Migration

**Files:**
- Create: `supabase/migrations/20251112000000_create_variants_table.sql`

**Step 1: Create migration file**

Run: `./bin/supabase migration new create_variants_table`
Expected: Creates timestamped file in `supabase/migrations/`

**Step 2: Write migration SQL**

Open the generated file and replace contents with:

```sql
-- Create variants table
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

-- Add indexes for performance
CREATE INDEX idx_variants_variant_of ON variants(variant_of);
CREATE INDEX idx_variants_attributes ON variants USING GIN(attributes);

-- Add PostgreSQL function for GraphQL computed field
CREATE OR REPLACE FUNCTION entity_variants(entity_row entities)
RETURNS SETOF variants AS $$
  SELECT * FROM variants WHERE variant_of = entity_row.id
$$ LANGUAGE SQL STABLE;

-- Tell PostgREST/GraphQL about the relationship
COMMENT ON FUNCTION entity_variants IS
  '@graphql({"totalCount": {"enabled": true}})';
```

**Step 3: Apply migration locally**

Run: `./scripts/safe-migrate push`
Expected: Output shows migration applied successfully, automatic backup created

**Step 4: Verify table created**

Run: `docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\d variants"`
Expected: Shows table structure with all columns (id, variant_of, name, image_url, thumbnail_url, attributes, created_at, updated_at)

**Step 5: Verify indexes created**

Run: `docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\di variants*"`
Expected: Shows idx_variants_variant_of and idx_variants_attributes indexes

**Step 6: Verify function created**

Run: `docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\df entity_variants"`
Expected: Shows entity_variants function with correct signature

**Step 7: Commit migration**

```bash
git add supabase/migrations/
git commit -m "feat: add variants table with GraphQL integration

- Create variants table with mandatory variant_of foreign key
- Add CASCADE delete when base entity removed
- Create indexes for variant_of and attributes queries
- Add entity_variants() function for GraphQL computed field

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Test CRUD Operations

**Files:**
- None (manual testing via CLI)

**Step 1: Create test entity**

Run:
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
INSERT INTO entities (name, type)
VALUES ('Test Base Card', 'card')
RETURNING id;"
```
Expected: Returns UUID of created entity (save this for next steps)

**Step 2: Create variant with valid foreign key**

Run (replace BASE_ENTITY_ID with UUID from Step 1):
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
INSERT INTO variants (variant_of, name, attributes)
VALUES ('BASE_ENTITY_ID', '1st Edition', '{\"edition\": \"1st\", \"rarity\": \"rare\"}'::jsonb)
RETURNING *;"
```
Expected: Returns created variant with all fields populated

**Step 3: Test foreign key constraint (should fail)**

Run:
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
INSERT INTO variants (variant_of, name)
VALUES ('00000000-0000-0000-0000-000000000000', 'Invalid Variant');"
```
Expected: ERROR - foreign key constraint violation (entity doesn't exist)

**Step 4: Test NOT NULL constraint (should fail)**

Run:
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
INSERT INTO variants (name)
VALUES ('Missing Parent');"
```
Expected: ERROR - null value in column "variant_of" violates not-null constraint

**Step 5: Query variants via entity_variants function**

Run (replace BASE_ENTITY_ID):
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
SELECT * FROM entity_variants((SELECT row(entities.*) FROM entities WHERE id = 'BASE_ENTITY_ID')::entities);"
```
Expected: Returns the 1st Edition variant created in Step 2

**Step 6: Test cascade delete**

Run (replace BASE_ENTITY_ID):
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
DELETE FROM entities WHERE id = 'BASE_ENTITY_ID';"
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
SELECT COUNT(*) FROM variants WHERE variant_of = 'BASE_ENTITY_ID';"
```
Expected: Count = 0 (variant was automatically deleted)

---

## Task 3: Test GraphQL API

**Files:**
- None (manual testing via GraphQL endpoint)

**Step 1: Ensure Supabase is running**

Run: `./bin/supabase status`
Expected: All services healthy, GraphQL endpoint at http://127.0.0.1:54321/graphql/v1

**Step 2: Create test data via SQL**

Run:
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
-- Create base entity
INSERT INTO entities (id, name, type)
VALUES ('11111111-1111-1111-1111-111111111111', 'Charizard', 'card');

-- Create variants
INSERT INTO variants (variant_of, name, attributes)
VALUES
  ('11111111-1111-1111-1111-111111111111', '1st Edition', '{\"edition\": \"1st\"}'::jsonb),
  ('11111111-1111-1111-1111-111111111111', 'Shadowless', '{\"print\": \"shadowless\"}'::jsonb),
  ('11111111-1111-1111-1111-111111111111', 'Base Set Unlimited', '{\"edition\": \"unlimited\"}'::jsonb);
"
```
Expected: 3 rows inserted

**Step 3: Get API key**

Run: `./bin/supabase status | grep "anon key"`
Expected: Shows API key (looks like `eyJhbGc...`)

**Step 4: Test GraphQL query for variants collection**

Create file `test-query-variants.graphql`:
```graphql
query {
  variantsCollection {
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

Run:
```bash
curl -X POST http://127.0.0.1:54321/graphql/v1 \
  -H "apikey: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ variantsCollection { edges { node { id name variant_of attributes } } } }"}'
```
Expected: JSON response with 3 variants (1st Edition, Shadowless, Base Set Unlimited)

**Step 5: Test entity_variants computed field**

Run:
```bash
curl -X POST http://127.0.0.1:54321/graphql/v1 \
  -H "apikey: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ entitiesCollection(filter: {name: {eq: \"Charizard\"}}) { edges { node { id name entity_variants { id name attributes } } } } }"}'
```
Expected: JSON response showing Charizard entity with nested entity_variants array containing all 3 variants

**Step 6: Test filtering variants by attributes**

Run:
```bash
curl -X POST http://127.0.0.1:54321/graphql/v1 \
  -H "apikey: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ variantsCollection(filter: {attributes: {contains: {edition: \"1st\"}}}) { edges { node { id name } } } }"}'
```
Expected: JSON response with only "1st Edition" variant

**Step 7: Clean up test data**

Run:
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
DELETE FROM entities WHERE id = '11111111-1111-1111-1111-111111111111';"
```
Expected: 1 row deleted, variants automatically cascade deleted

---

## Task 4: Update Documentation (CLAUDE.md)

**Files:**
- Modify: `/home/will/Projects/database-of-things/CLAUDE.md:154-198` (Database Architecture section)

**Step 1: Update schema description**

Find the "Pure Graph Model" section (around line 154) and update to mention variants table:

```markdown
### Pure Graph Model

The schema consists of three tables:

**`entities`** - Collections, items, and components in the system:
[keep existing content unchanged]

**`variants`** - Alternative versions of entities (e.g., 1st Edition, Shadowless):
- `id` (UUID): Primary key
- `variant_of` (UUID): Foreign key to entities (NOT NULL, CASCADE delete)
- `name` (TEXT): Variant name (e.g., "1st Edition", "Shadowless")
- `image_url` (TEXT): Image URL path (same pattern as entities)
- `thumbnail_url` (TEXT): Pre-generated thumbnail path
- `attributes` (JSONB): Variant-specific metadata (edition, print run, condition, etc.)
- Timestamps: `created_at`, `updated_at`

**`relationships`** - Connections between entities:
[keep existing content unchanged]
```

**Step 2: Add variants to Design Patterns section**

Find "Design Patterns" section (around line 185) and add variants note:

```markdown
**Variants Architecture**:
- Variants are stored in dedicated table, not as entities
- `variant_of` foreign key is mandatory (NOT NULL)
- CASCADE delete ensures variants removed when base entity deleted
- Access via `entity_variants()` GraphQL computed field
- Legacy: Some older variant data may exist as entities with `variant_of` relationships
```

**Step 3: Update Relationship Types section**

Find "Relationship Types" (around line 191) and update variant_of description:

```markdown
**Relationship Types** (all use parent→child direction):
- `contains`: Parent contains child (e.g., Collection → Card, Franchise → Game)
  - Most common relationship type
  - Makes querying intuitive: "show me what this collection contains"
- `variant_of`: **DEPRECATED** - Use variants table instead
  - Legacy: Some old variant data stored as entity relationships
  - New variants: Use dedicated variants table
- `part_of`: Component → Whole (e.g., "Megazord arm" → "Megazord")
  - For physical components or pieces
- Custom types as needed for domain-specific relationships
```

**Step 4: Update indexes section**

Find the indexes section (around line 205) and add variants indexes:

```markdown
**Variant lookups**:
- `idx_variants_variant_of`: Find all variants of a base entity
- `idx_variants_attributes`: JSONB queries on variant metadata (GIN)
```

**Step 5: Commit documentation updates**

```bash
git add CLAUDE.md
git commit -m "docs: update schema documentation for variants table

- Add variants table to Pure Graph Model section
- Document variant architecture patterns
- Mark variant_of relationships as deprecated
- Add variants indexes to documentation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Add GraphQL Query Examples to Documentation

**Files:**
- Modify: `/home/will/Projects/database-of-things/CLAUDE.md:307-370` (GraphQL API Usage section)

**Step 1: Add variants query examples**

Find the GraphQL examples section (around line 307) and add after existing examples:

```markdown
# Query variants of an entity (using computed field)
query {
  entitiesCollection(filter: {name: {eq: "Charizard"}}) {
    edges {
      node {
        id
        name
        image_url
        thumbnail_url
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

# Query all variants directly
query {
  variantsCollection {
    edges {
      node {
        id
        name
        variant_of
        attributes
        created_at
      }
    }
  }
}

# Filter variants by attributes
query {
  variantsCollection(
    filter: {
      attributes: {contains: {edition: "1st"}}
    }
  ) {
    edges {
      node {
        id
        name
        attributes
      }
    }
  }
}

# Get variants for specific entity by ID
query {
  variantsCollection(
    filter: {variant_of: {eq: "entity-uuid-here"}}
  ) {
    edges {
      node {
        id
        name
        attributes
      }
    }
  }
}
```

**Step 2: Commit GraphQL examples**

```bash
git add CLAUDE.md
git commit -m "docs: add GraphQL query examples for variants

- Query variants using entity_variants computed field
- Query variants table directly
- Filter variants by JSONB attributes
- Filter variants by variant_of foreign key

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Add SQL Query Examples to Documentation

**Files:**
- Modify: `/home/will/Projects/database-of-things/CLAUDE.md:900-970` (Common SQL Queries section)

**Step 1: Add variant query examples**

Find the "Relationship Queries" section (around line 937) and add after existing examples:

```sql
-- Get all variants of a base entity
SELECT v.*
FROM variants v
WHERE v.variant_of = 'base-entity-uuid';

-- Get variant count per entity
SELECT e.id, e.name, COUNT(v.id) as variant_count
FROM entities e
LEFT JOIN variants v ON v.variant_of = e.id
GROUP BY e.id, e.name
HAVING COUNT(v.id) > 0
ORDER BY variant_count DESC;

-- Find variants with specific attributes
SELECT v.*, e.name as base_name
FROM variants v
JOIN entities e ON v.variant_of = e.id
WHERE v.attributes @> '{"edition": "1st"}'::jsonb;

-- Get entity with all its variants (JSON aggregation)
SELECT
  e.id,
  e.name,
  json_agg(
    json_build_object(
      'id', v.id,
      'name', v.name,
      'attributes', v.attributes
    )
  ) FILTER (WHERE v.id IS NOT NULL) as variants
FROM entities e
LEFT JOIN variants v ON v.variant_of = e.id
WHERE e.id = 'entity-uuid-here'
GROUP BY e.id, e.name;
```

**Step 2: Replace old variant_of relationship example**

Find the query "Get all variants of a base item (variants point to base)" (around line 950) and update with deprecation notice:

```sql
-- DEPRECATED: Old variant_of relationships (use variants table instead)
-- Get all variants of a base item (legacy relationship-based variants)
SELECT e.*
FROM entities e
JOIN relationships r ON r.from_id = e.id
WHERE r.to_id = 'base-item-uuid'
  AND r.type = 'variant_of';

-- NOTE: New variants use the variants table, see examples above
```

**Step 3: Commit SQL query examples**

```bash
git add CLAUDE.md
git commit -m "docs: add SQL query examples for variants table

- Query variants by variant_of foreign key
- Aggregate variant counts per entity
- Filter variants by JSONB attributes
- JSON aggregation of entity with variants
- Mark relationship-based variant queries as deprecated

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Update Entity Examples Documentation

**Files:**
- Modify: `/home/will/Projects/database-of-things/CLAUDE.md:850-895` (Entity Examples section)

**Step 1: Add variant example**

Find the entity examples section and add variant example after existing examples:

```markdown
**Variant with attributes:**
```json
{
  "id": "variant-uuid-here",
  "variant_of": "base-entity-uuid",
  "name": "1st Edition",
  "image_url": "/storage/v1/object/public/images/originals/variant-uuid.jpg",
  "thumbnail_url": "/storage/v1/object/public/images/thumbnails/variant-uuid.webp",
  "attributes": {
    "edition": "1st",
    "print_run": "shadowless",
    "rarity": "rare",
    "condition": "mint"
  },
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```
```

**Step 2: Commit entity examples**

```bash
git add CLAUDE.md
git commit -m "docs: add variant entity example to documentation

Shows variant structure with edition, print_run, rarity metadata

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Update Curator Templates (Optional Pattern)

**Files:**
- Modify: `.curator/templates/import_items.py.template:1-50`

**Step 1: Add variant creation helper function to template**

Find the template file and add this function after the existing helper functions:

```python
def create_variant(self, base_entity_id: str, variant_name: str,
                   image_url: str = None, attributes: dict = None) -> Optional[str]:
    """
    Create a variant of an existing entity.

    Args:
        base_entity_id: UUID of the base entity
        variant_name: Display name for the variant (e.g., "1st Edition")
        image_url: Optional image URL for variant
        attributes: Optional dict of variant-specific metadata

    Returns:
        UUID of created variant, or None if failed
    """
    try:
        variant_data = {
            "variant_of": base_entity_id,
            "name": variant_name,
            "attributes": attributes or {}
        }

        if image_url:
            variant_data["image_url"] = image_url
            # Generate thumbnail path if using Supabase storage
            if image_url.startswith("/storage/"):
                variant_data["thumbnail_url"] = image_url.replace(
                    "/originals/", "/thumbnails/"
                ).replace(image_url.split(".")[-1], "webp")

        result = self.supabase.table("variants").insert(variant_data).execute()

        if result.data:
            variant_id = result.data[0]["id"]
            logger.info(f"Created variant: {variant_name} for {base_entity_id}")
            return variant_id
        else:
            logger.error(f"Failed to create variant: {variant_name}")
            return None

    except Exception as e:
        logger.error(f"Error creating variant {variant_name}: {e}")
        return None
```

**Step 2: Add variant example to template comments**

Add example usage in the template comments:

```python
# Example: Create a card entity and its variants
# base_id = create_entity("card", "Charizard", {...})
# create_variant(base_id, "1st Edition", image_url, {"edition": "1st"})
# create_variant(base_id, "Shadowless", image_url, {"print": "shadowless"})
```

**Step 3: Commit curator template update**

```bash
git add .curator/templates/import_items.py.template
git commit -m "feat: add variant creation helper to curator template

Optional pattern for curators that need variant support.
Includes thumbnail generation and attribute handling.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Update README with Variants Information

**Files:**
- Modify: `/home/will/Projects/database-of-things/README.md:80-120`

**Step 1: Update schema diagram**

Find the schema section in README.md and update to include variants:

```markdown
## Schema

**Entities** - Collections, items, components:
```
entities (id, type, name, year, country, language, image_url, thumbnail_url, attributes)
```

**Variants** - Alternative versions of entities:
```
variants (id, variant_of → entities, name, image_url, thumbnail_url, attributes)
```

**Relationships** - Connections between entities:
```
relationships (id, from_id → entities, to_id → entities, type, order)
```
```

**Step 2: Update relationship types section**

Update the relationships section to reflect variants table:

```markdown
**Variants**:
```
Base Entity ← Variant
(variants table, variant_of foreign key)
```

Note: Legacy variants may exist as entities with `variant_of` relationships.
```

**Step 3: Commit README updates**

```bash
git add README.md
git commit -m "docs: update README with variants table information

- Add variants to schema diagram
- Update relationship types section
- Note about legacy variant relationships

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Verification and Final Testing

**Files:**
- None (verification steps)

**Step 1: Restart Supabase to ensure clean state**

Run: `./bin/supabase stop && ./bin/supabase start`
Expected: All services start successfully

**Step 2: Verify migration is applied**

Run: `./bin/supabase migration list`
Expected: Shows create_variants_table migration as applied

**Step 3: Check GraphQL schema includes variants**

Run: `curl http://127.0.0.1:54321/graphql/v1 -H "apikey: $(./bin/supabase status | grep 'anon key' | awk '{print $3}')" -d '{"query": "{__schema{types{name}}}"}'`
Expected: Response includes "variants" and "variantsCollection" types

**Step 4: Create end-to-end test**

Run complete workflow:
```bash
# Create entity
ENTITY_ID=$(docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -t -c "
INSERT INTO entities (name, type) VALUES ('Final Test Entity', 'card') RETURNING id;" | tr -d ' \n\r')

# Create variant
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
INSERT INTO variants (variant_of, name, attributes)
VALUES ('$ENTITY_ID', 'Test Variant', '{\"test\": true}'::jsonb);"

# Query via GraphQL
curl -s http://127.0.0.1:54321/graphql/v1 \
  -H "apikey: $(./bin/supabase status | grep 'anon key' | awk '{print $3}')" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"{ entitiesCollection(filter: {name: {eq: \\\"Final Test Entity\\\"}}) { edges { node { id name entity_variants { id name attributes } } } } }\"}" | jq

# Cleanup
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
DELETE FROM entities WHERE id = '$ENTITY_ID';"
```
Expected: GraphQL query returns entity with nested variant, cleanup succeeds

**Step 5: Run all documentation verification**

Run: `git diff main --stat`
Expected: Shows changes to:
- supabase/migrations/ (new migration)
- CLAUDE.md (schema, examples, queries)
- README.md (schema diagram)
- .curator/templates/ (optional variant helper)
- docs/plans/ (design and implementation docs)

**Step 6: Final commit for verification**

```bash
git add -A
git commit -m "test: verify variants table end-to-end functionality

All systems verified:
- Migration applied successfully
- GraphQL schema includes variants
- CRUD operations working
- Cascade deletes functioning
- Documentation updated

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Success Criteria

✅ Variants table created with proper schema and indexes
✅ Foreign key constraint enforces mandatory parent
✅ CASCADE delete removes variants when base entity deleted
✅ GraphQL exposes `entity_variants` computed field
✅ GraphQL exposes `variantsCollection` query
✅ Can query variants by attributes (JSONB filtering)
✅ Documentation updated in CLAUDE.md and README.md
✅ Curator template includes optional variant pattern
✅ All changes committed to git with descriptive messages

## Notes for Implementation

- **Safe migration**: Use `./scripts/safe-migrate push` to ensure automatic backup
- **GraphQL cache**: May need to restart Supabase after migration for GraphQL schema updates
- **API keys**: Get from `./bin/supabase status | grep "anon key"`
- **UUID handling**: Use `-t` flag with psql for clean UUID output
- **Curator updates**: Variants are optional - curators can still create entities as before

## References

- Design document: `docs/plans/2025-11-12-variants-table-design.md`
- CLAUDE.md: Database architecture and query examples
- Supabase docs: GraphQL computed fields via PostgreSQL functions
