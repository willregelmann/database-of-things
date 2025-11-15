import { supabase } from "../../index.js";

interface CreateImageArgs {
  entity_id?: string;
  variant_id?: string;
  component_id?: string;
  image_url: string;
  thumbnail_url?: string;
  source_url?: string;
  is_primary?: boolean;
}

export async function createImage(args: CreateImageArgs): Promise<any> {
  try {
    const { entity_id, variant_id, component_id, image_url, thumbnail_url, source_url, is_primary } = args;

    // Validate that exactly one parent is provided
    const parents = [entity_id, variant_id, component_id].filter(Boolean);
    if (parents.length === 0) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Must provide exactly one of: entity_id, variant_id, or component_id",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    if (parents.length > 1) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Cannot link image to multiple parents. Provide only one of: entity_id, variant_id, or component_id",
            error_code: "INVALID_INPUT"
          }, null, 2)
        }]
      };
    }

    // Validate required field
    if (!image_url) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required field: image_url",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Validate UUID format for whichever parent ID is provided
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const parentId = entity_id || variant_id || component_id;
    const parentType = entity_id ? 'entity_id' : variant_id ? 'variant_id' : 'component_id';

    if (!uuidRegex.test(parentId!)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format for ${parentType}: ${parentId}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    // Check that the parent exists
    let parentExists = false;
    if (entity_id) {
      const { data, error } = await supabase
        .from("entities")
        .select("id")
        .eq("id", entity_id)
        .single();
      parentExists = !error && !!data;
    } else if (variant_id) {
      const { data, error } = await supabase
        .from("variants")
        .select("id")
        .eq("id", variant_id)
        .single();
      parentExists = !error && !!data;
    } else if (component_id) {
      const { data, error } = await supabase
        .from("components")
        .select("id")
        .eq("id", component_id)
        .single();
      parentExists = !error && !!data;
    }

    if (!parentExists) {
      const parentName = entity_id ? 'Entity' : variant_id ? 'Variant' : 'Component';
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `${parentName} '${parentId}' not found`,
            error_code: "NOT_FOUND"
          }, null, 2)
        }]
      };
    }

    // Create image record
    const { data: imageData, error: imageError } = await supabase
      .from("images")
      .insert({
        image_url,
        thumbnail_url,
        source_url
      })
      .select("id")
      .single();

    if (imageError) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: imageError.message,
            error_code: "DATABASE_ERROR",
            details: imageError
          }, null, 2)
        }]
      };
    }

    const image_id = imageData.id;

    // If is_primary, update the parent's primary_image_id
    if (is_primary) {
      let updateError = null;
      if (entity_id) {
        const { error } = await supabase
          .from("entities")
          .update({ primary_image_id: image_id })
          .eq("id", entity_id);
        updateError = error;
      } else if (variant_id) {
        const { error } = await supabase
          .from("variants")
          .update({ primary_image_id: image_id })
          .eq("id", variant_id);
        updateError = error;
      } else if (component_id) {
        const { error } = await supabase
          .from("components")
          .update({ primary_image_id: image_id })
          .eq("id", component_id);
        updateError = error;
      }

      if (updateError) {
        // Rollback: delete the image we just created
        await supabase.from("images").delete().eq("id", image_id);

        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: `Failed to set as primary image: ${updateError.message}`,
              error_code: "DATABASE_ERROR",
              details: updateError
            }, null, 2)
          }]
        };
      }
    } else {
      // Not primary, so add to additional images join table
      let linkError = null;
      if (entity_id) {
        const { error } = await supabase
          .from("entity_additional_images")
          .insert({ entity_id, image_id });
        linkError = error;
      } else if (variant_id) {
        const { error } = await supabase
          .from("variant_additional_images")
          .insert({ variant_id, image_id });
        linkError = error;
      } else if (component_id) {
        const { error } = await supabase
          .from("component_additional_images")
          .insert({ component_id, image_id });
        linkError = error;
      }

      if (linkError) {
        // Rollback: delete the image we just created
        await supabase.from("images").delete().eq("id", image_id);

        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: `Failed to link image to parent: ${linkError.message}`,
              error_code: linkError.code === "23503" ? "NOT_FOUND" : "DATABASE_ERROR",
              details: linkError
            }, null, 2)
          }]
        };
      }
    }

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: true,
          image_id
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
