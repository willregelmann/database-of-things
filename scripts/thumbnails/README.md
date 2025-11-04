# Thumbnail Generator

Generates optimized WebP thumbnails for collectible images in Supabase Storage.

## Why?

Supabase image transformations require **Pro Plan** ($25/month). This script generates thumbnails locally, allowing free-tier users to serve optimized images.

## Features

- ✅ **Backfill existing images** - Process all entities that don't have thumbnails
- ✅ **WebP format** - 25-35% smaller than JPEG/PNG
- ✅ **Configurable size & quality** - Default: 300x300 @ 85% quality
- ✅ **Dry-run mode** - Test before making changes
- ✅ **Progress tracking** - Shows download size, thumbnail size, and savings
- ✅ **Error handling** - Continues processing even if some images fail

## Setup

**Option A: Supabase CLI (Recommended)**

If you have Supabase CLI linked to your project:

```bash
# That's it! Credentials auto-detected from CLI
npm install  # Just install dependencies
```

The script automatically detects your Supabase project URL and service_role key from the CLI.

**Option B: Manual .env File**

If you don't have Supabase CLI or prefer manual configuration:

1. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Configure Supabase credentials** in `.env`:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key
   ```

   **⚠️ IMPORTANT**: Use the `service_role` key (not `anon` key). Find it in:
   ```
   Supabase Dashboard → Settings → API → service_role key (secret)
   ```

3. **Install dependencies**:
   ```bash
   npm install
   ```

## Usage

### Easy Mode: Wrapper Script

The easiest way to generate thumbnails:

```bash
# From project root
./scripts/generate-all-thumbnails
```

This launches an interactive menu with guided options:
- 🧪 Test with 5 images (dry-run)
- 🚀 Process first 100 images
- 🔥 Process ALL images (full backfill)
- 🔄 Resume (skip existing thumbnails)
- ⚙️  Custom options

### Manual Mode: Direct Script

For more control, run the backfill script directly:

```bash
cd scripts/thumbnails

# Dry run first (see what would happen)
npm run backfill -- --dry-run --limit=5

# Process first 100 entities (for testing)
npm run backfill -- --limit=100

# Process all entities
npm run backfill
```

**Options**:
- `--dry-run` - Preview without making changes
- `--limit=N` - Process only first N entities
- `--batch=N` - Process N entities per batch (default: 10)
- `--parallel=N` - Concurrent operations (default: 3, max recommended: 5)
- `--size=300` - Thumbnail size in pixels (default: 300x300)
- `--quality=85` - WebP quality 1-100 (default: 85)
- `--resume` - Skip entities that already have thumbnails

**Example output**:
```
🚀 Starting thumbnail backfill process

Configuration:
  Thumbnail size: 300x300
  WebP quality: 85
  Batch size: 10 entities
  Parallel operations: 3
  Dry run: NO
  Resume mode: NO
  Limit: All entities

📊 Found 15,432 entities to process

⏱️  Estimated time: ~172 minutes

⏳ Progress |████████████████████░░░░░░░░░░| 68% | 10,493/15,432 | Charizard Base Set           | ✓ 94.3% saved

════════════════════════════════════════════════════════════════════════════════
📈 Summary:
  Total: 15,432
  ✅ Success: 15,429
  ❌ Failed: 3

💾 Storage:
  Original total: 5,847.2 MB
  Thumbnail total: 312.5 MB
  Total savings: 94.7% (5,534.7 MB saved)

❌ Failed entities (showing first 10):
  - Corrupted Image: Failed to download: Not Found
  - Missing File: Failed to download: 404
  - Invalid Format: Input buffer contains unsupported image format
════════════════════════════════════════════════════════════════════════════════
```

### Generate Single Thumbnail (CLI)

```bash
# Generate thumbnail from local file
node generate-thumbnails.js photo.jpg --output=thumb.webp --size=300

# Custom size and quality
node generate-thumbnails.js photo.jpg --size=600 --quality=90
```

### Use in Your Application Code

```javascript
import { generateThumbnailFromBuffer } from './scripts/thumbnails/generate-thumbnails.js';
import { createClient } from '@supabase/supabase-js';

// When uploading a new collectible image
async function uploadCollectibleWithThumbnail(file, entityData) {
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
  const entityId = crypto.randomUUID();

  // Upload original image
  const originalPath = `originals/${entityId}.${file.extension}`;
  await supabase.storage.from('images').upload(originalPath, file.buffer);

  // Generate and upload thumbnail
  const thumbnailBuffer = await generateThumbnailFromBuffer(file.buffer, {
    size: 300,
    quality: 85
  });
  const thumbnailPath = `thumbnails/${entityId}.webp`;
  await supabase.storage.from('images').upload(thumbnailPath, thumbnailBuffer);

  // Create entity with both URLs
  await supabase.from('entities').insert({
    id: entityId,
    name: entityData.name,
    type: entityData.type,
    image_url: `/storage/v1/object/public/images/${originalPath}`,
    thumbnail_url: `/storage/v1/object/public/images/${thumbnailPath}`
  });
}
```

## How It Works

1. **Queries database** for entities with `image_url` but no `thumbnail_url`
2. **Downloads original** from Supabase Storage or external URL
3. **Generates thumbnail** using Sharp:
   - Resizes to 300x300 (cover fit, centered)
   - Converts to WebP format
   - Compresses to 85% quality
4. **Uploads thumbnail** to `images/thumbnails/{entity_id}.webp`
5. **Updates entity** with `thumbnail_url` column

## GraphQL Usage

After running the backfill, thumbnails are automatically available via GraphQL:

```graphql
query {
  entitiesCollection(filter: {type: {eq: "card"}}) {
    edges {
      node {
        id
        name
        image_url       # Original image
        thumbnail_url   # 300x300 WebP thumbnail
      }
    }
  }
}
```

## Storage Structure

```
images/
  originals/
    {uuid}.jpg           # Full resolution original
    {uuid}.png
  thumbnails/
    {uuid}.webp          # 300x300 WebP thumbnail
```

## Troubleshooting

**"Missing required environment variables"**
- Ensure `.env` file exists with valid `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`

**"Failed to download: 404"**
- Original image no longer exists in storage
- URL in `image_url` column is incorrect
- Run with `--dry-run` to see which entities would fail

**"Permission denied"**
- Ensure you're using the `service_role` key (not `anon` key)
- Service role bypasses Row Level Security (RLS)

**Sharp installation issues**
- Try: `npm rebuild sharp`
- On M1/M2 Macs: Ensure you're using Node 18+

## Performance

With default settings (`--parallel=3`, `--batch=10`):

- **Processing time**: ~2 seconds per image (parallelized)
- **Thumbnail size**: Typically 20-50 KB (vs 200-500 KB originals)
- **Space savings**: ~90-95% reduction
- **Throughput**: ~1.5 images/second (~90 images/minute)

**For 100,000 images:**
- Estimated runtime: ~18-37 hours (vs 55-83 hours without parallelization)
- Estimated thumbnail storage: 2-5 GB (vs 20-50 GB originals)
- **Speed tips**:
  - Increase `--parallel=5` for faster processing (max recommended: 5)
  - Run on a server with good network connection
  - Use `--resume` to continue after interruptions

## Cost Comparison

### Image Transformations (Pro Plan)

At 100,000 images with 10 views each:
- **Monthly cost**: $5,000+ (1M transforms @ $5 per 1,000)
- **Storage**: ~20 GB originals only

### Pre-Generated Thumbnails (Free Tier)

- **Monthly cost**: $0 (one-time processing)
- **Storage**: ~25 GB (originals + thumbnails)
- **Processing time**: One-time ~55-83 hours

**For high-volume use cases, pre-generating thumbnails saves thousands per month.**
