# Database of Things MCP Server

MCP (Model Context Protocol) server for querying the Database of Things collectibles database using natural language through Claude and other AI assistants.

## Features

### Read Operations
- **Semantic Search** - Find collectibles by name, description, or meaning
- **Entity Lookup** - Get detailed information about specific items
- **Collection Browsing** - Explore items within collections
- **Variants & Components** - View alternative versions and parts

This server is read-only. Canonical data is curated via `collections/` in the
repo root and PRs against it — see `docs/dbot-target-architecture.md`.

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
│       ├── entities.ts     # Search, find, get
│       ├── collections.ts  # Collection browsing
│       ├── variants.ts     # Variant lookup
│       └── components.ts   # Component lookup
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

## License

MIT
