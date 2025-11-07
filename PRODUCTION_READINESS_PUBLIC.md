# Production Readiness Guide: Public Read-Only Service

**Service Model**: Curator-only writes, public read access, free for consumers
**Scale Target**: 20K → 100K → 1M entities
**Timeline**: No rush - get it right

---

## Executive Summary

This is a **dramatically simpler** architecture than multi-user systems:

- ✅ **You're the only writer** - No user content, no moderation, no per-user isolation
- ✅ **All data is public** - Simple RLS: public read, admin write
- ✅ **Free service** - Cost optimization is critical, stay on free tier as long as possible
- ✅ **Read-heavy** - Focus on caching, CDN, read performance
- ✅ **Low volume** - API rate limiting to prevent abuse

**Key Simplifications**:
- No `user_id` column needed (all data is public)
- No per-user storage folders (single admin folder)
- No content moderation (you control all data)
- Simpler RLS policies (public read + admin write)
- Focus on read performance, not write performance

---

## Phase 1: Core Fixes (Week 1)

### 1.1 Fix Broken Functions ✅ **CRITICAL**

**Issue**: `semantic_search()` references deleted `image_key` column

**Fix**:
```bash
# Create migration
./bin/supabase migration new fix_semantic_search_image_url

# Copy this SQL:
```

```sql
-- Fix semantic_search to use image_url and thumbnail_url
CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(384),
    entity_type_filter text DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    name text,
    type text,
    year integer,
    country char(2),
    language char(2),
    image_url text,
    thumbnail_url text,
    attributes jsonb,
    similarity float
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        e.id,
        e.name,
        e.type,
        e.year,
        e.country,
        e.language,
        e.image_url,
        e.thumbnail_url,
        e.attributes,
        1 - (e.name_embedding <=> query_embedding) as similarity
    FROM entities e
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> query_embedding
    LIMIT result_limit;
$$;

-- Also fix search_by_text if it exists
CREATE OR REPLACE FUNCTION search_by_text(
    query_text text,
    entity_type_filter text DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    name text,
    type text,
    year integer,
    country char(2),
    language char(2),
    image_url text,
    thumbnail_url text,
    attributes jsonb,
    similarity float
)
LANGUAGE sql
STABLE
AS $$
    WITH reference_entity AS (
        SELECT name_embedding
        FROM entities
        WHERE name ILIKE '%' || query_text || '%'
          AND name_embedding IS NOT NULL
          AND (entity_type_filter IS NULL OR type = entity_type_filter)
        LIMIT 1
    )
    SELECT
        e.id,
        e.name,
        e.type,
        e.year,
        e.country,
        e.language,
        e.image_url,
        e.thumbnail_url,
        e.attributes,
        1 - (e.name_embedding <=> (SELECT name_embedding FROM reference_entity)) as similarity
    FROM entities e
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
      AND EXISTS (SELECT 1 FROM reference_entity)
    ORDER BY e.name_embedding <=> (SELECT name_embedding FROM reference_entity)
    LIMIT result_limit;
$$;
```

```bash
# Apply migration
./scripts/safe-migrate push

# Test it works
./tests/run-all-tests.sh
```

**Timeline**: 1 hour
**Risk**: Semantic search is completely broken until this is fixed

---

### 1.2 Automated Embeddings ✅ **CRITICAL**

Since semantic search is a core feature and you're scaling to 100K+:

```bash
# 1. Apply embedding queue migration (already created)
./scripts/safe-migrate push

# 2. Build and start worker
docker-compose -f docker-compose.embedding.yml up -d --build

# 3. Backfill existing entities
./scripts/manage-embeddings backfill

# 4. Monitor progress
./scripts/manage-embeddings monitor
```

**Cost**: ~$10-15/month at 100K entities (vs $500/month for serverless alternatives)

**Why This Matters**:
- You have 20K entities now (manual is barely manageable)
- Scaling to 100K makes manual impossible
- Automatic queue means you never forget to generate embeddings

**Timeline**: 1 day
**Risk**: Manual process breaks at scale, semantic search coverage degrades

---

### 1.3 Data Validation ✅ **IMPORTANT**

Even though you're the only writer, validation prevents:
- Typos in entity types ("card" vs "cards" vs "Card")
- Invalid years (1799, 2101)
- Malformed image URLs
- Invalid country/language codes

```bash
# Apply validation migration (already created)
./scripts/safe-migrate push

# Check for existing issues
psql -f - <<SQL
SELECT * FROM entity_data_quality_issues LIMIT 20;
SQL

# Run tests
./tests/run-all-tests.sh
```

**Timeline**: 1 day
**Risk**: Data quality degrades over time, harder to query consistently

---

### 1.4 Test Suite ✅ **IMPORTANT**

```bash
# Run all tests
./tests/run-all-tests.sh

# Fix any failures

# Add to pre-commit hook (optional)
echo "./tests/run-all-tests.sh" > .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

**Timeline**: 1 day
**Risk**: Can't safely refactor or add features

---

## Phase 2: Simple Public Security (Week 2)

### 2.1 Public Read-Only RLS ✅ **REQUIRED**

Much simpler than multi-user isolation:

```bash
# Apply RLS migration (already created)
./scripts/safe-migrate push  # Applies 20251105151000_add_public_read_only_rls.sql
```

**What This Does**:
- ✅ Anonymous users can read all entities/relationships
- ✅ Only service role key can write
- ✅ Prevents accidental deletes from client apps
- ✅ No `user_id` column needed

**How to Use**:
```javascript
// Frontend (read-only with anon key)
const supabase = createClient(url, ANON_KEY)
const { data } = await supabase.from('entities').select('*')  // ✓ Works

// Admin scripts (write with service role key)
const supabaseAdmin = createClient(url, SERVICE_ROLE_KEY)
await supabaseAdmin.from('entities').insert({...})  // ✓ Works

// Frontend tries to write (blocked)
await supabase.from('entities').insert({...})  // ✗ Fails (no policy)
```

**Testing**:
```bash
# Test public read (should work)
curl "http://127.0.0.1:54321/rest/v1/entities?select=id,name&limit=5" \
  -H "apikey: your-anon-key"

# Test write protection (should fail)
curl -X POST "http://127.0.0.1:54321/rest/v1/entities" \
  -H "apikey: your-anon-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "type": "card"}'
```

**Timeline**: 1 hour
**Risk**: Low (read-only service, but good practice)

---

### 2.2 API Rate Limiting ✅ **IMPORTANT**

Prevent abuse of your free public API:

**Option A: Supabase Built-in (Easiest)**

Supabase automatically rate limits:
- Free tier: 100 req/second
- Pro tier: 1000 req/second

For most use cases, this is sufficient.

**Option B: CloudFlare (Free)**

If you need more control:
1. Point your domain to Supabase via CloudFlare
2. Enable CloudFlare rate limiting (5 req/second free)
3. Cache static responses (entities rarely change)

**Timeline**: 1 hour (CloudFlare setup)
**Risk**: API abuse could exhaust free tier limits

---

## Phase 3: Performance & Cost Optimization (Week 3)

### 3.1 Caching Strategy ✅ **RECOMMENDED**

Since data is public and read-heavy:

**Option A: HTTP Caching (Easiest, Free)**

Add cache headers to your API responses:
```javascript
// In your API middleware
response.headers['Cache-Control'] = 'public, max-age=3600'  // 1 hour
```

**Option B: CloudFlare CDN (Free)**

1. Route API through CloudFlare
2. Enable Page Rules for `/rest/v1/*`
3. Set cache TTL to 1 hour

**Benefits**:
- Reduces database load by 80-90%
- Faster response times globally
- Stays on free tier longer

**Timeline**: 1 day
**Cost**: $0 (CloudFlare free tier)

---

### 3.2 Read Replicas (Future: 500K+ entities)

When you outgrow free tier and need more read performance:

**Supabase Pro** ($25/month) includes:
- Read replicas
- Point-in-time recovery
- Daily backups

**Self-hosted** (if cost is critical at scale):
- Primary PostgreSQL: AWS RDS or DigitalOcean
- Read replica: AWS RDS read replica
- Load balancer: Route reads to replica, writes to primary

**Timeline**: Future (not needed until 500K+ entities)
**Cost**: $25-50/month (Supabase Pro) or $30-60/month (self-hosted)

---

### 3.3 Image CDN ✅ **RECOMMENDED**

Your images are the largest cost factor:

**Current**: All images served from Supabase Storage
- Free tier: 2GB bandwidth/day
- At 100K entities with 100KB thumbnails = 10GB
- If 1000 users browse 100 images = 10GB/day = **exceeds free tier**

**Solution**: CloudFlare CDN (Free)

1. Point custom domain to Supabase
2. Enable CloudFlare CDN
3. Images cached at edge (reduces bandwidth 90%)

**Timeline**: 1 hour
**Cost**: $0 (CloudFlare free tier)

---

## Phase 4: Operational Excellence (Ongoing)

### 4.1 Curator Tools ✅ **NEW**

I created a tool for you to manage data quality:

```bash
# Show statistics
./scripts/curator-tools stats

# Check data quality issues
./scripts/curator-tools quality

# Find duplicates
./scripts/curator-tools duplicates

# Find entities missing images/embeddings
./scripts/curator-tools missing

# Show recently added
./scripts/curator-tools recent

# Find orphaned entities (not in any collection)
./scripts/curator-tools orphans

# Check embedding coverage
./scripts/curator-tools embeddings

# Check image coverage
./scripts/curator-tools images
```

**Use this regularly** to maintain data quality as you scale.

---

### 4.2 Backup to Cloud ✅ **RECOMMENDED**

Your 33GB of local backups need to go to cloud:

```bash
# Install Backblaze B2 CLI (cheapest option)
pip install b2

# Configure
b2 authorize-account YOUR_KEY_ID YOUR_APPLICATION_KEY

# Update safe-migrate script to auto-upload
# Add after creating backup:
b2 upload-file your-bucket "$BACKUP_FILE" "backups/$(basename $BACKUP_FILE)"

# Retention: keep last 30 days
b2 ls your-bucket backups/ | grep -v "$(date +%Y%m)" | xargs -I {} b2 delete-file-version {}
```

**Cost**:
- Backblaze B2: $0.005/GB/month
- 2GB backup × 30 days = ~$0.30/month
- Much cheaper than AWS S3 ($0.023/GB/month)

**Timeline**: 1 hour
**Risk**: Disk failure = data loss

---

### 4.3 Monitoring Dashboard

Simple health check queries:

```sql
-- Run daily to monitor health

-- Database size
SELECT pg_size_pretty(pg_database_size('postgres'));

-- Entity growth
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as added_last_week
FROM entities;

-- Embedding coverage
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE name_embedding IS NOT NULL) as with_embedding,
    ROUND(100.0 * COUNT(*) FILTER (WHERE name_embedding IS NOT NULL) / COUNT(*), 1) as pct
FROM entities;

-- Embedding queue health
SELECT * FROM embedding_queue_stats;

-- Image coverage
SELECT
    COUNT(*) FILTER (WHERE image_url IS NOT NULL) as with_image,
    COUNT(*) FILTER (WHERE thumbnail_url IS NOT NULL) as with_thumbnail
FROM entities;
```

---

## Cost Optimization: Stay on Free Tier Longer

### Free Tier Limits (Supabase)
- **Database**: 500 MB
- **Storage**: 1 GB
- **Bandwidth**: 2 GB/day (60 GB/month)
- **API Requests**: Unlimited

### How to Stay Free Longer

**1. Aggressive Image Compression** (Already doing ✓)
- Thumbnails: 300x300 WebP @ 85% quality
- ~90% size reduction
- Originals: Store externally (Backblaze B2, ImageKit)

**2. CDN for Images** (Free)
- CloudFlare caching reduces bandwidth by 90%
- 60 GB/month → 600 GB effective bandwidth

**3. API Response Caching** (Free)
- HTTP cache headers: `Cache-Control: public, max-age=3600`
- Reduces database queries by 80-90%

**4. Embedding Worker** (Cheap)
- DigitalOcean Droplet: $5/month
- Processes 10-20 embeddings/second
- Much cheaper than Supabase Edge Functions

**5. Lazy Thumbnail Generation**
- Don't generate thumbnails for rarely-accessed entities
- Generate on first access, cache result

### Cost Timeline

| Entities | DB Size | Storage | Bandwidth | Supabase | Worker | CDN | **Total** |
|----------|---------|---------|-----------|----------|--------|-----|-----------|
| 20K | 2 GB | 10 GB | 60 GB/mo | $0 (free)* | $0 (local) | $0 | **$0** |
| 50K | 5 GB | 25 GB | 150 GB/mo | $25 (Pro) | $5 | $0 | **$30/mo** |
| 100K | 10 GB | 50 GB | 300 GB/mo | $25 | $10 | $0 | **$35/mo** |
| 500K | 50 GB | 250 GB | 1.5 TB/mo | $25 | $20 | $0 | **$45/mo** |
| 1M | 100 GB | 500 GB | 3 TB/mo | $25 | $20 | $0 | **$45/mo** |

*Free tier exceeded at 2 GB, but CDN caching extends effective bandwidth 10x

**Key Insight**: With CDN + caching, you can serve 100K+ entities on free tier for months.

---

## Production Deployment Checklist

### Pre-Launch
- [ ] Fix `semantic_search()` function
- [ ] Deploy embedding worker
- [ ] Apply validation constraints
- [ ] Run test suite (all passing)
- [ ] Apply RLS policies (public read, admin write)
- [ ] Set up CloudFlare CDN
- [ ] Configure backup to cloud storage
- [ ] Test with frontend application

### Launch Day
- [ ] Create Supabase Cloud project (free tier)
- [ ] Run `./bin/supabase link` to connect local → cloud
- [ ] Push database schema: `./bin/supabase db push`
- [ ] Deploy embedding worker (DigitalOcean, AWS, etc.)
- [ ] Update frontend to point to production URL
- [ ] Create first production backup
- [ ] Monitor embedding queue
- [ ] Test public API access
- [ ] Test admin write access

### First Week
- [ ] Monitor API usage (Supabase dashboard)
- [ ] Check embedding queue health daily
- [ ] Watch for data quality issues
- [ ] Monitor database size growth
- [ ] Test backup restore procedure

### Ongoing
- [ ] Run `./scripts/curator-tools stats` weekly
- [ ] Review CloudFlare analytics monthly
- [ ] Check for orphaned entities monthly
- [ ] Review costs monthly
- [ ] Update embeddings when entity names change

---

## Architecture Evolution: 20K → 1M

### Today: 20K Entities
**Architecture**: Simple PostgreSQL + Supabase
- ✓ JSONB attributes work fine
- ✓ No partitioning needed
- ✓ Free tier sufficient
- ✓ No CDN needed (yet)

### At 100K: 6-12 Months
**Changes Needed**:
- ✅ Add CloudFlare CDN (free)
- ✅ Upgrade to Supabase Pro ($25/month)
- ✅ Larger embedding worker ($10/month)
- ⚠️ Consider JSONB query optimization

### At 500K: 1-2 Years
**Changes Needed**:
- ✅ Add caching layer (Redis, $10-20/month)
- ✅ Optimize HNSW index parameters
- ✅ Consider read replica
- ⚠️ Consider table partitioning by type

### At 1M: 2+ Years
**Changes Needed**:
- ✅ Table partitioning (cards, figures, games separate)
- ✅ Separate semantic search index table
- ✅ Read replicas for scaling
- ⚠️ Consider hybrid model (typed tables for common entities)

**Key Insight**: You don't need to optimize for 1M now. Build for 100K, monitor performance, optimize when needed.

---

## Recommended Timeline

### Week 1: Core Fixes (4-5 days)
- Day 1: Fix `semantic_search()` function
- Day 2: Deploy embedding worker
- Day 3: Apply validation + tests
- Day 4: Test everything
- Day 5: Buffer/documentation

### Week 2: Infrastructure (3-4 days)
- Day 1: Apply RLS policies
- Day 2: Set up CloudFlare CDN
- Day 3: Configure cloud backups
- Day 4: Deploy to Supabase Cloud

### Week 3: Polish (2-3 days)
- Day 1: API rate limiting
- Day 2: Monitoring dashboard
- Day 3: Documentation + runbook

**Total**: ~3 weeks for production-ready system

**No Rush**: You can spread this over weeks/months as you have time.

---

## Success Metrics

### Data Quality
- [ ] >95% entity coverage for images
- [ ] >95% entity coverage for embeddings
- [ ] <1% data quality issues
- [ ] No duplicate entities

### Performance
- [ ] API response time <500ms
- [ ] Semantic search <1s for 10 results
- [ ] Embedding generation >10/second

### Cost
- [ ] Stay on free tier through 50K entities
- [ ] <$50/month at 100K entities
- [ ] <$100/month at 1M entities

### Reliability
- [ ] Embedding queue <100 pending
- [ ] Zero failed embeddings
- [ ] Daily backups to cloud
- [ ] Tested restore procedure

---

## Next Steps

Based on your "no rush, get it right" approach:

**This Week**:
1. Fix `semantic_search()` function (1 hour) - **Do this first, it's broken**
2. Run tests to verify (30 min)

**Next Week**:
1. Deploy embedding automation (1 day)
2. Apply validation migration (1 hour)
3. Run curator tools to check data quality

**Following Week**:
1. Apply RLS policies
2. Test with frontend
3. Document any issues

**Month 2-3**:
1. Set up CloudFlare CDN
2. Configure cloud backups
3. Deploy to Supabase Cloud when ready

---

## Questions?

The main question is: **What's your timeline for production launch?**

- **1 month**: Do all of Weeks 1-3
- **3 months**: Spread it out, Week 1 now, rest over time
- **6 months**: Leisurely pace, test thoroughly

All paths lead to the same destination: a production-ready, cost-optimized, read-only public API for your collectibles database.

Want me to help implement any specific part? I recommend starting with the `semantic_search()` fix since it's broken and blocks testing.
