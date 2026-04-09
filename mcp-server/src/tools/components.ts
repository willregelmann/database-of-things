import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { supabase } from "../db.js";

export function register(server: McpServer) {
  server.tool(
    "component_list",
    "List all physical components of an entity (e.g. Zord pieces in a Megazord, tokens in a board game).",
    {
      entity_id: z.string().uuid().describe("Parent entity UUID"),
    },
    async ({ entity_id }) => {
      const { data: entity, error: eErr } = await supabase.from("entities").select("id, name").eq("id", entity_id).single();
      if (eErr) throw new Error(`Entity not found: ${eErr.message}`);

      const { data: components, error } = await supabase
        .from("components")
        .select("id, name, quantity, order, attributes, component_primary_image:images!primary_image_id(image_url, thumbnail_url)")
        .eq("component_of", entity_id)
        .order("order", { ascending: true, nullsFirst: false });
      if (error) throw new Error(`Failed to list components: ${error.message}`);

      if (!components?.length) return { content: [{ type: "text", text: `No components for "${entity.name}".` }] };

      let out = `# Components of ${entity.name}\n\n`;
      components.forEach((c: any, i: number) => {
        out += `## ${i + 1}. ${c.name}${c.quantity > 1 ? ` ×${c.quantity}` : ""}  ID: ${c.id}\n`;
        if (c.component_primary_image) out += `Image: ${c.component_primary_image.image_url}\n`;
        if (c.attributes && Object.keys(c.attributes).length > 0) {
          for (const [k, val] of Object.entries(c.attributes)) out += `- ${k}: ${JSON.stringify(val)}\n`;
        }
        out += "\n";
      });
      return { content: [{ type: "text", text: out }] };
    }
  );

  server.tool(
    "component_create",
    "Create a component (physical part) of an entity.",
    {
      component_of: z.string().uuid().describe("Parent entity UUID"),
      name: z.string().describe("Component name"),
      quantity: z.number().int().min(1).default(1).describe("Quantity (default 1)"),
      order: z.number().int().optional().describe("Display order"),
      attributes: z.record(z.unknown()).optional().describe("Component metadata"),
    },
    async ({ component_of, name, quantity, order, attributes }) => {
      const { data, error } = await supabase
        .from("components")
        .insert({ component_of, name, quantity, order, attributes: attributes ?? {} })
        .select("id")
        .single();
      if (error) return { content: [{ type: "text", text: JSON.stringify({ success: false, error: error.message }, null, 2) }] };
      return { content: [{ type: "text", text: JSON.stringify({ success: true, component_id: data.id }, null, 2) }] };
    }
  );
}
