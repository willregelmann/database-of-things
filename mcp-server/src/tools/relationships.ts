import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { supabase } from "../db.js";

export function register(server: McpServer) {
  server.tool(
    "relationship_create",
    "Create a parent→child relationship between two entities (e.g. add a card to a collection).",
    {
      from_id: z.string().uuid().describe("Parent entity UUID"),
      to_id: z.string().uuid().describe("Child entity UUID"),
      order: z.number().int().optional().describe("Sort order within parent"),
    },
    async ({ from_id, to_id, order }) => {
      if (from_id === to_id) {
        return { content: [{ type: "text", text: JSON.stringify({ success: false, error: "Cannot relate entity to itself" }, null, 2) }] };
      }
      const { data, error } = await supabase
        .from("relationships")
        .insert({ from_id, to_id, order })
        .select("id")
        .single();

      if (error) {
        if (error.code === "23505") return { content: [{ type: "text", text: JSON.stringify({ success: false, error: "Relationship already exists" }, null, 2) }] };
        return { content: [{ type: "text", text: JSON.stringify({ success: false, error: error.message }, null, 2) }] };
      }
      return { content: [{ type: "text", text: JSON.stringify({ success: true, relationship_id: data.id }, null, 2) }] };
    }
  );

  server.tool(
    "relationship_delete",
    "Remove a parent→child relationship between two entities.",
    {
      from_id: z.string().uuid().describe("Parent entity UUID"),
      to_id: z.string().uuid().describe("Child entity UUID"),
    },
    async ({ from_id, to_id }) => {
      const { error } = await supabase.from("relationships").delete().eq("from_id", from_id).eq("to_id", to_id);
      if (error) return { content: [{ type: "text", text: JSON.stringify({ success: false, error: error.message }, null, 2) }] };
      return { content: [{ type: "text", text: JSON.stringify({ success: true }, null, 2) }] };
    }
  );
}
