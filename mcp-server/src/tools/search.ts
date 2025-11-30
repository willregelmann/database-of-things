import { supabase } from "../index.js";

interface SearchArgs {
  query: string;
  entity_type?: string;
  category?: string;
  limit?: number;
}

export async function searchCollectibles(args: SearchArgs) {
  const { query, entity_type, category, limit = 20 } = args;

  // Cap limit at 100
  const cappedLimit = Math.min(limit, 100);

  // Call the search_by_text database function
  const { data, error } = await supabase.rpc("search_by_text", {
    query_text: query,
    entity_type_filter: entity_type || null,
    category_filter: category || null,
    result_limit: cappedLimit,
  });

  if (error) {
    throw new Error(`Search failed: ${error.message}`);
  }

  if (!data || data.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: `No results found for query: "${query}"`,
        },
      ],
    };
  }

  // Format results
  const results = data.map((item: any, index: number) => {
    const similarity = (item.similarity * 100).toFixed(1);
    const categoryInfo = item.category ? ` | ${item.category}` : "";
    const imageInfo = item.thumbnail_url || item.image_url ? `\n   Image: ${item.thumbnail_url || item.image_url}` : "";
    return `${index + 1}. **${item.name}** (${item.type}${categoryInfo})
   ID: ${item.id}
   Similarity: ${similarity}%
   Year: ${item.year || "Unknown"}${imageInfo}`;
  }).join("\n\n");

  return {
    content: [
      {
        type: "text",
        text: `Found ${data.length} results for "${query}":\n\n${results}`,
      },
    ],
  };
}

interface SearchByExternalIdArgs {
  external_id_key: string;
  external_id_value: string;
  entity_type?: string;
}

export async function searchByExternalId(args: SearchByExternalIdArgs) {
  const { external_id_key, external_id_value, entity_type } = args;

  // Build the JSONB containment query
  let query = supabase
    .from("entities")
    .select("id, name, type, year, country, language, external_ids, attributes, source_url")
    .contains("external_ids", { [external_id_key]: external_id_value });

  // Add type filter if provided
  if (entity_type) {
    query = query.eq("type", entity_type);
  }

  const { data, error } = await query.limit(10);

  if (error) {
    throw new Error(`Search by external_id failed: ${error.message}`);
  }

  if (!data || data.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: `No entity found with ${external_id_key}="${external_id_value}"`,
        },
      ],
    };
  }

  // Return structured data (for programmatic use)
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          found: data.length,
          results: data.map((item: any) => ({
            id: item.id,
            name: item.name,
            type: item.type,
            year: item.year,
            external_ids: item.external_ids,
          })),
        }, null, 2),
      },
    ],
  };
}
