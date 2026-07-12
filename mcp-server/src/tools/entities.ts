import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { supabase } from "../db.js";

export function register(server: McpServer) {
  // entity_search — semantic + trigram search
  server.tool(
    "entity_search",
    "Search for collectibles by name using semantic search. Handles synonyms and variations (e.g. 'pokemon' vs 'pokémon').",
    {
      query: z.string().describe("Search query"),
      type: z.string().optional().describe("Filter by entity type (e.g. 'card', 'collection')"),
      category: z.string().optional().describe("Filter by category (trading_card_games, figures, comics, video_games, buildables)"),
      limit: z.number().int().min(1).max(100).default(20).describe("Max results (default 20)"),
    },
    async ({ query, type, category, limit }) => {
      const { data, error } = await supabase.rpc("search_by_text", {
        query_text: query,
        entity_type_filter: type ?? null,
        category_filter: category ?? null,
        result_limit: limit,
      });
      if (error) throw new Error(`Search failed: ${error.message}`);
      if (!data?.length) return { content: [{ type: "text", text: `No results for "${query}"` }] };

      const results = data.map((item: any, i: number) => {
        const sim = (item.similarity * 100).toFixed(1);
        const img = item.thumbnail_url || item.image_url ? `\n   Image: ${item.thumbnail_url || item.image_url}` : "";
        return `${i + 1}. **${item.name}** (${item.type}${item.category ? ` | ${item.category}` : ""})\n   ID: ${item.id} | Similarity: ${sim}%${img}`;
      }).join("\n\n");

      return { content: [{ type: "text", text: `Found ${data.length} results for "${query}":\n\n${results}` }] };
    }
  );

  // entity_find — exact lookup by external_id (deduplication)
  server.tool(
    "entity_find",
    "Find an entity by external ID. Essential for deduplication in curator workflows.",
    {
      key: z.string().describe("External ID field name (e.g. 'pokemontcg_io', 'tcgplayer')"),
      value: z.string().describe("External ID value"),
      type: z.string().optional().describe("Filter by entity type"),
    },
    async ({ key, value, type }) => {
      let query = supabase
        .from("entities")
        .select("id, name, type, year, external_ids")
        .contains("external_ids", { [key]: value });
      if (type) query = query.eq("type", type);
      const { data, error } = await query.limit(10);
      if (error) throw new Error(`Find failed: ${error.message}`);
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ found: data?.length ?? 0, results: data ?? [] }, null, 2),
        }],
      };
    }
  );

  // entity_get — full entity details
  server.tool(
    "entity_get",
    "Get full details for an entity: attributes, images, parents, children, variants, and components.",
    {
      id: z.string().uuid().describe("Entity UUID"),
    },
    async ({ id }) => {
      const { data: entity, error } = await supabase
        .from("entities")
        .select("*, entity_primary_image:images!primary_image_id(id, image_url, thumbnail_url)")
        .eq("id", id)
        .single();
      if (error) throw new Error(`Entity not found: ${error.message}`);

      const [{ data: variants }, { data: components }, { data: parents }, { data: children }] = await Promise.all([
        supabase.from("variants").select("id, name, attributes").eq("variant_of", id),
        supabase.from("components").select("id, name, quantity, order, attributes").eq("component_of", id).order("order", { ascending: true, nullsFirst: false }),
        supabase.from("relationships").select("from_id, entities!relationships_from_id_fkey(id, name, type)").eq("to_id", id),
        supabase.from("relationships").select("to_id, order, entities!relationships_to_id_fkey(id, name, type)").eq("from_id", id).order("order", { ascending: true, nullsFirst: false }),
      ]);

      let out = `# ${entity.name}\n\n`;
      out += `**Type**: ${entity.type}  **ID**: ${entity.id}\n`;
      if (entity.year) out += `**Year**: ${entity.year}\n`;
      if (entity.country) out += `**Country**: ${entity.country}\n`;
      if (entity.language) out += `**Language**: ${entity.language}\n`;
      if (entity.source_url) out += `**Source**: ${entity.source_url}\n`;

      if (entity.entity_primary_image) {
        out += `\n## Images\n- **Primary**: ${entity.entity_primary_image.image_url}\n`;
        if (entity.entity_primary_image.thumbnail_url) out += `- **Thumbnail**: ${entity.entity_primary_image.thumbnail_url}\n`;
      }

      if (entity.external_ids && Object.keys(entity.external_ids).length > 0) {
        out += `\n## External IDs\n`;
        for (const [k, v] of Object.entries(entity.external_ids)) out += `- **${k}**: ${v}\n`;
      }

      if (entity.attributes && Object.keys(entity.attributes).length > 0) {
        out += `\n## Attributes\n`;
        for (const [k, v] of Object.entries(entity.attributes)) out += `- **${k}**: ${JSON.stringify(v)}\n`;
      }

      if (parents?.length) {
        out += `\n## Parent Collections\n`;
        parents.forEach((p: any) => out += `- ${p.entities.name} (${p.entities.type}) — ${p.entities.id}\n`);
      }

      if (children?.length) {
        out += `\n## Contains (${children.length})\n`;
        children.forEach((c: any, i: number) => out += `${i + 1}. ${c.entities.name} (${c.entities.type}) — ${c.entities.id}\n`);
      }

      if (variants?.length) {
        out += `\n## Variants (${variants.length})\n`;
        variants.forEach((v: any, i: number) => {
          out += `${i + 1}. **${v.name}** — ${v.id}\n`;
          if (v.attributes && Object.keys(v.attributes).length > 0) {
            for (const [k, val] of Object.entries(v.attributes)) out += `   - ${k}: ${JSON.stringify(val)}\n`;
          }
        });
      }

      if (components?.length) {
        out += `\n## Components (${components.length})\n`;
        components.forEach((c: any, i: number) => {
          out += `${i + 1}. **${c.name}**${c.quantity > 1 ? ` ×${c.quantity}` : ""} — ${c.id}\n`;
        });
      }

      return { content: [{ type: "text", text: out }] };
    }
  );
}
