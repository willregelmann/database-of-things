#!/usr/bin/env node

/**
 * Generate Thumbnails for New Uploads
 *
 * Helper module for generating thumbnails when uploading new images.
 * Can be imported and used in your application code.
 *
 * Usage as CLI:
 *   node generate-thumbnails.js <image-path> [--output=path] [--size=300]
 *
 * Usage as module:
 *   import { generateThumbnailFromFile, generateThumbnailFromBuffer } from './generate-thumbnails.js';
 */

import sharp from 'sharp';
import { readFile, writeFile } from 'fs/promises';

/**
 * Generate thumbnail from image buffer
 * @param {Buffer} imageBuffer - Original image buffer
 * @param {Object} options - Thumbnail options
 * @param {number} options.size - Thumbnail size (default: 300)
 * @param {number} options.quality - WebP quality (default: 85)
 * @returns {Promise<Buffer>} Thumbnail buffer
 */
export async function generateThumbnailFromBuffer(imageBuffer, options = {}) {
  const { size = 300, quality = 85 } = options;

  return sharp(imageBuffer)
    .resize(size, size, {
      fit: 'inside',
      withoutEnlargement: true
    })
    .webp({ quality })
    .toBuffer();
}

/**
 * Generate thumbnail from file path
 * @param {string} inputPath - Path to original image
 * @param {Object} options - Thumbnail options
 * @returns {Promise<Buffer>} Thumbnail buffer
 */
export async function generateThumbnailFromFile(inputPath, options = {}) {
  const imageBuffer = await readFile(inputPath);
  return generateThumbnailFromBuffer(imageBuffer, options);
}

/**
 * Get image metadata
 * @param {Buffer} imageBuffer - Image buffer
 * @returns {Promise<Object>} Image metadata
 */
export async function getImageMetadata(imageBuffer) {
  const metadata = await sharp(imageBuffer).metadata();
  return {
    width: metadata.width,
    height: metadata.height,
    format: metadata.format,
    size: imageBuffer.length
  };
}

// CLI usage
if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0].startsWith('--help')) {
    console.log(`
Usage: node generate-thumbnails.js <image-path> [options]

Options:
  --output=<path>  Output path for thumbnail (default: <input>-thumb.webp)
  --size=<pixels>  Thumbnail size (default: 300)
  --quality=<1-100> WebP quality (default: 85)

Example:
  node generate-thumbnails.js photo.jpg --output=thumb.webp --size=300
    `);
    process.exit(0);
  }

  const inputPath = args[0];
  const options = args.slice(1).reduce((acc, arg) => {
    if (arg.startsWith('--')) {
      const [key, value] = arg.slice(2).split('=');
      acc[key] = value;
    }
    return acc;
  }, {});

  const outputPath = options.output || inputPath.replace(/\.[^.]+$/, '-thumb.webp');
  const size = options.size ? parseInt(options.size) : 300;
  const quality = options.quality ? parseInt(options.quality) : 85;

  try {
    console.log(`📥 Reading: ${inputPath}`);
    const imageBuffer = await readFile(inputPath);

    const metadata = await getImageMetadata(imageBuffer);
    console.log(`📊 Original: ${metadata.width}x${metadata.height} ${metadata.format.toUpperCase()} (${(metadata.size / 1024).toFixed(1)} KB)`);

    console.log(`🖼️  Generating ${size}x${size} WebP thumbnail...`);
    const thumbnailBuffer = await generateThumbnailFromBuffer(imageBuffer, { size, quality });

    console.log(`💾 Saving: ${outputPath}`);
    await writeFile(outputPath, thumbnailBuffer);

    const savings = ((1 - thumbnailBuffer.length / imageBuffer.length) * 100).toFixed(1);
    console.log(`✅ Done! ${(thumbnailBuffer.length / 1024).toFixed(1)} KB (${savings}% smaller)`);
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    process.exit(1);
  }
}
