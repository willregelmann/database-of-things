import { supabase } from "../../index.js";

interface CreateVariantArgs {
  variant_of: string;
  name: string;
  attributes?: Record<string, any>;
}

export async function createVariant(args: CreateVariantArgs): Promise<any> {
  try {
    const { variant_of, name, attributes } = args;

    // Validate required fields
    if (!variant_of || !name) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required fields: variant_of and name are required",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Validate UUID format for variant_of
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(variant_of)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format for variant_of: ${variant_of}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    // Check that base entity exists
    const { data: baseEntity, error: checkError } = await supabase
      .from("entities")
      .select("id")
      .eq("id", variant_of)
      .single();

    if (checkError || !baseEntity) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Base entity '${variant_of}' not found`,
            error_code: "NOT_FOUND"
          }, null, 2)
        }]
      };
    }

    // Create variant
    // Note: For images, use the create_image MCP tool after creating the variant
    // to add images to the images table and link via primary_image_id
    const { data, error } = await supabase
      .from("variants")
      .insert({
        variant_of,
        name,
        attributes: attributes || {}
      })
      .select("id")
      .single();

    if (error) {
      // Check for foreign key violation (should have been caught above, but just in case)
      if (error.code === "23503") {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: `Base entity '${variant_of}' not found`,
              error_code: "NOT_FOUND"
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

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: true,
          variant_id: data.id
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

export async function updateVariant(args: any): Promise<any> {
  try {
    const { variant_id, ...updates } = args;

    // Validate required field
    if (!variant_id) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required field: variant_id",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Validate UUID format for variant_id
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(variant_id)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format for variant_id: ${variant_id}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    // Check if variant exists
    const { data: existing, error: checkError } = await supabase
      .from("variants")
      .select("id")
      .eq("id", variant_id)
      .single();

    if (checkError || !existing) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Variant with id '${variant_id}' not found`,
            error_code: "NOT_FOUND"
          }, null, 2)
        }]
      };
    }

    // Update variant
    const { error } = await supabase
      .from("variants")
      .update(updates)
      .eq("id", variant_id);

    if (error) {
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
