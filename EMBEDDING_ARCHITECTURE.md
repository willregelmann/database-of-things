# Automated Embedding Generation System Design

## Executive Summary

This document outlines a production-ready, scalable architecture for automated embedding generation in your Supabase database. The system supports 20K entities today, scaling to 100K soon and 1M+ eventually, using sentence-transformers (all-MiniLM-L6-v2) for semantic search.

## 1. Recommended Architecture: Hybrid Queue-Based System

### Overview
A **hybrid approach** combining database triggers with external Python workers provides the best balance of reliability, cost-effectiveness, and maintainability.

```mermaid
graph TD
    A[Entity Insert/Update] --> B[Database Trigger]
    B --> C[Embedding Queue Table]
    C --> D{Processing Method}
    D -->|Primary| E[Python Worker Service]
    D -->|Backup| F[Manual Batch Processing]
    E --> G[Generate Embeddings]
    F --> G
    G --> H[Update entities.name_embedding]
    H --> I[Mark Queue Item Processed]
```

### Why This Architecture?

**Pros:**
- ✅ **Reliable**: Queue ensures no embeddings are missed
- ✅ **Cost-effective**: ~$5-10/month at 100K scale
- ✅ **Maintainable**: Simple Python code, easy debugging
- ✅ **Flexible**: Can switch between real-time and batch processing
- ✅ **Resilient**: Automatic retry on failures
- ✅ **Observable**: Clear queue status and monitoring

**Cons:**
- ❌ Requires separate service deployment
- ❌ Not instant (5-30 second delay typical)
- ❌ Additional infrastructure complexity

## 2. Alternative Architectures Considered

### Option A: Supabase Edge Functions (Serverless)

**Pros:**
- Zero infrastructure management
- Auto-scaling
- Pay-per-use pricing

**Cons:**
- ❌ **Model loading overhead**: 2-3s cold start per invocation
- ❌ **Size limitations**: Edge Functions have 50MB limit, models are ~80MB
- ❌ **Cost at scale**: $0.00001/invocation = $100/month at 10M calls
- ❌ **Complexity**: Need external model hosting (Hugging Face Inference API)

**Verdict**: Not recommended due to model size constraints and cold start latency.

### Option B: Pure Database Triggers + pg_cron

**Pros:**
- Everything in PostgreSQL
- No external services

**Cons:**
- ❌ Cannot run Python/ML models in PostgreSQL
- ❌ Would require external API for embeddings
- ❌ Limited error handling

**Verdict**: Not feasible without external embedding API.

### Option C: Real-time Webhooks

**Pros:**
- Instant processing
- Event-driven architecture

**Cons:**
- ❌ Complex retry logic needed
- ❌ Webhook endpoint must be highly available
- ❌ Harder to batch optimize

**Verdict**: Over-engineered for this use case.

## 3. Implementation Design

### 3.1 Database Schema

```sql
-- Migration: 20251106_create_embedding_queue.sql

-- Embedding generation queue
CREATE TABLE embedding_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    entity_name TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'MANUAL')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    attempts INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    UNIQUE(entity_id, status) -- Prevent duplicate pending items
);

-- Indexes for efficient queue processing
CREATE INDEX idx_embedding_queue_status_created
ON embedding_queue(status, created_at)
WHERE status = 'pending';

CREATE INDEX idx_embedding_queue_entity_id
ON embedding_queue(entity_id);

-- Trigger function to queue embedding generation
CREATE OR REPLACE FUNCTION queue_embedding_generation()
RETURNS TRIGGER AS $$
BEGIN
    -- Only queue if name changed or embedding is missing
    IF (TG_OP = 'INSERT' AND NEW.name IS NOT NULL) OR
       (TG_OP = 'UPDATE' AND (
           NEW.name IS DISTINCT FROM OLD.name OR
           NEW.name_embedding IS NULL
       )) THEN

        -- Insert or update queue entry
        INSERT INTO embedding_queue (entity_id, entity_name, operation)
        VALUES (NEW.id, NEW.name, TG_OP)
        ON CONFLICT (entity_id, status)
        WHERE status = 'pending'
        DO UPDATE SET
            entity_name = EXCLUDED.entity_name,
            created_at = NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on entities table
CREATE TRIGGER trigger_queue_embedding
AFTER INSERT OR UPDATE OF name ON entities
FOR EACH ROW
EXECUTE FUNCTION queue_embedding_generation();

-- Monitoring view
CREATE VIEW embedding_queue_stats AS
SELECT
    status,
    COUNT(*) as count,
    MIN(created_at) as oldest,
    MAX(created_at) as newest,
    AVG(EXTRACT(EPOCH FROM (processed_at - created_at))) as avg_processing_time_seconds
FROM embedding_queue
GROUP BY status;

-- Function to claim items for processing (with locking)
CREATE OR REPLACE FUNCTION claim_embedding_batch(
    batch_size INTEGER DEFAULT 100,
    worker_id TEXT DEFAULT 'default'
)
RETURNS TABLE (
    queue_id UUID,
    entity_id UUID,
    entity_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH claimed AS (
        SELECT q.id, q.entity_id, q.entity_name
        FROM embedding_queue q
        WHERE q.status = 'pending'
        AND q.attempts < 3  -- Max retry limit
        ORDER BY q.created_at
        LIMIT batch_size
        FOR UPDATE SKIP LOCKED  -- Critical: prevents race conditions
    )
    UPDATE embedding_queue q
    SET status = 'processing',
        attempts = attempts + 1,
        processed_at = NOW()
    FROM claimed c
    WHERE q.id = c.id
    RETURNING q.id, q.entity_id, q.entity_name;
END;
$$ LANGUAGE plpgsql;
```

### 3.2 Python Worker Service

```python
# embedding_worker.py
import os
import time
import logging
import asyncio
from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import asyncpg
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingWorker:
    def __init__(
        self,
        database_url: str,
        model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',
        batch_size: int = 100,
        poll_interval: int = 10
    ):
        self.database_url = database_url
        self.model_name = model_name
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.model = None
        self.pool = None

    async def init(self):
        """Initialize model and database connection."""
        logger.info(f"Loading model {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        logger.info(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

        # Create connection pool
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool created")

    async def claim_batch(self) -> List[Tuple[str, str, str]]:
        """Claim a batch of items from the queue."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM claim_embedding_batch($1)",
                self.batch_size
            )
            return [(row['queue_id'], row['entity_id'], row['entity_name']) for row in rows]

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a batch of texts."""
        return self.model.encode(texts, batch_size=32, show_progress_bar=False)

    async def update_embeddings(self, updates: List[Tuple[str, str, np.ndarray]]):
        """Update entities with embeddings and mark queue items as processed."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Update entities with embeddings
                for entity_id, _, embedding in updates:
                    embedding_list = embedding.tolist()
                    await conn.execute(
                        """
                        UPDATE entities
                        SET name_embedding = $1::vector(384),
                            updated_at = NOW()
                        WHERE id = $2
                        """,
                        embedding_list,
                        entity_id
                    )

                # Mark queue items as completed
                queue_ids = [queue_id for queue_id, _, _ in updates]
                await conn.execute(
                    """
                    UPDATE embedding_queue
                    SET status = 'completed',
                        processed_at = NOW()
                    WHERE id = ANY($1::uuid[])
                    """,
                    queue_ids
                )

    async def mark_failed(self, queue_id: str, error: str):
        """Mark a queue item as failed."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE embedding_queue
                SET status = CASE
                    WHEN attempts >= 3 THEN 'failed'
                    ELSE 'pending'  -- Will retry
                END,
                last_error = $1,
                processed_at = NOW()
                WHERE id = $2
                """,
                error,
                queue_id
            )

    async def process_batch(self):
        """Process a single batch of embeddings."""
        # Claim batch
        batch = await self.claim_batch()

        if not batch:
            return 0

        logger.info(f"Processing batch of {len(batch)} items")

        try:
            # Extract texts
            texts = [entity_name for _, _, entity_name in batch]

            # Generate embeddings
            embeddings = self.generate_embeddings(texts)

            # Prepare updates
            updates = [
                (queue_id, entity_id, embedding)
                for (queue_id, entity_id, _), embedding
                in zip(batch, embeddings)
            ]

            # Update database
            await self.update_embeddings(updates)

            logger.info(f"Successfully processed {len(batch)} embeddings")
            return len(batch)

        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            # Mark all items in batch as failed
            for queue_id, _, _ in batch:
                await self.mark_failed(queue_id, str(e))
            return 0

    async def cleanup_old_completed(self):
        """Clean up old completed queue items."""
        async with self.pool.acquire() as conn:
            deleted = await conn.fetchval(
                """
                DELETE FROM embedding_queue
                WHERE status = 'completed'
                AND processed_at < NOW() - INTERVAL '7 days'
                RETURNING COUNT(*)
                """
            )
            if deleted:
                logger.info(f"Cleaned up {deleted} old completed queue items")

    async def run(self):
        """Main worker loop."""
        await self.init()

        logger.info("Starting embedding worker...")
        consecutive_empty = 0

        while True:
            try:
                processed = await self.process_batch()

                if processed == 0:
                    consecutive_empty += 1
                    # Exponential backoff when queue is empty
                    wait_time = min(self.poll_interval * (2 ** min(consecutive_empty - 1, 5)), 300)
                    await asyncio.sleep(wait_time)
                else:
                    consecutive_empty = 0
                    # Process immediately if there might be more
                    await asyncio.sleep(1)

                # Periodic cleanup (every 100 iterations)
                if consecutive_empty % 100 == 99:
                    await self.cleanup_old_completed()

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(30)  # Wait before retrying

# Docker deployment
if __name__ == "__main__":
    import sys

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:54322/postgres"
    )

    worker = EmbeddingWorker(
        database_url=database_url,
        batch_size=int(os.getenv("BATCH_SIZE", "100")),
        poll_interval=int(os.getenv("POLL_INTERVAL", "10"))
    )

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("Worker stopped")
        sys.exit(0)
```

### 3.3 Docker Deployment

```dockerfile
# Dockerfile.embedding-worker
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    sentence-transformers==2.2.2 \
    asyncpg==0.29.0 \
    numpy==1.24.3 \
    torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# Copy worker script
COPY embedding_worker.py .

# Pre-download model during build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

CMD ["python", "embedding_worker.py"]
```

```yaml
# docker-compose.embedding.yml
version: '3.8'

services:
  embedding-worker:
    build:
      context: .
      dockerfile: Dockerfile.embedding-worker
    environment:
      DATABASE_URL: postgresql://postgres:postgres@host.docker.internal:54322/postgres
      BATCH_SIZE: 100
      POLL_INTERVAL: 10
      PYTHONUNBUFFERED: 1
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    networks:
      - supabase_network_database-of-things

networks:
  supabase_network_database-of-things:
    external: true
```

## 4. Cost Analysis

### At 100K Entities Scale

**Assumptions:**
- 1,000 new entities/day
- 500 entity name updates/day
- 384-dimensional embeddings (all-MiniLM-L6-v2)

**Infrastructure Costs:**
```
Python Worker (1 vCPU, 2GB RAM):
- AWS ECS Fargate: ~$15/month
- DigitalOcean App Platform: $10/month
- Self-hosted: ~$5/month

Database Storage:
- Queue table: ~10MB
- Embeddings: 100K × 384 × 4 bytes = ~150MB
- Total additional: ~160MB = $0.10/month

Network Transfer:
- ~1GB/month = $0.10/month

Total: ~$10-15/month
```

### At 1M Entities Scale

```
Python Worker (2 vCPU, 4GB RAM):
- AWS ECS Fargate: ~$30/month
- DigitalOcean App Platform: $20/month

Database Storage:
- Embeddings: 1M × 384 × 4 bytes = ~1.5GB
- Total additional: ~1.5GB = $1/month

Network Transfer:
- ~10GB/month = $1/month

Total: ~$20-30/month
```

### Comparison with Alternatives

| Solution | 100K Scale | 1M Scale | Pros | Cons |
|----------|------------|----------|------|------|
| **Python Worker (Recommended)** | $10-15/mo | $20-30/mo | Reliable, simple | Needs deployment |
| Supabase Edge Functions + HF API | $50/mo | $500/mo | Serverless | Expensive, complex |
| OpenAI Embeddings API | $40/mo | $400/mo | No infrastructure | Vendor lock-in, latency |
| AWS Lambda + SageMaker | $25/mo | $250/mo | Scalable | Complex setup |

## 5. Failure Handling & Recovery

### Automatic Retry Logic

```sql
-- Built into queue design:
-- 1. Max 3 attempts per item
-- 2. Exponential backoff in worker
-- 3. Failed items remain in queue for manual review

-- Manual retry for failed items
UPDATE embedding_queue
SET status = 'pending',
    attempts = 0,
    last_error = NULL
WHERE status = 'failed'
AND created_at > NOW() - INTERVAL '24 hours';
```

### Monitoring Queries

```sql
-- Check queue health
SELECT * FROM embedding_queue_stats;

-- Find stuck items
SELECT entity_id, entity_name, attempts, last_error
FROM embedding_queue
WHERE status = 'failed'
OR (status = 'processing' AND processed_at < NOW() - INTERVAL '1 hour');

-- Entities missing embeddings
SELECT COUNT(*) as missing_count
FROM entities
WHERE name IS NOT NULL
AND name_embedding IS NULL;
```

### Recovery Procedures

```bash
# 1. Restart worker if crashed
docker-compose -f docker-compose.embedding.yml restart embedding-worker

# 2. Requeue all missing embeddings
psql $DATABASE_URL -c "
INSERT INTO embedding_queue (entity_id, entity_name, operation)
SELECT id, name, 'MANUAL'
FROM entities
WHERE name IS NOT NULL
AND name_embedding IS NULL
ON CONFLICT DO NOTHING;
"

# 3. Force regenerate for specific entities
psql $DATABASE_URL -c "
UPDATE entities
SET name_embedding = NULL
WHERE id IN ('uuid1', 'uuid2');
"
```

## 6. Migration Path

### Phase 1: Deploy Infrastructure (Week 1)
1. Create queue schema migration
2. Deploy Python worker to staging
3. Test with small batch (100 entities)
4. Monitor performance and costs

### Phase 2: Backfill Existing (Week 2)
```bash
# Gradual backfill script
#!/bin/bash

# Queue existing entities in batches
for offset in $(seq 0 1000 20000); do
  psql $DATABASE_URL -c "
  INSERT INTO embedding_queue (entity_id, entity_name, operation)
  SELECT id, name, 'MANUAL'
  FROM entities
  WHERE name_embedding IS NULL
  ORDER BY created_at
  LIMIT 1000 OFFSET $offset
  ON CONFLICT DO NOTHING;
  "

  echo "Queued batch $offset, waiting for processing..."
  sleep 60  # Let worker process
done
```

### Phase 3: Production Deployment (Week 3)
1. Deploy worker to production
2. Enable database trigger
3. Monitor queue depth and processing times
4. Tune batch size and polling interval

### Phase 4: Optimization (Ongoing)
- Add metrics collection (Prometheus/Grafana)
- Implement smart batching by entity type
- Consider GPU acceleration at 1M+ scale
- Add embedding versioning support

## 7. Advanced Features (Future)

### Multi-Model Support

```python
# Support multiple models for different entity types
MODELS = {
    'card': 'sentence-transformers/all-mpnet-base-v2',  # 768 dims
    'figure': 'sentence-transformers/all-MiniLM-L6-v2',  # 384 dims
    'default': 'sentence-transformers/all-MiniLM-L6-v2'
}
```

### Incremental Updates

```sql
-- Track embedding version for model upgrades
ALTER TABLE entities ADD COLUMN embedding_version INTEGER DEFAULT 1;

-- Queue only outdated embeddings
INSERT INTO embedding_queue (entity_id, entity_name, operation)
SELECT id, name, 'VERSION_UPGRADE'
FROM entities
WHERE embedding_version < 2;
```

### Real-time Priority Queue

```sql
-- Add priority support
ALTER TABLE embedding_queue
ADD COLUMN priority INTEGER DEFAULT 0;

-- High priority for recently viewed items
CREATE OR REPLACE FUNCTION boost_embedding_priority(entity_id UUID)
RETURNS VOID AS $$
UPDATE embedding_queue
SET priority = priority + 10
WHERE entity_id = $1
AND status = 'pending';
$$ LANGUAGE sql;
```

## 8. Deployment Commands

```bash
# Create migration
./bin/supabase migration new create_embedding_queue

# Copy migration content from this document
cat > supabase/migrations/[timestamp]_create_embedding_queue.sql

# Apply migration (with automatic backup)
./scripts/safe-migrate push

# Build and start worker
docker-compose -f docker-compose.embedding.yml up -d --build

# View logs
docker-compose -f docker-compose.embedding.yml logs -f

# Check queue status
docker exec supabase_db_database-of-things psql -U postgres -c "SELECT * FROM embedding_queue_stats;"
```

## 9. Production Checklist

- [ ] Database migration applied and tested
- [ ] Worker deployed with resource limits
- [ ] Monitoring dashboards configured
- [ ] Alerting for queue depth > 10,000
- [ ] Backup strategy for embeddings
- [ ] Documentation for operations team
- [ ] Load testing completed
- [ ] Rollback procedure documented
- [ ] SLA defined (e.g., 95% within 60 seconds)

## 10. Summary

The recommended **hybrid queue-based architecture** provides:

✅ **Reliability**: Queue ensures no missed embeddings
✅ **Cost-effectiveness**: ~$10-15/month at 100K scale
✅ **Scalability**: Handles 1M+ entities with minor adjustments
✅ **Maintainability**: Simple Python code, clear monitoring
✅ **Flexibility**: Easy to switch models or add features

This solution balances all requirements while keeping operational complexity manageable.