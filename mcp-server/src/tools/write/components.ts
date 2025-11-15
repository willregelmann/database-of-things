import { supabase } from "../../index.js";

interface CreateComponentArgs {
  component_of: string;
  name: string;
  quantity?: number;
  order?: number;
  image_url?: string;
  thumbnail_url?: string;
  attributes?: Record<string, any>;
}

export async function createComponent(args: CreateComponentArgs): Promise<any> {
  try {
    const { component_of, name, quantity, order, image_url, thumbnail_url, attributes } = args;

    // Validate required fields
    if (!component_of || !name) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required fields: component_of and name are required",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Validate UUID format for component_of
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(component_of)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format for component_of: ${component_of}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    // Check that parent entity exists
    const { data: parentEntity, error: checkError } = await supabase
      .from("entities")
      .select("id")
      .eq("id", component_of)
      .single();

    if (checkError || !parentEntity) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Parent entity '${component_of}' not found`,
            error_code: "NOT_FOUND"
          }, null, 2)
        }]
      };
    }

    // Create component
    const { data, error } = await supabase
      .from("components")
      .insert({
        component_of,
        name,
        quantity: quantity || 1,
        order,
        image_url,
        thumbnail_url,
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
              error: `Parent entity '${component_of}' not found`,
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
          component_id: data.id
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
