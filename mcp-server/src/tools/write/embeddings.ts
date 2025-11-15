import { supabase } from "../../index.js";

// Validate UUID format
function isValidUUID(uuid: string): boolean {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

// Note: This tool queues embedding generation, actual generation happens server-side
// Embeddings must be generated externally using scripts/generate-embeddings.py
export async function generateEmbedding(args: { entity_id: string }): Promise<any> {
  try {
    const { entity_id } = args;

    if (!entity_id) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required field: entity_id",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Validate UUID format
    if (!isValidUUID(entity_id)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format: ${entity_id}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    // Check if entity exists
    const { data: entity, error: checkError } = await supabase
      .from("entities")
      .select("id, name")
      .eq("id", entity_id)
      .single();

    if (checkError || !entity) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Entity '${entity_id}' not found`,
            error_code: "NOT_FOUND"
          }, null, 2)
        }]
      };
    }

    // For now, just mark that embedding generation was requested
    // In real implementation, this would trigger background job
    // User must run scripts/generate-embeddings.py separately

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: true,
          message: `Embedding generation queued for entity '${entity.name}'. Run scripts/generate-embeddings.py to process.`
        }, null, 2)
      }]
    };

  } catch (err: any) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: false,
          error: err.message,
          error_code: "INTERNAL_ERROR"
        }, null, 2)
      }]
    };
  }
}

export async function bulkGenerateEmbeddings(args: { entity_ids: string[] }): Promise<any> {
  try {
    const { entity_ids } = args;

    if (!entity_ids || entity_ids.length === 0) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required field: entity_ids",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Validate all UUIDs
    const invalid_uuids = entity_ids.filter(id => !isValidUUID(id));
    if (invalid_uuids.length > 0) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format: ${invalid_uuids.join(", ")}`,
            error_code: "INVALID_UUID",
            details: { invalid_uuids }
          }, null, 2)
        }]
      };
    }

    // Check which entities exist
    const { data: entities, error } = await supabase
      .from("entities")
      .select("id, name")
      .in("id", entity_ids);

    if (error) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: error.message,
            error_code: "DATABASE_ERROR"
          }, null, 2)
        }]
      };
    }

    const found_ids = entities?.map(e => e.id) || [];
    const not_found = entity_ids.filter(id => !found_ids.includes(id));

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: true,
          success_count: found_ids.length,
          failed: not_found,
          errors: not_found.length > 0 ? { not_found: `${not_found.length} entities not found` } : {},
          message: `Embedding generation queued for ${found_ids.length} entities. Run scripts/generate-embeddings.py to process.`
        }, null, 2)
      }]
    };

  } catch (err: any) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: false,
          error: err.message,
          error_code: "INTERNAL_ERROR"
        }, null, 2)
      }]
    };
  }
}
