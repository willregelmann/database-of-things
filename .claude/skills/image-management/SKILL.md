---
name: image-management
description: This skill should be used when the user is working with image storage, thumbnails, Supabase Storage, image localization, or the images table. Examples: "generate thumbnails", "localize external images", "fix missing thumbnails", "image storage structure", "upload image".
analyzed: 2025-12-29
source_files:
  - supabase/migrations/20251114221309_add_images_table_and_reverse_image_search.sql
  - supabase/migrations/20251021064735_create_collectible_images_bucket.sql
  - mcp-server/src/tools/write/localize-image.ts
  - mcp-server/src/tools/write/bulk-localize-images.ts
  - mcp-server/src/tools/write/images.ts
  - scripts/thumbnails/
  - THUMBNAIL_QUICKSTART.md
---

# Image Management

## What This Domain Does

Image management handles storage, thumbnails, and localization for collectibles images. The system uses **Supabase Storage** with a centralized `images` table and pre-generated 300x300 WebP thumbnails for performance.

Key insight: Supabase image transformations require Pro Plan ($25/month + $5/1000 transforms). Pre-generating thumbnails achieves **97.6% size reduction** and **$0 cost**.

## Key Concepts

- **images table**: Centralized storage for all image URLs and CLIP embeddings
- **primary_image_id**: FK on entities/variants/components pointing to main image
- **Additional images**: Join tables for multiple images per entity
- **Localization**: Download external images → generate thumbnail → upload to Supabase Storage
- **Thumbnail**: 300x300 WebP, ~90% size reduction from originals

## How It Works

### Storage Structure

```
images/
├── originals/
│   └── {uuid}.{ext}       # Full resolution (200-500 KB)
└── thumbnails/
    └── {uuid}.webp        # 300x300 WebP (20-50 KB)
```

**URL patterns:**
- Original: `/storage/v1/object/public/images/originals/{uuid}.jpg`
- Thumbnail: `/storage/v1/object/public/images/thumbnails/{uuid}.webp`

### Images Table

```sql
CREATE TABLE images (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  image_url TEXT NOT NULL,           -- Storage path or external URL
  thumbnail_url TEXT,                 -- 300x300 WebP path
  embedding vector(512),              -- CLIP embedding for reverse image search
  source_url TEXT,                    -- Attribution URL
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Primary vs Additional Images

**Primary image**: One main image shown in lists
```sql
-- Entity references primary image via FK
entities.primary_image_id → images.id
variants.primary_image_id → images.id
components.primary_image_id → images.id
```

**Additional images**: Gallery of extra images via join tables
```sql
-- Join tables for additional images
entity_additional_images (entity_id, image_id, order)
variant_additional_images (variant_id, image_id, order)
component_additional_images (component_id, image_id, order)
```

### Localization Workflow (MCP)

The `localize_image` tool handles the complete workflow:

```typescript
const result = await localize_image({
  external_url: "https://images.pokemontcg.io/base1/4.png",
  entity_id: "uuid-of-entity",
  thumbnail_size: 300  // Optional, default 300
});

// Returns:
// {
//   success: true,
//   image_id: "new-image-uuid",
//   image_url: "/storage/v1/object/public/images/originals/uuid.jpg",
//   thumbnail_url: "/storage/v1/object/public/images/thumbnails/uuid.webp"
// }
```

**What it does:**
1. Downloads external image
2. Generates 300x300 WebP thumbnail (using sharp)
3. Generates CLIP embedding (512d)
4. Uploads both to Supabase Storage
5. Creates images table record
6. Links to entity as primary image

### Bulk Localization

For batch operations, use `bulk_localize_images`:

```typescript
await bulk_localize_images({
  images: [
    { entity_id: "uuid1", external_url: "https://..." },
    { entity_id: "uuid2", external_url: "https://..." },
    // ... up to hundreds of images
  ],
  parallel_limit: 10  // Concurrent downloads
});
```

## Important Files

- `supabase/migrations/20251114221309_add_images_table_and_reverse_image_search.sql`: Images table and join tables
- `supabase/migrations/20251021064735_create_collectible_images_bucket.sql`: Storage bucket creation
- `mcp-server/src/tools/write/localize-image.ts`: Single image localization
- `mcp-server/src/tools/write/bulk-localize-images.ts`: Batch localization
- `mcp-server/src/tools/write/images.ts`: create_image tool
- `scripts/thumbnails/`: Thumbnail generation scripts
- `THUMBNAIL_QUICKSTART.md`: Quick reference for thumbnails

## Working With This Domain

### Creating Images Manually

Use `create_image` MCP tool:

```typescript
await create_image({
  entity_id: "uuid",           // Or variant_id, or component_id
  image_url: "https://...",    // External URL or storage path
  thumbnail_url: "https://...", // Optional
  source_url: "https://...",   // Attribution
  is_primary: true             // Set as primary image (default: false)
});
```

### Finding Entities Without Images

```sql
-- Entities missing primary image
SELECT e.id, e.name, e.type
FROM entities e
WHERE e.primary_image_id IS NULL
LIMIT 100;

-- Entities with images but missing thumbnails
SELECT e.id, e.name, i.image_url
FROM entities e
JOIN images i ON e.primary_image_id = i.id
WHERE i.thumbnail_url IS NULL
LIMIT 100;
```

### Backfilling Thumbnails

For existing images without thumbnails:

```bash
cd scripts/thumbnails
npm install
npm run backfill -- --dry-run  # Preview first
npm run backfill               # Process all
```

Or use the shell script:
```bash
./scripts/generate-all-thumbnails
```

### Storage Bucket Configuration

The `images` bucket is configured via migration:

```sql
-- Public read access
CREATE POLICY "Public can read images"
ON storage.objects FOR SELECT
USING (bucket_id = 'images');

-- Authenticated write access
CREATE POLICY "Authenticated can upload images"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'images' AND auth.role() = 'authenticated');
```

**Limits:**
- Max file size: 5MB
- Allowed types: JPEG, PNG, GIF, WebP

### GraphQL Access

Images are accessed via computed fields:

```graphql
query {
  entitiesCollection(filter: {name: {eq: "Charizard"}}) {
    edges {
      node {
        id
        name
        entity_primary_image {
          edges {
            node {
              image_url
              thumbnail_url
            }
          }
        }
        entity_additional_images {
          edges {
            node {
              image_id
              order
            }
          }
        }
      }
    }
  }
}
```

### Common Mistakes to Avoid

- **Don't use Supabase image transformations in production**: They require Pro Plan and cost $5/1000 transforms
- **Don't skip thumbnails**: 97.6% size reduction is significant for performance
- **Don't store image data in entities**: Use the images table and FKs
- **Don't forget CLIP embeddings**: Enable reverse image search
- **Don't upload without authentication**: Write operations require auth

### Image URL Handling

Images can be:
1. **External URLs**: `https://images.pokemontcg.io/base1/4.png`
2. **Storage paths**: `/storage/v1/object/public/images/originals/uuid.jpg`

The `localize_image` tool converts external URLs to storage paths.

### Thumbnail Generation (Manual)

Using sharp in Node.js:

```javascript
import sharp from 'sharp';

const thumbnail = await sharp(imageBuffer)
  .resize(300, 300, { fit: 'inside', withoutEnlargement: true })
  .webp({ quality: 85 })
  .toBuffer();
```

### Cost Savings

| Approach | Cost at 100K images |
|----------|---------------------|
| Supabase transforms | ~$60,000/year |
| Pre-generated thumbnails | $0 |

Pre-generating thumbnails saves significant money at scale.
