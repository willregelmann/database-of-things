import { supabase } from "../../index.js";
import { generateTextEmbedding } from "../../utils/embeddings.js";

interface CreateEntityArgs {
  name: string;
  type: string;
  category?: string;
  year?: number;
  country?: string;
  language?: string;
  source_url?: string;
  external_ids?: Record<string, string>;
  attributes?: Record<string, any>;
}

interface EntityResponse {
  success: boolean;
  entity_id?: string;
  error?: string;
  error_code?: string;
  details?: any;
}

export async function createEntity(args: CreateEntityArgs): Promise<any> {
  try {
    const { name, type, category, year, country, language, source_url, external_ids, attributes } = args;

    // Validate required fields
    if (!name || !type) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required fields: name and type are required",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Create entity
    const { data, error } = await supabase
      .from("entities")
      .insert({
        name,
        type,
        category,
        year,
        country,
        language,
        source_url,
        external_ids: external_ids || {},
        attributes: attributes || {}
      })
      .select("id")
      .single();

    if (error) {
      // Check for duplicate
      if (error.code === "23505") {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: `Entity with name '${name}' already exists`,
              error_code: "DUPLICATE_ENTITY",
              details: { message: error.message }
            }, null, 2)
          }]
        };
      }

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: error.message,
            error_code: "DATABASE_ERROR",
            details: error
          }, null, 2)
        }]
      };
    }

    // AUTOMATIC: Generate text embedding for semantic search
    try {
      console.error(`Generating text embedding for "${name}"...`);
      const embedding = await generateTextEmbedding(name);

      // Update entity with embedding
      await supabase
        .from("entities")
        .update({ name_embedding: embedding })
        .eq("id", data.id);

      console.error(`✓ Text embedding generated for "${name}"`);
    } catch (embeddingError: any) {
      // Log but don't fail - entity was created successfully
      console.error(`Warning: Failed to generate embedding: ${embeddingError.message}`);
    }

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: true,
          entity_id: data.id
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

export async function updateEntity(args: any): Promise<any> {
  try {
    const { entity_id, ...updates } = args;

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

    // Check if entity exists
    const { data: existing, error: checkError } = await supabase
      .from("entities")
      .select("id")
      .eq("id", entity_id)
      .single();

    if (checkError || !existing) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Entity with id '${entity_id}' not found`,
            error_code: "NOT_FOUND"
          }, null, 2)
        }]
      };
    }

    // Update entity
    const { error } = await supabase
      .from("entities")
      .update(updates)
      .eq("id", entity_id);

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

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: true
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

export async function deleteEntity(args: { entity_id: string }): Promise<any> {
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

    const { error } = await supabase
      .from("entities")
      .delete()
      .eq("id", entity_id);

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

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: true
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
