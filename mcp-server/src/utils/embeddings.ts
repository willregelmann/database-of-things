/**
 * Embedding utilities for text and image semantic search.
 *
 * Uses Transformers.js (ONNX runtime) for client-side inference.
 * Models are cached locally after first download.
 */

import { pipeline, env, RawImage } from "@xenova/transformers";

// Configure Transformers.js
// Use local cache, disable remote models
env.allowLocalModels = true;
env.allowRemoteModels = true;

// Singleton instances (lazy-loaded)
let textEmbeddingPipeline: any = null;
let imageEmbeddingPipeline: any = null;

/**
 * Generate text embedding for semantic search.
 *
 * Uses sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
 * Same model as Python implementation for consistency.
 *
 * @param text - Text to embed (e.g., entity name)
 * @returns 384-dimensional embedding vector
 */
export async function generateTextEmbedding(text: string): Promise<number[]> {
  if (!text || text.trim().length === 0) {
    throw new Error("Text cannot be empty");
  }

  // Lazy-load pipeline
  if (!textEmbeddingPipeline) {
    console.error("Loading text embedding model (first run, may take 30s)...");
    textEmbeddingPipeline = await pipeline(
      "feature-extraction",
      "Xenova/all-MiniLM-L6-v2"
    );
    console.error("Text embedding model loaded!");
  }

  // Generate embedding
  const output = await textEmbeddingPipeline(text, {
    pooling: "mean",
    normalize: true,
  });

  // Convert to plain array
  return Array.from(output.data);
}

/**
 * Generate image embedding for reverse image search.
 *
 * Uses CLIP vision transformer (512 dimensions)
 * Same as Python implementation for consistency.
 *
 * @param imageBuffer - Image data as Buffer
 * @returns 512-dimensional embedding vector
 */
export async function generateImageEmbedding(imageBuffer: Buffer): Promise<number[]> {
  if (!imageBuffer || imageBuffer.length === 0) {
    throw new Error("Image buffer cannot be empty");
  }

  // Lazy-load pipeline (use image-feature-extraction for vision models)
  if (!imageEmbeddingPipeline) {
    console.error("Loading image embedding model (CLIP, first run may take 60s)...");
    imageEmbeddingPipeline = await pipeline(
      "image-feature-extraction",
      "Xenova/clip-vit-base-patch32"
    );
    console.error("Image embedding model loaded!");
  }

  // Convert buffer to RawImage (Transformers.js image format)
  // Create a Blob from the buffer, then load it as a RawImage
  const uint8Array = new Uint8Array(imageBuffer);
  const blob = new Blob([uint8Array]);
  const image = await RawImage.fromBlob(blob);

  // Generate embedding (CLIP handles preprocessing internally)
  const output = await imageEmbeddingPipeline(image);

  // Extract embedding from output
  // CLIP returns a tensor, we need to convert to array
  const embedding = output.data || output;
  return Array.from(embedding);
}

/**
 * Batch generate text embeddings.
 * More efficient than calling generateTextEmbedding multiple times.
 *
 * @param texts - Array of texts to embed
 * @returns Array of 384-dimensional embeddings
 */
export async function batchGenerateTextEmbeddings(texts: string[]): Promise<number[][]> {
  if (!texts || texts.length === 0) {
    return [];
  }

  // Filter out empty texts
  const validTexts = texts.filter(t => t && t.trim().length > 0);
  if (validTexts.length === 0) {
    return [];
  }

  // Lazy-load pipeline
  if (!textEmbeddingPipeline) {
    console.error("Loading text embedding model (first run, may take 30s)...");
    textEmbeddingPipeline = await pipeline(
      "feature-extraction",
      "Xenova/all-MiniLM-L6-v2"
    );
    console.error("Text embedding model loaded!");
  }

  // Generate embeddings for all texts
  const embeddings: number[][] = [];
  for (const text of validTexts) {
    const output = await textEmbeddingPipeline(text, {
      pooling: "mean",
      normalize: true,
    });
    embeddings.push(Array.from(output.data));
  }

  return embeddings;
}
