import { supabase } from "../index.js";

interface GetEntityArgs {
  id: string;
}

export async function getEntity(args: GetEntityArgs) {
  const { id } = args;

  // Get entity with images
  const { data: entity, error } = await supabase
    .from("entities")
    .select(`
      *,
      entity_primary_image:images!primary_image_id (
        id,
        image_url,
        thumbnail_url
      )
    `)
    .eq("id", id)
    .single();

  if (error) {
    throw new Error(`Entity not found: ${error.message}`);
  }

  // Get variants
  const { data: variants } = await supabase
    .from("variants")
    .select("*")
    .eq("variant_of", id);

  // Get components
  const { data: components } = await supabase
    .from("components")
    .select("*")
    .eq("component_of", id)
    .order("order", { ascending: true, nullsFirst: false });

  // Get parent collections
  const { data: parents } = await supabase
    .from("relationships")
    .select(`
      from_id,
      type,
      entities!relationships_from_id_fkey (
        id,
        name,
        type
      )
    `)
    .eq("to_id", id)
    .eq("type", "contains");

  // Get child items
  const { data: children } = await supabase
    .from("relationships")
    .select(`
      to_id,
      type,
      order,
      entities!relationships_to_id_fkey (
        id,
        name,
        type
      )
    `)
    .eq("from_id", id)
    .eq("type", "contains")
    .order("order", { ascending: true, nullsFirst: false });

  // Format output
  let output = `# ${entity.name}\n\n`;
  output += `**Type**: ${entity.type}\n`;
  if (entity.year) output += `**Year**: ${entity.year}\n`;
  if (entity.country) output += `**Country**: ${entity.country}\n`;
  if (entity.language) output += `**Language**: ${entity.language}\n`;
  output += `**ID**: ${entity.id}\n\n`;

  // Images
  if (entity.entity_primary_image) {
    output += `## Images\n\n`;
    output += `- **Primary Image**: ${entity.entity_primary_image.image_url}\n`;
    if (entity.entity_primary_image.thumbnail_url) {
      output += `- **Thumbnail**: ${entity.entity_primary_image.thumbnail_url}\n`;
    }
    output += `\n`;
  }

  // Attributes
  if (entity.attributes && Object.keys(entity.attributes).length > 0) {
    output += `## Attributes\n\n`;
    for (const [key, value] of Object.entries(entity.attributes)) {
      output += `- **${key}**: ${JSON.stringify(value)}\n`;
    }
    output += `\n`;
  }

  // External IDs
  if (entity.external_ids && Object.keys(entity.external_ids).length > 0) {
    output += `## External IDs\n\n`;
    for (const [key, value] of Object.entries(entity.external_ids)) {
      output += `- **${key}**: ${value}\n`;
    }
    output += `\n`;
  }

  // Parents
  if (parents && parents.length > 0) {
    output += `## Parent Collections\n\n`;
    parents.forEach((p: any) => {
      const parent = p.entities;
      output += `- ${parent.name} (${parent.type}) - ID: ${parent.id}\n`;
    });
    output += `\n`;
  }

  // Children
  if (children && children.length > 0) {
    output += `## Contains (${children.length} items)\n\n`;
    children.forEach((c: any, idx: number) => {
      const child = c.entities;
      output += `${idx + 1}. ${child.name} (${child.type}) - ID: ${child.id}\n`;
    });
    output += `\n`;
  }

  // Variants
  if (variants && variants.length > 0) {
    output += `## Variants (${variants.length})\n\n`;
    variants.forEach((v: any, idx: number) => {
      output += `${idx + 1}. **${v.name}** - ID: ${v.id}\n`;
      if (v.attributes && Object.keys(v.attributes).length > 0) {
        for (const [key, value] of Object.entries(v.attributes)) {
          output += `   - ${key}: ${JSON.stringify(value)}\n`;
        }
      }
    });
    output += `\n`;
  }

  // Components
  if (components && components.length > 0) {
    output += `## Components (${components.length})\n\n`;
    components.forEach((c: any, idx: number) => {
      output += `${idx + 1}. **${c.name}**`;
      if (c.quantity > 1) output += ` (×${c.quantity})`;
      output += ` - ID: ${c.id}\n`;
    });
    output += `\n`;
  }

  // Source
  if (entity.source_url) {
    output += `## Source\n\n${entity.source_url}\n`;
  }

  return {
    content: [
      {
        type: "text",
        text: output,
      },
    ],
  };
}
