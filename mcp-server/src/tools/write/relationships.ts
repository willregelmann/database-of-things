import { supabase } from "../../index.js";

interface CreateRelationshipArgs {
  from_id: string;
  to_id: string;
  type: string;
  order?: number;
}

export async function createRelationship(args: CreateRelationshipArgs): Promise<any> {
  try {
    const { from_id, to_id, type, order } = args;

    // Validate required fields
    if (!from_id || !to_id || !type) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required fields: from_id, to_id, and type are required",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Validate UUID format (basic check)
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(from_id)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format for from_id: ${from_id}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    if (!uuidRegex.test(to_id)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format for to_id: ${to_id}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    // Check for circular reference (from_id === to_id)
    if (from_id === to_id) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Cannot create self-referential relationship",
            error_code: "CIRCULAR_REFERENCE"
          }, null, 2)
        }]
      };
    }

    // Create relationship
    const { data, error } = await supabase
      .from("relationships")
      .insert({
        from_id,
        to_id,
        type,
        order
      })
      .select("id")
      .single();

    if (error) {
      // Check for duplicate relationship (unique constraint violation)
      if (error.code === "23505") {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: "Relationship already exists",
              error_code: "RELATIONSHIP_EXISTS",
              details: { from_id, to_id, type }
            }, null, 2)
          }]
        };
      }

      // Check for foreign key violation (entity doesn't exist)
      if (error.code === "23503") {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: "Referenced entity does not exist",
              error_code: "NOT_FOUND",
              details: { from_id, to_id }
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
          relationship_id: data.id
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

export async function deleteRelationship(args: { from_id: string; to_id: string; type: string }): Promise<any> {
  try {
    const { from_id, to_id, type } = args;

    // Validate required fields
    if (!from_id || !to_id || !type) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: "Missing required fields: from_id, to_id, and type are required",
            error_code: "MISSING_REQUIRED_FIELD"
          }, null, 2)
        }]
      };
    }

    // Validate UUID format (basic check)
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(from_id)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format for from_id: ${from_id}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    if (!uuidRegex.test(to_id)) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: false,
            error: `Invalid UUID format for to_id: ${to_id}`,
            error_code: "INVALID_UUID"
          }, null, 2)
        }]
      };
    }

    const { error } = await supabase
      .from("relationships")
      .delete()
      .eq("from_id", from_id)
      .eq("to_id", to_id)
      .eq("type", type);

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
