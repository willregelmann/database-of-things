#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { createClient } from "@supabase/supabase-js";
import type { SupabaseClient } from "@supabase/supabase-js";

import { searchCollectibles, searchByExternalId } from "./tools/search.js";
import { getEntity } from "./tools/entity.js";
import { browseCollection } from "./tools/collections.js";
import { getVariants } from "./tools/variants.js";
import { getComponents } from "./tools/components.js";
import { createEntity, updateEntity, deleteEntity } from "./tools/write/entities.js";
import { createRelationship, deleteRelationship } from "./tools/write/relationships.js";
import { createVariant, updateVariant } from "./tools/write/variants.js";
import { createComponent } from "./tools/write/components.js";
import { createImage } from "./tools/write/images.js";
import { generateEmbedding, bulkGenerateEmbeddings } from "./tools/write/embeddings.js";
import { localizeImage } from "./tools/write/localize-image.js";
import { listCurators, getCuratorConfig } from "./tools/curator/discovery.js";
import { runCuratorFetch, validateCuratorData, getCuratorStats } from "./tools/curator/execution.js";

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
    name: "search_by_external_id",
    description: "Search for entities by external_ids. Essential for deduplication and parent lookup in curator workflows. Returns entity with matching external ID key/value pair.",
    inputSchema: {
      type: "object",
      properties: {
        external_id_key: {
          type: "string",
          description: "External ID field name (e.g., 'metron_id', 'tcgplayer_id', 'pokemontcg_io')"
        },
        external_id_value: {
          type: "string",
          description: "External ID value to search for"
        },
        entity_type: {
          type: "string",
          description: "Optional: Filter by entity type (e.g., 'collection', 'comic', 'card')",
        },
      },
      required: ["external_id_key", "external_id_value"],
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
  // Write Tools - Relationship Operations
  {
    name: "create_relationship",
    description: "Create a relationship between two entities (e.g., add card to collection).",
    inputSchema: {
      type: "object",
      properties: {
        from_id: { type: "string", description: "Parent entity UUID (required)" },
        to_id: { type: "string", description: "Child entity UUID (required)" },
        type: { type: "string", description: "Relationship type like 'contains' (required)" },
        order: { type: "number", description: "Sort order (optional)" }
      },
      required: ["from_id", "to_id", "type"]
    }
  },
  {
    name: "delete_relationship",
    description: "Delete a relationship between two entities.",
    inputSchema: {
      type: "object",
      properties: {
        from_id: { type: "string", description: "Parent entity UUID (required)" },
        to_id: { type: "string", description: "Child entity UUID (required)" },
        type: { type: "string", description: "Relationship type (required)" }
      },
      required: ["from_id", "to_id", "type"]
    }
  },
  // Write Tools - Variant Operations
  {
    name: "create_variant",
    description: "Create a variant of an entity (e.g., '1st Edition', 'Shadowless').",
    inputSchema: {
      type: "object",
      properties: {
        variant_of: { type: "string", description: "Base entity UUID (required)" },
        name: { type: "string", description: "Variant name (required)" },
        image_url: { type: "string", description: "Image URL (optional)" },
        thumbnail_url: { type: "string", description: "Thumbnail URL (optional)" },
        attributes: { type: "object", description: "Variant metadata (optional)" }
      },
      required: ["variant_of", "name"]
    }
  },
  {
    name: "update_variant",
    description: "Update a variant's fields.",
    inputSchema: {
      type: "object",
      properties: {
        variant_id: { type: "string", description: "Variant UUID (required)" },
        name: { type: "string" },
        image_url: { type: "string" },
        thumbnail_url: { type: "string" },
        attributes: { type: "object" }
      },
      required: ["variant_id"]
    }
  },
  // Write Tools - Component Operations
  {
    name: "create_component",
    description: "Create a component/part of an entity (e.g., Zord piece, game token).",
    inputSchema: {
      type: "object",
      properties: {
        component_of: { type: "string", description: "Parent entity UUID (required)" },
        name: { type: "string", description: "Component name (required)" },
        quantity: { type: "number", description: "Quantity (default 1)" },
        order: { type: "number", description: "Display order (optional)" },
        image_url: { type: "string", description: "Image URL (optional)" },
        thumbnail_url: { type: "string", description: "Thumbnail URL (optional)" },
        attributes: { type: "object", description: "Component metadata (optional)" }
      },
      required: ["component_of", "name"]
    }
  },
  // Write Tools - Image Operations
  {
    name: "create_image",
    description: "Create and link an image to an entity, variant, or component. Provide exactly one of entity_id, variant_id, or component_id. Use is_primary to set as the primary image (shown in lists), otherwise adds to additional images.",
    inputSchema: {
      type: "object",
      properties: {
        entity_id: { type: "string", description: "Entity UUID (provide exactly one of: entity_id, variant_id, component_id)" },
        variant_id: { type: "string", description: "Variant UUID (provide exactly one of: entity_id, variant_id, component_id)" },
        component_id: { type: "string", description: "Component UUID (provide exactly one of: entity_id, variant_id, component_id)" },
        image_url: { type: "string", description: "Image URL (required)" },
        thumbnail_url: { type: "string", description: "Thumbnail URL (optional)" },
        source_url: { type: "string", description: "Source URL for attribution (optional)" },
        is_primary: { type: "boolean", description: "Set as primary image (default: false, adds to additional images instead)" }
      },
      required: ["image_url"]
    }
  },
  // Write Tools - Embedding Operations
  {
    name: "generate_embedding",
    description: "Queue embedding generation for an entity. Note: Requires running scripts/generate-embeddings.py separately.",
    inputSchema: {
      type: "object",
      properties: {
        entity_id: { type: "string", description: "Entity UUID (required)" }
      },
      required: ["entity_id"]
    }
  },
  {
    name: "bulk_generate_embeddings",
    description: "Queue embedding generation for multiple entities. Note: Requires running scripts/generate-embeddings.py separately.",
    inputSchema: {
      type: "object",
      properties: {
        entity_ids: {
          type: "array",
          items: { type: "string" },
          description: "Array of entity UUIDs (required)"
        }
      },
      required: ["entity_ids"]
    }
  },
  {
    name: "localize_image",
    description: "Download external image, generate thumbnail, and upload to Supabase storage. Returns localized image_url and thumbnail_url paths. This is the standard way to import images in curator workflows.",
    inputSchema: {
      type: "object",
      properties: {
        external_url: { type: "string", description: "External image URL to download (required)" },
        entity_id: { type: "string", description: "Entity UUID for storage paths (required)" },
        thumbnail_size: { type: "number", description: "Thumbnail max width/height in pixels (default: 300)" }
      },
      required: ["external_url", "entity_id"]
    }
  },
  // Curator Tools - Discovery
  {
    name: "list_curators",
    description: "List all available curators with their status.",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "get_curator_config",
    description: "Get configuration and details for a specific curator.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Curator name (required)" }
      },
      required: ["name"]
    }
  },
  // Curator Tools - Execution
  {
    name: "run_curator_fetch",
    description: "Execute a curator's fetch_data.py script and return the fetched JSON data. Returns status, items_fetched count, partial data (first 5 items), and any errors.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Curator name (required)" },
        options: { type: "object", description: "Optional parameters for fetch script" }
      },
      required: ["name"]
    }
  },
  {
    name: "validate_curator_data",
    description: "Run validation on fetched curator data. Validates JSON structure and checks for required fields. Uses fetched_data.json if data not provided.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Curator name (required)" },
        data: { type: "object", description: "Optional data to validate (uses fetched_data.json if not provided)" }
      },
      required: ["name"]
    }
  },
  {
    name: "get_curator_stats",
    description: "Get statistics about a curator's collection from the database. Returns total items, last import date, collection info.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Curator name (required)" }
      },
      required: ["name"]
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

      case "search_by_external_id":
        return await searchByExternalId(args as any);

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

      case "create_relationship":
        return await createRelationship(args as any);
      case "delete_relationship":
        return await deleteRelationship(args as any);

      case "create_variant":
        return await createVariant(args as any);
      case "update_variant":
        return await updateVariant(args as any);

      case "create_component":
        return await createComponent(args as any);

      case "create_image":
        return await createImage(args as any);

      case "generate_embedding":
        return await generateEmbedding(args as any);
      case "bulk_generate_embeddings":
        return await bulkGenerateEmbeddings(args as any);

      case "localize_image":
        return await localizeImage(args as any);

      case "list_curators":
        return await listCurators();
      case "get_curator_config":
        return await getCuratorConfig(args as any);

      case "run_curator_fetch":
        return await runCuratorFetch(args as any);
      case "validate_curator_data":
        return await validateCuratorData(args as any);
      case "get_curator_stats":
        return await getCuratorStats(args as any);

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
