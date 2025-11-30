# GraphQL API Reference

Complete GraphQL API reference for the collectibles database. Optimized for AI assistants and automated tooling.

## Quick Reference

**Endpoint:** `http://127.0.0.1:54321/graphql/v1` (local) or `https://yourproject.supabase.co/graphql/v1` (production)

**Authentication:** Header `apikey: your-anon-key`

**Page limits:** Default 20, max 100

**Tables:** entities, relationships, variants, components, images

**Search functions:** semantic_search, search_by_text, image_search

**Computed fields:** entity_variants, entity_components, entity_primary_image, entity_additional_images (+ variant/component equivalents)

## Schema Reference

### entities Table

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| type | text | NOT NULL | Entity type (collection, card, figure, comic, video_game, etc.) |
| name | text | NOT NULL | Display name |
| year | integer | NULL | Universal year attribute |
| country | char(2) | NULL | ISO 3166-1 alpha-2 country code |
| language | char(2) | NULL | ISO 639-1 language code |
| primary_image_id | uuid | NULL | Foreign key to images table |
| source_url | text | NULL | Source URL for data provenance |
| name_embedding | vector(384) | NULL | Sentence-transformer embedding for semantic search |
| external_ids | jsonb | NULL | External system IDs (e.g., {"tcgplayer": "base1-4"}) |
| attributes | jsonb | NULL | Flexible metadata (hp, rarity, description, etc.) |
| created_at | timestamptz | NOT NULL | Creation timestamp |
| updated_at | timestamptz | NOT NULL | Last update timestamp |

**Indexes:**
- Primary key: id (B-tree)
- B-tree: type
- B-tree partial: language (WHERE language IS NOT NULL)
- GIN: name (trigram)
- GIN: attributes
- GIN: external_ids
- HNSW: name_embedding (vector_cosine_ops)
- Full-text: to_tsvector('english', name)

**Constraints:**
- PRIMARY KEY (id)
- FOREIGN KEY (primary_image_id) REFERENCES images(id) ON DELETE SET NULL

### relationships Table

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| from_id | uuid | NOT NULL | Source entity foreign key |
| to_id | uuid | NOT NULL | Target entity foreign key |
| type | text | NOT NULL | Relationship type (contains, variant_of, part_of, etc.) |
| order | integer | NULL | Sort order for ordered collections |
| created_at | timestamptz | NOT NULL | Creation timestamp |

**Indexes:**
- Primary key: id (B-tree)
- Composite: (from_id, type)
- Composite: (to_id, type)
- B-tree partial: order (WHERE order IS NOT NULL)

**Constraints:**
- PRIMARY KEY (id)
- FOREIGN KEY (from_id) REFERENCES entities(id) ON DELETE CASCADE
- FOREIGN KEY (to_id) REFERENCES entities(id) ON DELETE CASCADE
- UNIQUE (from_id, to_id, type)

**Note:** The `attributes` column was removed in migration `20251024195010`. All relationship metadata must use dedicated columns.

### variants Table

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| variant_of | uuid | NOT NULL | Base entity foreign key |
| name | text | NOT NULL | Variant name (e.g., "1st Edition", "Shadowless") |
| primary_image_id | uuid | NULL | Foreign key to images table |
| attributes | jsonb | NULL | Variant metadata (edition, print_run, condition, etc.) |
| created_at | timestamptz | NOT NULL | Creation timestamp |
| updated_at | timestamptz | NOT NULL | Last update timestamp |

**Indexes:**
- Primary key: id (B-tree)
- B-tree: variant_of
- GIN: attributes

**Constraints:**
- PRIMARY KEY (id)
- FOREIGN KEY (variant_of) REFERENCES entities(id) ON DELETE CASCADE
- FOREIGN KEY (primary_image_id) REFERENCES images(id) ON DELETE SET NULL

### components Table

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| component_of | uuid | NOT NULL | Parent entity foreign key |
| name | text | NOT NULL | Component name (e.g., "Red Ranger Zord") |
| quantity | integer | NOT NULL | Quantity (default 1) |
| order | integer | NULL | Display order for assembly/sorting |
| primary_image_id | uuid | NULL | Foreign key to images table |
| attributes | jsonb | NULL | Component metadata (material, condition, specs) |
| created_at | timestamptz | NOT NULL | Creation timestamp |
| updated_at | timestamptz | NOT NULL | Last update timestamp |

**Indexes:**
- Primary key: id (B-tree)
- B-tree: component_of
- B-tree partial: order (WHERE order IS NOT NULL)
- GIN: attributes

**Constraints:**
- PRIMARY KEY (id)
- FOREIGN KEY (component_of) REFERENCES entities(id) ON DELETE CASCADE
- FOREIGN KEY (primary_image_id) REFERENCES images(id) ON DELETE SET NULL

### images Table

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| image_url | text | NOT NULL | Image URL path (Supabase storage or external) |
| thumbnail_url | text | NULL | Thumbnail URL path (300x300 WebP) |
| embedding | vector(512) | NULL | CLIP embedding for reverse image search |
| source_url | text | NULL | Attribution/provenance URL |
| created_at | timestamptz | NOT NULL | Creation timestamp |
| updated_at | timestamptz | NOT NULL | Last update timestamp |

**Indexes:**
- Primary key: id (B-tree)
- HNSW: embedding (vector_cosine_ops)

**Constraints:**
- PRIMARY KEY (id)

**Join tables for additional images:**
- entity_additional_images (entity_id, image_id, order)
- variant_additional_images (variant_id, image_id, order)
- component_additional_images (component_id, image_id, order)

## Core Queries

### Entities

**Get all entities:**
```graphql
query {
  entitiesCollection {
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

**Get entity by ID:**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "d6a0f2f0-f6cf-48f4-b8fb-604e03907058"}}) {
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

**Get entities by type:**
```graphql
query {
  entitiesCollection(filter: {type: {eq: "collection"}}) {
    edges {
      node {
        id
        name
        type
        year
      }
    }
  }
}
```

**Get entities by multiple types:**
```graphql
query {
  entitiesCollection(filter: {type: {in: ["card", "figure"]}}) {
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

**Get by name (exact):**
```graphql
query {
  entitiesCollection(filter: {name: {eq: "Charizard"}}) {
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

**Get by name (case-insensitive fuzzy):**
```graphql
query {
  entitiesCollection(filter: {name: {ilike: "%char%"}}) {
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

**Filter by year:**
```graphql
query {
  entitiesCollection(filter: {year: {gte: 1999}}) {
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

**Filter by country:**
```graphql
query {
  entitiesCollection(filter: {country: {eq: "US"}}) {
    edges {
      node {
        id
        name
        country
      }
    }
  }
}
```

**Filter by language:**
```graphql
query {
  entitiesCollection(filter: {language: {eq: "en"}}) {
    edges {
      node {
        id
        name
        language
      }
    }
  }
}
```

**Filter by attributes (JSONB):**
```graphql
query {
  entitiesCollection(
    filter: {
      attributes: {contains: {hp: 120}}
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
```

**Filter by external IDs:**
```graphql
query {
  entitiesCollection(
    filter: {
      external_ids: {contains: {tcgplayer: "base1-4"}}
    }
  ) {
    edges {
      node {
        id
        name
        external_ids
      }
    }
  }
}
```

**Combined filters:**
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
        type
        year
        language
      }
    }
  }
}
```

**With primary image:**
```graphql
query {
  entitiesCollection(filter: {type: {eq: "card"}}) {
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

### Relationships

**Get outbound relationships (what does this entity contain/relate to?):**
```graphql
query {
  relationshipsCollection(
    filter: {
      from_id: {eq: "ea731c06-2fc9-4fa6-89e4-6657891721ef"}
      type: {eq: "contains"}
    }
  ) {
    edges {
      node {
        to_id
        type
        order
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

**Get inbound relationships (what contains/relates to this entity?):**
```graphql
query {
  relationshipsCollection(
    filter: {
      to_id: {eq: "1c0957dc-3f31-43e3-95bf-f7759a8d74fb"}
      type: {eq: "contains"}
    }
  ) {
    edges {
      node {
        from_id
        type
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

**Ordered relationships:**
```graphql
query {
  relationshipsCollection(
    filter: {
      from_id: {eq: "ea731c06-2fc9-4fa6-89e4-6657891721ef"}
      type: {eq: "contains"}
    }
    orderBy: {order: AscNullsLast}
  ) {
    edges {
      node {
        order
        entities {
          id
          name
        }
      }
    }
  }
}
```

**Get all relationship types for an entity:**
```graphql
query {
  relationshipsCollection(
    filter: {from_id: {eq: "d6a0f2f0-f6cf-48f4-b8fb-604e03907058"}}
  ) {
    edges {
      node {
        type
        to_id
        entities {
          name
          type
        }
      }
    }
  }
}
```

### Variants

**Get all variants of an entity (using computed field):**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "1c0957dc-3f31-43e3-95bf-f7759a8d74fb"}}) {
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

**Query variants directly:**
```graphql
query {
  variantsCollection(
    filter: {variant_of: {eq: "1c0957dc-3f31-43e3-95bf-f7759a8d74fb"}}
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

**Get all variants in database:**
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

**Filter variants by attributes:**
```graphql
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
        variant_of
        attributes
      }
    }
  }
}
```

### Components

**Get all components of an entity (using computed field):**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "77f2d72b-0f2a-470c-9e4a-722c03a3be18"}}) {
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
              attributes
            }
          }
        }
      }
    }
  }
}
```

**Query components directly:**
```graphql
query {
  componentsCollection(
    filter: {component_of: {eq: "77f2d72b-0f2a-470c-9e4a-722c03a3be18"}}
    orderBy: {order: AscNullsLast}
  ) {
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

**Get all components in database:**
```graphql
query {
  componentsCollection {
    edges {
      node {
        id
        name
        component_of
        quantity
        order
      }
    }
  }
}
```

**Filter components by attributes:**
```graphql
query {
  componentsCollection(
    filter: {
      attributes: {contains: {material: "plastic"}}
    }
  ) {
    edges {
      node {
        id
        name
        component_of
        attributes
      }
    }
  }
}
```

### Images

**Get entity with all images:**
```graphql
query {
  entitiesCollection(filter: {id: {eq: "1c0957dc-3f31-43e3-95bf-f7759a8d74fb"}}) {
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

**Get variant with images:**
```graphql
query {
  variantsCollection(filter: {id: {eq: "variant-uuid"}}) {
    edges {
      node {
        id
        name
        variant_primary_image {
          image_url
          thumbnail_url
        }
        variant_additional_images {
          edges {
            node {
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

**Get component with images:**
```graphql
query {
  componentsCollection(filter: {id: {eq: "component-uuid"}}) {
    edges {
      node {
        id
        name
        component_primary_image {
          image_url
          thumbnail_url
        }
        component_additional_images {
          edges {
            node {
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

**Query images table directly:**
```graphql
query {
  imagesCollection {
    edges {
      node {
        id
        image_url
        thumbnail_url
        source_url
        created_at
      }
    }
  }
}
```

## Search Functions

### semantic_search

**Function signature:**
```sql
semantic_search(
  query_embedding vector(384),
  entity_type_filter text DEFAULT NULL,
  category_filter text DEFAULT NULL,
  result_limit integer DEFAULT 20
)
RETURNS TABLE (
  id uuid,
  name text,
  type text,
  category text,
  year integer,
  country char(2),
  language char(2),
  source_url text,
  external_ids jsonb,
  attributes jsonb,
  similarity float,
  image_url text,
  thumbnail_url text
)
```

**GraphQL usage:**
```graphql
query {
  semantic_search(
    args: {
      query_embedding: "[0.123, 0.456, ...]"
      entity_type_filter: "item"
      category_filter: "trading_card_games"
      result_limit: 20
    }
  ) {
    id
    name
    type
    category
    similarity
    image_url
    thumbnail_url
  }
}
```

**Parameters:**
- `query_embedding` (vector(384), required): 384-dimensional vector from sentence-transformers model (e.g., all-MiniLM-L6-v2)
- `entity_type_filter` (text, optional): Filter by entity type ('item' or 'collection')
- `category_filter` (text, optional): Filter by category ('trading_card_games', 'figures', 'comics', 'video_games', 'buildables')
- `result_limit` (integer, optional): Maximum results (default 20)

**Returns:**
- Only entities with non-null `name_embedding`
- Ranked by cosine similarity (1 - distance)
- Similarity score 0-1 (higher = more similar)
- Includes image URLs from the images table

**Example with category filter:**
```graphql
query {
  semantic_search(
    args: {
      query_embedding: "[0.1, 0.2, 0.3, ...]"
      entity_type_filter: "item"
      category_filter: "trading_card_games"
      result_limit: 10
    }
  ) {
    id
    name
    type
    category
    year
    country
    language
    attributes
    similarity
    image_url
    thumbnail_url
  }
}
```

**Without filters:**
```graphql
query {
  semantic_search(
    args: {
      query_embedding: "[0.1, 0.2, 0.3, ...]"
      result_limit: 50
    }
  ) {
    id
    name
    type
    category
    similarity
  }
}
```

### search_by_text

**Function signature:**
```sql
search_by_text(
  query_text text,
  entity_type_filter text DEFAULT NULL,
  category_filter text DEFAULT NULL,
  result_limit integer DEFAULT 20
)
RETURNS TABLE (
  id uuid,
  name text,
  type text,
  category text,
  year integer,
  country char(2),
  language char(2),
  source_url text,
  external_ids jsonb,
  attributes jsonb,
  similarity float,
  image_url text,
  thumbnail_url text
)
```

**GraphQL usage:**
```graphql
query {
  search_by_text(
    args: {
      query_text: "fire dragon pokemon"
      entity_type_filter: "item"
      category_filter: "trading_card_games"
      result_limit: 20
    }
  ) {
    id
    name
    type
    category
    similarity
    image_url
    thumbnail_url
  }
}
```

**Parameters:**
- `query_text` (text, required): Plain text search query
- `entity_type_filter` (text, optional): Filter by entity type ('item' or 'collection')
- `category_filter` (text, optional): Filter by category ('trading_card_games', 'figures', 'comics', 'video_games', 'buildables')
- `result_limit` (integer, optional): Maximum results (default 20)

**Limitations:**
- Uses trigram matching to find similar entity name first
- Then uses that entity's embedding for semantic search
- Fails for synonyms/variations ("and" vs "&")
- **Recommendation:** Use MCP tool `search_collectibles` for proper semantic search with synonym handling

### image_search

**Function signature:**
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

**GraphQL usage:**
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
- `query_embedding` (vector(512), required): 512-dimensional CLIP embedding
- `result_limit` (integer, optional): Maximum results (default 20)

**Returns:**
- Images ranked by visual similarity (cosine distance)
- Includes parent information (entity/variant/component)
- One row per parent association (image with 2 parents = 2 rows)
- Similarity score 0-1 (higher = more similar)

**Parent types:**
- `entity`: Image belongs to an entity (primary or additional)
- `variant`: Image belongs to a variant
- `component`: Image belongs to a component

## Computed Fields

### entity_variants

Returns all variants for an entity.

**Function signature:**
```sql
entity_variants(entity_row entities) RETURNS SETOF variants
```

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

### entity_components

Returns all components for an entity.

**Function signature:**
```sql
entity_components(entity_row entities) RETURNS SETOF components
```

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

### entity_primary_image

Returns the primary image for an entity.

**Function signature:**
```sql
entity_primary_image(entity_row entities) RETURNS SETOF images
```

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

### entity_additional_images

Returns additional images for an entity (ordered).

**Function signature:**
```sql
entity_additional_images(entity_row entities) RETURNS SETOF images
```

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

### Variant and Component Image Computed Fields

**Equivalent functions exist for variants and components:**

- `variant_primary_image(variant_row variants)` - Returns primary image for variant
- `variant_additional_images(variant_row variants)` - Returns additional images for variant
- `component_primary_image(component_row components)` - Returns primary image for component
- `component_additional_images(component_row components)` - Returns additional images for component

**Usage pattern identical to entity equivalents.**

## Filtering & Sorting

### Filter Operators

**Text operators:**
- `eq` - Equals (exact match)
- `neq` - Not equals
- `like` - SQL LIKE (case-sensitive, % wildcard)
- `ilike` - Case-insensitive LIKE
- `in` - In array
- `is` - IS NULL check (use "NULL" string)

**Numeric operators:**
- `eq` - Equals
- `neq` - Not equals
- `lt` - Less than
- `lte` - Less than or equal
- `gt` - Greater than
- `gte` - Greater than or equal
- `in` - In array

**JSONB operators:**
- `contains` - JSONB @> operator (contains value)
- `containedBy` - JSONB <@ operator (contained by value)

### Filter Examples

**Text filtering:**
```graphql
# Exact match
filter: {name: {eq: "Charizard"}}

# Case-insensitive pattern
filter: {name: {ilike: "%pokemon%"}}

# In array
filter: {type: {in: ["card", "figure"]}}

# IS NULL
filter: {language: {is: "NULL"}}
```

**Numeric filtering:**
```graphql
# Exact year
filter: {year: {eq: 1999}}

# Year range
filter: {year: {gte: 1999, lte: 2000}}

# Year in list
filter: {year: {in: [1999, 2000, 2001]}}
```

**JSONB filtering:**
```graphql
# Exact attribute match
filter: {attributes: {contains: {hp: 120}}}

# Multiple attributes
filter: {attributes: {contains: {hp: 120, rarity: "rare"}}}

# External ID lookup
filter: {external_ids: {contains: {tcgplayer: "base1-4"}}}
```

**Combined filters (AND logic):**
```graphql
filter: {
  type: {eq: "card"}
  year: {gte: 1999}
  language: {eq: "en"}
  attributes: {contains: {rarity: "rare"}}
}
```

### Sorting

**Order options:**
- `AscNullsFirst` - Ascending, nulls first
- `AscNullsLast` - Ascending, nulls last
- `DescNullsFirst` - Descending, nulls first
- `DescNullsLast` - Descending, nulls last

**Single field:**
```graphql
orderBy: {name: AscNullsLast}
```

**Multiple fields:**
```graphql
orderBy: [{year: Desc}, {name: Asc}]
```

**Common patterns:**
```graphql
# Alphabetical with nulls at end
orderBy: {name: AscNullsLast}

# Newest first
orderBy: {year: DescNullsFirst}

# Ordered collection items
orderBy: {order: AscNullsLast}

# Year descending, then name ascending
orderBy: [{year: Desc}, {name: Asc}]
```

## Pagination Patterns

### Edges/Nodes Structure

All `*Collection` queries return paginated results:

```graphql
{
  edges {
    node {
      # Entity fields
    }
    cursor
  }
  pageInfo {
    hasNextPage
    hasPreviousPage
    startCursor
    endCursor
  }
}
```

### Forward Pagination

**First page:**
```graphql
query {
  entitiesCollection(first: 20) {
    edges {
      node {
        id
        name
      }
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
  entitiesCollection(first: 20, after: "cursor-from-previous") {
    edges {
      node {
        id
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### Backward Pagination

**Last page:**
```graphql
query {
  entitiesCollection(last: 20) {
    edges {
      node {
        id
        name
      }
    }
    pageInfo {
      hasPreviousPage
      startCursor
    }
  }
}
```

**Previous page:**
```graphql
query {
  entitiesCollection(last: 20, before: "cursor-from-current") {
    edges {
      node {
        id
        name
      }
    }
    pageInfo {
      hasPreviousPage
      startCursor
    }
  }
}
```

### Page Size Limits

- Default: 20 items
- Maximum: 100 items
- Configured in migration `20251023185803_increase_graphql_page_limit.sql`

**Custom page size:**
```graphql
query {
  entitiesCollection(first: 50) {
    edges {
      node {
        id
        name
      }
    }
  }
}
```

## Complete Query Catalog

### Basic Entity Queries

```graphql
# Get all entities
query { entitiesCollection { edges { node { id name type } } } }

# Get by ID
query { entitiesCollection(filter: {id: {eq: "uuid"}}) { edges { node { id name } } } }

# Get by type
query { entitiesCollection(filter: {type: {eq: "card"}}) { edges { node { id name } } } }

# Get by name (exact)
query { entitiesCollection(filter: {name: {eq: "Charizard"}}) { edges { node { id name } } } }

# Get by name (fuzzy)
query { entitiesCollection(filter: {name: {ilike: "%char%"}}) { edges { node { id name } } } }

# Get by year
query { entitiesCollection(filter: {year: {gte: 1999}}) { edges { node { id name year } } } }

# Get by language
query { entitiesCollection(filter: {language: {eq: "en"}}) { edges { node { id name language } } } }

# Get by attributes
query { entitiesCollection(filter: {attributes: {contains: {hp: 120}}}) { edges { node { id name attributes } } } }

# Get by external ID
query { entitiesCollection(filter: {external_ids: {contains: {tcgplayer: "base1-4"}}}) { edges { node { id name external_ids } } } }

# Combined filters
query { entitiesCollection(filter: {type: {eq: "card"}, year: {gte: 1999}}) { edges { node { id name type year } } } }
```

### Relationship Queries

```graphql
# Outbound relationships
query { relationshipsCollection(filter: {from_id: {eq: "uuid"}, type: {eq: "contains"}}) { edges { node { to_id entities { name } } } } }

# Inbound relationships
query { relationshipsCollection(filter: {to_id: {eq: "uuid"}, type: {eq: "contains"}}) { edges { node { from_id entities { name } } } } }

# Ordered relationships
query { relationshipsCollection(filter: {from_id: {eq: "uuid"}}, orderBy: {order: AscNullsLast}) { edges { node { order entities { name } } } } }

# All relationships for entity
query { relationshipsCollection(filter: {from_id: {eq: "uuid"}}) { edges { node { type to_id entities { name } } } } }
```

### Variant Queries

```graphql
# Via computed field
query { entitiesCollection(filter: {id: {eq: "uuid"}}) { edges { node { entity_variants { edges { node { id name } } } } } } }

# Direct query
query { variantsCollection(filter: {variant_of: {eq: "uuid"}}) { edges { node { id name attributes } } } }

# All variants
query { variantsCollection { edges { node { id name variant_of } } } }

# Filter by attributes
query { variantsCollection(filter: {attributes: {contains: {edition: "1st"}}}) { edges { node { id name attributes } } } }
```

### Component Queries

```graphql
# Via computed field
query { entitiesCollection(filter: {id: {eq: "uuid"}}) { edges { node { entity_components { edges { node { id name quantity } } } } } } }

# Direct query
query { componentsCollection(filter: {component_of: {eq: "uuid"}}, orderBy: {order: AscNullsLast}) { edges { node { id name quantity order } } } }

# All components
query { componentsCollection { edges { node { id name component_of quantity } } } }

# Filter by attributes
query { componentsCollection(filter: {attributes: {contains: {material: "plastic"}}}) { edges { node { id name attributes } } } }
```

### Image Queries

```graphql
# Entity with all images
query { entitiesCollection(filter: {id: {eq: "uuid"}}) { edges { node { primary_image { image_url thumbnail_url } entity_additional_images { edges { node { image_url } } } } } } }

# Variant images
query { variantsCollection(filter: {id: {eq: "uuid"}}) { edges { node { variant_primary_image { image_url } } } } }

# Component images
query { componentsCollection(filter: {id: {eq: "uuid"}}) { edges { node { component_primary_image { image_url } } } } }

# All images
query { imagesCollection { edges { node { id image_url thumbnail_url } } } }
```

### Search Queries

```graphql
# Semantic search with category filter
query { semantic_search(args: {query_embedding: "[...]", entity_type_filter: "item", category_filter: "trading_card_games", result_limit: 20}) { id name category similarity } }

# Text search (limited, use MCP search_collectibles instead)
query { search_by_text(args: {query_text: "fire dragon", entity_type_filter: "item", category_filter: "trading_card_games", result_limit: 20}) { id name category similarity } }

# Image search
query { image_search(args: {query_embedding: "[...]", result_limit: 20}) { image_id image_url similarity parent_type parent_name } }
```

### Pagination Queries

```graphql
# First page
query { entitiesCollection(first: 20) { edges { node { id name } cursor } pageInfo { hasNextPage endCursor } } }

# Next page
query { entitiesCollection(first: 20, after: "cursor") { edges { node { id name } } pageInfo { hasNextPage endCursor } } }

# Previous page
query { entitiesCollection(last: 20, before: "cursor") { edges { node { id name } } pageInfo { hasPreviousPage startCursor } } }
```

### Complex Nested Queries

```graphql
# Entity with variants and components
query {
  entitiesCollection(filter: {id: {eq: "uuid"}}) {
    edges {
      node {
        id
        name
        primary_image {
          image_url
          thumbnail_url
        }
        entity_variants {
          edges {
            node {
              id
              name
              attributes
            }
          }
        }
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

# Collection with items and their images
query {
  relationshipsCollection(filter: {from_id: {eq: "uuid"}, type: {eq: "contains"}}) {
    edges {
      node {
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

## API Limits and Performance

**Rate limiting:** None currently enforced (local development)

**Query complexity:** No hard limit, but avoid:
- Deeply nested queries (>3 levels)
- Fetching all fields when only few needed
- Large page sizes (>100) without pagination

**Indexing:** Queries using indexed fields are fast:
- `id`, `type`, `language` (B-tree)
- `name` (trigram GIN)
- `attributes`, `external_ids` (JSONB GIN)
- `name_embedding`, `embedding` (HNSW vector)

**Recommended practices:**
- Request only needed fields
- Use specific filters (type, year, language)
- Paginate large result sets
- Leverage computed fields for common patterns

## Migration References

**Key migrations:**
- `20251020000000_initial_schema.sql` - Core entities and relationships
- `20251023190331_add_language_and_order_columns.sql` - Language and order fields
- `20251023215655_add_semantic_search_function.sql` - Semantic search function
- `20251024195010_drop_relationships_attributes.sql` - Removed relationships.attributes
- `20251105125958_add_vector_embedding.sql` - Added name_embedding for semantic search
- `20251112171928_create_variants_table.sql` - Variants table
- `20251113195527_create_components_table.sql` - Components table
- `20251114221309_add_images_table_and_reverse_image_search.sql` - Images table and image_search function
- `20251114223852_add_graphql_image_computed_fields.sql` - Image computed fields

## Additional Resources

- **User Guide:** See `docs/graphql-user-guide.md` for tutorial-style documentation
- **Project docs:** `CLAUDE.md` in project root
- **Migrations:** `supabase/migrations/` directory
- **Seed data:** `scripts/seed-sample-data.py`
- **Semantic search CLI:** `scripts/semantic-search`
