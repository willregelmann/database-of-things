#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { createClient } from "@supabase/supabase-js";
import type { SupabaseClient } from "@supabase/supabase-js";

import { searchCollectibles } from "./tools/search.js";
import { getEntity } from "./tools/entity.js";
import { browseCollection } from "./tools/collections.js";
import { getVariants } from "./tools/variants.js";
import { getComponents } from "./tools/components.js";
import { createEntity, updateEntity, deleteEntity } from "./tools/write/entities.js";

// Initialize Supabase client
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error("Error: SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_KEY) environment variables are required");
  process.exit(1);
}

export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseKey);

// Create MCP server
const server = new Server(
  {
    name: "database-of-things",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions
const TOOLS = [
  {
    name: "search_collectibles",
    description: "Search for collectibles using semantic search. Searches by name/description and returns ranked results based on similarity. Use this when the user asks about finding, looking for, or searching for collectibles.",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "The search query (e.g., 'fire dragon pokemon', 'power rangers megazord')"
        },
        entity_type: {
          type: "string",
          description: "Optional: Filter by entity type (e.g., 'card', 'figure', 'comic', 'collection')",
        },
        limit: {
          type: "number",
          description: "Maximum number of results to return (default: 20, max: 100)",
          default: 20,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "get_entity",
    description: "Get detailed information about a specific collectible by ID. Returns full entity details including attributes, images, relationships, variants, and components.",
    inputSchema: {
      type: "object",
      properties: {
        id: {
          type: "string",
          description: "The UUID of the entity to retrieve",
        },
      },
      required: ["id"],
    },
  },
  {
    name: "browse_collection",
    description: "Browse items within a collection. Returns all entities that are contained in the specified collection, optionally filtered by type.",
    inputSchema: {
      type: "object",
      properties: {
        collection_id: {
          type: "string",
          description: "The UUID of the collection to browse",
        },
        entity_type: {
          type: "string",
          description: "Optional: Filter items by type (e.g., 'card', 'figure')",
        },
        limit: {
          type: "number",
          description: "Maximum number of items to return (default: 50)",
          default: 50,
        },
      },
      required: ["collection_id"],
    },
  },
  {
    name: "get_variants",
    description: "Get all variants of a collectible. Variants are alternative versions like '1st Edition', 'Shadowless', 'Holofoil', etc.",
    inputSchema: {
      type: "object",
      properties: {
        entity_id: {
          type: "string",
          description: "The UUID of the base entity",
        },
      },
      required: ["entity_id"],
    },
  },
  {
    name: "get_components",
    description: "Get all components/parts of a collectible. Components are physical pieces that can be removed or lost (e.g., Zords that make up a Megazord, pieces in a LEGO set).",
    inputSchema: {
      type: "object",
      properties: {
        entity_id: {
          type: "string",
          description: "The UUID of the parent entity",
        },
      },
      required: ["entity_id"],
    },
  },
  // Write Tools - Entity Operations
  {
    name: "create_entity",
    description: "Create a new entity (collection, card, figure, etc.) in the database. Returns the entity_id on success.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Entity name (required)" },
        type: { type: "string", description: "Entity type like 'collection', 'card', 'figure' (required)" },
        year: { type: "number", description: "Year (optional)" },
        country: { type: "string", description: "ISO country code (optional)" },
        language: { type: "string", description: "ISO 639-1 language code (optional)" },
        source_url: { type: "string", description: "Source URL for attribution (optional)" },
        external_ids: { type: "object", description: "External system IDs (optional)" },
        attributes: { type: "object", description: "Additional metadata (optional)" }
      },
      required: ["name", "type"]
    }
  },
  {
    name: "update_entity",
    description: "Update an existing entity. Only updates provided fields.",
    inputSchema: {
      type: "object",
      properties: {
        entity_id: { type: "string", description: "UUID of entity to update (required)" },
        name: { type: "string" },
        year: { type: "number" },
        country: { type: "string" },
        language: { type: "string" },
        source_url: { type: "string" },
        external_ids: { type: "object" },
        attributes: { type: "object" }
      },
      required: ["entity_id"]
    }
  },
  {
    name: "delete_entity",
    description: "Delete an entity by ID. Cascades to relationships, variants, and components.",
    inputSchema: {
      type: "object",
      properties: {
        entity_id: { type: "string", description: "UUID of entity to delete (required)" }
      },
      required: ["entity_id"]
    }
  },
];

// Register tool handlers
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (!args) {
    throw new Error("Missing arguments");
  }

  try {
    switch (name) {
      case "search_collectibles":
        return await searchCollectibles(args as any);

      case "get_entity":
        return await getEntity(args as any);

      case "browse_collection":
        return await browseCollection(args as any);

      case "get_variants":
        return await getVariants(args as any);

      case "get_components":
        return await getComponents(args as any);

      case "create_entity":
        return await createEntity(args as any);
      case "update_entity":
        return await updateEntity(args as any);
      case "delete_entity":
        return await deleteEntity(args as any);

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [
        {
          type: "text",
          text: `Error: ${errorMessage}`,
        },
      ],
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Database of Things MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
