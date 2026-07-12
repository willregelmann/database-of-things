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
}
