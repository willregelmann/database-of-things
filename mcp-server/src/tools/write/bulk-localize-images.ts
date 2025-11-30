import { localizeImage } from "./localize-image.js";

interface ImageItem {
  entity_id: string;
  external_url: string;
}

interface BulkLocalizeImagesArgs {
  images: ImageItem[];
  parallel_limit?: number;
}

interface BulkLocalizeResult {
  success: boolean;
  summary: {
    total: number;
    succeeded: number;
    failed: number;
  };
  succeeded: Array<{ entity_id: string; image_url: string; thumbnail_url: string }>;
  errors: Array<{ entity_id: string; external_url: string; error: string }>;
  execution_time_ms: number;
}

/**
 * Bulk localize images for existing entities
 * Downloads, generates thumbnails + CLIP embeddings, uploads to storage, links to entities
 * Uses parallel batching for efficient processing
 */
export async function bulkLocalizeImages(args: BulkLocalizeImagesArgs): Promise<any> {
  try {
    const { images, parallel_limit = 10 } = args;

    // Validate required fields
    if (!images || !Array.isArray(images)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required field: images array is required",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    if (images.length === 0) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: true,
            summary: { total: 0, succeeded: 0, failed: 0 },
            succeeded: [],
            errors: [],
            execution_time_ms: 0
          }, null, 2)
        }]
      };
    }

    // Validate each item has required fields
    for (let i = 0; i < images.length; i++) {
      const item = images[i];
      if (!item.entity_id || !item.external_url) {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: `Item at index ${i} missing required fields: entity_id and external_url are required`,
              error_code: "INVALID_ITEM"
            }, null, 2)
          }]
        };
      }
    }

    console.error(`\n🖼️  Starting bulk image localization: ${images.length} images (parallel limit: ${parallel_limit})`);
    const startTime = Date.now();

    const result: BulkLocalizeResult = {
      success: true,
      summary: { total: images.length, succeeded: 0, failed: 0 },
      succeeded: [],
      errors: [],
      execution_time_ms: 0
    };

    // Process images in batches with concurrency limit
    const processBatch = async (batch: ImageItem[]) => {
      const results = await Promise.allSettled(
        batch.map(async (item) => {
          try {
            const response = await localizeImage({
              entity_id: item.entity_id,
              external_url: item.external_url
            });

            // Parse the response to extract URLs
            const responseText = response.content[0].text;
            const responseData = JSON.parse(responseText);

            if (responseData.success) {
              result.succeeded.push({
                entity_id: item.entity_id,
                image_url: responseData.image_url,
                thumbnail_url: responseData.thumbnail_url
              });
              result.summary.succeeded++;
            } else {
              result.errors.push({
                entity_id: item.entity_id,
                external_url: item.external_url,
                error: responseData.error || "Unknown error"
              });
              result.summary.failed++;
            }
          } catch (err: any) {
            result.errors.push({
              entity_id: item.entity_id,
              external_url: item.external_url,
              error: err.message || String(err)
            });
            result.summary.failed++;
          }
        })
      );
    };

    // Process in batches
    for (let i = 0; i < images.length; i += parallel_limit) {
      const batch = images.slice(i, i + parallel_limit);
      await processBatch(batch);
      const processed = Math.min(i + parallel_limit, images.length);
      console.error(`   Progress: ${processed}/${images.length} images (${result.summary.succeeded} succeeded, ${result.summary.failed} failed)`);
    }

    result.execution_time_ms = Date.now() - startTime;

    console.error(`\n✅ Bulk image localization complete in ${(result.execution_time_ms / 1000).toFixed(2)}s`);
    console.error(`   Succeeded: ${result.summary.succeeded}, Failed: ${result.summary.failed}`);

    return {
      content: [{
        type: "text",
        text: JSON.stringify(result, null, 2)
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
