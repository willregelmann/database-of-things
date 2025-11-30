# GraphQL API User Guide

The collectibles database provides a powerful GraphQL API for querying and exploring collectibles data. This guide will help you get started and master common tasks.

## Introduction

### What You Can Do

The GraphQL API provides free read-only access to:
- **Comprehensive collectibles catalog** - Cards, figures, comics, video games, and more
- **Rich relationship graph** - Navigate hierarchies and cross-references
- **Semantic search** - Find items by meaning, not just exact text matches
- **Reverse image search** - Find similar images using visual similarity
- **Variants and components** - Track different editions and physical parts

### Who This API Is For

- **Price tracking apps** - Need comprehensive item catalogs
- **Collection management tools** - Leverage relationship graph
- **Market research** - Analyze collectibles trends
- **Educational resources** - Explore collectibles history

### Read-Only Access

The API is currently read-only via GraphQL. For write operations, see the MCP server documentation.

## Quick Start

### Endpoints

**Local Development:**
```
GraphQL: http://127.0.0.1:54321/graphql/v1
Studio: http://127.0.0.1:54323
```

**Production:**
```
GraphQL: https://yourproject.supabase.co/graphql/v1
```

### Authentication

Include the `apikey` header with your anonymous key:

```bash
curl -X POST http://127.0.0.1:54321/graphql/v1 \
  -H "apikey: sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __schema { types { name } } }"}'
```

**Note:** The key shown above is for local development only. Get your production key from Supabase dashboard.

### Your First Query

Let's get all collections:

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

**Response:**
```json
{
  "data": {
    "entitiesCollection": {
      "edges": [
        {
          "node": {
            "id": "d6a0f2f0-f6cf-48f4-b8fb-604e03907058",
            "name": "Pokemon Trading Card Game",
            "type": "collection",
            "year": null
          }
        },
        {
          "node": {
            "id": "4cd9a3f3-537f-428c-9488-c3a3acc7b622",
            "name": "Power Rangers Toys",
            "type": "collection",
            "year": null
          }
        }
      ]
    }
  }
}
```

### Seeding Sample Data

To try these examples yourself:

```bash
# Start Supabase locally
./bin/supabase start

# Seed sample data
python3 scripts/seed-sample-data.py

# Generate embeddings for semantic search
python3 scripts/generate-embeddings.py
```

## Schema Overview

### Core Concept: Pure Graph Model

Everything is an **entity** connected by typed **relationships**. No rigid hierarchies - maximum flexibility.

```
┌─────────────┐
│  entities   │  Collections, items, etc.
└─────────────┘
       │
       │ connected by
       ▼
┌─────────────┐
│relationships│  "contains", "part_of", etc.
└─────────────┘
       │
       │ extended by
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  variants   │     │ components  │     │   images    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Key Tables

**entities** - Collections, cards, figures, comics, games, etc.
- `id`, `type`, `name`, `year`, `country`, `language`
- `primary_image_id` (foreign key to images)
- `name_embedding` (384-dim vector for semantic search)
- `external_ids` (JSONB: original system IDs)
- `attributes` (JSONB: flexible metadata)

**relationships** - Typed connections between entities
- `from_id`, `to_id`, `type`
- `order` (for sorted collections)

**variants** - Alternative versions (1st Edition, Shadowless, etc.)
- `variant_of` (foreign key to base entity)
- `name`, `primary_image_id`, `attributes`

**components** - Physical parts (Zord pieces, game tokens)
- `component_of` (foreign key to parent entity)
- `name`, `quantity`, `order`, `primary_image_id`, `attributes`

**images** - Unified image storage with visual search
- `image_url`, `thumbnail_url`
- `embedding` (512-dim CLIP vector for reverse image search)
- `source_url` (attribution)

### JSONB Attributes

The `attributes` field stores flexible metadata as JSON:

```json
{
  "hp": 120,
  "card_number": "4/102",
  "rarity": "rare",
  "description": "A legendary Fire-type Pokémon"
}
```

This allows heterogeneous items (cards, toys, games) to coexist without schema changes.

## Common Tasks

### Browsing Collections

**Get all top-level collections:**

```graphql
query {
  entitiesCollection(filter: {type: {eq: "collection"}}) {
    edges {
      node {
        id
        name
        year
        primary_image {
          thumbnail_url
        }
      }
    }
  }
}
```

**Get items in a collection:**

Navigate relationships to find what a collection contains:

```graphql
query {
  relationshipsCollection(
    filter: {
      from_id: {eq: "ea731c06-2fc9-4fa6-89e4-6657891721ef"}  # Base Set
      type: {eq: "contains"}
    }
    orderBy: {order: AscNullsLast}
  ) {
    edges {
      node {
        order
        entities {  # Auto-joined by foreign key
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

**Response:**
```json
{
  "data": {
    "relationshipsCollection": {
      "edges": [
        {
          "node": {
            "order": 1,
            "entities": {
              "id": "1c0957dc-3f31-43e3-95bf-f7759a8d74fb",
              "name": "Charizard",
              "type": "card",
              "primary_image": {
                "thumbnail_url": "/storage/v1/object/public/images/thumbnails/charizard.webp"
              }
            }
          }
        },
        {
          "node": {
            "order": 2,
            "entities": {
              "id": "3896727d-5776-4b15-8c0b-bc98af1b9eef",
              "name": "Blastoise",
              "type": "card",
              "primary_image": {
                "thumbnail_url": "/storage/v1/object/public/images/thumbnails/blastoise.webp"
              }
            }
          }
        }
      ]
    }
  }
}
```

**Reverse lookup (what contains this item?):**

```graphql
query {
  relationshipsCollection(
    filter: {
      to_id: {eq: "1c0957dc-3f31-43e3-95bf-f7759a8d74fb"}  # Charizard
      type: {eq: "contains"}
    }
  ) {
    edges {
      node {
        entities {  # The parent collection
          id
          name
          type
        }
      }
    }
  }
}
```

**Multi-level hierarchy:**

Get collections and their sub-collections in one query:

```graphql
query {
  entitiesCollection(
    filter: {
      id: {eq: "d6a0f2f0-f6cf-48f4-b8fb-604e03907058"}  # Pokemon Trading Card Game
    }
  ) {
    edges {
      node {
        id
        name
        # Get direct children via relationships
        relationshipsCollection(filter: {type: {eq: "contains"}}) {
          edges {
            node {
              entities {
                id
                name
                type
              }
            }
          }
        }
      }
    }
  }
}
```

### Searching Items

**Text search (exact match):**

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

**Fuzzy text search (case-insensitive):**

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
        language
      }
    }
  }
}
```

**Filter by JSONB attributes:**

```graphql
query {
  entitiesCollection(
    filter: {
      type: {eq: "card"}
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

**Semantic search (find by meaning):**

Semantic search uses vector embeddings to find items by meaning, not just text:

```graphql
query {
  semantic_search(
    args: {
      query_embedding: "[0.123, 0.456, ...]"  # 384-dimensional vector
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

**Example response:**
```json
{
  "data": {
    "semantic_search": [
      {
        "id": "1c0957dc-3f31-43e3-95bf-f7759a8d74fb",
        "name": "Charizard",
        "type": "item",
        "category": "trading_card_games",
        "similarity": 0.92,
        "image_url": "/storage/v1/object/public/images/originals/abc123.jpg",
        "thumbnail_url": "/storage/v1/object/public/images/thumbnails/abc123.webp"
      }
    ]
  }
}
```

**Available category filters:** `trading_card_games`, `figures`, `comics`, `video_games`, `buildables`

**Note:** Generating embeddings requires external tooling. For easier semantic search, use the MCP tool:

```
mcp__database-of-things-local__search_collectibles
  query: "fire dragon pokemon"
  category: "trading_card_games"
  limit: 10
```

### Working with Variants and Components

**Get entity with all variants (using computed field):**

```graphql
query {
  entitiesCollection(
    filter: {id: {eq: "1c0957dc-3f31-43e3-95bf-f7759a8d74fb"}}  # Charizard
  ) {
    edges {
      node {
        id
        name
        primary_image {
          image_url
        }
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

**Example response:**
```json
{
  "data": {
    "entitiesCollection": {
      "edges": [
        {
          "node": {
            "id": "1c0957dc-3f31-43e3-95bf-f7759a8d74fb",
            "name": "Charizard",
            "primary_image": {
              "image_url": "/storage/v1/object/public/images/originals/charizard.jpg"
            },
            "entity_variants": {
              "edges": [
                {
                  "node": {
                    "id": "variant-uuid-1",
                    "name": "1st Edition",
                    "primary_image": {
                      "image_url": "/storage/v1/object/public/images/originals/charizard-1st.jpg",
                      "thumbnail_url": "/storage/v1/object/public/images/thumbnails/charizard-1st.webp"
                    },
                    "attributes": {
                      "edition": "1st",
                      "rarity": "rare"
                    }
                  }
                },
                {
                  "node": {
                    "id": "variant-uuid-2",
                    "name": "Shadowless",
                    "primary_image": {
                      "image_url": "/storage/v1/object/public/images/originals/charizard-shadowless.jpg",
                      "thumbnail_url": "/storage/v1/object/public/images/thumbnails/charizard-shadowless.webp"
                    },
                    "attributes": {
                      "print_run": "shadowless",
                      "rarity": "rare"
                    }
                  }
                }
              ]
            }
          }
        }
      ]
    }
  }
}
```

**Get entity with all components:**

```graphql
query {
  entitiesCollection(
    filter: {id: {eq: "77f2d72b-0f2a-470c-9e4a-722c03a3be18"}}  # Megazord
  ) {
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

**Query all components for an entity:**

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
      }
    }
  }
}
```

### Finding Similar Images

**Reverse image search (find visually similar images):**

```graphql
query {
  image_search(
    args: {
      query_embedding: "[0.1, 0.2, ...]"  # 512-dimensional CLIP vector
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

**Example response:**
```json
{
  "data": {
    "image_search": [
      {
        "image_id": "img-uuid-1",
        "image_url": "/storage/v1/object/public/images/originals/charizard.jpg",
        "thumbnail_url": "/storage/v1/object/public/images/thumbnails/charizard.webp",
        "similarity": 0.95,
        "parent_type": "entity",
        "parent_id": "1c0957dc-3f31-43e3-95bf-f7759a8d74fb",
        "parent_name": "Charizard"
      },
      {
        "image_id": "img-uuid-2",
        "image_url": "/storage/v1/object/public/images/originals/moltres.jpg",
        "thumbnail_url": "/storage/v1/object/public/images/thumbnails/moltres.webp",
        "similarity": 0.87,
        "parent_type": "entity",
        "parent_id": "another-uuid",
        "parent_name": "Moltres"
      }
    ]
  }
}
```

**Note:** The function returns one row per parent. If an image is used by multiple entities, you'll get multiple rows with the same `image_id` but different `parent_*` fields.

**Get all images for an entity:**

```graphql
query {
  entitiesCollection(
    filter: {id: {eq: "1c0957dc-3f31-43e3-95bf-f7759a8d74fb"}}
  ) {
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

### Traversing Relationships

**Forward traversal (what does this contain?):**

Already covered in "Browsing Collections" section above.

**Deep hierarchy navigation (franchise → game → set → card):**

Use nested queries or multiple steps:

```graphql
# Step 1: Get Pokemon franchise
query {
  entitiesCollection(filter: {name: {eq: "Pokemon Trading Card Game"}}) {
    edges {
      node {
        id
        name
        # Step 2: Get all sets
        relationshipsCollection(filter: {type: {eq: "contains"}}) {
          edges {
            node {
              entities {
                id
                name
                # Step 3: Get all cards in this set
                relationshipsCollection(filter: {type: {eq: "contains"}}) {
                  edges {
                    node {
                      entities {
                        id
                        name
                        type
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Note:** For very deep hierarchies, consider making multiple smaller queries to avoid response size issues.

## Pagination & Performance

### Page Size Limits

- **Default:** 20 items per page
- **Maximum:** 100 items per page

Configure using `first` parameter:

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

### Cursor-Based Pagination

**First page:**

```graphql
query {
  entitiesCollection(first: 20, filter: {type: {eq: "card"}}) {
    edges {
      node {
        id
        name
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
}
```

**Next page:**

Use `endCursor` from previous response:

```graphql
query {
  entitiesCollection(
    first: 20
    after: "WyJwdWJsaWMuZW50aXRpZXMiLDE2XQ=="  # endCursor from previous page
    filter: {type: {eq: "card"}}
  ) {
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

**Previous page:**

Use `startCursor` with `last` and `before`:

```graphql
query {
  entitiesCollection(
    last: 20
    before: "WyJwdWJsaWMuZW50aXRpZXMiLDFd"  # startCursor from current page
    filter: {type: {eq: "card"}}
  ) {
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

### Best Practices

**1. Request only what you need:**
```graphql
# Bad: Over-fetching
query {
  entitiesCollection {
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
        # ... everything
      }
    }
  }
}

# Good: Minimal fields
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

**2. Use filters to reduce result size:**
```graphql
# Better performance with specific filters
query {
  entitiesCollection(
    filter: {
      type: {eq: "card"}
      year: {eq: 1999}
    }
    first: 20
  ) {
    edges {
      node {
        id
        name
      }
    }
  }
}
```

**3. Paginate large collections:**

Don't fetch thousands of items at once. Use cursor-based pagination.

**4. Leverage indexes:**

Filtering by indexed columns is fast:
- `type`, `language`, `name` (indexed)
- JSONB paths in `attributes` and `external_ids` (GIN indexed)
- Embeddings (HNSW indexed)

## Error Handling

### Common Errors

**Authentication failure:**
```json
{
  "errors": [
    {
      "message": "Invalid API key"
    }
  ]
}
```
**Solution:** Check your `apikey` header.

**Invalid UUID format:**
```json
{
  "errors": [
    {
      "message": "invalid input syntax for type uuid: \"not-a-uuid\""
    }
  ]
}
```
**Solution:** Ensure UUIDs are valid format (e.g., `d6a0f2f0-f6cf-48f4-b8fb-604e03907058`).

**Invalid filter syntax:**
```json
{
  "errors": [
    {
      "message": "Unknown filter operator"
    }
  ]
}
```
**Solution:** Check filter operators documentation (see API Reference).

**Missing embeddings:**

Semantic search returns empty results if entities don't have embeddings.

**Solution:** Generate embeddings using `python3 scripts/generate-embeddings.py`.

### Empty Results vs Errors

Empty results are valid responses:

```json
{
  "data": {
    "entitiesCollection": {
      "edges": []
    }
  }
}
```

This is **not an error** - the query succeeded but found no matches.

### Troubleshooting

**GraphQL introspection:**

Explore the schema interactively:

```graphql
query {
  __schema {
    types {
      name
      kind
      description
    }
  }
}
```

**Check field availability:**

```graphql
query {
  __type(name: "entities") {
    fields {
      name
      type {
        name
        kind
      }
    }
  }
}
```

## Examples Gallery

### Real-World Scenario: Building a Collection Browser

**Goal:** Display Pokemon Base Set cards with variants in a grid.

**Step 1: Get Base Set ID**
```graphql
query {
  entitiesCollection(
    filter: {
      name: {eq: "Base Set"}
      type: {eq: "collection"}
    }
  ) {
    edges {
      node {
        id
        name
      }
    }
  }
}
```

**Step 2: Get all cards in Base Set**
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
        entities {
          id
          name
          primary_image {
            thumbnail_url
          }
          attributes
          entity_variants {
            edges {
              node {
                id
                name
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
}
```

**Step 3: Display in your app**

Process the response and render cards with variant dropdowns.

### Real-World Scenario: Price Tracking App

**Goal:** Find all Pokemon Red Version variants to track prices.

```graphql
query {
  entitiesCollection(filter: {name: {eq: "Pokemon Red Version"}}) {
    edges {
      node {
        id
        name
        type
        year
        primary_image {
          thumbnail_url
        }
        external_ids
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

Use `external_ids` to cross-reference with pricing APIs (e.g., PriceCharting).

### Real-World Scenario: Visual Search for Card Identification

**Goal:** User uploads card photo, find similar cards.

1. Generate CLIP embedding from uploaded image (using Python/ML model)
2. Search for visually similar images:

```graphql
query {
  image_search(
    args: {
      query_embedding: "[user-generated-vector]"
      result_limit: 10
    }
  ) {
    image_id
    thumbnail_url
    similarity
    parent_type
    parent_id
    parent_name
  }
}
```

3. Display top matches with similarity scores

### Complex Filtering: Finding Specific Items

**Goal:** Find all English Pokemon cards from 1999 with HP >= 100.

```graphql
query {
  entitiesCollection(
    filter: {
      type: {eq: "card"}
      year: {eq: 1999}
      language: {eq: "en"}
      attributes: {contains: {hp: {gte: 100}}}
    }
  ) {
    edges {
      node {
        id
        name
        year
        attributes
      }
    }
  }
}
```

**Note:** JSONB numeric comparisons (like `hp: {gte: 100}`) may not work in GraphQL. Use exact matches or query via SQL for complex attribute filtering.

## Next Steps

- **Explore the API Reference:** See `docs/graphql-api-reference.md` for complete schema documentation
- **Try semantic search:** Use `./scripts/semantic-search` for better search results
- **Generate embeddings:** Run `python3 scripts/generate-embeddings.py` to enable semantic search on your data
- **Experiment in Studio:** Open http://127.0.0.1:54323 for interactive GraphQL explorer
- **Build an app:** Use these patterns to build price trackers, collection managers, and more

## Additional Resources

- **Project documentation:** See `CLAUDE.md` in project root
- **Migration history:** `supabase/migrations/` directory
- **Seed data script:** `scripts/seed-sample-data.py`
- **MCP Server:** For write operations, see `mcp-server/README.md`

## Support

For issues or questions:
- File an issue on GitHub (if public repo)
- Check migration files for schema details
- Review SQL queries in `CLAUDE.md` for advanced patterns
