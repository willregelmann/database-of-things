import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { supabase } from "../db.js";
import { generateTextEmbedding } from "../utils/embeddings.js";
import { localizeImageInternal } from "./images.js";

const ItemSchema = z.object({
  name: z.string(),
  type: z.string().optional(),
  category: z.string().optional(),
  year: z.number().int().optional(),
  country: z.string().optional(),
  language: z.string().optional(),
  source_url: z.string().optional(),
  external_ids: z.record(z.string()).optional(),
  attributes: z.record(z.unknown()).optional(),
  image_url: z.string().optional(),
  order: z.number().int().optional(),
});

export function register(server: McpServer) {
  server.tool(
    "entities_upsert",
    "Bulk upsert items into a collection in a single transaction. Handles deduplication via external_ids, parallel image processing, and text embeddings. Use for all curator imports.",
    {
      collection_id: z.string().uuid().describe("Parent collection UUID"),
      items: z.array(ItemSchema).describe("Items to upsert"),
      skip_duplicates: z.boolean().default(true).describe("Skip items with existing external_ids (default true)"),
      update_existing: z.boolean().default(false).describe("Update existing items instead of skipping"),
      localize_images: z.boolean().default(true).describe("Download and store images in Supabase Storage"),
      parallel_image_limit: z.number().int().min(1).max(50).default(10).describe("Max concurrent image downloads"),
    },
    async ({ collection_id, items, skip_duplicates, update_existing, localize_images, parallel_image_limit }) => {
      if (!items.length) {
        return { content: [{ type: "text", text: JSON.stringify({ success: true, summary: { total: 0, created: 0, updated: 0, skipped: 0, errors: 0 } }, null, 2) }] };
      }

      console.error(`\nStarting bulk upsert: ${items.length} items into collection ${collection_id}`);
      const startTime = Date.now();

      // Step 1: Bulk DB insert via stored procedure
      const { data: importResult, error: importError } = await supabase.rpc("import_curator_batch", {
        p_collection_id: collection_id,
        p_items: items,
        p_skip_duplicates: skip_duplicates,
        p_update_existing: update_existing,
      });

      if (importError) {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({ success: false, error: importError.message, error_code: "DATABASE_ERROR" }, null, 2),
          }],
        };
      }

      const result = importResult as any;
      console.error(`DB import: ${result.summary.created} created, ${result.summary.updated} updated, ${result.summary.skipped} skipped`);

      // Step 2: Generate text embeddings for new entities
      if (result.created_entity_ids?.length > 0) {
        console.error(`Generating embeddings for ${result.created_entity_ids.length} new entities...`);
        const { data: entities } = await supabase
          .from("entities")
          .select("id, name")
          .in("id", result.created_entity_ids);

        if (entities) {
          const batchSize = 50;
          for (let i = 0; i < entities.length; i += batchSize) {
            await Promise.allSettled(
              entities.slice(i, i + batchSize).map(async (e: any) => {
                try {
                  const embedding = await generateTextEmbedding(e.name);
                  await supabase.from("entities").update({ name_embedding: embedding }).eq("id", e.id);
                } catch (err: any) {
                  console.error(`Embedding failed for "${e.name}": ${err.message}`);
                }
              })
            );
          }
        }
        console.error(`Embeddings done`);
      }

      // Step 3: Process images
      const imageStats = { attempted: 0, succeeded: 0, failed: 0 };

      if (localize_images) {
        // Build map from external_id value → entity_id for created + updated entities
        const entityMap = new Map<string, string>();
        const allEntityIds = [...(result.created_entity_ids ?? []), ...(result.updated_entity_ids ?? [])];

        if (allEntityIds.length > 0) {
          const { data: entities } = await supabase
            .from("entities")
            .select("id, external_ids")
            .in("id", allEntityIds);

          for (const e of entities ?? []) {
            if (e.external_ids) {
              const firstVal = Object.values(e.external_ids)[0] as string;
              if (firstVal) entityMap.set(firstVal, e.id);
            }
          }
        }

        const itemsWithImages = items.filter(item => item.image_url);
        imageStats.attempted = itemsWithImages.length;

        if (itemsWithImages.length > 0) {
          console.error(`Processing ${itemsWithImages.length} images (parallel: ${parallel_image_limit})...`);
          for (let i = 0; i < itemsWithImages.length; i += parallel_image_limit) {
            await Promise.allSettled(
              itemsWithImages.slice(i, i + parallel_image_limit).map(async (item) => {
                let entityId: string | undefined;
                if (item.external_ids) {
                  const firstVal = Object.values(item.external_ids)[0] as string;
                  entityId = entityMap.get(firstVal);
                }
                if (!entityId) return;
                try {
                  await localizeImageInternal({ external_url: item.image_url!, entity_id: entityId });
                  imageStats.succeeded++;
                } catch (err: any) {
                  console.error(`Image failed for "${item.name}": ${err.message}`);
                  imageStats.failed++;
                }
              })
            );
          }
          console.error(`Images: ${imageStats.succeeded}/${imageStats.attempted} processed`);
        }
      }

      const totalMs = Date.now() - startTime;
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            ...result,
            execution_time_ms: totalMs,
            image_processing: localize_images ? imageStats : undefined,
          }, null, 2),
        }],
      };
    }
  );
}
