import { supabase } from "../../index.js";
import sharp from "sharp";
import { generateImageEmbedding } from "../../utils/embeddings.js";

interface LocalizeImageArgs {
  external_url: string;
  entity_id: string;
  thumbnail_size?: number;
}

export async function localizeImage(args: LocalizeImageArgs) {
  const { external_url, entity_id, thumbnail_size = 300 } = args;

  if (!external_url) {
    throw new Error("external_url is required");
  }

  if (!entity_id) {
    throw new Error("entity_id is required");
  }

  try {
    // Download image from external URL
    console.error(`Downloading image from ${external_url}...`);
    const response = await fetch(external_url);
    if (!response.ok) {
      throw new Error(`Failed to download image: ${response.statusText}`);
    }

    const imageBuffer = Buffer.from(await response.arrayBuffer());

    // Generate image embedding for reverse image search
    let imageEmbedding: number[] | null = null;
    let embeddingError: string | null = null;
    try {
      console.error(`Generating image embedding (CLIP)...`);
      imageEmbedding = await generateImageEmbedding(imageBuffer);
      console.error(`✓ Image embedding generated (512 dimensions)`);
    } catch (err: any) {
      embeddingError = err.message || String(err);
      console.error(`⚠️  Failed to generate image embedding: ${embeddingError}`);
      console.error(`⚠️  Stack trace: ${err.stack}`);
      // Continue without embedding - still upload image
    }

    // Determine file extension
    const contentType = response.headers.get("content-type") || "image/jpeg";
    const extMap: Record<string, string> = {
      "image/jpeg": "jpg",
      "image/png": "png",
      "image/gif": "gif",
      "image/webp": "webp",
    };
    const ext = extMap[contentType] || "jpg";

    // Upload original to storage
    const originalPath = `originals/${entity_id}.${ext}`;
    console.error(`Uploading original to ${originalPath}...`);

    const { error: uploadError } = await supabase.storage
      .from("images")
      .upload(originalPath, imageBuffer, {
        contentType,
        upsert: true, // Allow overwriting if exists
      });

    if (uploadError) {
      throw new Error(`Failed to upload original: ${uploadError.message}`);
    }

    // Generate thumbnail
    console.error(`Generating ${thumbnail_size}x${thumbnail_size} thumbnail...`);
    const thumbnailBuffer = await sharp(imageBuffer)
      .resize(thumbnail_size, thumbnail_size, {
        fit: "inside",
        withoutEnlargement: true,
      })
      .webp({ quality: 85 })
      .toBuffer();

    // Upload thumbnail
    const thumbnailPath = `thumbnails/${entity_id}.webp`;
    console.error(`Uploading thumbnail to ${thumbnailPath}...`);

    const { error: thumbError } = await supabase.storage
      .from("images")
      .upload(thumbnailPath, thumbnailBuffer, {
        contentType: "image/webp",
        upsert: true,
      });

    if (thumbError) {
      // If thumbnail fails, still return original
      console.error(`Warning: Failed to upload thumbnail: ${thumbError.message}`);
      const imageUrl = `/storage/v1/object/public/images/${originalPath}`;
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                success: true,
                image_url: imageUrl,
                thumbnail_url: null,
                image_embedding: imageEmbedding,
                warning: "Thumbnail generation failed",
              },
              null,
              2
            ),
          },
        ],
      };
    }

    // Success - return both URLs
    const imageUrl = `/storage/v1/object/public/images/${originalPath}`;
    const thumbnailUrl = `/storage/v1/object/public/images/${thumbnailPath}`;

    // Create image record in database with embedding
    console.error(`Creating image record in database...`);
    const { data: imageRecord, error: imageError } = await supabase
      .from("images")
      .insert({
        image_url: imageUrl,
        thumbnail_url: thumbnailUrl,
        embedding: imageEmbedding ? JSON.stringify(imageEmbedding) : null,
        source_url: external_url,
      })
      .select("id")
      .single();

    if (imageError) {
      console.error(`Warning: Failed to create image record: ${imageError.message}`);
      // Still return success since files were uploaded
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                success: true,
                image_url: imageUrl,
                thumbnail_url: thumbnailUrl,
                image_embedding: imageEmbedding,
                warning: "Image record creation failed - files uploaded but not linked to entity",
              },
              null,
              2
            ),
          },
        ],
      };
    }

    // Link image to entity via primary_image_id
    console.error(`Linking image to entity ${entity_id}...`);
    const { error: updateError } = await supabase
      .from("entities")
      .update({ primary_image_id: imageRecord.id })
      .eq("id", entity_id);

    if (updateError) {
      console.error(`Warning: Failed to link image to entity: ${updateError.message}`);
    }

    const result: any = {
      success: true,
      image_url: imageUrl,
      thumbnail_url: thumbnailUrl,
      image_embedding: imageEmbedding,
      image_id: imageRecord.id,
    };

    // Include embedding error if it failed
    if (embeddingError) {
      result.embedding_error = embeddingError;
      result.warning = "Image uploaded successfully but CLIP embedding generation failed";
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    throw new Error(`Image localization failed: ${errorMessage}`);
  }
}
