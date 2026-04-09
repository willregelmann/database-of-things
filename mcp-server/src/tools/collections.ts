import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { supabase } from "../db.js";

export function register(server: McpServer) {
  server.tool(
    "collection_browse",
    "List items inside a collection, optionally filtered by entity type.",
    {
      collection_id: z.string().uuid().describe("Collection UUID"),
      type: z.string().optional().describe("Filter by entity type (e.g. 'card', 'figure')"),
      limit: z.number().int().min(1).max(500).default(50).describe("Max items to return"),
    },
    async ({ collection_id, type, limit }) => {
      const { data: collection, error: collErr } = await supabase
        .from("entities")
        .select("id, name, type, year")
        .eq("id", collection_id)
        .single();
      if (collErr) throw new Error(`Collection not found: ${collErr.message}`);

      const { data: items, error } = await supabase
        .from("relationships")
        .select("to_id, order, entities!relationships_to_id_fkey(id, name, type, year)")
        .eq("from_id", collection_id)
        .order("order", { ascending: true, nullsFirst: false })
        .limit(limit);
      if (error) throw new Error(`Browse failed: ${error.message}`);

      const filtered = type ? (items ?? []).filter((r: any) => r.entities.type === type) : (items ?? []);

      if (!filtered.length) {
        return { content: [{ type: "text", text: `Collection "${collection.name}" has no ${type ? `items of type "${type}"` : "items"}.` }] };
      }

      let out = `# ${collection.name}\n\n`;
      out += `**Type**: ${collection.type}${collection.year ? `  **Year**: ${collection.year}` : ""}  **Items**: ${filtered.length}\n\n`;
      filtered.forEach((r: any, i: number) => {
        const e = r.entities;
        out += `${i + 1}. **${e.name}** (${e.type})${e.year ? ` — ${e.year}` : ""}\n   ID: ${e.id}\n`;
      });

      return { content: [{ type: "text", text: out }] };
    }
  );
}
