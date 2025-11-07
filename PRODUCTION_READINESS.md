# Production Readiness Guide

**Status**: 🟡 In Progress
**Target**: Production launch for multi-user system
**Current Scale**: 20K entities → Target: 100K soon, 1M eventually

---

## Executive Summary

This document outlines the critical path from personal prototype to production-ready multi-user system. Based on your context:

- ✅ **Working foundation**: 20K entities, semantic search active, backend for another project
- ⚠️ **Missing**: Multi-user security, automated operations, testing, validation
- 🎯 **Goal**: Production-ready system that scales from 20K → 1M entities with multiple users

**Timeline**: 2-3 weeks for Phase 1 (pre-launch), ongoing for Phases 2-3

---

## Phase 1: Pre-Launch Critical Items (2-3 Weeks)

These **must** be completed before production launch:

### 1.1 Multi-User Security ✅ **BLOCKING**

**Why Critical**: Without RLS, any user can read/modify/delete any other user's data.

**Status**: 🔴 Not Implemented

**What to Do**:

```bash
# 1. Create the migration
./bin/supabase migration new add_multi_user_security

# 2. Add these changes:
# - Add user_id column to entities
# - Add is_public column for sharing
# - Enable Row Level Security (RLS)
# - Create RLS policies
# - Update indexes for multi-tenant queries
# - Update storage bucket policies

# See detailed implementation in the architecture review
```

**Key Changes**:
- `entities.user_id`: Track ownership
- `entities.is_public`: Enable sharing (future feature)
- RLS policies: Users can only CRUD their own entities
- Storage: Users upload to `/images/{user_id}/originals/`

**Testing**:
```sql
-- Test as user A
SET ROLE authenticated;
SET request.jwt.claims TO '{"sub": "user-a-id"}';
INSERT INTO entities (name, type) VALUES ('My Card', 'card');
SELECT * FROM entities; -- Should only see user A's entities

-- Test as user B
SET request.jwt.claims TO '{"sub": "user-b-id"}';
SELECT * FROM entities; -- Should only see user B's entities (none yet)
```

**Timeline**: 2-3 days

**Risk if Skipped**: 🔴 CRITICAL - Complete data breach

---

### 1.2 Automated Embedding Generation ✅ **BLOCKING**

**Why Critical**: Manual embedding generation breaks at scale. Semantic search is a core feature.

**Status**: 🟡 Designed, Not Deployed

**What to Do**:

```bash
# 1. Apply the embedding queue migration
./scripts/safe-migrate push  # Applies 20251105150334_create_embedding_queue.sql

# 2. Build and start the worker
docker-compose -f docker-compose.embedding.yml up -d --build

# 3. Backfill existing entities
./scripts/manage-embeddings backfill

# 4. Monitor progress
./scripts/manage-embeddings monitor
```

**Architecture**:
- Database trigger queues entities when created/updated
- Python worker polls queue, generates embeddings
- Automatic retries for failures
- Monitoring dashboard for operations

**Cost**: ~$10-15/month at 100K entities (vs $500/month for Edge Functions)

**Testing**:
```bash
# Create test entity without embedding
psql -c "INSERT INTO entities (name, type) VALUES ('Test Entity', 'card')"

# Check it was queued
psql -c "SELECT * FROM embedding_queue WHERE status = 'pending' ORDER BY created_at DESC LIMIT 5"

# Wait for worker to process
sleep 10

# Verify embedding was generated
psql -c "SELECT name, name_embedding IS NOT NULL as has_embedding FROM entities WHERE name = 'Test Entity'"
```

**Timeline**: 1-2 days

**Risk if Skipped**: 🔴 CRITICAL - Semantic search breaks, manual process unsustainable

**Documentation**: See `EMBEDDING_ARCHITECTURE.md` and `EMBEDDING_DEPLOYMENT.md`

---

### 1.3 Data Validation ✅ **BLOCKING**

**Why Critical**: Bad data from users will corrupt database, break features, cause crashes.

**Status**: 🟡 Migration Created, Not Applied

**What to Do**:

```bash
# 1. Apply validation migration
./scripts/safe-migrate push  # Applies 20251105150500_add_data_validation.sql

# 2. Check for existing invalid data
psql -f - <<SQL
SELECT * FROM entity_data_quality_issues LIMIT 20;
SQL

# 3. Clean up any issues found
# (Manual fixes based on specific issues)

# 4. Test validation works
./tests/run-all-tests.sh
```

**Constraints Added**:
- ✅ Names cannot be empty/whitespace
- ✅ Years must be 1800-2100
- ✅ Country codes must be ISO 3166-1 (2 letters)
- ✅ Language codes must be ISO 639-1 (2 letters)
- ✅ Image URLs must be valid paths or URLs
- ✅ Thumbnails require original image
- ✅ Relationships cannot self-reference
- ✅ Order values must be non-negative
- ✅ JSONB fields must be objects
- ✅ Card HP must be positive integer (if provided)

**Testing**:
```bash
# Run constraint tests
./tests/run-all-tests.sh

# All tests should pass
```

**Timeline**: 1 day

**Risk if Skipped**: 🟡 HIGH - Database corruption, crashes, support burden

---

### 1.4 Test Infrastructure ✅ **BLOCKING**

**Why Critical**: Can't iterate on production without tests. Already have broken functions.

**Status**: 🟡 Created, Need to Run

**What to Do**:

```bash
# 1. Run all tests
./tests/run-all-tests.sh

# 2. Fix any failures (likely semantic_search function)

# 3. Add to CI (GitHub Actions)
# Create .github/workflows/test.yml (see below)

# 4. Run tests before every deployment
```

**Test Coverage**:
- ✅ Schema constraints (names, years, codes, etc.)
- ✅ Relationship rules (no self-reference, cascades)
- ✅ Function correctness (semantic_search, search_by_text)
- ✅ Data quality views

**CI Integration** (create `.github/workflows/test.yml`):
```yaml
name: Database Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start Supabase
        run: ./bin/supabase start

      - name: Run Tests
        run: ./tests/run-all-tests.sh

      - name: Stop Supabase
        run: ./bin/supabase stop
```

**Timeline**: 1 day

**Risk if Skipped**: 🟡 HIGH - Deploy broken code, can't refactor safely

---

### 1.5 Backup to Cloud Storage ✅ **RECOMMENDED**

**Why Critical**: Local 33GB backups will fail when disk fills. Need offsite storage.

**Status**: 🔴 Not Implemented

**What to Do**:

```bash
# Option A: AWS S3 (Recommended)
# 1. Install AWS CLI: apt install awscli
# 2. Configure: aws configure
# 3. Update safe-migrate to upload to S3

# Option B: Backblaze B2 (Cheaper)
# 1. Install b2 CLI: pip install b2
# 2. Configure: b2 authorize-account
# 3. Update safe-migrate to upload to B2

# Add to scripts/safe-migrate:
# After creating backup:
aws s3 cp "$BACKUP_FILE" "s3://your-bucket/backups/"
# Or:
b2 upload-file your-bucket "$BACKUP_FILE" "backups/$(basename $BACKUP_FILE)"
```

**Retention Policy**:
- Keep last 7 daily backups locally
- Keep last 30 daily backups in cloud
- Keep monthly backups for 1 year
- Auto-delete older backups

**Cost**:
- AWS S3: ~$0.023/GB/month = ~$0.04/month for 1.7GB
- Backblaze B2: ~$0.005/GB/month = ~$0.01/month

**Timeline**: 1 day

**Risk if Skipped**: 🟡 MEDIUM - Data loss if disk fails, backups fill disk

---

### 1.6 Fix Broken Functions ✅ **BLOCKING**

**Why Critical**: `semantic_search()` still references deleted `image_key` column.

**Status**: 🔴 Broken in Production

**What to Do**:

```bash
# 1. Create migration to fix function
./bin/supabase migration new fix_semantic_search_image_url

# 2. Update function to use image_url instead of image_key
# Copy from supabase/migrations/20251023215655_add_semantic_search_function.sql
# Change line 37: image_key → image_url

# 3. Apply migration
./scripts/safe-migrate push

# 4. Test it works
./tests/run-all-tests.sh
```

**Migration Content**:
```sql
-- Fix semantic_search function to use image_url instead of image_key
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
    image_url text,  -- Changed from image_key
    thumbnail_url text,  -- Add this too
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
        e.image_url,       -- Changed from image_key
        e.thumbnail_url,   -- Add this
        e.attributes,
        1 - (e.name_embedding <=> query_embedding) as similarity
    FROM entities e
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> query_embedding
    LIMIT result_limit;
$$;
```

**Timeline**: 1 hour

**Risk if Skipped**: 🔴 CRITICAL - Semantic search completely broken

---

## Phase 2: Launch Day (1 Day)

### 2.1 Deploy to Supabase Cloud

```bash
# 1. Create project at supabase.com
# Free tier: 500MB database, 1GB storage, 50K monthly active users

# 2. Link local to production
./bin/supabase link --project-ref your-project-ref

# 3. Push database
./bin/supabase db push

# 4. Verify schema
./bin/supabase db remote ls

# 5. Push storage bucket config
# (Should be automatic from migrations)

# 6. Deploy embedding worker
# See EMBEDDING_DEPLOYMENT.md for AWS/DigitalOcean/K8s options
```

### 2.2 Update Frontend

```javascript
// Update Supabase URL in your frontend project
const supabaseUrl = 'https://your-project.supabase.co'  // From Supabase dashboard
const supabaseKey = 'your-anon-key'  // From Settings > API

// Image URLs automatically work (no code changes needed)
// /storage/v1/object/public/images/... resolves to production
```

### 2.3 Migration Checklist

- [ ] Enable RLS on all tables
- [ ] Embedding worker deployed and running
- [ ] Run test suite against production (read-only tests)
- [ ] Create first production backup
- [ ] Monitor embedding queue (`SELECT * FROM embedding_queue_stats`)
- [ ] Check for any data quality issues
- [ ] Verify semantic search works
- [ ] Test with real user account

---

## Phase 3: Post-Launch Monitoring (Ongoing)

### 3.1 Daily Monitoring

```bash
# Check embedding queue health
psql -c "SELECT * FROM embedding_queue_stats"

# Check for failed embeddings
psql -c "SELECT COUNT(*) FROM embedding_queue WHERE status = 'failed' AND retry_count >= 3"

# Check data quality
psql -c "SELECT COUNT(*), issue_type FROM entity_data_quality_issues GROUP BY issue_type"

# Check recent growth
psql -c "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h FROM entities"
```

### 3.2 Weekly Tasks

- Review backup retention (clean old local backups)
- Check disk usage: `du -sh backups/`
- Review embedding coverage: `SELECT COUNT(*) FILTER (WHERE name_embedding IS NULL) FROM entities`
- Test backup restore (monthly)

### 3.3 Monthly Tasks

- Review Supabase costs (database size, storage, API calls)
- Test backup restore procedure
- Review query performance (`EXPLAIN ANALYZE` on slow queries)
- Update documentation

---

## Scale Planning: 100K → 1M Entities

### At 100K Entities (Next Few Months)

**Expected**:
- Database size: ~10-15 GB
- Storage: ~50-100 GB (images)
- Monthly cost: ~$25/month (Supabase Pro tier)

**Actions Needed**:
- ✅ None, current architecture supports this
- Monitor query performance
- Consider read replicas if needed

### At 500K Entities (1 Year)

**Expected**:
- Database size: ~50-75 GB
- Storage: ~250-500 GB
- Monthly cost: ~$100-150/month

**Actions Needed**:
- Add database indexes for slow queries
- Consider table partitioning by type
- Add Redis caching for popular collections
- Tune HNSW index parameters

### At 1M Entities (2+ Years)

**Expected**:
- Database size: ~100-150 GB
- Storage: ~500 GB - 1 TB
- Monthly cost: ~$200-300/month

**Actions Needed**:
- **Table partitioning** by entity type (separate cards, figures, games)
- **Read replicas** for scaling queries
- **CDN** for image delivery (Cloudflare)
- **Separate semantic search** to dedicated index table
- **Background jobs** for heavy operations

**Architecture Changes**:
```sql
-- Partition entities by type
CREATE TABLE entities_cards PARTITION OF entities FOR VALUES IN ('card');
CREATE TABLE entities_figures PARTITION OF entities FOR VALUES IN ('figure');
CREATE TABLE entities_games PARTITION OF entities FOR VALUES IN ('game');

-- Separate semantic search index
CREATE TABLE entity_embeddings (
    entity_id UUID PRIMARY KEY REFERENCES entities(id),
    embedding vector(384),
    updated_at TIMESTAMPTZ
);
-- Rebuild semantic_search() to join this table
```

---

## Cost Estimates

### Development (Current - Free)
- Supabase: Local Docker (free)
- Storage: Local disk (free)
- Embedding Worker: Local Docker (free)

### Production Launch (Supabase Free Tier)
- Database: 500 MB (free up to 500MB)
- Storage: 1 GB (free up to 1GB)
- Users: Unlimited (up to 50K monthly active)
- **Cost: $0/month** until you exceed free tier

### At 20K Entities
- Database: ~2 GB → **$25/month** (Pro tier required)
- Storage: ~10 GB → Included
- Embedding Worker: $5-10/month (DigitalOcean Droplet)
- **Total: ~$30-35/month**

### At 100K Entities
- Database: ~10 GB → **$25/month**
- Storage: ~50 GB → $2.50/month
- Embedding Worker: $10/month
- **Total: ~$37.50/month**

### At 1M Entities
- Database: ~100 GB → **$25/month** + overage
- Storage: ~500 GB → $25/month
- Embedding Worker: $20/month (larger instance)
- CDN: $5/month (Cloudflare Pro)
- **Total: ~$75-100/month**

**Note**: These are estimates. Actual costs depend on usage patterns, API calls, and egress bandwidth.

---

## Deployment Options

### Option A: Supabase Cloud (Recommended for Start)

**Pros**:
- Fully managed (database, storage, auth, realtime)
- Free tier available
- Automatic backups
- Global CDN

**Cons**:
- More expensive at scale (>500K entities)
- Vendor lock-in
- Limited control

**Cost**: $0/month (free) → $25/month (Pro) → $599/month (Team)

### Option B: Self-Hosted Supabase

**Pros**:
- Full control
- Lower costs at scale
- No vendor lock-in

**Cons**:
- More maintenance
- Need to manage backups, scaling, monitoring
- No free tier

**Cost**: ~$50-100/month (AWS EC2/RDS) at 100K entities

### Option C: Hybrid (Recommended for 1M+ Scale)

**Pros**:
- Best of both worlds
- Use managed services where they add value
- Self-host where you need control

**Setup**:
- Database: Self-hosted PostgreSQL (AWS RDS or EC2)
- Storage: AWS S3 or Cloudflare R2
- CDN: Cloudflare
- Auth: Supabase Auth (can be self-hosted)
- GraphQL: Hasura (self-hosted)

**Cost**: ~$100-200/month at 1M entities

---

## Success Metrics

### Pre-Launch
- [ ] All Phase 1 items completed
- [ ] Test suite passing
- [ ] RLS policies tested with multiple users
- [ ] Embedding worker processing >10 entities/second
- [ ] Zero broken functions

### Launch Week
- [ ] No security incidents
- [ ] Embedding queue < 100 pending items
- [ ] Response time <500ms for entity queries
- [ ] Zero data loss incidents
- [ ] Backup retention working

### First Month
- [ ] >90% embedding coverage
- [ ] <1% failed embedding attempts
- [ ] Query performance <1s for complex traversals
- [ ] User growth tracked
- [ ] Costs within budget

### Long Term
- [ ] Linear scaling (2x data = 2x cost, not 10x)
- [ ] Automated operations (no manual intervention)
- [ ] Self-service user management
- [ ] Comprehensive monitoring/alerting

---

## Decision Log

**2025-11-05: Removed Curator System**
- **Decision**: Deleted automated Python-based curators (pokemon-tcg, power-rangers, etc.)
- **Reason**: Overly complex, manual curation provides better data quality
- **Impact**: Simplified codebase, will revisit automation later
- **Alternative**: Use collectibles-manager skill for imports

**2025-11-05: Prioritize Production Security**
- **Decision**: Add RLS, validation, testing before any new features
- **Reason**: Transitioning from personal project to multi-user production
- **Impact**: 2-3 week delay, but prevents security disasters
- **Trade-off**: Delay new features to build solid foundation

---

## Resources

- **Architecture**: `ARCHITECTURE_REVIEW.md` - Critical issues and design concerns
- **Embeddings**: `EMBEDDING_ARCHITECTURE.md` - Semantic search automation
- **Deployment**: `EMBEDDING_DEPLOYMENT.md` - Production deployment guide
- **Operations**: `CLAUDE.md` - Day-to-day development guide
- **Tests**: `tests/` - Test suite for validation

---

## Questions?

If you have questions during implementation:

1. **Security**: Review RLS examples in Supabase docs
2. **Performance**: Use `EXPLAIN ANALYZE` to profile queries
3. **Scaling**: Consult PostgreSQL performance tuning guides
4. **Costs**: Check Supabase pricing calculator

**Remember**: You can start with free tier and scale gradually. Don't over-optimize for 1M entities when you have 20K.
