#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import * as entities from "./tools/entities.js";
import * as bulk from "./tools/bulk.js";
import * as collections from "./tools/collections.js";
import * as relationships from "./tools/relationships.js";
import * as variants from "./tools/variants.js";
import * as components from "./tools/components.js";
import * as images from "./tools/images.js";
import * as curatorResources from "./resources/curators.js";
import * as runCuratorPrompt from "./prompts/run-curator.js";

const server = new McpServer({
  name: "database-of-things",
  version: "0.2.0",
});

// Tools: entity CRUD + search (6)
entities.register(server);
// Tools: bulk upsert (1)
bulk.register(server);
// Tools: collection browse (1)
collections.register(server);
// Tools: relationships (2)
relationships.register(server);
// Tools: variants (3)
variants.register(server);
// Tools: components (2)
components.register(server);
// Tools: image localization (1)
images.register(server);

// Resources: curator specs accessible at curator://{name}
curatorResources.register(server);

// Prompts: run_curator execution template
runCuratorPrompt.register(server);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Database of Things MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
