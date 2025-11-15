# Database of Things MCP Server

MCP (Model Context Protocol) server for querying the Database of Things collectibles database using natural language through Claude and other AI assistants.

## Features

### Read Operations
- **Semantic Search** - Find collectibles by name, description, or meaning
- **Entity Lookup** - Get detailed information about specific items
- **Collection Browsing** - Explore items within collections
- **Variants & Components** - View alternative versions and parts

### Write Operations
- **Entity Management** - Create, update, and delete entities
- **Relationship Management** - Link items to collections
- **Variant & Component Management** - Manage alternative versions and parts
- **Image Management** - Associate images with entities
- **Embedding Generation** - Queue semantic search indexing

### Curator Integration
- **Curator Discovery** - List and configure available curators
- **Data Fetching** - Execute curator fetch scripts
- **Validation** - Validate fetched data before import
- **AI-Driven Workflows** - Let Claude orchestrate complex import operations

## Installation

```bash
cd mcp-server
npm install
npm run build
```

## Configuration

### Local Development

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "database-of-things": {
      "command": "node",
      "args": ["/path/to/database-of-things/mcp-server/build/index.js"],
      "env": {
        "SUPABASE_URL": "http://127.0.0.1:54321",
        "SUPABASE_ANON_KEY": "your-anon-key-here"
      }
    }
  }
}
```

### Production

```json
{
  "mcpServers": {
    "database-of-things": {
      "command": "node",
      "args": ["/path/to/database-of-things/mcp-server/build/index.js"],
      "env": {
        "SUPABASE_URL": "https://yourproject.supabase.co",
        "SUPABASE_ANON_KEY": "your-production-anon-key"
      }
    }
  }
}
```

Get your Supabase credentials:
```bash
# Local development
./bin/supabase status

# Production
# From Supabase Dashboard → Settings → API
```

## Multi-Environment Setup (Claude Code)

For Claude Code projects, use the project-scoped `.mcp.json` configuration with separate servers for local and production:

### Configuration

The `.mcp.json` in the project root includes two servers:

```json
{
  "mcpServers": {
    "database-of-things-local": {
      "type": "stdio",
      "command": "node",
      "args": ["mcp-server/build/index.js"],
      "env": {
        "SUPABASE_URL": "http://127.0.0.1:54321",
        "SUPABASE_ANON_KEY": "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"
      }
    },
    "database-of-things-prod": {
      "type": "stdio",
      "command": "node",
      "args": ["mcp-server/build/index.js"],
      "env": {
        "SUPABASE_URL": "${SUPABASE_PROD_URL}",
        "SUPABASE_ANON_KEY": "${SUPABASE_PROD_ANON_KEY}"
      }
    }
  }
}
```

### Setting Up Production Access

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your production credentials:
```bash
export SUPABASE_PROD_URL="https://yourproject.supabase.co"
export SUPABASE_PROD_ANON_KEY="your-production-anon-key"
```

3. Source the environment file before starting Claude Code:
```bash
source .env
claude
```

### Using Multiple Environments

Once configured, you'll have access to both environments:

- **Local tools**: `mcp__database-of-things-local__search_collectibles`, etc.
- **Production tools**: `mcp__database-of-things-prod__search_collectibles`, etc.

You can:
- Enable/disable servers via `/mcp` command or @mentioning
- Query both environments simultaneously to compare data
- Switch between them as needed during development

## Available Tools

### Read Tools (5 tools)

#### 1. `search_collectibles`

Search for collectibles using semantic search.

**Parameters:**
- `query` (required): Search query (e.g., "fire dragon pokemon")
- `entity_type` (optional): Filter by type ("card", "figure", "comic", etc.)
- `limit` (optional): Max results (default 20, max 100)

**Example:**
```
search_collectibles({
  query: "power rangers megazord",
  entity_type: "toy",
  limit: 10
})
```

#### 2. `get_entity`

Get detailed information about a specific collectible.

**Parameters:**
- `id` (required): Entity UUID

**Returns:**
- Full entity details
- Images and attributes
- Parent collections
- Child items (if collection)
- Variants and components

**Example:**
```
get_entity({
  id: "uuid-here"
})
```

#### 3. `browse_collection`

Browse items within a collection.

**Parameters:**
- `collection_id` (required): Collection UUID
- `entity_type` (optional): Filter by type
- `limit` (optional): Max items (default 50)

**Example:**
```
browse_collection({
  collection_id: "uuid-here",
  entity_type: "card",
  limit: 20
})
```

#### 4. `get_variants`

Get all variants of a collectible (e.g., "1st Edition", "Shadowless").

**Parameters:**
- `entity_id` (required): Base entity UUID

**Example:**
```
get_variants({
  entity_id: "uuid-here"
})
```

#### 5. `get_components`

Get all components/parts of a collectible.

**Parameters:**
- `entity_id` (required): Parent entity UUID

**Example:**
```
get_components({
  entity_id: "uuid-here"
})
```

### Write Tools (11 tools)

#### Entity Operations

**`create_entity`** - Create a new entity (collection, card, figure, etc.)

**Parameters:**
- `name` (required): Entity name
- `type` (required): Entity type (e.g., "collection", "card", "figure")
- `year` (optional): Year
- `country` (optional): ISO country code
- `language` (optional): ISO 639-1 language code
- `source_url` (optional): Source URL for attribution
- `external_ids` (optional): External system IDs
- `attributes` (optional): Additional metadata

**Returns:** `{ success: true, entity_id: "..." }` or error

**Example:**
```javascript
create_entity({
  name: "Charizard",
  type: "card",
  year: 1999,
  language: "en",
  external_ids: { "pokemontcg_io": "base1-4" },
  attributes: { hp: 120, card_number: "4/102" }
})
```

**`update_entity`** - Update an existing entity

**Parameters:**
- `entity_id` (required): UUID of entity to update
- Any field from `create_entity` (all optional)

**`delete_entity`** - Delete an entity

**Parameters:**
- `entity_id` (required): UUID of entity to delete

**Note:** Cascades to relationships, variants, and components.

#### Relationship Operations

**`create_relationship`** - Create a relationship between entities

**Parameters:**
- `from_id` (required): Parent entity UUID
- `to_id` (required): Child entity UUID
- `type` (required): Relationship type (e.g., "contains")
- `order` (optional): Sort order

**Example:**
```javascript
create_relationship({
  from_id: "collection-uuid",
  to_id: "card-uuid",
  type: "contains",
  order: 1
})
```

**`delete_relationship`** - Delete a relationship

**Parameters:**
- `from_id` (required): Parent entity UUID
- `to_id` (required): Child entity UUID
- `type` (required): Relationship type

#### Variant Operations

**`create_variant`** - Create a variant of an entity

**Parameters:**
- `variant_of` (required): Base entity UUID
- `name` (required): Variant name (e.g., "1st Edition")
- `attributes` (optional): Variant-specific metadata

**Example:**
```javascript
create_variant({
  variant_of: "charizard-uuid",
  name: "1st Edition",
  attributes: { edition: "1st", print_run: "shadowless" }
})
```

**`update_variant`** - Update a variant

**Parameters:**
- `variant_id` (required): Variant UUID
- `name` (optional): New name
- `attributes` (optional): Updated attributes

#### Component Operations

**`create_component`** - Create a component/part of an entity

**Parameters:**
- `component_of` (required): Parent entity UUID
- `name` (required): Component name
- `quantity` (optional): Quantity (default 1)
- `order` (optional): Display order
- `attributes` (optional): Component metadata

**Example:**
```javascript
create_component({
  component_of: "megazord-uuid",
  name: "Red Ranger Zord",
  quantity: 1,
  order: 1
})
```

#### Image Operations

**`create_image`** - Create and link an image

**Parameters:**
- One of: `entity_id`, `variant_id`, or `component_id` (required)
- `image_url` (required): Image URL
- `thumbnail_url` (optional): Thumbnail URL
- `source_url` (optional): Source URL
- `is_primary` (optional): Set as primary image

**Example:**
```javascript
create_image({
  entity_id: "charizard-uuid",
  image_url: "/storage/v1/object/public/images/originals/uuid.jpg",
  thumbnail_url: "/storage/v1/object/public/images/thumbnails/uuid.webp",
  is_primary: true
})
```

#### Embedding Operations

**`generate_embedding`** - Queue embedding generation for an entity

**Parameters:**
- `entity_id` (required): Entity UUID

**Note:** Requires running `scripts/generate-embeddings.py` separately to process the queue.

**`bulk_generate_embeddings`** - Queue embedding generation for multiple entities

**Parameters:**
- `entity_ids` (required): Array of entity UUIDs

### Curator Tools (5 tools)

The curator tools enable AI-driven data import workflows by exposing curator discovery and execution capabilities.

#### Discovery Tools

**`list_curators`** - List all available curators

**Returns:** Array of curators with:
- `name`: Curator name
- `path`: File system path
- `has_fetch_script`: Whether fetch_data.py exists
- `has_import_script`: Whether import_items.py exists
- `environment`: "local", "prod", or "unknown"

**Example:**
```javascript
list_curators()
// Returns: { curators: [{ name: "Pokemon TCG", has_fetch_script: true, ... }] }
```

**`get_curator_config`** - Get configuration and details for a specific curator

**Parameters:**
- `name` (required): Curator name

**Returns:**
- `plan`: Content of plan.md
- `config`: Parsed config.json
- `collection_id`: Collection UUID from secrets.env
- `data_source`: Inferred data source

**Example:**
```javascript
get_curator_config({ name: "Pokemon TCG" })
```

#### Execution Tools

**`run_curator_fetch`** - Execute a curator's fetch_data.py script

**Parameters:**
- `name` (required): Curator name
- `options` (optional): Parameters for fetch script

**Returns:**
- `status`: "success" or "error"
- `items_fetched`: Number of items fetched
- `data`: The fetched JSON data
- `errors`: Any errors encountered

**Example:**
```javascript
run_curator_fetch({ name: "Pokemon TCG" })
```

**`validate_curator_data`** - Validate fetched curator data

**Parameters:**
- `name` (required): Curator name
- `data` (optional): Data to validate (uses fetched_data.json if not provided)

**Returns:**
- `valid`: Boolean
- `warnings`: Array of warning messages
- `errors`: Array of error messages

**`get_curator_stats`** - Get statistics about a curator's collection

**Parameters:**
- `name` (required): Curator name

**Returns:**
- `total_items`: Total items in collection
- `last_import`: Last import timestamp
- `items_in_collection`: Count of items

**Note:** Stats tracking is currently a placeholder.

## Curator Integration Workflow

The write and curator tools enable Claude to autonomously import and manage collectibles data:

```
1. list_curators()
   → Discover available curators

2. get_curator_config("Pokemon TCG")
   → Understand data source and configuration

3. run_curator_fetch("Pokemon TCG")
   → Fetch data from external API

4. For each item in fetched data:
   a. search_collectibles(item.name)
      → Check for existing entities (deduplication)

   b. If new entity:
      create_entity({
        name: item.name,
        type: "card",
        external_ids: { pokemontcg_io: item.id },
        attributes: { hp: item.hp, ... }
      })

   c. create_relationship({
        from_id: collection_id,
        to_id: entity_id,
        type: "contains"
      })

   d. create_image({
        entity_id: entity_id,
        image_url: item.image_url
      })

5. bulk_generate_embeddings(all_entity_ids)
   → Enable semantic search

6. Report results: "Imported X new, Y updated, Z errors"
```

This workflow combines:
- **Curator tools** for data fetching and discovery
- **Search tools** for deduplication
- **Write tools** for database mutations
- **AI intelligence** for error handling and edge cases

## Usage Examples

Once configured, you can ask Claude:

- "Find me fire-type Pokemon cards"
- "Show me all Power Rangers toys from 1993"
- "What are the variants of Charizard?"
- "Browse the Base Set Pokemon collection"
- "What components does the Megazord have?"

## Development

```bash
# Watch mode for development
npm run watch

# Build for production
npm run build
```

## Architecture

```
mcp-server/
├── src/
│   ├── index.ts           # Main MCP server
│   └── tools/
│       ├── read/
│       │   ├── search.ts       # Semantic search
│       │   ├── entity.ts       # Entity lookup
│       │   ├── collections.ts  # Collection browsing
│       │   ├── variants.ts     # Variant lookup
│       │   └── components.ts   # Component lookup
│       ├── write/
│       │   ├── entities.ts     # Entity CRUD
│       │   ├── relationships.ts # Relationship operations
│       │   ├── variants.ts     # Variant operations
│       │   ├── components.ts   # Component operations
│       │   ├── images.ts       # Image operations
│       │   └── embeddings.ts   # Embedding queue
│       └── curator/
│           ├── discovery.ts    # List and configure curators
│           └── execution.ts    # Run and validate curators
├── package.json
├── tsconfig.json
└── README.md
```

## Database Schema

The server queries a PostgreSQL database with:
- **entities** - Collectibles and collections
- **variants** - Alternative versions
- **components** - Physical parts
- **relationships** - Parent-child connections
- **images** - Photos with CLIP embeddings

## Future Enhancements

- [ ] Reverse image search (find by photo)
- [ ] Price tracking queries
- [ ] Cross-collection relationship search
- [ ] GraphQL query optimization
- [ ] Caching layer for popular queries
- [x] Write operations (implemented: 11 write tools + 5 curator tools)
- [ ] Production write confirmation prompts
- [ ] Dry run mode for testing writes
- [ ] Transaction support for multi-step operations
- [ ] Orphan cleanup tools

## License

MIT
