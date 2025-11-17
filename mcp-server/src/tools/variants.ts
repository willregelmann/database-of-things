import { supabase } from "../index.js";

interface GetVariantsArgs {
  entity_id: string;
}

export async function getVariants(args: GetVariantsArgs) {
  const { entity_id } = args;

  // Get base entity
  const { data: entity, error: entityError } = await supabase
    .from("entities")
    .select("id, name, type")
    .eq("id", entity_id)
    .single();

  if (entityError) {
    throw new Error(`Entity not found: ${entityError.message}`);
  }

  // Get variants
  const { data: variants, error } = await supabase
    .from("variants")
    .select(`
      id,
      name,
      attributes,
      created_at,
      variant_primary_image:images!primary_image_id (
        image_url,
        thumbnail_url
      )
    `)
    .eq("variant_of", entity_id);

  if (error) {
    throw new Error(`Failed to get variants: ${error.message}`);
  }

  if (!variants || variants.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: `No variants found for "${entity.name}".`,
        },
      ],
    };
  }

  // Format output
  let output = `# Variants of ${entity.name}\n\n`;
  output += `Found ${variants.length} variant(s):\n\n`;

  variants.forEach((variant: any, idx: number) => {
    output += `## ${idx + 1}. ${variant.name}\n\n`;
    output += `**ID**: ${variant.id}\n`;

    if (variant.variant_primary_image) {
      output += `**Image**: ${variant.variant_primary_image.image_url}\n`;
    }

    if (variant.attributes && Object.keys(variant.attributes).length > 0) {
      output += `\n**Attributes**:\n`;
      for (const [key, value] of Object.entries(variant.attributes)) {
        output += `- ${key}: ${JSON.stringify(value)}\n`;
      }
    }

    output += `\n`;
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
