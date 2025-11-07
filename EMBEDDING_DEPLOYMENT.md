# Embedding System Deployment Guide

## Quick Start

### 1. Apply Database Migration

```bash
# Apply the embedding queue migration (with automatic backup)
./scripts/safe-migrate push

# Verify migration
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT * FROM embedding_queue_stats;
"
```

### 2. Start the Embedding Worker

```bash
# Build and start the worker
docker-compose -f docker-compose.embedding.yml up -d --build

# View logs
docker-compose -f docker-compose.embedding.yml logs -f

# Check worker status
docker ps | grep embedding_worker
```

### 3. Queue Existing Entities (Backfill)

```bash
# Queue all entities missing embeddings
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT queue_missing_embeddings(NULL, NULL);
"

# Or queue in smaller batches
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT queue_missing_embeddings(NULL, 1000);
"
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database connection (for production)
DATABASE_URL=postgresql://postgres:your-password@your-host:5432/postgres

# Worker configuration
MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
BATCH_SIZE=100
POLL_INTERVAL=10
LOG_LEVEL=INFO

# Resource limits
OMP_NUM_THREADS=4
MKL_NUM_THREADS=4
```

### Using Different Models

The system supports any sentence-transformer model. Popular options:

| Model | Dimensions | Quality | Speed | Size |
|-------|------------|---------|-------|------|
| all-MiniLM-L6-v2 (default) | 384 | Good | Fast | 80MB |
| all-MiniLM-L12-v2 | 384 | Better | Medium | 120MB |
| all-mpnet-base-v2 | 768 | Best | Slow | 420MB |
| paraphrase-MiniLM-L3-v2 | 384 | Okay | Very Fast | 60MB |

**Note**: If changing models, update the database schema to match dimensions:

```sql
-- For 768-dimensional models
ALTER TABLE entities
ALTER COLUMN name_embedding TYPE vector(768);
```

## Monitoring

### Real-Time Queue Statistics

```bash
# View queue status
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT * FROM embedding_queue_stats;
"

# Example output:
#  status    | count | oldest | newest | avg_wait_seconds | max_attempts
# -----------+-------+--------+--------+------------------+--------------
#  pending   |    42 | ...    | ...    |            5.2   |     0
#  completed | 19532 | ...    | ...    |            3.8   |     1
#  failed    |     3 | ...    | ...    |          120.5   |     3
```

### Find Problematic Items

```bash
# View failed items
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT entity_id, entity_name, attempts, last_error
FROM embedding_queue
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;
"

# Find stuck processing items
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT entity_id, entity_name, processed_at
FROM embedding_queue
WHERE status = 'processing'
AND processed_at < NOW() - INTERVAL '1 hour';
"
```

### Entities Missing Embeddings

```bash
# Count entities without embeddings
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT COUNT(*) as missing_count
FROM entities_missing_embeddings;
"

# List specific entities
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT id, name, type, queue_status
FROM entities_missing_embeddings
LIMIT 10;
"
```

## Operations

### Starting and Stopping

```bash
# Start worker
docker-compose -f docker-compose.embedding.yml up -d

# Stop worker gracefully
docker-compose -f docker-compose.embedding.yml stop

# Restart worker
docker-compose -f docker-compose.embedding.yml restart

# Remove worker (preserves model cache)
docker-compose -f docker-compose.embedding.yml down
```

### Scaling Workers

To run multiple workers for faster processing:

```bash
# Scale to 3 workers
docker-compose -f docker-compose.embedding.yml up -d --scale embedding-worker=3

# Check all workers
docker ps | grep embedding_worker
```

**Note**: Each worker uses row-level locking, so they won't process the same items.

### Manual Operations

#### Retry Failed Items

```bash
# Retry all failed items from last 24 hours
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT retry_failed_embeddings(24);
"
```

#### Force Regenerate Embeddings

```bash
# Clear embeddings for specific entities
docker exec supabase_db_database-of-things psql -U postgres -c "
UPDATE entities
SET name_embedding = NULL
WHERE type = 'card'
AND name LIKE '%Charizard%';
"

# They'll be automatically queued by the trigger
```

#### Clean Up Old Queue Items

```bash
# Remove completed items older than 7 days
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT cleanup_old_queue_items(7);
"
```

#### Priority Boost

```bash
# Boost priority for specific entity types
docker exec supabase_db_database-of-things psql -U postgres -c "
UPDATE embedding_queue
SET priority = priority + 10
WHERE entity_id IN (
  SELECT id FROM entities WHERE type = 'collection'
)
AND status = 'pending';
"
```

## Troubleshooting

### Worker Not Processing

1. **Check worker logs:**
```bash
docker-compose -f docker-compose.embedding.yml logs --tail 100
```

2. **Verify database connection:**
```bash
docker-compose -f docker-compose.embedding.yml exec embedding-worker \
  python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))"
```

3. **Check for stuck items:**
```bash
docker exec supabase_db_database-of-things psql -U postgres -c "
UPDATE embedding_queue
SET status = 'pending', processed_at = NULL
WHERE status = 'processing'
AND processed_at < NOW() - INTERVAL '1 hour';
"
```

### High Memory Usage

1. **Reduce batch size:**
```bash
# Edit docker-compose.embedding.yml or set in .env
BATCH_SIZE=50
```

2. **Limit model threads:**
```bash
OMP_NUM_THREADS=2
MKL_NUM_THREADS=2
```

### Slow Processing

1. **Check queue depth:**
```bash
docker exec supabase_db_database-of-things psql -U postgres -c "
SELECT status, COUNT(*) FROM embedding_queue GROUP BY status;
"
```

2. **Scale workers:**
```bash
docker-compose -f docker-compose.embedding.yml up -d --scale embedding-worker=3
```

3. **Use faster model:**
```bash
MODEL_NAME=paraphrase-MiniLM-L3-v2
```

### Database Connection Issues

1. **For local Supabase:**
```bash
# Use host.docker.internal on Mac/Windows
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54322/postgres

# Or use Docker network on Linux
DATABASE_URL=postgresql://postgres:postgres@supabase_db_database-of-things:5432/postgres
```

2. **For production Supabase:**
```bash
# Get connection string from Supabase dashboard
DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:6543/postgres?sslmode=require
```

## Production Deployment

### AWS ECS

1. **Build and push image:**
```bash
# Build image
docker build -t embedding-worker ./services/embedding-worker

# Tag for ECR
docker tag embedding-worker:latest [account].dkr.ecr.[region].amazonaws.com/embedding-worker:latest

# Push to ECR
docker push [account].dkr.ecr.[region].amazonaws.com/embedding-worker:latest
```

2. **Create task definition** with environment variables
3. **Create ECS service** with desired task count

### DigitalOcean App Platform

1. **Create app.yaml:**
```yaml
name: embedding-worker
services:
- name: worker
  github:
    repo: your-repo
    branch: main
    deploy_on_push: true
  dockerfile_path: services/embedding-worker/Dockerfile
  instance_size: basic-xs
  instance_count: 1
  envs:
  - key: DATABASE_URL
    value: ${db.DATABASE_URL}
  - key: BATCH_SIZE
    value: "100"
```

2. **Deploy:**
```bash
doctl apps create --spec app.yaml
```

### Kubernetes

1. **Create deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: embedding-worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: embedding-worker
  template:
    metadata:
      labels:
        app: embedding-worker
    spec:
      containers:
      - name: worker
        image: embedding-worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        resources:
          limits:
            memory: "2Gi"
            cpu: "1000m"
          requests:
            memory: "512Mi"
            cpu: "250m"
```

2. **Apply:**
```bash
kubectl apply -f embedding-worker-deployment.yaml
```

## Performance Tuning

### Batch Size Optimization

Test different batch sizes to find optimal throughput:

```python
# Test script
import time
for batch_size in [50, 100, 200, 500]:
    start = time.time()
    # Process with batch_size
    elapsed = time.time() - start
    print(f"Batch {batch_size}: {elapsed:.2f}s")
```

Typical results:
- **Small batches (50)**: Lower memory, more database calls
- **Medium batches (100-200)**: Good balance
- **Large batches (500+)**: Faster per item, higher memory

### Database Optimization

```sql
-- Ensure indexes are being used
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM claim_embedding_batch(100);

-- Vacuum and analyze regularly
VACUUM ANALYZE embedding_queue;
VACUUM ANALYZE entities;

-- Monitor table bloat
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('entities', 'embedding_queue')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Monitoring Dashboard (Grafana)

Create these queries for a monitoring dashboard:

```sql
-- Queue depth over time
SELECT
  date_trunc('minute', NOW()) as time,
  COUNT(*) FILTER (WHERE status = 'pending') as pending,
  COUNT(*) FILTER (WHERE status = 'processing') as processing,
  COUNT(*) FILTER (WHERE status = 'completed') as completed,
  COUNT(*) FILTER (WHERE status = 'failed') as failed
FROM embedding_queue;

-- Processing rate
SELECT
  date_trunc('minute', processed_at) as time,
  COUNT(*) as processed_per_minute
FROM embedding_queue
WHERE status = 'completed'
AND processed_at > NOW() - INTERVAL '1 hour'
GROUP BY 1
ORDER BY 1;

-- Average wait time
SELECT
  date_trunc('minute', processed_at) as time,
  AVG(EXTRACT(EPOCH FROM (processed_at - created_at))) as avg_wait_seconds
FROM embedding_queue
WHERE status = 'completed'
AND processed_at > NOW() - INTERVAL '1 hour'
GROUP BY 1
ORDER BY 1;
```

## Security Considerations

1. **Use read-only database user for monitoring**
2. **Rotate database credentials regularly**
3. **Use secrets management (AWS Secrets Manager, K8s Secrets)**
4. **Run worker as non-root user (already configured)**
5. **Limit network access to database**
6. **Enable SSL for database connections in production**

## Backup and Recovery

### Backup Embeddings

```bash
# Export embeddings to file
docker exec supabase_db_database-of-things psql -U postgres -c "
COPY (
  SELECT id, name_embedding
  FROM entities
  WHERE name_embedding IS NOT NULL
) TO '/tmp/embeddings_backup.csv' CSV HEADER;
"

# Copy from container
docker cp supabase_db_database-of-things:/tmp/embeddings_backup.csv ./backups/
```

### Restore Embeddings

```bash
# Copy to container
docker cp ./backups/embeddings_backup.csv supabase_db_database-of-things:/tmp/

# Import embeddings
docker exec supabase_db_database-of-things psql -U postgres -c "
CREATE TEMP TABLE embedding_restore (
  id UUID,
  name_embedding vector(384)
);

COPY embedding_restore FROM '/tmp/embeddings_backup.csv' CSV HEADER;

UPDATE entities e
SET name_embedding = r.name_embedding
FROM embedding_restore r
WHERE e.id = r.id;
"
```

## Maintenance Schedule

### Daily
- Check queue stats
- Review failed items
- Monitor worker logs

### Weekly
- Clean up old completed items
- Review processing performance
- Check for stuck items

### Monthly
- Vacuum and analyze tables
- Review and optimize batch sizes
- Update worker image if needed
- Backup embeddings

## Support

For issues or questions:
1. Check worker logs first
2. Review queue statistics
3. Verify database connectivity
4. Check this guide's troubleshooting section