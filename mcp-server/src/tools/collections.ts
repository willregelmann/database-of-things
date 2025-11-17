import { supabase } from "../index.js";

interface BrowseCollectionArgs {
  collection_id: string;
  entity_type?: string;
  limit?: number;
}

export async function browseCollection(args: BrowseCollectionArgs) {
  const { collection_id, entity_type, limit = 50 } = args;

  // Get collection info
  const { data: collection, error: collectionError } = await supabase
    .from("entities")
    .select("id, name, type, year")
    .eq("id", collection_id)
    .single();

  if (collectionError) {
    throw new Error(`Collection not found: ${collectionError.message}`);
  }

  // Build query for items in collection
  let query = supabase
    .from("relationships")
    .select(`
      to_id,
      order,
      entities!relationships_to_id_fkey (
        id,
        name,
        type,
        year,
        attributes
      )
    `)
    .eq("from_id", collection_id)
    .eq("type", "contains")
    .order("order", { ascending: true, nullsFirst: false })
    .limit(limit);

  const { data: items, error } = await query;

  if (error) {
    throw new Error(`Failed to browse collection: ${error.message}`);
  }

  if (!items || items.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: `Collection "${collection.name}" is empty.`,
        },
      ],
    };
  }

  // Filter by entity_type if specified
  const filteredItems = entity_type
    ? items.filter((item: any) => item.entities.type === entity_type)
    : items;

  if (filteredItems.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: `No items of type "${entity_type}" found in collection "${collection.name}".`,
        },
      ],
    };
  }

  // Format output
  let output = `# ${collection.name}\n\n`;
  output += `**Type**: ${collection.type}\n`;
  if (collection.year) output += `**Year**: ${collection.year}\n`;
  output += `**Items**: ${filteredItems.length}${entity_type ? ` (type: ${entity_type})` : ""}\n\n`;

  filteredItems.forEach((item: any, idx: number) => {
    const entity = item.entities;
    output += `${idx + 1}. **${entity.name}** (${entity.type})`;
    if (entity.year) output += ` - ${entity.year}`;
    output += `\n   ID: ${entity.id}\n`;
  });

  return {
    content: [
      {
        type: "text",
        text: output,
      },
    ],
  };
}
