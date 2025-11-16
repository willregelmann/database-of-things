# GraphQL API Documentation Design

**Date:** 2025-11-16
**Status:** Approved
**Audience:** External developers + AI assistants

## Overview

Document the Supabase GraphQL API comprehensively for two distinct audiences:
1. **External developers** - Building apps that consume collectibles data
2. **AI assistants** - Claude and other LLMs querying the database

## Goals

- Provide complete API coverage (all tables, fields, functions, computed fields)
- Enable immediate hands-on experimentation with real seed data examples
- Optimize for both human learning and AI consumption
- Make reverse image search and semantic search easily discoverable

## Design Decisions

### Two-Document Approach

Following the established curator documentation pattern (`curator-user-guide.md` + `curator-technical-reference.md`), we split documentation by audience needs:

**`docs/graphql-user-guide.md`** - External developer tutorial
- Tutorial-style progression with narrative
- Real-world use case examples
- Setup and authentication walkthrough
- Best practices and troubleshooting

**`docs/graphql-api-reference.md`** - AI-optimized reference
- Complete schema documentation (structured tables)
- Exhaustive query catalog by table/operation
- Token-efficient format (minimal prose, maximum structure)
- Easy scanning and pattern matching

### Content Organization (Hybrid Approach)

Both documents use hybrid organization:
1. **Schema reference first** - Complete table definitions, fields, types
2. **Query patterns by task** - Grouped by common operations

**User Guide emphasis:** Lighter schema overview, heavier task-oriented narrative
**API Reference emphasis:** Complete schema specs, comprehensive query examples

### Example Data Strategy

All examples use **real seed data** from `scripts/seed-sample-data.py`:

**Collections:**
- Pokemon TCG (Base Set, Jungle, Fossil, Scarlet & Violet sub-collections)
- Power Rangers Toys (Mighty Morphin series)
- Marvel Comics (Amazing Spider-Man series)
- Video Games (Pokemon games)

**Items:**
- Charizard, Blastoise, Venusaur cards
- Megazord figures
- Spider-Man comics
- Pokemon Red/Blue games

**Benefits:**
- Copy-paste executable examples after seeding
- Demonstrates graph relationships naturally
- AI assistants see realistic data patterns
- Developers can verify results immediately

## Document Structures

### graphql-user-guide.md (External Developers)

```markdown
# GraphQL API User Guide

## Introduction
- What the API provides
- Who it's for
- Key use cases (price tracking, collection management, market research)

## Quick Start
- Authentication (apikey header)
- Endpoint URLs (local vs production)
- Making your first query
- Seeding sample data for testing

## Schema Overview
- High-level table relationships diagram
- Key concepts (entities, relationships, pure graph model)
- JSONB attributes philosophy
- Image storage patterns

## Common Tasks

### Browsing Collections
- Get all collections
- Get collection hierarchy
- Get items in a collection (via relationships)
- Ordered collections

### Searching Items
- Text search (fuzzy matching with trigram)
- Semantic search (vector embeddings, 384-dim)
- Filter by type, year, language, attributes
- Similarity scoring

### Working with Variants and Components
- Access via computed fields (entity_variants, entity_components)
- Direct table queries
- Filtering by variant attributes
- Ordered components with quantities

### Finding Similar Images
- Reverse image search (CLIP embeddings, 512-dim)
- Primary vs additional images
- Image URLs (originals vs thumbnails)
- Parent information in results

### Traversing Relationships
- Forward traversal (what does this contain?)
- Reverse traversal (what contains this?)
- Multi-level hierarchy navigation
- Recursive CTE patterns for deep graphs

## Pagination & Performance
- Page size limits (default 20, max 100)
- Cursor-based pagination (edges/nodes pattern)
- Best practices for large collections
- When to use limit vs pagination

## Error Handling
- Common errors and solutions
- Authentication failures
- Invalid UUIDs
- Missing embeddings
- Empty results vs errors

## Examples Gallery
- Real-world scenarios with complete queries
- Multi-step workflows
- Complex filtering patterns
```

### graphql-api-reference.md (AI Assistants)

```markdown
# GraphQL API Reference

## Schema Reference

### entities Table
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| type | text | NOT NULL | Entity type |
| name | text | NOT NULL | Display name |
| year | integer | NULL | Universal year |
| country | char(2) | NULL | ISO country code |
| language | char(2) | NULL | ISO 639-1 language |
| primary_image_id | uuid | NULL | Foreign key to images |
| source_url | text | NULL | Data provenance URL |
| name_embedding | vector(384) | NULL | Semantic search vector |
| external_ids | jsonb | NULL | External system IDs |
| attributes | jsonb | NULL | Flexible metadata |
| created_at | timestamptz | NOT NULL | Creation timestamp |
| updated_at | timestamptz | NOT NULL | Update timestamp |

**Indexes:**
- Primary key: id
- GIN: attributes, external_ids
- GIN trigram: name
- HNSW: name_embedding (cosine distance)
- B-tree: type, language (partial, non-null only)

### relationships Table
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| from_id | uuid | NOT NULL | Source entity FK |
| to_id | uuid | NOT NULL | Target entity FK |
| type | text | NOT NULL | Relationship type |
| order | integer | NULL | Sort order |
| created_at | timestamptz | NOT NULL | Creation timestamp |

**Constraints:**
- UNIQUE (from_id, to_id, type)

**Indexes:**
- Composite: (from_id, type), (to_id, type)
- Partial: order (non-null only)

### variants Table
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| variant_of | uuid | NOT NULL | Base entity FK (CASCADE) |
| name | text | NOT NULL | Variant name |
| primary_image_id | uuid | NULL | Foreign key to images |
| attributes | jsonb | NULL | Variant metadata |
| created_at | timestamptz | NOT NULL | Creation timestamp |
| updated_at | timestamptz | NOT NULL | Update timestamp |

**Indexes:**
- Foreign key: variant_of
- GIN: attributes

### components Table
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| component_of | uuid | NOT NULL | Parent entity FK (CASCADE) |
| name | text | NOT NULL | Component name |
| quantity | integer | NOT NULL | Quantity (default 1) |
| order | integer | NULL | Display order |
| primary_image_id | uuid | NULL | Foreign key to images |
| attributes | jsonb | NULL | Component metadata |
| created_at | timestamptz | NOT NULL | Creation timestamp |
| updated_at | timestamptz | NOT NULL | Update timestamp |

**Indexes:**
- Foreign key: component_of
- Partial: order (non-null only)
- GIN: attributes

### images Table
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| image_url | text | NOT NULL | Image URL path |
| thumbnail_url | text | NULL | Thumbnail path |
| embedding | vector(512) | NULL | CLIP embedding |
| source_url | text | NULL | Attribution URL |
| created_at | timestamptz | NOT NULL | Creation timestamp |
| updated_at | timestamptz | NOT NULL | Update timestamp |

**Indexes:**
- HNSW: embedding (cosine distance)

## Core Queries

### Entities

**Get all collections:**
```graphql
query {
  entitiesCollection(filter: {type: {eq: "collection"}}) {
    edges {
      node {
        id
        name
        type
        year
        primary_image {
          image_url
          thumbnail_url
        }
      }
    }
  }
}
```

**Get entity by ID:**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "uuid-here"}}) {
    edges {
      node {
        id
        name
        type
        year
        country
        language
        attributes
        external_ids
      }
    }
  }
}
```

**Filter by multiple criteria:**
```graphql
query {
  entitiesCollection(
    filter: {
      type: {eq: "card"}
      year: {gte: 1999}
      language: {eq: "en"}
    }
  ) {
    edges {
      node {
        id
        name
        year
      }
    }
  }
}
```

**Text search (fuzzy):**
```graphql
query {
  entitiesCollection(filter: {name: {ilike: "%Charizard%"}}) {
    edges {
      node {
        id
        name
        type
      }
    }
  }
}
```

### Relationships

**Get collection contents (parent → children):**
```graphql
query {
  relationshipsCollection(
    filter: {
      from_id: {eq: "collection-uuid"}
      type: {eq: "contains"}
    }
    orderBy: {order: AscNullsLast}
  ) {
    edges {
      node {
        to_id
        order
        entities {
          id
          name
          type
          primary_image {
            thumbnail_url
          }
        }
      }
    }
  }
}
```

**Reverse lookup (what contains this?):**
```graphql
query {
  relationshipsCollection(
    filter: {
      to_id: {eq: "item-uuid"}
      type: {eq: "contains"}
    }
  ) {
    edges {
      node {
        from_id
        entities {
          id
          name
          type
        }
      }
    }
  }
}
```

### Variants & Components

**Get entity with variants (computed field):**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "charizard-uuid"}}) {
    edges {
      node {
        id
        name
        entity_variants {
          edges {
            node {
              id
              name
              primary_image {
                image_url
                thumbnail_url
              }
              attributes
            }
          }
        }
      }
    }
  }
}
```

**Get entity with components (computed field):**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "megazord-uuid"}}) {
    edges {
      node {
        id
        name
        entity_components {
          edges {
            node {
              id
              name
              quantity
              order
              primary_image {
                thumbnail_url
              }
            }
          }
        }
      }
    }
  }
}
```

**Direct variant query:**
```graphql
query {
  variantsCollection(
    filter: {variant_of: {eq: "base-entity-uuid"}}
  ) {
    edges {
      node {
        id
        name
        attributes
        created_at
      }
    }
  }
}
```

### Images

**Get entity with all images:**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "uuid"}}) {
    edges {
      node {
        id
        name
        primary_image {
          id
          image_url
          thumbnail_url
          source_url
        }
        entity_additional_images {
          edges {
            node {
              id
              image_url
              thumbnail_url
            }
          }
        }
      }
    }
  }
}
```

## Search Functions

### semantic_search

**Signature:**
```sql
semantic_search(
  query_embedding vector(384),
  entity_type_filter text DEFAULT NULL,
  result_limit integer DEFAULT 20
)
RETURNS TABLE (
  id uuid,
  name text,
  type text,
  year integer,
  country char(2),
  language char(2),
  attributes jsonb,
  similarity float
)
```

**GraphQL Usage:**
```graphql
query {
  semantic_search(
    args: {
      query_embedding: "[0.123, 0.456, ...]"
      entity_type_filter: "card"
      result_limit: 20
    }
  ) {
    id
    name
    type
    similarity
  }
}
```

**Parameters:**
- `query_embedding`: 384-dimensional vector (from sentence-transformers model)
- `entity_type_filter`: Optional type filter (e.g., "card", "figure")
- `result_limit`: Max results (default 20)

**Returns:**
- Entities ranked by cosine similarity (1 - distance)
- Only returns entities with embeddings
- Similarity score 0-1 (higher = more similar)

### search_by_text

**Signature:**
```sql
search_by_text(
  query_text text,
  entity_type_filter text DEFAULT NULL,
  result_limit integer DEFAULT 20
)
RETURNS TABLE (
  id uuid,
  name text,
  type text,
  similarity float
)
```

**GraphQL Usage:**
```graphql
query {
  search_by_text(
    args: {
      query_text: "fire dragon pokemon"
      entity_type_filter: "card"
      result_limit: 20
    }
  ) {
    id
    name
    type
    similarity
  }
}
```

**Parameters:**
- `query_text`: Plain text search query
- `entity_type_filter`: Optional type filter
- `result_limit`: Max results (default 20)

**Limitations:**
- Uses trigram matching to find similar entity first
- Then uses that entity's embedding for semantic search
- Fails for synonyms/variations ("and" vs "&")
- **Recommendation:** Use CLI tool `scripts/semantic-search` instead

### image_search

**Signature:**
```sql
image_search(
  query_embedding vector(512),
  result_limit int DEFAULT 20
)
RETURNS TABLE (
  image_id uuid,
  image_url text,
  thumbnail_url text,
  similarity float,
  parent_type text,
  parent_id uuid,
  parent_name text
)
```

**GraphQL Usage:**
```graphql
query {
  image_search(
    args: {
      query_embedding: "[0.1, 0.2, ...]"
      result_limit: 20
    }
  ) {
    image_id
    image_url
    thumbnail_url
    similarity
    parent_type
    parent_id
    parent_name
  }
}
```

**Parameters:**
- `query_embedding`: 512-dimensional CLIP embedding
- `result_limit`: Max results (default 20)

**Returns:**
- Images ranked by visual similarity
- Includes parent information (entity/variant/component)
- One row per parent (image with 2 parents = 2 rows)
- Similarity score 0-1 (higher = more similar)

## Computed Fields

### entity_variants(entity_row entities)
Returns all variants of an entity.

**Usage:**
```graphql
query {
  entitiesCollection {
    edges {
      node {
        id
        name
        entity_variants {
          edges {
            node {
              id
              name
              attributes
            }
          }
        }
      }
    }
  }
}
```

### entity_components(entity_row entities)
Returns all components of an entity.

**Usage:**
```graphql
query {
  entitiesCollection {
    edges {
      node {
        id
        name
        entity_components {
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
    }
  }
}
```

### entity_primary_image(entity_row entities)
Returns the primary image for an entity.

**Usage:**
```graphql
query {
  entitiesCollection {
    edges {
      node {
        id
        name
        primary_image {
          id
          image_url
          thumbnail_url
        }
      }
    }
  }
}
```

### entity_additional_images(entity_row entities)
Returns additional images for an entity (ordered).

**Usage:**
```graphql
query {
  entitiesCollection {
    edges {
      node {
        id
        name
        entity_additional_images {
          edges {
            node {
              id
              image_url
              thumbnail_url
            }
          }
        }
      }
    }
  }
}
```

**Similar computed fields exist for variants and components:**
- variant_primary_image, variant_additional_images
- component_primary_image, component_additional_images

## Filtering & Sorting

### Filter Operators

**Text:**
- `eq`: Equals
- `neq`: Not equals
- `like`: SQL LIKE (case-sensitive)
- `ilike`: Case-insensitive LIKE
- `in`: In array
- `is`: IS NULL

**Numeric:**
- `eq`, `neq`, `lt`, `lte`, `gt`, `gte`
- `in`: In array

**JSONB:**
- `contains`: JSONB @> operator
- `containedBy`: JSONB <@ operator

**Examples:**
```graphql
# Text filtering
filter: {name: {ilike: "%pokemon%"}}
filter: {type: {in: ["card", "figure"]}}
filter: {language: {is: "NULL"}}

# Numeric filtering
filter: {year: {gte: 2000}}
filter: {year: {in: [1999, 2000, 2001]}}

# JSONB filtering
filter: {attributes: {contains: {hp: 120}}}
filter: {external_ids: {contains: {tcgplayer: "base1-4"}}}

# Combined filters
filter: {
  type: {eq: "card"}
  year: {gte: 1999}
  language: {eq: "en"}
}
```

### Sorting

**Available orders:**
- `AscNullsFirst`, `AscNullsLast`
- `DescNullsFirst`, `DescNullsLast`

**Examples:**
```graphql
orderBy: {name: AscNullsLast}
orderBy: {year: DescNullsFirst}
orderBy: [{year: Desc}, {name: Asc}]
```

## Pagination Patterns

### Edges/Nodes Structure

All collections return:
```graphql
{
  edges {
    node {
      # Entity fields
    }
    cursor  # For pagination
  }
  pageInfo {
    hasNextPage
    hasPreviousPage
    startCursor
    endCursor
  }
}
```

### Cursor-Based Pagination

**First page:**
```graphql
query {
  entitiesCollection(first: 20) {
    edges {
      node { id name }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

**Next page:**
```graphql
query {
  entitiesCollection(first: 20, after: "cursor-from-previous-page") {
    edges {
      node { id name }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### Limits
- Default page size: 20
- Maximum page size: 100
- Configured in migration `20251023185803_increase_graphql_page_limit.sql`

## Complete Query Catalog

### Basic Entity Operations
- Get all entities
- Get by ID
- Get by type
- Get by name (exact/fuzzy)
- Filter by year/country/language
- Filter by attributes (JSONB)
- Filter by external IDs

### Relationship Operations
- Get outbound relationships (from_id)
- Get inbound relationships (to_id)
- Filter by relationship type
- Ordered relationships
- Multi-level traversal

### Variant Operations
- Get variants via computed field
- Get variants via direct query
- Filter by variant_of
- Filter by variant attributes

### Component Operations
- Get components via computed field
- Get components via direct query
- Filter by component_of
- Ordered components

### Image Operations
- Get primary image
- Get additional images
- Get all images for entity
- Reverse image search
- Filter by image embeddings

### Search Operations
- Semantic search (vector)
- Text-based search
- Fuzzy name matching
- Full-text search
- Image similarity search

### Advanced Patterns
- Recursive hierarchy traversal
- Many-to-many relationships
- Cross-collection relationships
- Aggregate queries
- Combined filters (type + year + language)
```

## Implementation Notes

### Extracting Real UUIDs

Before writing examples, we'll:
1. Start Supabase locally (`./bin/supabase start`)
2. Run seed script (`python3 scripts/seed-sample-data.py`)
3. Query for actual UUIDs:
```sql
SELECT id, name, type FROM entities
WHERE name IN ('Pokemon TCG', 'Charizard', 'Megazord')
ORDER BY name;
```
4. Replace placeholder UUIDs in examples

### Validation

Test all query examples against local instance:
- Copy each GraphQL query
- Execute via GraphQL endpoint
- Verify results match documentation
- Check error cases (invalid UUIDs, missing embeddings)

### Maintenance

When schema changes:
- Update schema reference tables
- Add new query examples
- Update migration references
- Test all examples still work
- Increment documentation version

## Success Criteria

**User Guide:**
- External developer can set up and run first query in <5 minutes
- Each common task has working example with real data
- Troubleshooting section covers 90% of common errors
- Examples are copy-paste executable after seeding

**API Reference:**
- Every table completely documented with all fields
- Every search function documented with all parameters
- All computed fields with usage examples
- AI assistants can construct correct queries without trial-and-error
- Token-efficient format (minimal scanning needed)

## Next Steps

After design approval:
1. Start local Supabase and seed data
2. Extract real UUIDs for examples
3. Write `docs/graphql-user-guide.md`
4. Write `docs/graphql-api-reference.md`
5. Test all examples against local instance
6. Commit documentation
7. Optionally: Add to CLAUDE.md references
