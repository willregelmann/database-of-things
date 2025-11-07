# Architecture Review: Database of Things

**Date**: 2025-11-04
**Reviewer**: Claude Code
**Scope**: Complete project architecture, schema design, operations, and scalability

---

## Executive Summary

This project implements a flexible graph-based collectibles database using PostgreSQL/Supabase. While the core concept is sound, the implementation has accumulated significant **technical debt** through:

- ❌ **21 migrations with orphaned code** and broken references
- ❌ **33GB of backup files** consuming disk space
- ❌ **Migration drift** between local and production
- ⚠️ **3 separate search systems** (trigram, full-text, semantic) with unclear usage patterns
- ⚠️ **Manual operational workflows** with high complexity

**Overall Assessment**: 🟡 **Functional but fragile**. The system works in production but needs refactoring before scaling or adding features.

---

## 🔴 Critical Issues (Fix Immediately)

### 1. **Broken Database Functions**

The `semantic_search()` function still references `image_key` column that was removed in migration 16:

```sql
-- From semantic_search function (BROKEN)
SELECT e.image_key, ...  -- ❌ Column doesn't exist!
```

**Impact**: Semantic search queries will fail with "column does not exist" errors.

**Fix Required**:
```sql
-- Create migration to update function
CREATE OR REPLACE FUNCTION semantic_search(...)
RETURNS TABLE (..., image_url text, ...) -- Change image_key → image_url
AS $$
  SELECT e.image_url, ...  -- Fix column reference
$$;
```

### 2. **Orphaned Database Objects**

Migration 8 (`add_entities_with_image_urls_view.sql`) created view and functions that were supposed to be dropped in migration 16, but the DROP statements failed:

```sql
-- These were partially dropped but may still have remnants:
- VIEW entities_with_urls (references non-existent image_key)
- TRIGGER entities_image_url_trigger (references non-existent image_key)
- FUNCTION update_entity_image_url() (calls non-existent get_image_url())
- FUNCTION get_image_url() (removed but maybe not fully cleaned up)
```

**Impact**:
- Potential runtime errors if view/trigger are accessed
- Confusion about which columns/functions actually exist
- Migration 16 claimed to drop these but they might still exist in production

**Verification Needed**:
```bash
# Check if these still exist in production
docker exec supabase_db psql -c "\dv entities_with_urls"
docker exec supabase_db psql -c "\df get_image_url"
```

### 3. **Empty Migration File**

`20251023172157_increase_graphql_page_size.sql` is completely empty (0 bytes).

**Impact**:
- Breaks migration sequence reproducibility
- Confuses developers about what this migration was supposed to do
- Duplicate of migration 10?

**Fix**: Remove or replace with commented explanation.

---

## 🟡 Design Issues (Architectural Concerns)

### 1. **Removed `relationships.attributes` Column**

Migration 17 removed the `attributes` JSONB column from `relationships` table because "all values were empty."

**Problem**: This creates a future limitation. What if you need relationship metadata later?

Examples of metadata you might want:
```jsonb
{
  "rarity_in_collection": "chase variant",
  "quantity": 3,
  "acquisition_date": "2024-01-15",
  "condition": "mint"
}
```

**Current Workaround**: You'd have to create a new table or add it back with another migration.

**Recommendation**: Consider re-adding as `metadata JSONB DEFAULT '{}'` for future flexibility.

### 2. **Three Overlapping Search Systems**

The database has THREE different search mechanisms with unclear use cases:

| Search Type | Technology | Use Case | Performance |
|------------|------------|----------|-------------|
| **Trigram** | `pg_trgm` | Fuzzy name matching | Fast for typos |
| **Full-text** | `tsvector` | Keyword search | Fast for multi-word |
| **Semantic** | `pgvector` | Meaning-based | Slow, requires embeddings |

**Problems**:
1. **No guidance** on when to use which search method
2. **Triple indexing overhead** (3 indexes just for searching names!)
3. **Semantic search requires external embedding generation** (not automated)
4. **~20,632 entities have embeddings** - but how are they kept in sync?

**Questions**:
- When entity names change, do embeddings get regenerated?
- What happens to new entities - do they get embeddings automatically?
- Why have trigram AND full-text? Aren't they redundant for name searches?

**Recommendation**:
- Document clear use cases for each search type
- Consider removing one of trigram/full-text (probably full-text, since it's only on `name`)
- Add automation for embedding generation or remove semantic search

### 3. **JSONB Philosophy Inconsistency**

The schema mixes structured columns and JSONB inconsistently:

**Extracted to columns**: `year`, `country`, `language`, `image_url`, `thumbnail_url`, `external_ids`

**Left in JSONB**: `description`, additional images, custom fields

**Why `external_ids` gets its own JSONB column but additional images stay in `attributes`?**

Current structure:
```json
{
  "external_ids": {"tcgplayer": "base1-4"},  // Dedicated column
  "attributes": {
    "description": "...",
    "images": ["url1", "url2"]  // Why not image_urls column?
  }
}
```

**Recommendation**: Document clear rules for when to extract columns vs use JSONB.

---

## 🟠 Migration Management Issues

### Migration Drift Timeline

Your migrations show signs of chaotic evolution:

1. **Migration 4**: `convert_image_url_to_flexible_key` - Created `image_key` column
2. **Migration 8**: Added view + trigger to compute `image_url` from `image_key`
3. **Migration 9**: Added `image_url` as stored column (duplicating migration 8's logic)
4. **Migration 16**: Converted `image_key` back to `image_url` (full circle!)
5. **Migrations 20-21**: Added columns that existed in production but not locally

**This indicates**:
- Experimentation in production without proper testing
- Manual schema changes applied directly to production
- Migrations written retroactively to match production

**Recommendations**:
1. **Use branches for schema changes** - test locally first
2. **Never modify production schema manually** - always use migrations
3. **Consider migration squashing** - 21 migrations for a simple schema is excessive

### Migration Permission Issues

Some migrations fail with permission errors:
```
ERROR: permission denied to set parameter "graphql.default_page_size"
```

**Impact**: Can't apply migrations using `supabase db push`, must use manual `psql`.

**Root Cause**: Supabase local Docker doesn't have permissions for certain ALTER DATABASE statements.

**Fix**: Either:
- Use `ALTER ROLE postgres SET graphql.default_page_size = 1000;` instead
- Apply these settings via `supabase/config.toml` instead of migrations

---

## 🔵 Operational Complexity

### Backup Management: 33GB Problem

You have **33GB of backup files** (20 backups) stored locally.

**At 1.65GB per backup**, this will fill disk fast. Calculation:
- 1 backup/day = 50GB/month = 600GB/year

**Issues**:
1. **No automatic cleanup** - old backups accumulate forever
2. **No offsite storage** - if disk fails, backups are lost
3. **No restore testing** - do these backups actually work?
4. **Storage bucket backups separate** - must restore both DB + storage for consistency

**Recommendations**:
1. **Retention policy**: Keep last 7 daily + 4 weekly + 3 monthly
2. **Automated cleanup**:
   ```bash
   # Add to safe-migrate script
   find backups/ -name "backup_*.sql" -mtime +7 -delete  # Delete >7 days old
   ```
3. **S3/Cloud backup**: Upload to AWS S3 / Backblaze B2 for disaster recovery
4. **Test restores**: Monthly restore test to verify backups work

### Manual Embedding Generation

Semantic search requires embeddings to be generated manually:

```python
# Currently: Manual process
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode(entity_name)
supabase.update({'name_embedding': embedding})
```

**Problems**:
- No documentation on how to generate embeddings for new entities
- No script to backfill missing embeddings
- Embeddings not updated when entity names change
- Production has 20,632 embeddings - how were they generated?

**Recommendations**:
1. **Create script**: `scripts/generate-embeddings` (like generate-thumbnails)
2. **Document workflow**: When/how to regenerate embeddings
3. **Consider**: Database trigger to mark entities needing re-embedding
4. **Or**: Remove semantic search if it's not actively used

### Thumbnail Generation: Better Model

The thumbnail system is well-designed:
- ✅ Dedicated script with dry-run mode
- ✅ Parallel processing and progress bars
- ✅ Clear documentation

**This should be the model for other operational tasks** (especially embeddings).

---

## ⚡ Performance & Scalability

### Index Analysis

**Good**:
- ✅ Composite indexes on relationships (`from_id, type`) enable efficient graph traversal
- ✅ Partial indexes save space (only index non-null values)
- ✅ HNSW index for semantic search is appropriate choice

**Concerns**:
1. **No index on `updated_at`** - common query pattern for "recent changes"
2. **JSONB indexes use `jsonb_path_ops`** - fast but limited to `@>` operator
3. **HNSW index configuration not documented** - using defaults (m=16, ef_construction=64)?

**At 20K entities**: Current indexes are fine.

**At 200K+ entities**:
- Consider partitioning by `type` (separate tables for cards vs figures)
- HNSW index may need tuning (increase `m` parameter for better recall)
- Full table scans on `name_embedding IS NULL` may become slow

### Query Performance (Untested)

No documentation of query performance characteristics:
- What's the typical latency for semantic search?
- How fast is graph traversal for deep hierarchies?
- Do collection page loads perform well with 1000+ items?

**Recommendation**: Add performance benchmarks to documentation.

---

## 📚 Documentation Issues

### Documentation Sprawl

**33 markdown files** across the project, with overlapping content:

- `README.md` - Quick start guide
- `CLAUDE.md` - Comprehensive reference (18,901 bytes!)
- `BACKUP_SYSTEM.md` - Backup documentation
- `THUMBNAIL_QUICKSTART.md` - Thumbnail guide
- Plus 29 more files in `.claude/` and `scripts/`

**Problems**:
1. **Information scattered** - where do I find X?
2. **Duplication** - same info in multiple places
3. **Inconsistency** - docs were out of date with actual schema
4. **Maintenance burden** - changes require updating multiple files

**Recommendations**:
1. **Single source of truth**: Make `CLAUDE.md` the definitive guide
2. **Specialized guides**: Keep THUMBNAIL_QUICKSTART.md for step-by-step workflows
3. **Link, don't duplicate**: README.md should link to CLAUDE.md sections
4. **Automated checks**: CI job to validate docs match schema

---

## 🎯 Recommendations by Priority

### Priority 1: Fix Critical Bugs (This Week)

1. ✅ Fix `semantic_search()` function to use `image_url` instead of `image_key`
2. ✅ Verify and clean up orphaned views/functions/triggers
3. ✅ Remove or document empty migration file
4. ✅ Test semantic search end-to-end to ensure it works

### Priority 2: Reduce Operational Burden (This Month)

1. ✅ Implement backup retention policy (keep last 7 days)
2. ✅ Create embedding generation script (like thumbnail script)
3. ✅ Document which search method to use when
4. ✅ Add restore testing to monthly checklist
5. ✅ Set up S3/cloud backup for disaster recovery

### Priority 3: Technical Debt (This Quarter)

1. ✅ Consider migration squashing (21 migrations → ~5 logical migrations)
2. ✅ Re-add `relationships.metadata` JSONB column for future flexibility
3. ✅ Remove either trigram or full-text search (keep the one you actually use)
4. ✅ Add performance benchmarks to documentation
5. ✅ Set up CI/CD for automated testing and deployment

### Priority 4: Scalability Prep (6+ Months)

1. ✅ Implement table partitioning if dataset grows >200K entities
2. ✅ Tune HNSW index parameters for semantic search
3. ✅ Consider read replicas for production
4. ✅ Add caching layer (Redis) for frequently accessed collections

---

## 🏆 What's Working Well

Let's acknowledge the good parts:

✅ **Pure graph model is elegant** - entities + relationships is flexible and powerful
✅ **Supabase choice is solid** - GraphQL API, Auth, Storage all integrated
✅ **Thumbnail optimization is excellent** - 90%+ size reduction, well-documented
✅ **Backup automation exists** - `safe-migrate` prevents data loss
✅ **pgvector integration shows foresight** - semantic search is a valuable feature
✅ **Index design is thoughtful** - composite, partial, and specialized indexes used appropriately

The foundation is good. It just needs cleanup and documentation to be production-ready at scale.

---

## Final Grade: **C+ (Functional but Needs Work)**

**Strengths**: Good core architecture, working production system, 20K+ entities managed successfully

**Weaknesses**: Technical debt, migration chaos, operational complexity, documentation sprawl

**Bottom Line**: This system works today but will become increasingly difficult to maintain and extend without addressing the issues above. Invest the time to clean it up now before scaling further.

---

## Questions for You

1. **Which search method do you actually use?** (Trigram vs Full-text vs Semantic)
2. **How often do you query by semantic similarity?** (Daily? Weekly? Never?)
3. **Do you update embeddings when entity names change?** (Or are they stale?)
4. **What's your actual production deployment process?** (Manual? CI/CD?)
5. **Have you ever needed to restore from backup?** (Test your backups!)

Understanding your actual usage patterns will help prioritize which issues to tackle first.
