---
name: supabase-deployment
description: Deploy local Supabase database to production (Supabase Cloud or self-hosted). Use when deploying the collectibles database to production, migrating data and storage, or preparing for production deployment. Handles schema migrations, data export/import, storage file uploads, image URL conversion, and deployment verification.
---

# Supabase Production Deployment

Deploy the local Supabase collectibles database to production with complete data and storage migration.

## Purpose

This skill provides a complete workflow for deploying the graph-based collectibles database from local development to production. It handles:

- Converting localhost image URLs to environment-portable relative paths
- Exporting database data (20,000+ entities and relationships)
- Pushing schema migrations to production
- Uploading storage bucket files (600+ images)
- Verifying deployment success
- Troubleshooting common deployment issues

## When to Use This Skill

Use this skill when:
- Deploying the database to Supabase Cloud for the first time
- Setting up a production or staging environment
- Migrating from local development to hosted infrastructure
- Preparing data and storage for production readiness
- Verifying a production deployment succeeded

## Deployment Workflow

### Phase 1: Pre-Deployment Preparation

Before deploying, prepare the local database for production by making it environment-portable.

**Step 1: Convert Image URLs to Relative Paths**

Run `scripts/convert_images_to_relative.py` to convert localhost URLs to relative paths:

```bash
cd .claude/skills/supabase-deployment/scripts
python3 convert_images_to_relative.py --dry-run  # Preview changes
python3 convert_images_to_relative.py            # Apply conversion
```

This converts:
- From: `http://127.0.0.1:54321/storage/v1/object/public/images/uuid.jpg`
- To: `/storage/v1/object/public/images/uuid.jpg`

These relative paths are portable - clients prepend the Supabase project URL.

**Step 2: Create Backup**

```bash
./scripts/db-backup
```

Creates timestamped backup in `backups/` for rollback if needed.

**Step 3: Export Data**

Run `scripts/export_data.sh` to export production-ready data:

```bash
cd .claude/skills/supabase-deployment/scripts
./export_data.sh production-data.sql
```

This exports entities and relationships tables (data only, not schema).

**Step 4: Backup Storage Files**

Ensure storage files are backed up:

```bash
./scripts/storage-backup
```

### Phase 2: Production Setup

**Step 5: Create Production Project**

Create a new Supabase project at https://supabase.com/dashboard or set up self-hosted instance.

**Step 6: Link to Production**

```bash
./bin/supabase link --project-ref YOUR_PROJECT_REF
```

**Step 7: Push Migrations**

```bash
./scripts/safe-migrate push
```

This creates production schema, extensions, indexes, functions, and storage bucket.

**Step 8: Import Data**

```bash
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres" \
  -f production-data.sql
```

Get connection string from Supabase dashboard: Settings → Database → Connection string.

**Step 9: Upload Storage Files**

Run `scripts/upload_storage.py` to upload images:

```bash
cd .claude/skills/supabase-deployment/scripts

python3 upload_storage.py \
  --project-url "https://YOUR_PROJECT_REF.supabase.co" \
  --service-key "YOUR_SERVICE_ROLE_KEY"
```

Get service role key from: Settings → API → service_role.

### Phase 3: Verification

**Step 10: Verify Deployment**

Run `scripts/verify_deployment.py` to check deployment:

```bash
cd .claude/skills/supabase-deployment/scripts

python3 verify_deployment.py \
  --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres" \
  --project-url "https://YOUR_PROJECT_REF.supabase.co"
```

Verifies:
- Table row counts
- Extensions (uuid-ossp, pg_trgm, vector)
- Functions (search_by_text)
- Storage bucket accessibility

**Step 11: Test GraphQL API**

Open GraphQL playground at `https://YOUR_PROJECT_REF.supabase.co/graphql/v1` and test queries.

**Step 12: Test Search**

```sql
SELECT * FROM search_by_text('charizard', NULL, 10);
SELECT name, image_url FROM entities WHERE image_url IS NOT NULL LIMIT 5;
```

## Bundled Scripts

### convert_images_to_relative.py

Converts localhost image URLs to relative paths for environment portability.

**Usage**:
```bash
python3 convert_images_to_relative.py [--dry-run]
```

**What it does**:
- Finds all entities with localhost URLs
- Converts to relative paths (e.g., `images/uuid.jpg`)
- Supports dry-run mode to preview changes

### export_data.sh

Exports database data for production import.

**Usage**:
```bash
./export_data.sh [output_file]
```

**What it exports**:
- Entities table (all rows)
- Relationships table (all rows)
- Data only (no schema, no ownership)

### upload_storage.py

Uploads storage bucket files to production Supabase Storage.

**Usage**:
```bash
python3 upload_storage.py \
  --project-url <url> \
  --service-key <key> \
  [--dry-run]
```

**What it does**:
- Reads files from `storage-backup/` directory
- Uploads to production storage bucket
- Preserves file paths and content types
- Supports dry-run mode

### verify_deployment.py

Verifies production deployment succeeded.

**Usage**:
```bash
python3 verify_deployment.py \
  --db-url <connection-string> \
  --project-url <url>
```

**Checks**:
- Table counts match expectations
- Required extensions installed
- Database functions exist (search_by_text)
- Storage bucket accessible

## Detailed Reference

For complete step-by-step instructions, troubleshooting, and rollback procedures, load `references/deployment-checklist.md` into context:

```bash
# Read the full deployment checklist
cat .claude/skills/supabase-deployment/references/deployment-checklist.md
```

The checklist includes:
- Detailed instructions for each step
- Troubleshooting common issues
- Rollback procedures
- Cost estimation
- Post-deployment configuration
- Security setup (RLS policies)

## Deployment Targets

### Supabase Cloud (Recommended)

**Pros**:
- Fully managed (no infrastructure)
- Built-in backups, auth, storage
- Free tier available (500MB DB, 1GB storage)
- Automatic scaling

**Cons**:
- Costs scale with usage
- Vendor lock-in

### Self-Hosted Supabase

**Pros**:
- Full control over infrastructure
- No vendor lock-in
- Potentially lower costs at scale

**Cons**:
- Requires DevOps expertise
- Manual backups and updates
- More setup complexity

## Common Issues

### Image URLs Not Loading

**Cause**: Image URLs still have localhost domain prefix.

**Solution**: Run `convert_images_to_relative.py` to strip localhost URLs before export (see Phase 1, Step 1).

### Data Import Fails

**Cause**: UUID conflicts or constraint violations.

**Solution**: Import entities before relationships. See troubleshooting section in `references/deployment-checklist.md`.

### Storage Upload Fails

**Cause**: Incorrect service role key or bucket doesn't exist.

**Solution**: Verify bucket exists in dashboard (Storage → Buckets) and service role key is correct (Settings → API).

## Data Overview

Current database size:
- **20,632 entities** (Pokemon cards, Power Rangers toys, video games)
- **20,633 relationships**
- **610 localized images** (~200-500 MB)

This fits comfortably within Supabase Cloud free tier limits:
- ✅ 500 MB database
- ✅ 1 GB storage
- ✅ 50,000 monthly active users

## Post-Deployment

After successful deployment:

1. **Update client applications** with production API URL and keys
2. **Configure RLS policies** if authentication is needed
3. **Set up monitoring** for database and storage usage
4. **Schedule backups** (Supabase Cloud auto-backs up daily)
5. **Test thoroughly** with integration tests

## Rollback

If deployment fails:

```bash
# Rollback database
./scripts/db-restore backups/backup_YYYYMMDD_HHMMSS.sql

# Re-run storage backup
./scripts/storage-backup
```

## Migration from Local to Production

The deployment process uses migrations to recreate the schema in production, then imports data. This ensures:
- Schema is always up-to-date with migrations
- Data can be imported cleanly without conflicts
- Environment-specific settings (like image URLs) can be configured per environment
