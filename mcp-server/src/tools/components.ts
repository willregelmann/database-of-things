import { supabase } from "../index.js";

interface GetComponentsArgs {
  entity_id: string;
}

export async function getComponents(args: GetComponentsArgs) {
  const { entity_id } = args;

  // Get parent entity
  const { data: entity, error: entityError } = await supabase
    .from("entities")
    .select("id, name, type")
    .eq("id", entity_id)
    .single();

  if (entityError) {
    throw new Error(`Entity not found: ${entityError.message}`);
  }

  // Get components
  const { data: components, error } = await supabase
    .from("components")
    .select(`
      id,
      name,
      quantity,
      order,
      attributes,
      component_primary_image:images!primary_image_id (
        image_url,
        thumbnail_url
      )
    `)
    .eq("component_of", entity_id)
    .order("order", { ascending: true, nullsFirst: false });

  if (error) {
    throw new Error(`Failed to get components: ${error.message}`);
  }

  if (!components || components.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: `No components found for "${entity.name}".`,
        },
      ],
    };
  }

  // Format output
  let output = `# Components of ${entity.name}\n\n`;
  output += `Found ${components.length} component(s):\n\n`;

  components.forEach((component: any, idx: number) => {
    output += `## ${idx + 1}. ${component.name}`;
    if (component.quantity > 1) {
      output += ` (×${component.quantity})`;
    }
    output += `\n\n`;
    output += `**ID**: ${component.id}\n`;

    if (component.component_primary_image) {
      output += `**Image**: ${component.component_primary_image.image_url}\n`;
    }

    if (component.attributes && Object.keys(component.attributes).length > 0) {
      output += `\n**Attributes**:\n`;
      for (const [key, value] of Object.entries(component.attributes)) {
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
