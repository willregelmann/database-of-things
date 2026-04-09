import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { supabase } from "../db.js";

export function register(server: McpServer) {
  server.tool(
    "variant_list",
    "List all variants of an entity (e.g. 1st Edition, Shadowless, Holofoil).",
    {
      entity_id: z.string().uuid().describe("Base entity UUID"),
    },
    async ({ entity_id }) => {
      const { data: entity, error: eErr } = await supabase.from("entities").select("id, name").eq("id", entity_id).single();
      if (eErr) throw new Error(`Entity not found: ${eErr.message}`);

      const { data: variants, error } = await supabase
        .from("variants")
        .select("id, name, attributes, variant_primary_image:images!primary_image_id(image_url, thumbnail_url)")
        .eq("variant_of", entity_id);
      if (error) throw new Error(`Failed to list variants: ${error.message}`);

      if (!variants?.length) return { content: [{ type: "text", text: `No variants for "${entity.name}".` }] };

      let out = `# Variants of ${entity.name}\n\n`;
      variants.forEach((v: any, i: number) => {
        out += `## ${i + 1}. ${v.name}  ID: ${v.id}\n`;
        if (v.variant_primary_image) out += `Image: ${v.variant_primary_image.image_url}\n`;
        if (v.attributes && Object.keys(v.attributes).length > 0) {
          for (const [k, val] of Object.entries(v.attributes)) out += `- ${k}: ${JSON.stringify(val)}\n`;
        }
        out += "\n";
      });
      return { content: [{ type: "text", text: out }] };
    }
  );

  server.tool(
    "variant_create",
    "Create a variant of an entity (e.g. a 1st Edition printing of a card).",
    {
      variant_of: z.string().uuid().describe("Base entity UUID"),
      name: z.string().describe("Variant name (e.g. '1st Edition', 'Shadowless')"),
      attributes: z.record(z.unknown()).optional().describe("Variant metadata (edition, condition, etc.)"),
    },
    async ({ variant_of, name, attributes }) => {
      const { data, error } = await supabase
        .from("variants")
        .insert({ variant_of, name, attributes: attributes ?? {} })
        .select("id")
        .single();
      if (error) return { content: [{ type: "text", text: JSON.stringify({ success: false, error: error.message }, null, 2) }] };
      return { content: [{ type: "text", text: JSON.stringify({ success: true, variant_id: data.id }, null, 2) }] };
    }
  );

  server.tool(
    "variant_update",
    "Update a variant's name or attributes.",
    {
      variant_id: z.string().uuid().describe("Variant UUID"),
      name: z.string().optional(),
      attributes: z.record(z.unknown()).optional(),
    },
    async ({ variant_id, ...updates }) => {
      const { error } = await supabase.from("variants").update(updates).eq("id", variant_id);
      if (error) return { content: [{ type: "text", text: JSON.stringify({ success: false, error: error.message }, null, 2) }] };
      return { content: [{ type: "text", text: JSON.stringify({ success: true }, null, 2) }] };
    }
  );
}
