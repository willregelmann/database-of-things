import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import sharp from "sharp";
import { supabase } from "../db.js";
import { generateImageEmbedding } from "../utils/embeddings.js";

interface LocalizeArgs {
  external_url: string;
  entity_id: string;
  thumbnail_size?: number;
}

/**
 * Core image localization logic, shared by the MCP tool and bulk upsert.
 */
export async function localizeImageInternal({ external_url, entity_id, thumbnail_size = 300 }: LocalizeArgs): Promise<void> {
  const response = await fetch(external_url);
  if (!response.ok) throw new Error(`Download failed: ${response.statusText}`);
  const imageBuffer = Buffer.from(await response.arrayBuffer());

  // Generate CLIP embedding (best-effort)
  let imageEmbedding: number[] | null = null;
  try {
    imageEmbedding = await generateImageEmbedding(imageBuffer);
  } catch (err: any) {
    console.error(`CLIP embedding failed: ${err.message}`);
  }

  const contentType = response.headers.get("content-type") ?? "image/jpeg";
  const extMap: Record<string, string> = { "image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp" };
  const ext = extMap[contentType] ?? "jpg";

  const originalPath = `originals/${entity_id}.${ext}`;
  const { error: uploadError } = await supabase.storage.from("images").upload(originalPath, imageBuffer, { contentType, upsert: true });
  if (uploadError) throw new Error(`Upload failed: ${uploadError.message}`);

  const thumbnailBuffer = await sharp(imageBuffer)
    .resize(thumbnail_size, thumbnail_size, { fit: "inside", withoutEnlargement: true })
    .webp({ quality: 85 })
    .toBuffer();

  const thumbnailPath = `thumbnails/${entity_id}.webp`;
  await supabase.storage.from("images").upload(thumbnailPath, thumbnailBuffer, { contentType: "image/webp", upsert: true });

  const imageUrl = `/storage/v1/object/public/images/${originalPath}`;
  const thumbnailUrl = `/storage/v1/object/public/images/${thumbnailPath}`;

  const { data: imageRecord, error: imageError } = await supabase
    .from("images")
    .insert({ image_url: imageUrl, thumbnail_url: thumbnailUrl, embedding: imageEmbedding ? JSON.stringify(imageEmbedding) : null, source_url: external_url })
    .select("id")
    .single();

  if (imageError) throw new Error(`Image record failed: ${imageError.message}`);

  await supabase.from("entities").update({ primary_image_id: imageRecord.id }).eq("id", entity_id);
}

export function register(server: McpServer) {
  server.tool(
    "image_localize",
    "Download an external image, generate a thumbnail and CLIP embedding, upload to Supabase Storage, and link to an entity as its primary image.",
    {
      external_url: z.string().url().describe("External image URL to download"),
      entity_id: z.string().uuid().describe("Entity UUID to link the image to"),
      thumbnail_size: z.number().int().min(50).max(1000).default(300).describe("Thumbnail max dimension in pixels"),
    },
    async ({ external_url, entity_id, thumbnail_size }) => {
      try {
        await localizeImageInternal({ external_url, entity_id, thumbnail_size });
        return { content: [{ type: "text", text: JSON.stringify({ success: true }, null, 2) }] };
      } catch (err: any) {
        return { content: [{ type: "text", text: JSON.stringify({ success: false, error: err.message }, null, 2) }] };
      }
    }
  );
}
