# Components Table Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a dedicated components table for tracking physical pieces that can be removed/lost from collectible items, following the variants table pattern with quantity tracking.

**Architecture:** New `components` table with NOT NULL foreign key to entities, CASCADE delete, quantity field, optional ordering, GraphQL computed field for querying components through parent entities.

**Tech Stack:** PostgreSQL, Supabase migrations, PostgREST/GraphQL

---

## Task 1: Create Migration File

**Files:**
- Create: `supabase/migrations/20251113000000_create_components_table.sql`

**Step 1: Create migration file**

Create the migration file with the exact schema from the design:

```bash
./bin/supabase migration new create_components_table
```

This will create a timestamped file. Note the actual filename for the next steps.

**Step 2: Write the migration SQL**

Write this content to the created migration file:

```sql
-- Create components table
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

-- Add indexes for performance
CREATE INDEX idx_components_component_of ON components(component_of);
CREATE INDEX idx_components_order ON components("order") WHERE "order" IS NOT NULL;
CREATE INDEX idx_components_attributes ON components USING GIN(attributes);

-- Add PostgreSQL function for GraphQL computed field
CREATE OR REPLACE FUNCTION entity_components(entity_row entities)
RETURNS SETOF components AS $$
  SELECT * FROM components
  WHERE component_of = entity_row.id
  ORDER BY COALESCE("order", 999999), name
$$ LANGUAGE SQL STABLE;

-- Tell PostgREST/GraphQL about the relationship
COMMENT ON FUNCTION entity_components IS
  '@graphql({"totalCount": {"enabled": true}})';
```

**Step 3: Verify migration file syntax**

```bash
cat supabase/migrations/*_create_components_table.sql
```

Expected: File content matches the SQL above exactly.

**Step 4: Commit migration file**

```bash
git add supabase/migrations/*_create_components_table.sql
git commit -m "feat: add components table migration

Create dedicated components table for tracking physical pieces.
Includes quantity tracking, optional ordering, and GraphQL computed field.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Apply Migration Locally

**Files:**
- Modify: Database schema (via migration)

**Step 1: Ensure Supabase is running**

```bash
./bin/supabase status
```

Expected: Shows "supabase local development setup is running"

If not running:
```bash
./bin/supabase start
```

**Step 2: Apply migration**

```bash
./scripts/safe-migrate push
```

Expected: Output shows migration applied successfully with automatic backup created.

**Step 3: Verify table creation**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\d components"
```

Expected: Shows table structure with all columns (id, component_of, name, quantity, order, image_url, thumbnail_url, attributes, created_at, updated_at).

**Step 4: Verify indexes**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\d+ components"
```

Expected: Shows three indexes (idx_components_component_of, idx_components_order, idx_components_attributes).

**Step 5: Verify function creation**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\df entity_components"
```

Expected: Shows function exists with return type SETOF components.

---

## Task 3: Test Basic CRUD Operations

**Files:**
- None (interactive testing)

**Step 1: Create test entity**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
INSERT INTO entities (id, name, type)
VALUES ('00000000-0000-0000-0000-000000000001', 'Test Megazord', 'toy')
RETURNING id, name;
EOF
```

Expected: Returns the inserted entity ID and name.

**Step 2: Insert component with default quantity**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
INSERT INTO components (component_of, name, "order")
VALUES ('00000000-0000-0000-0000-000000000001', 'Red Ranger Zord', 1)
RETURNING id, name, quantity, "order";
EOF
```

Expected: Returns component with quantity=1 (default), order=1.

**Step 3: Insert component with custom quantity**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
INSERT INTO components (component_of, name, quantity)
VALUES ('00000000-0000-0000-0000-000000000001', 'Wooden Tokens', 50)
RETURNING id, name, quantity;
EOF
```

Expected: Returns component with quantity=50.

**Step 4: Query all components for entity**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
SELECT name, quantity, "order"
FROM components
WHERE component_of = '00000000-0000-0000-0000-000000000001'
ORDER BY COALESCE("order", 999999), name;
EOF
```

Expected: Returns two components in order (Red Ranger Zord first with order=1, then Wooden Tokens).

---

## Task 4: Test GraphQL Computed Field

**Files:**
- None (interactive testing)

**Step 1: Get GraphQL endpoint and API key**

```bash
./bin/supabase status | grep -E "(GraphQL URL|anon key)"
```

Expected: Shows GraphQL URL (http://127.0.0.1:54321/graphql/v1) and anon key.

**Step 2: Test entity_components computed field**

Create a test file to make this easier:

```bash
cat > /tmp/test_components_graphql.sh << 'SCRIPT'
#!/bin/bash
GRAPHQL_URL="http://127.0.0.1:54321/graphql/v1"
API_KEY=$(./bin/supabase status | grep "anon key" | awk '{print $3}')

curl -X POST "$GRAPHQL_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: $API_KEY" \
  -d '{
    "query": "query { entitiesCollection(filter: {id: {eq: \"00000000-0000-0000-0000-000000000001\"}}) { edges { node { id name entity_components { id name quantity order } } } } }"
  }' | python3 -m json.tool
SCRIPT

chmod +x /tmp/test_components_graphql.sh
/tmp/test_components_graphql.sh
```

Expected: JSON response showing the Test Megazord entity with entity_components array containing Red Ranger Zord and Wooden Tokens.

**Step 3: Test direct components table query**

```bash
GRAPHQL_URL="http://127.0.0.1:54321/graphql/v1"
API_KEY=$(./bin/supabase status | grep "anon key" | awk '{print $3}')

curl -X POST "$GRAPHQL_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: $API_KEY" \
  -d '{
    "query": "query { componentsCollection(filter: {component_of: {eq: \"00000000-0000-0000-0000-000000000001\"}}) { edges { node { id name quantity order } } } }"
  }' | python3 -m json.tool
```

Expected: JSON response showing components directly from components table.

---

## Task 5: Test Cascade Delete

**Files:**
- None (interactive testing)

**Step 1: Verify components exist before delete**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
SELECT COUNT(*) FROM components WHERE component_of = '00000000-0000-0000-0000-000000000001';
EOF
```

Expected: Returns count=2.

**Step 2: Delete parent entity**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
DELETE FROM entities WHERE id = '00000000-0000-0000-0000-000000000001';
EOF
```

Expected: DELETE 1

**Step 3: Verify components were cascade deleted**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
SELECT COUNT(*) FROM components WHERE component_of = '00000000-0000-0000-0000-000000000001';
EOF
```

Expected: Returns count=0. Components automatically deleted when parent removed.

---

## Task 6: Update CLAUDE.md Documentation (Part 1: Schema)

**Files:**
- Modify: `CLAUDE.md:200-300` (Database Architecture section)

**Step 1: Find variants table documentation**

```bash
grep -n "variants.*Alternative versions" CLAUDE.md
```

This shows where the variants table is documented. Add components documentation after it.

**Step 2: Add components table schema**

After the variants table documentation, add:

```markdown
**`components`** - Physical pieces that can be removed/lost from items:
- `id` (UUID): Primary key
- `component_of` (UUID): Foreign key to entities (NOT NULL, CASCADE delete)
- `name` (TEXT): Component name (e.g., "Red Ranger Zord", "Wooden Tokens")
- `quantity` (INTEGER): How many of this component (default 1)
- `order` (INTEGER): Optional sort order for display
- `image_url` (TEXT): Image URL path (same pattern as entities)
- `thumbnail_url` (TEXT): Pre-generated thumbnail path
- `attributes` (JSONB): Component metadata (condition notes, materials, physical specs)
- Timestamps: `created_at`, `updated_at`
```

**Step 3: Verify formatting**

```bash
grep -A 10 "components.*Physical pieces" CLAUDE.md
```

Expected: Shows the newly added components documentation.

---

## Task 7: Update CLAUDE.md Documentation (Part 2: Patterns)

**Files:**
- Modify: `CLAUDE.md` (Design Patterns section)

**Step 1: Find Variants Architecture section**

```bash
grep -n "Variants Architecture:" CLAUDE.md
```

**Step 2: Add Components Architecture section**

After the Variants Architecture section, add:

```markdown
**Components Architecture**:
- Components stored in dedicated table, not as entities
- `component_of` foreign key is mandatory (NOT NULL)
- CASCADE delete ensures components removed when parent entity deleted
- Access via `entity_components()` GraphQL computed field
- Quantity tracking for bulk items (e.g., 50 tokens vs. 1 unique piece)
- Optional ordering for assembly instructions or logical grouping
- Legacy: Some older component data may exist as entities with `part_of` relationships
```

**Step 3: Update Relationship Types section**

Find the relationship types documentation:

```bash
grep -n "part_of:" CLAUDE.md
```

Update the `part_of` entry to mark it as deprecated:

```markdown
- `part_of`: **DEPRECATED** - Use components table instead
  - Legacy: Some old component data stored as entity relationships
  - New components: Use dedicated components table
```

---

## Task 8: Update CLAUDE.md Documentation (Part 3: Indexes)

**Files:**
- Modify: `CLAUDE.md` (Indexes section)

**Step 1: Find variant indexes section**

```bash
grep -n "Variant lookups:" CLAUDE.md
```

**Step 2: Add component indexes section**

After the variant indexes, add:

```markdown
**Component lookups**:
- `idx_components_component_of`: Find all components of a parent entity
- `idx_components_order`: Sort by order (partial index, only non-null values)
- `idx_components_attributes`: JSONB queries on component metadata (GIN)
```

---

## Task 9: Update CLAUDE.md Documentation (Part 4: Examples)

**Files:**
- Modify: `CLAUDE.md` (GraphQL Examples and Common SQL Queries sections)

**Step 1: Add GraphQL example for components**

Find the variants GraphQL examples section and add:

```markdown
# Query components of an entity (using computed field)
query {
  entitiesCollection(filter: {id: {eq: "megazord-uuid"}}) {
    edges {
      node {
        id
        name
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

# Query all components directly
query {
  componentsCollection {
    edges {
      node {
        id
        name
        component_of
        quantity
        attributes
      }
    }
  }
}

# Get components for specific entity by ID
query {
  componentsCollection(
    filter: {component_of: {eq: "entity-uuid-here"}}
  ) {
    edges {
      node {
        id
        name
        quantity
        order
      }
    }
  }
}
```

**Step 2: Add SQL query examples for components**

Find the Common SQL Queries section and add component examples:

```sql
-- Get all components for an item (ordered)
SELECT * FROM components
WHERE component_of = 'item-uuid'
ORDER BY COALESCE("order", 999999), name;

-- Check if item has all required components (with quantities)
SELECT name, quantity
FROM components
WHERE component_of = 'item-uuid'
ORDER BY COALESCE("order", 999999), name;

-- Get component count per entity
SELECT e.id, e.name, COUNT(c.id) as component_count
FROM entities e
LEFT JOIN components c ON c.component_of = e.id
GROUP BY e.id, e.name
HAVING COUNT(c.id) > 0
ORDER BY component_count DESC;

-- Find components with specific attributes
SELECT c.*, e.name as parent_name
FROM components c
JOIN entities e ON c.component_of = e.id
WHERE c.attributes @> '{"material": "plastic"}'::jsonb;

-- Get entity with all its components (JSON aggregation)
SELECT
  e.id,
  e.name,
  json_agg(
    json_build_object(
      'id', c.id,
      'name', c.name,
      'quantity', c.quantity,
      'order', c.order
    )
  ) FILTER (WHERE c.id IS NOT NULL) as components
FROM entities e
LEFT JOIN components c ON c.component_of = e.id
WHERE e.id = 'entity-uuid-here'
GROUP BY e.id, e.name;
```

---

## Task 10: Commit Documentation Updates

**Files:**
- Modified: `CLAUDE.md`

**Step 1: Review changes**

```bash
git diff CLAUDE.md
```

Expected: Shows additions for components table schema, architecture patterns, indexes, and query examples.

**Step 2: Commit documentation**

```bash
git add CLAUDE.md
git commit -m "docs: add components table to CLAUDE.md

Document components table schema, architecture patterns, indexes, and
query examples. Mark part_of relationships as deprecated in favor of
dedicated components table.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: Create Real-World Test Case

**Files:**
- None (interactive testing)

**Step 1: Create a board game entity**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
INSERT INTO entities (id, name, type, year)
VALUES (
  '10000000-0000-0000-0000-000000000001',
  'Catan Board Game',
  'board_game',
  1995
)
RETURNING id, name;
EOF
```

**Step 2: Add components with varying quantities and order**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
INSERT INTO components (component_of, name, quantity, "order") VALUES
  ('10000000-0000-0000-0000-000000000001', 'Game Board', 1, 1),
  ('10000000-0000-0000-0000-000000000001', 'Resource Cards', 95, 2),
  ('10000000-0000-0000-0000-000000000001', 'Development Cards', 25, 3),
  ('10000000-0000-0000-0000-000000000001', 'Wooden Settlements', 20, 4),
  ('10000000-0000-0000-0000-000000000001', 'Wooden Cities', 16, 5),
  ('10000000-0000-0000-0000-000000000001', 'Wooden Roads', 60, 6),
  ('10000000-0000-0000-0000-000000000001', 'Number Tokens', 18, 7),
  ('10000000-0000-0000-0000-000000000001', 'Dice', 2, 8)
RETURNING name, quantity, "order";
EOF
```

Expected: Returns 8 components in order.

**Step 3: Query via GraphQL computed field**

```bash
GRAPHQL_URL="http://127.0.0.1:54321/graphql/v1"
API_KEY=$(./bin/supabase status | grep "anon key" | awk '{print $3}')

curl -X POST "$GRAPHQL_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: $API_KEY" \
  -d '{
    "query": "query { entitiesCollection(filter: {name: {eq: \"Catan Board Game\"}}) { edges { node { id name type year entity_components { name quantity order } } } } }"
  }' | python3 -m json.tool
```

Expected: JSON showing Catan Board Game with all 8 components in correct order.

**Step 4: Verify ordering behavior**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
SELECT name, quantity, COALESCE("order", 999999) as effective_order
FROM components
WHERE component_of = '10000000-0000-0000-0000-000000000001'
ORDER BY COALESCE("order", 999999), name;
EOF
```

Expected: Components listed with Game Board first (order=1) through Dice last (order=8).

---

## Task 12: Final Verification

**Files:**
- None (verification)

**Step 1: Verify migration applied**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
SELECT version FROM supabase_migrations.schema_migrations
WHERE version LIKE '%create_components_table%';
EOF
```

Expected: Shows the migration version.

**Step 2: Verify GraphQL schema includes components**

Open http://127.0.0.1:54323 (Supabase Studio), navigate to API Docs, and verify:
- `componentsCollection` query exists
- `entity_components` field appears on entities type

**Step 3: Run full test suite (if exists)**

```bash
# Check if there are tests to run
if [ -f package.json ]; then
  npm test 2>/dev/null || echo "No tests configured"
elif [ -f pyproject.toml ]; then
  pytest 2>/dev/null || echo "No tests configured"
else
  echo "No test suite found - manual testing only"
fi
```

**Step 4: Verify documentation completeness**

```bash
# Check that components are documented in all key sections
grep -c "components" CLAUDE.md
```

Expected: Multiple matches (schema, patterns, indexes, examples).

**Step 5: Clean up test data**

```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres << 'EOF'
DELETE FROM entities WHERE id IN (
  '00000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001'
);
EOF
```

Expected: Test entities and their components (cascade deleted) removed.

---

## Verification Checklist

- [ ] Migration file created and applied
- [ ] Components table exists with correct schema
- [ ] All three indexes created
- [ ] GraphQL function `entity_components` exists
- [ ] Basic CRUD operations work
- [ ] Quantity tracking works (default 1, custom values)
- [ ] Optional ordering works (ordered items first, then alphabetical)
- [ ] CASCADE delete works (parent deleted → components removed)
- [ ] GraphQL computed field works
- [ ] Direct components table queries work
- [ ] CLAUDE.md updated (schema, patterns, indexes, examples)
- [ ] Real-world test case passes (board game with 8 components)
- [ ] Test data cleaned up

---

## Notes

**TDD not applicable:** This is primarily schema and infrastructure work. Testing is done through:
- Direct SQL verification
- GraphQL query testing
- Manual cascade delete verification

**Frequent commits:** Each major section (migration, documentation updates) gets its own commit.

**DRY:** Migration SQL follows exact pattern from variants table.

**YAGNI:** No features beyond the approved design (no nesting, no sharing, no complex validation).

**References:**
- Design doc: `docs/plans/2025-11-13-components-table-design.md`
- Variants migration: `supabase/migrations/20251112171928_create_variants_table.sql`
- @superpowers:verification-before-completion for final checks
