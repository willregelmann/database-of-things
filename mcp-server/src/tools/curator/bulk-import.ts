import { supabase } from "../../index.js";
import { localizeImage } from "../write/localize-image.js";
import { generateTextEmbedding } from "../../utils/embeddings.js";

interface BulkImportItem {
  name: string;
  type?: string;
  category?: string;
  year?: number;
  country?: string;
  language?: string;
  source_url?: string;
  external_ids?: Record<string, string>;
  attributes?: Record<string, any>;
  image_url?: string;
  order?: number;
}

interface BulkImportArgs {
  collection_id: string;
  items: BulkImportItem[];
  skip_duplicates?: boolean;
  update_existing?: boolean;
  generate_embeddings?: boolean;
  localize_images?: boolean;
  parallel_image_limit?: number;
}

interface BulkImportResult {
  success: boolean;
  summary: {
    total: number;
    created: number;
    updated: number;
    skipped: number;
    errors: number;
  };
  created_entity_ids: string[];
  updated_entity_ids: string[];
  errors: Array<{ item: string; error: string }>;
  execution_time_ms: number;
  image_processing?: {
    attempted: number;
    succeeded: number;
    failed: number;
  };
}

/**
 * Bulk import curator items in a single transaction
 * Much faster than individual MCP calls (100x+ speedup for large batches)
 */
export async function bulkImportCuratorBatch(args: BulkImportArgs): Promise<any> {
  try {
    const {
      collection_id,
      items,
      skip_duplicates = true,
      update_existing = false,
      generate_embeddings = true,
      localize_images = true,
      parallel_image_limit = 10
    } = args;

    // Validate required fields
    if (!collection_id || !items || !Array.isArray(items)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required fields: collection_id and items array are required",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    if (items.length === 0) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: true,
            summary: { total: 0, created: 0, updated: 0, skipped: 0, errors: 0 },
            created_entity_ids: [],
            updated_entity_ids: [],
            errors: [],
            execution_time_ms: 0
          }, null, 2)
        }]
      };
    }

    console.error(`\n🚀 Starting bulk import: ${items.length} items`);
    const startTime = Date.now();

    // Step 1: Call database function for bulk entity creation
    console.error(`📦 Bulk creating entities and relationships...`);
    const { data: importResult, error: importError } = await supabase.rpc('import_curator_batch', {
      p_collection_id: collection_id,
      p_items: items,
      p_skip_duplicates: skip_duplicates,
      p_update_existing: update_existing
    });

    if (importError) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: importError.message,
            error_code: "DATABASE_ERROR",
            details: importError
          }, null, 2)
        }]
      };
    }

    const result = importResult as BulkImportResult;
    console.error(`✅ Database import complete: ${result.summary.created} created, ${result.summary.updated} updated, ${result.summary.skipped} skipped`);

    // Step 2: Generate embeddings for new entities (if enabled)
    if (generate_embeddings && result.created_entity_ids.length > 0) {
      console.error(`🧠 Generating text embeddings for ${result.created_entity_ids.length} new entities...`);

      // Get entity names for embedding generation
      const { data: entities, error: fetchError } = await supabase
        .from('entities')
        .select('id, name')
        .in('id', result.created_entity_ids);

      if (!fetchError && entities) {
        // Generate embeddings in batches (avoid overwhelming the system)
        const batchSize = 50;
        for (let i = 0; i < entities.length; i += batchSize) {
          const batch = entities.slice(i, i + batchSize);

          await Promise.allSettled(
            batch.map(async (entity) => {
              try {
                const embedding = await generateTextEmbedding(entity.name);
                await supabase
                  .from('entities')
                  .update({ name_embedding: embedding })
                  .eq('id', entity.id);
              } catch (err: any) {
                console.error(`⚠️  Failed to generate embedding for "${entity.name}": ${err.message}`);
              }
            })
          );
        }
        console.error(`✓ Text embeddings generated`);
      }
    }

    // Step 3: Process images in parallel (if enabled)
    let imageProcessing = {
      attempted: 0,
      succeeded: 0,
      failed: 0
    };

    if (localize_images) {
      // Collect items that need images (both created and updated)
      const itemsWithImages = items.filter(item => item.image_url);
      imageProcessing.attempted = itemsWithImages.length;

      if (itemsWithImages.length > 0) {
        console.error(`🖼️  Processing ${itemsWithImages.length} images (parallel limit: ${parallel_image_limit})...`);

        // Create a mapping of external_ids to entity_ids
        const entityMap = new Map<string, string>();

        // Map created entities
        for (let i = 0; i < Math.min(items.length, result.created_entity_ids.length); i++) {
          const item = items[i];
          const entityId = result.created_entity_ids[i];
          if (item.external_ids) {
            const firstKey = Object.keys(item.external_ids)[0];
            if (firstKey) {
              entityMap.set(item.external_ids[firstKey], entityId);
            }
          }
        }

        // Map updated entities
        for (let i = 0; i < result.updated_entity_ids.length; i++) {
          const entityId = result.updated_entity_ids[i];
          // Find corresponding item
          const item = items.find(it => {
            if (it.external_ids) {
              const firstKey = Object.keys(it.external_ids)[0];
              return firstKey && entityMap.get(it.external_ids[firstKey]) === undefined;
            }
            return false;
          });
          if (item && item.external_ids) {
            const firstKey = Object.keys(item.external_ids)[0];
            if (firstKey) {
              entityMap.set(item.external_ids[firstKey], entityId);
            }
          }
        }

        // Process images in batches with concurrency limit
        const processBatch = async (batch: BulkImportItem[]) => {
          const results = await Promise.allSettled(
            batch.map(async (item) => {
              if (!item.image_url) return;

              // Find entity_id for this item
              let entityId: string | undefined;
              if (item.external_ids) {
                const firstKey = Object.keys(item.external_ids)[0];
                if (firstKey) {
                  entityId = entityMap.get(item.external_ids[firstKey]);
                }
              }

              if (!entityId) {
                console.error(`⚠️  Could not find entity_id for "${item.name}"`);
                return;
              }

              try {
                await localizeImage({
                  entity_id: entityId,
                  external_url: item.image_url
                });
                imageProcessing.succeeded++;
              } catch (err: any) {
                console.error(`⚠️  Failed to process image for "${item.name}": ${err.message}`);
                imageProcessing.failed++;
              }
            })
          );
        };

        // Process in batches
        for (let i = 0; i < itemsWithImages.length; i += parallel_image_limit) {
          const batch = itemsWithImages.slice(i, i + parallel_image_limit);
          await processBatch(batch);
          console.error(`   Progress: ${Math.min(i + parallel_image_limit, itemsWithImages.length)}/${itemsWithImages.length} images processed`);
        }

        console.error(`✓ Image processing complete: ${imageProcessing.succeeded} succeeded, ${imageProcessing.failed} failed`);
      }
    }

    // Final result
    const totalTime = Date.now() - startTime;
    const finalResult = {
      ...result,
      execution_time_ms: totalTime,
      image_processing: localize_images ? imageProcessing : undefined
    };

    console.error(`\n✅ Bulk import complete in ${(totalTime / 1000).toFixed(2)}s`);
    console.error(`   Created: ${result.summary.created}, Updated: ${result.summary.updated}, Skipped: ${result.summary.skipped}`);
    if (localize_images) {
      console.error(`   Images: ${imageProcessing.succeeded}/${imageProcessing.attempted} processed`);
    }

    return {
      content: [{
        type: "text",
        text: JSON.stringify(finalResult, null, 2)
      }]
    };

  } catch (err: any) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: false,
          error: err.message,
          error_code: "INTERNAL_ERROR",
          stack: err.stack
        }, null, 2)
      }]
    };
  }
}
