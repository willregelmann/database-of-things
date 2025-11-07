#!/usr/bin/env node

/**
 * Backfill Thumbnails Script
 *
 * Generates thumbnails for all existing images in the entities table.
 *
 * Usage:
 *   Option A - Supabase CLI (recommended):
 *     1. Link your project: supabase link (if not already linked)
 *     2. Run: npm run backfill
 *     Credentials auto-detected from CLI!
 *
 *   Option B - Manual .env:
 *     1. Create .env file with SUPABASE_URL and SUPABASE_SERVICE_KEY
 *     2. Run: npm run backfill
 *
 * Options:
 *   --dry-run      - Preview what would be processed without making changes
 *   --limit=N      - Process only first N entities (for testing)
 *   --batch=N      - Process N entities at a time (default: 10)
 *   --size=300     - Thumbnail size in pixels (default: 300x300)
 *   --quality=85   - WebP quality 1-100 (default: 85)
 *   --resume       - Skip entities that already have thumbnails
 *   --parallel=N   - Number of concurrent downloads/uploads (default: 3)
 */

import { createClient } from '@supabase/supabase-js';
import sharp from 'sharp';
import cliProgress from 'cli-progress';
import { getCredentials } from './get-credentials.js';

// Parse CLI arguments
const args = process.argv.slice(2).reduce((acc, arg) => {
  if (arg.startsWith('--')) {
    const [key, value] = arg.slice(2).split('=');
    acc[key] = value || true;
  }
  return acc;
}, {});

const DRY_RUN = args['dry-run'] === true;
const LIMIT = args.limit ? parseInt(args.limit) : null;
const BATCH_SIZE = args.batch ? parseInt(args.batch) : 10;
const THUMBNAIL_SIZE = args.size ? parseInt(args.size) : 300;
const QUALITY = args.quality ? parseInt(args.quality) : 85;
const RESUME = args.resume === true;
const PARALLEL = args.parallel ? parseInt(args.parallel) : 3;

// Auto-detect credentials from Supabase CLI or .env
const credentials = getCredentials();

if (!credentials) {
  console.error('❌ Could not find Supabase credentials\n');
  console.error('Tried:');
  console.error('  1. Supabase CLI (no linked project found)');
  console.error('  2. .env file (not found or incomplete)\n');
  console.error('Solutions:');
  console.error('  A. Link to Supabase project:');
  console.error('     supabase link\n');
  console.error('  B. Create .env file:');
  console.error('     cp .env.example .env');
  console.error('     # Edit .env with your SUPABASE_URL and SUPABASE_SERVICE_KEY\n');
  process.exit(1);
}

const { SUPABASE_URL, SUPABASE_SERVICE_KEY } = credentials;

// Initialize Supabase client with service role key (bypasses RLS)
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

/**
 * Download image from Supabase Storage or external URL
 */
async function downloadImage(imageUrl) {
  // Check if it's a Supabase storage path
  if (imageUrl.startsWith('/storage/v1/object/public/')) {
    const path = imageUrl.replace('/storage/v1/object/public/', '');
    const bucketName = path.split('/')[0];
    const filePath = path.split('/').slice(1).join('/');

    const { data, error } = await supabase.storage
      .from(bucketName)
      .download(filePath);

    if (error) throw error;
    return Buffer.from(await data.arrayBuffer());
  }

  // External URL - download via fetch
  const fullUrl = imageUrl.startsWith('http')
    ? imageUrl
    : `${SUPABASE_URL}${imageUrl}`;

  const response = await fetch(fullUrl);
  if (!response.ok) {
    throw new Error(`Failed to download: ${response.statusText}`);
  }
  return Buffer.from(await response.arrayBuffer());
}

/**
 * Generate thumbnail using Sharp
 */
async function generateThumbnail(imageBuffer, size = THUMBNAIL_SIZE, quality = QUALITY) {
  return sharp(imageBuffer)
    .resize(size, size, {
      fit: 'inside',
      withoutEnlargement: true
    })
    .webp({ quality })
    .toBuffer();
}

/**
 * Upload thumbnail to Supabase Storage
 */
async function uploadThumbnail(entityId, thumbnailBuffer) {
  const filename = `${entityId}.webp`;
  const path = `thumbnails/${filename}`;

  const { data, error } = await supabase.storage
    .from('images')
    .upload(path, thumbnailBuffer, {
      contentType: 'image/webp',
      upsert: true // Overwrite if exists
    });

  if (error) throw error;
  return `/storage/v1/object/public/images/${path}`;
}

/**
 * Update entity with thumbnail_url
 */
async function updateEntityThumbnail(entityId, thumbnailUrl) {
  const { error } = await supabase
    .from('entities')
    .update({ thumbnail_url: thumbnailUrl })
    .eq('id', entityId);

  if (error) throw error;
}

/**
 * Process a single entity
 */
async function processEntity(entity, progressBar = null) {
  const { id, name, image_url } = entity;

  try {
    // Download original image
    const imageBuffer = await downloadImage(image_url);

    // Generate thumbnail
    const thumbnailBuffer = await generateThumbnail(imageBuffer);

    const originalSize = imageBuffer.length;
    const thumbnailSize = thumbnailBuffer.length;
    const savings = ((1 - thumbnailSize / originalSize) * 100).toFixed(1);

    if (DRY_RUN) {
      if (progressBar) {
        progressBar.increment(1, {
          entity: name.substring(0, 30).padEnd(30),
          status: `[DRY RUN] ${savings}% saved`
        });
      }
      return { success: true, dryRun: true, originalSize, thumbnailSize };
    }

    // Upload thumbnail
    const thumbnailUrl = await uploadThumbnail(id, thumbnailBuffer);

    // Update entity
    await updateEntityThumbnail(id, thumbnailUrl);

    if (progressBar) {
      progressBar.increment(1, {
        entity: name.substring(0, 30).padEnd(30),
        status: `✓ ${savings}% saved`
      });
    }

    return { success: true, originalSize, thumbnailSize };
  } catch (error) {
    if (progressBar) {
      progressBar.increment(1, {
        entity: name.substring(0, 30).padEnd(30),
        status: `✗ ${error.message.substring(0, 20)}`
      });
    }
    return { success: false, error: error.message };
  }
}

/**
 * Process entities in parallel batches
 */
async function processBatch(entities, progressBar) {
  const chunks = [];
  for (let i = 0; i < entities.length; i += PARALLEL) {
    chunks.push(entities.slice(i, i + PARALLEL));
  }

  const results = {
    success: 0,
    failed: 0,
    totalOriginal: 0,
    totalThumbnail: 0,
    errors: []
  };

  for (const chunk of chunks) {
    const promises = chunk.map(entity => processEntity(entity, progressBar));
    const chunkResults = await Promise.all(promises);

    chunkResults.forEach((result, idx) => {
      if (result.success) {
        results.success++;
        if (result.originalSize) {
          results.totalOriginal += result.originalSize;
          results.totalThumbnail += result.thumbnailSize;
        }
      } else {
        results.failed++;
        results.errors.push({
          id: chunk[idx].id,
          name: chunk[idx].name,
          error: result.error
        });
      }
    });
  }

  return results;
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 Starting thumbnail backfill process\n');
  console.log(`Configuration:`);
  console.log(`  Credentials: ${credentials.source === 'cli' ? '✅ Auto-detected from Supabase CLI' : '📄 Loaded from .env file'}`);
  console.log(`  Project: ${SUPABASE_URL}`);
  console.log(`  Thumbnail size: ${THUMBNAIL_SIZE}x${THUMBNAIL_SIZE}`);
  console.log(`  WebP quality: ${QUALITY}`);
  console.log(`  Batch size: ${BATCH_SIZE} entities`);
  console.log(`  Parallel operations: ${PARALLEL}`);
  console.log(`  Dry run: ${DRY_RUN ? 'YES' : 'NO'}`);
  console.log(`  Resume mode: ${RESUME ? 'YES (skip existing)' : 'NO'}`);
  console.log(`  Limit: ${LIMIT || 'All entities'}\n`);

  // Count total entities first
  console.log('🔍 Counting entities...');
  let countQuery = supabase
    .from('entities')
    .select('id', { count: 'exact', head: true })
    .not('image_url', 'is', null);

  if (!RESUME) {
    countQuery = countQuery.is('thumbnail_url', null);
  }

  const { count: totalCount, error: countError } = await countQuery;

  if (countError) {
    console.error('❌ Failed to count entities:', countError.message);
    process.exit(1);
  }

  const effectiveLimit = LIMIT ? Math.min(LIMIT, totalCount) : totalCount;
  console.log(`📊 Found ${effectiveLimit.toLocaleString()} entities to process\n`);

  if (effectiveLimit === 0) {
    console.log('✨ All entities already have thumbnails!');
    return;
  }

  // Estimate time
  const estimatedSeconds = Math.ceil((effectiveLimit / PARALLEL) * 2); // ~2s per image
  const estimatedMinutes = Math.ceil(estimatedSeconds / 60);
  console.log(`⏱️  Estimated time: ~${estimatedMinutes} minutes\n`);

  // Create progress bar
  const progressBar = new cliProgress.SingleBar({
    format: '⏳ Progress |{bar}| {percentage}% | {value}/{total} | {entity} | {status}',
    barCompleteChar: '\u2588',
    barIncompleteChar: '\u2591',
    hideCursor: true
  });

  progressBar.start(effectiveLimit, 0, {
    entity: 'Starting...'.padEnd(30),
    status: ''
  });

  // Process in batches
  const results = {
    total: effectiveLimit,
    success: 0,
    failed: 0,
    totalOriginal: 0,
    totalThumbnail: 0,
    errors: []
  };

  // Fetch and process in pages using cursor-based pagination (avoids Supabase offset limit)
  const PAGE_SIZE = 1000;
  let processed = 0;
  let lastCreatedAt = null;
  let lastId = null;

  while (processed < effectiveLimit) {
    // Fetch next page
    const pageSize = Math.min(PAGE_SIZE, effectiveLimit - processed);

    let query = supabase
      .from('entities')
      .select('id, name, image_url, created_at')
      .not('image_url', 'is', null)
      .order('created_at', { ascending: true })
      .order('id', { ascending: true })
      .limit(pageSize);

    // Cursor-based pagination: fetch records after the last processed entity
    if (lastCreatedAt) {
      query = query.or(`created_at.gt.${lastCreatedAt},and(created_at.eq.${lastCreatedAt},id.gt.${lastId})`);
    }

    if (!RESUME) {
      query = query.is('thumbnail_url', null);
    }

    const { data: entities, error } = await query;

    if (error) {
      console.error(`\n❌ Failed to fetch entities (page ${Math.floor(processed / PAGE_SIZE) + 1}):`, error.message);
      break;
    }

    if (!entities || entities.length === 0) {
      break;
    }

    // Process this page in batches
    for (let i = 0; i < entities.length; i += BATCH_SIZE) {
      const batch = entities.slice(i, i + BATCH_SIZE);
      const batchResults = await processBatch(batch, progressBar);

      results.success += batchResults.success;
      results.failed += batchResults.failed;
      results.totalOriginal += batchResults.totalOriginal;
      results.totalThumbnail += batchResults.totalThumbnail;
      results.errors.push(...batchResults.errors);
    }

    processed += entities.length;

    // Update cursor for next page (track last entity)
    if (entities.length > 0) {
      const lastEntity = entities[entities.length - 1];
      lastCreatedAt = lastEntity.created_at;
      lastId = lastEntity.id;
    }
  }

  progressBar.stop();

  // Summary
  const totalSavings = results.totalOriginal > 0
    ? ((1 - results.totalThumbnail / results.totalOriginal) * 100).toFixed(1)
    : 0;

  console.log('\n' + '═'.repeat(80));
  console.log('📈 Summary:');
  console.log(`  Total: ${results.total}`);
  console.log(`  ✅ Success: ${results.success}`);
  console.log(`  ❌ Failed: ${results.failed}`);

  if (results.totalOriginal > 0) {
    console.log(`\n💾 Storage:`);
    console.log(`  Original total: ${(results.totalOriginal / 1024 / 1024).toFixed(1)} MB`);
    console.log(`  Thumbnail total: ${(results.totalThumbnail / 1024 / 1024).toFixed(1)} MB`);
    console.log(`  Total savings: ${totalSavings}% (${((results.totalOriginal - results.totalThumbnail) / 1024 / 1024).toFixed(1)} MB saved)`);
  }

  if (results.errors.length > 0) {
    console.log(`\n❌ Failed entities (showing first 10):`);
    results.errors.slice(0, 10).forEach(({ name, error }) => {
      console.log(`  - ${name}: ${error}`);
    });
    if (results.errors.length > 10) {
      console.log(`  ... and ${results.errors.length - 10} more`);
    }
  }

  if (DRY_RUN) {
    console.log('\n⚠️  This was a DRY RUN - no changes were made');
    console.log('   Remove --dry-run flag to process for real');
  }

  console.log('═'.repeat(80));
}

// Run the script
main().catch(console.error);
