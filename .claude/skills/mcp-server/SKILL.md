---
name: mcp-server
description: This skill should be used when the user is working with MCP tools, adding new tools, modifying existing tools, debugging MCP server issues, or integrating with Claude Code. Examples: "adding a new MCP tool", "fixing search_collectibles", "how does localize_image work", "MCP server configuration".
analyzed: 2025-12-29
source_files:
  - mcp-server/src/index.ts
  - mcp-server/src/tools/search.ts
  - mcp-server/src/tools/entity.ts
  - mcp-server/src/tools/write/entities.ts
  - mcp-server/src/tools/write/localize-image.ts
  - mcp-server/src/tools/curator/bulk-import.ts
  - mcp-server/package.json
  - .mcp.json
---

# MCP Server

## What This Domain Does

The MCP (Model Context Protocol) server provides AI assistants like Claude Code with 25 tools to interact with the collectibles database. It's a TypeScript application using `@modelcontextprotocol/sdk` that connects to Supabase and exposes read, write, and curator operations.

The server supports two environments: **local** (`database-of-things-local`) and **production** (`database-of-things-prod`), configured via `.mcp.json`.

## Key Concepts

- **Read Tools (6)**: `search_collectibles`, `search_by_external_id`, `get_entity`, `browse_collection`, `get_variants`, `get_components`

- **Write Tools (13)**: Entity CRUD (`create_entity`, `update_entity`, `delete_entity`), relationships (`create_relationship`, `delete_relationship`), variants (`create_variant`, `update_variant`), components (`create_component`), images (`create_image`, `localize_image`, `bulk_localize_images`), embeddings (`generate_embedding`, `bulk_generate_embeddings`)

- **Curator Tools (6)**: `list_curators`, `get_curator_config`, `run_curator_fetch`, `validate_curator_data`, `get_curator_stats`, `bulk_import_curator_batch`

- **Utility Tools (1)**: `list_categories`

## How It Works

### Server Architecture

The server is defined in `mcp-server/src/index.ts`:

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(
  { name: "database-of-things", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

// Tool definitions in TOOLS array
server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

// Tool execution via switch statement
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  switch (name) {
    case "search_collectibles": return await searchCollectibles(args);
    case "create_entity": return await createEntity(args);
    // ... 23 more cases
  }
});
```

### Tool Organization

Tools are organized in `mcp-server/src/tools/`:

```
tools/
├── search.ts          # search_collectibles, search_by_external_id
├── entity.ts          # get_entity
├── collections.ts     # browse_collection
├── variants.ts        # get_variants
├── components.ts      # get_components
├── write/
│   ├── entities.ts    # create_entity, update_entity, delete_entity
│   ├── relationships.ts
│   ├── variants.ts
│   ├── components.ts
│   ├── images.ts      # create_image
│   ├── localize-image.ts
│   ├── bulk-localize-images.ts
│   └── embeddings.ts
└── curator/
    ├── discovery.ts   # list_curators, get_curator_config
    ├── execution.ts   # run_curator_fetch, validate_curator_data, get_curator_stats
    └── bulk-import.ts # bulk_import_curator_batch
```

### Automatic Embedding Generation

When `create_entity` is called, text embeddings are generated automatically via Transformers.js (`Xenova/all-MiniLM-L6-v2`, 384 dimensions).

When `localize_image` is called, image embeddings are generated automatically via CLIP (`Xenova/clip-vit-base-patch32`, 512 dimensions).

### Environment Configuration

`.mcp.json` defines both environments:

```json
{
  "mcpServers": {
    "database-of-things-local": {
      "command": "node",
      "args": ["mcp-server/build/index.js"],
      "env": {
        "SUPABASE_URL": "http://127.0.0.1:54321",
        "SUPABASE_ANON_KEY": "..."
      }
    },
    "database-of-things-prod": {
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

## Important Files

- `mcp-server/src/index.ts`: Main server, tool definitions, request handlers
- `mcp-server/src/tools/search.ts`: Semantic search implementation using embeddings
- `mcp-server/src/tools/write/localize-image.ts`: Image download, thumbnail generation, CLIP embeddings
- `mcp-server/src/tools/curator/bulk-import.ts`: High-performance bulk import (100x faster)
- `mcp-server/package.json`: Dependencies (@modelcontextprotocol/sdk, @supabase/supabase-js, @xenova/transformers, sharp)
- `.mcp.json`: MCP server configuration for Claude Code

## Working With This Domain

### Adding a New Tool

1. **Define the tool schema** in `index.ts` TOOLS array:
```typescript
{
  name: "my_new_tool",
  description: "What it does and when to use it",
  inputSchema: {
    type: "object",
    properties: {
      param1: { type: "string", description: "..." },
    },
    required: ["param1"]
  }
}
```

2. **Implement the handler** in appropriate tools/ file:
```typescript
export async function myNewTool(args: { param1: string }): Promise<any> {
  const { param1 } = args;
  // Implementation using supabase client
  return {
    content: [{
      type: "text",
      text: JSON.stringify({ success: true, data: result }, null, 2)
    }]
  };
}
```

3. **Add the case** in index.ts switch statement:
```typescript
case "my_new_tool":
  return await myNewTool(args as any);
```

4. **Rebuild**: `cd mcp-server && npm run build`

### Tool Response Format

All tools return MCP-compliant responses:

```typescript
return {
  content: [{
    type: "text",
    text: JSON.stringify({
      success: true,
      // ... tool-specific data
    }, null, 2)
  }]
};
```

For errors:
```typescript
return {
  content: [{
    type: "text",
    text: JSON.stringify({
      success: false,
      error: error.message,
      error_code: "DATABASE_ERROR"
    }, null, 2)
  }]
};
```

### Common Mistakes to Avoid

- **Don't forget to rebuild**: After editing TypeScript, run `npm run build`
- **Don't hardcode environment**: Use `process.env.SUPABASE_URL`, not hardcoded URLs
- **Don't skip error handling**: Always wrap Supabase calls in try/catch
- **Don't return raw Supabase errors**: Format errors with success: false

### Key Dependencies

```json
{
  "@modelcontextprotocol/sdk": "^0.5.0",
  "@supabase/supabase-js": "^2.39.0",
  "@xenova/transformers": "^2.17.0",  // For embeddings
  "sharp": "^0.33.0"                   // For thumbnail generation
}
```

### Testing Tools

You can test MCP tools directly via Claude Code:
- Enable the server via `/mcp` command
- Call tools: `mcp__database-of-things-local__search_collectibles`
- Check server logs in Claude Code output

### Debugging

If the server fails to start:
1. Check environment variables are set
2. Verify Supabase is running: `./bin/supabase status`
3. Check for build errors: `cd mcp-server && npm run build`
4. Look at stderr output in Claude Code
