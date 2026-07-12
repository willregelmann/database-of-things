#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import * as entities from "./tools/entities.js";
import * as collections from "./tools/collections.js";
import * as variants from "./tools/variants.js";
import * as components from "./tools/components.js";

const server = new McpServer({
  name: "database-of-things",
  version: "0.3.0",
});

// Tools: entity search/lookup (3) — read-only
entities.register(server);
// Tools: collection browse (1)
collections.register(server);
// Tools: variants (1)
variants.register(server);
// Tools: components (1)
components.register(server);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Database of Things MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
