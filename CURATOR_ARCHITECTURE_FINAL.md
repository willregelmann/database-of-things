# Curator Agent Architecture Plan - FINAL

**Status**: ✅ Validated & Ready for Implementation
**Date**: November 2, 2025
**Version**: 1.0 (Incorporating technical validation feedback)

---

## Changelog from v0.2

**Architecture Enhancements:**
- ✅ Added DeepAgents 0.2 composite backend for persistent memory across sessions
- ✅ Implemented tiered Mem0 memory strategy with importance scoring
- ✅ Comprehensive database indexing strategy for 100K+ entities
- ✅ Structured progress event system
- ✅ Self-hosted LangGraph Platform deployment configuration
- ✅ Token cost monitoring and budget management
- ✅ Memory collision prevention strategy
- ✅ Rate limiting with exponential backoff
- ✅ Comprehensive error logging framework

**Validation Results:**
- ✅ Technology stack validated against current releases
- ✅ Architecture patterns align with agentic best practices
- ✅ MVP readiness confirmed
- ✅ Database strategy validated for scale

---

## Table of Contents

1. [Technology Stack (Validated)](#technology-stack-validated)
2. [Enhanced System Architecture](#enhanced-system-architecture)
3. [DeepAgents Configuration (Enhanced)](#deepagents-configuration-enhanced)
4. [Mem0 Memory Strategy (Tiered)](#mem0-memory-strategy-tiered)
5. [Database Indexing Strategy](#database-indexing-strategy)
6. [Structured Progress Monitoring](#structured-progress-monitoring)
7. [Self-Hosted Deployment](#self-hosted-deployment)
8. [MVP Success Factors](#mvp-success-factors)
9. [Potential Challenges & Mitigations](#potential-challenges--mitigations)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Technology Stack (Validated)

### Core Technologies

| Technology | Version | Purpose | Validation Status |
|-----------|---------|---------|------------------|
| **DeepAgents** | 0.2+ | Agent framework with planning, filesystem, subagents | ✅ Validated - Built on LangGraph, designed for autonomous long-running agents |
| **Mem0** | Latest | Intelligent memory with auto-pruning | ✅ Validated - 26% better accuracy, 91% faster than alternatives |
| **LangGraph Platform** | Self-Hosted Enterprise | Workflow engine, cron scheduling | ✅ Validated - Supports self-hosted with full control |
| **Supabase** | Current | PostgreSQL database, storage | ✅ Validated - Scales to millions of entities |
| **PostgreSQL** | 15+ | RDBMS | ✅ Validated - BRIN indexes, CONCURRENTLY operations |
| **LangSmith** | Current | Observability, secrets | ✅ Validated - Native integration |

### Key Validations

**DeepAgents 0.2 Release (October 2025):**
- Pluggable backend abstraction
- Composite backends for persistent filesystem
- S3, local filesystem, and LangGraph Store support
- Native LangChain/LangGraph integration

**Mem0 Capabilities:**
- Automatic memory pruning with decay
- Relevance + importance + recency scoring
- Category-based protection
- Native LangChain integration
- Multi-backend support (PostgreSQL, MongoDB, etc.)

**LangGraph Platform:**
- Self-Hosted Enterprise available
- Cron job scheduling
- Webhook triggers
- Multi-step workflow execution
- Horizontal scaling support

---

## Enhanced System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│         LangGraph Platform (Self-Hosted Enterprise)                 │
│  - Docker-based deployment (horizontal scaling)                     │
│  - Cron scheduling with distributed execution                       │
│  - Redis for state management                                       │
│  - PostgreSQL for checkpointing                                     │
│  - LangSmith integration for observability                          │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Curator Agent Layer                              │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ DeepAgent (with Composite Backend)                         │   │
│  │  - Base prompt + runtime instructions                      │   │
│  │  - Mem0 client (tiered memory strategy)                   │   │
│  │  - Virtual filesystem (S3-backed for persistence)         │   │
│  │  - Planning & todo tracking                               │   │
│  │  - Subagent spawning                                      │   │
│  │  - Progress event emission                                │   │
│  │  - Token budget tracking                                  │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  Memory Layer (Mem0)                                │
│  - Tiered importance scoring                                        │
│  - Protected categories (never pruned)                              │
│  - Auto-pruned categories (decay over time)                         │
│  - Namespace isolation per curator                                  │
│  - Relevance-based retrieval                                        │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Collection-Agnostic Utilities                          │
│  - Entity manager (batch operations)                                │
│  - Image handler (with rate limiting)                               │
│  - Thumbnail generator (synchronous for rate limit control)         │
│  - Relationship builder (with validation)                           │
│  - Progress tracker (structured events)                             │
│  - Error logger (comprehensive with context)                        │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  Data Storage Layer                                 │
│  Supabase (PostgreSQL):                                             │
│  - Composite indexes for collection queries                         │
│  - Partial indexes for active entities                              │
│  - Covering indexes for relationship lookups                        │
│  - BRIN indexes for time-series data                                │
│  - Concurrent index creation (non-blocking)                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## DeepAgents Configuration (Enhanced)

### Composite Backend for Persistence

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, LocalBackend, S3Backend
from mem0 import MemoryClient
import os

# Composite backend: local for speed, S3 for persistence
backend = CompositeBackend(
    base=LocalBackend(),
    mappings={
        "/memories/": S3Backend(
            bucket="curator-memories",
            region="us-east-1",
            credentials={
                "access_key": os.getenv("AWS_ACCESS_KEY"),
                "secret_key": os.getenv("AWS_SECRET_KEY")
            }
        ),
        "/workflows/": S3Backend(
            bucket="curator-workflows",
            region="us-east-1"
        )
    }
)

# Mem0 client with tiered strategy
mem0_client = MemoryClient(
    api_key=os.getenv("MEM0_API_KEY"),
    host=os.getenv("MEM0_HOST", "https://api.mem0.ai")
)

# Enhanced curator agent
curator_agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",

    # Persistent backend across sessions
    backend=backend,

    # System prompt
    system_prompt=user_base_prompt + """

    You have access to:
    - Planning tools (write_todos, mark_complete)
    - Persistent filesystem (scripts saved to S3)
    - Subagent spawning
    - Tiered memory via Mem0:
      * Protected memories (importance=1.0): Never pruned
      * Strategic memories (importance=0.7): Decay over time
      * Temporary memories (importance=0.3): Pruned aggressively
    - Collection utilities with rate limiting
    - Progress event emission (structured)
    - Token budget tracking

    Token Budget: 1M tokens/day
    Current Usage: {token_usage}/1,000,000

    Your workflow:
    1. Check token budget (abort if exceeded)
    2. Retrieve high-importance memories from Mem0
    3. Plan import with rate-limit awareness
    4. Request approval (local dev only)
    5. Execute with progress events
    6. Store successes (with importance scores)
    7. Delete failures immediately
    8. Update token usage
    """,

    # Enable all features
    use_longterm_memory=True,
    use_filesystem=True,
    use_subagents=True,
    use_planning=True,

    # Mem0 integration
    memory_client=mem0_client,
    memory_user_id=f"curator-{collection_id}",

    # Tools
    tools=[
        # Collection-agnostic
        create_entity_tool,
        create_relationship_tool,
        download_and_thumbnail_tool,

        # Monitoring
        emit_progress_tool,
        check_token_budget_tool,
        log_error_tool,

        # Approval
        request_approval_tool,

        # Data sources (with rate limiting)
        fetch_from_api_tool,  # Includes exponential backoff
        scrape_webpage_tool,  # Includes rate limiting
        validate_data_tool,
    ],

    # Token tracking
    callbacks=[TokenCounterCallback()],
)
```

---

## Mem0 Memory Strategy (Tiered)

### Importance-Based Tiering

**Protected Tier (importance=1.0)** - Never auto-pruned:
```python
# Collection structure - permanent
mem0.add(
    messages=[{
        "role": "assistant",
        "content": "Pokemon TCG organized as: Era → Series → Set → Card"
    }],
    user_id="curator-pokemon-tcg",
    metadata={
        "category": "collection_structure",
        "importance": 1.0,  # Protected from pruning
        "protected": True,
        "created_at": datetime.now().isoformat()
    }
)

# API credentials - permanent
mem0.add(
    messages=[{
        "role": "assistant",
        "content": "pokemontcg.io API: X-Api-Key header, rate limit 1000/hr"
    }],
    user_id="curator-pokemon-tcg",
    metadata={
        "category": "api_credentials",
        "importance": 1.0,
        "protected": True
    }
)

# Metadata schema - permanent
mem0.add(
    messages=[{
        "role": "assistant",
        "content": "Card entities require: name, number, rarity, hp, type"
    }],
    user_id="curator-pokemon-tcg",
    metadata={
        "category": "metadata_schema",
        "importance": 1.0,
        "protected": True
    }
)
```

**Strategic Tier (importance=0.7)** - Decays slowly, keeps successful patterns:
```python
# Successful import strategy
mem0.add(
    messages=[{
        "role": "assistant",
        "content": "Base Set import via pokemontcg.io API: 102 cards, 98% success, 120s runtime"
    }],
    user_id="curator-pokemon-tcg",
    metadata={
        "category": "strategy",
        "importance": 0.7,  # Will decay if not used
        "success_rate": 0.98,
        "last_used": datetime.now().isoformat(),
        "usage_count": 1,
        "avg_runtime_seconds": 120
    }
)

# Data source reliability
mem0.add(
    messages=[{
        "role": "assistant",
        "content": "pokemontcg.io API reliability: 99.5%, occasional timeout on large sets"
    }],
    user_id="curator-pokemon-tcg",
    metadata={
        "category": "data_source",
        "importance": 0.7,
        "reliability": 0.995,
        "quirks": ["timeout_on_large_sets"]
    }
)
```

**Tactical Tier (importance=0.3)** - Pruned aggressively:
```python
# Temporary execution notes
mem0.add(
    messages=[{
        "role": "assistant",
        "content": "Currently importing Scarlet & Violet series, 45/100 sets complete"
    }],
    user_id="curator-pokemon-tcg",
    metadata={
        "category": "execution_state",
        "importance": 0.3,  # Will be pruned quickly
        "temporary": True
    }
)
```

### Memory Update on Success

```python
def record_success(strategy_id: str, execution_result: dict):
    # Increment usage, boost importance slightly
    existing_memory = mem0.get(strategy_id, user_id="curator-pokemon-tcg")

    new_importance = min(
        existing_memory.metadata["importance"] + 0.05,
        0.9  # Cap below protected tier
    )

    mem0.update(
        memory_id=strategy_id,
        user_id="curator-pokemon-tcg",
        metadata={
            **existing_memory.metadata,
            "importance": new_importance,
            "usage_count": existing_memory.metadata["usage_count"] + 1,
            "last_used": datetime.now().isoformat(),
            "success_rate": calculate_new_success_rate(existing_memory, execution_result)
        }
    )
```

### Memory Deletion on Failure

```python
def record_failure(strategy_id: str, error: str):
    # Delete immediately (user decision from architecture review)
    mem0.delete(
        memory_id=strategy_id,
        user_id="curator-pokemon-tcg"
    )

    # Log for manual review (comprehensive error logging)
    logger.error(
        "Strategy failed and deleted from memory",
        extra={
            "curator": "pokemon-tcg",
            "strategy_id": strategy_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
    )
```

---

## Database Indexing Strategy

### For 100K+ Entities

```sql
-- Composite index for collection hierarchy queries
-- Optimizes: SELECT * FROM entities WHERE collection_id = X AND entity_type = Y ORDER BY created_at DESC
CREATE INDEX CONCURRENTLY idx_entities_collection_type
ON entities(collection_id, entity_type, created_at DESC);

-- Partial index for active entities only (excludes soft-deleted)
-- Optimizes: SELECT * FROM entities WHERE collection_id = X AND name LIKE '%...' AND deleted_at IS NULL
CREATE INDEX CONCURRENTLY idx_entities_active
ON entities(collection_id, name)
WHERE deleted_at IS NULL;

-- Covering index for relationship lookups (includes commonly-queried columns)
-- Optimizes: SELECT relationship_type, attributes FROM relationships WHERE from_entity_id = X AND to_entity_id = Y
CREATE INDEX CONCURRENTLY idx_relationships_lookup
ON relationships(from_entity_id, to_entity_id)
INCLUDE (relationship_type, attributes);

-- BRIN index for time-series data (very space efficient, good for large tables)
-- Optimizes: SELECT * FROM entities WHERE created_at > '2025-01-01'
CREATE INDEX idx_entities_created_brin
ON entities USING BRIN(created_at);

-- GIN index for JSONB attributes (already in original schema, validated)
CREATE INDEX idx_entities_attributes
ON entities USING GIN(attributes);

-- Composite index for relationship traversal with type filtering
-- Optimizes: SELECT * FROM relationships WHERE from_entity_id = X AND relationship_type = 'contains'
CREATE INDEX CONCURRENTLY idx_relationships_from_type
ON relationships(from_entity_id, relationship_type)
INCLUDE (to_entity_id, order, attributes);

-- Reverse relationship traversal
-- Optimizes: SELECT * FROM relationships WHERE to_entity_id = X AND relationship_type = 'contains'
CREATE INDEX CONCURRENTLY idx_relationships_to_type
ON relationships(to_entity_id, relationship_type)
INCLUDE (from_entity_id, order, attributes);
```

### Index Maintenance

```sql
-- Monitor index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;

-- Identify unused indexes (consider dropping)
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND schemaname = 'public';

-- Rebuild indexes if bloated (run during maintenance window)
REINDEX INDEX CONCURRENTLY idx_entities_collection_type;
```

### Query Optimization Examples

```sql
-- GOOD: Uses idx_entities_collection_type
EXPLAIN ANALYZE
SELECT * FROM entities
WHERE collection_id = 'pokemon-tcg'
    AND entity_type = 'card'
ORDER BY created_at DESC
LIMIT 100;

-- GOOD: Uses idx_entities_active (partial index)
EXPLAIN ANALYZE
SELECT * FROM entities
WHERE collection_id = 'pokemon-tcg'
    AND name ILIKE '%charizard%'
    AND deleted_at IS NULL;

-- GOOD: Uses idx_relationships_from_type with INCLUDE columns
EXPLAIN ANALYZE
SELECT to_entity_id, relationship_type, attributes
FROM relationships
WHERE from_entity_id = 'set-base1'
    AND relationship_type = 'contains'
ORDER BY order ASC;
```

---

## Structured Progress Monitoring

### Progress Event Schema

```python
from typing import Literal, Optional
from pydantic import BaseModel
from datetime import datetime

class ProgressEvent(BaseModel):
    """Structured progress event for real-time monitoring"""

    # Event identification
    run_id: str
    curator_id: str
    timestamp: datetime

    # Progress phase
    phase: Literal[
        "planning",
        "approval_requested",
        "fetching",
        "downloading",
        "thumbnail_generation",
        "entity_creation",
        "relationship_building",
        "validation",
        "memory_update",
        "complete",
        "error"
    ]

    # Human-readable message
    message: str

    # Quantitative metrics
    metrics: Optional[dict] = None  # {current, total, percentage}

    # Phase-specific metadata
    metadata: Optional[dict] = None

    # Error details (if phase="error")
    error: Optional[dict] = None

class ProgressTracker:
    def __init__(self, run_id: str, curator_id: str):
        self.run_id = run_id
        self.curator_id = curator_id

    def emit(
        self,
        phase: str,
        message: str,
        current: Optional[int] = None,
        total: Optional[int] = None,
        metadata: Optional[dict] = None,
        error: Optional[dict] = None
    ):
        event = ProgressEvent(
            run_id=self.run_id,
            curator_id=self.curator_id,
            timestamp=datetime.now(),
            phase=phase,
            message=message,
            metrics={
                "current": current,
                "total": total,
                "percentage": int((current / total) * 100) if (current and total) else None
            } if current else None,
            metadata=metadata or {},
            error=error
        )

        # Emit to LangGraph state for streaming
        return {"progress_events": [event.dict()]}

    def planning(self, todos_count: int):
        return self.emit(
            phase="planning",
            message=f"Created plan with {todos_count} todos",
            metadata={"todos_count": todos_count}
        )

    def fetching(self, source: str, current: int, total: int):
        return self.emit(
            phase="fetching",
            message=f"Fetching from {source}",
            current=current,
            total=total,
            metadata={"source": source}
        )

    def downloading(self, item_name: str, current: int, total: int):
        return self.emit(
            phase="downloading",
            message=f"Downloading: {item_name}",
            current=current,
            total=total,
            metadata={"item_name": item_name}
        )

    def thumbnail_generation(self, current: int, total: int, size_reduction_pct: float):
        return self.emit(
            phase="thumbnail_generation",
            message=f"Generating thumbnails",
            current=current,
            total=total,
            metadata={
                "size_reduction_pct": size_reduction_pct,
                "avg_savings": f"{size_reduction_pct:.1f}%"
            }
        )

    def entity_creation(self, entity_type: str, current: int, total: int):
        return self.emit(
            phase="entity_creation",
            message=f"Creating {entity_type} entities",
            current=current,
            total=total,
            metadata={"entity_type": entity_type}
        )

    def error(self, error_message: str, context: dict):
        return self.emit(
            phase="error",
            message=error_message,
            error={
                "message": error_message,
                "context": context,
                "traceback": context.get("traceback")
            }
        )

    def complete(self, summary: dict):
        return self.emit(
            phase="complete",
            message="Import completed successfully",
            metadata=summary
        )
```

### CLI Progress Display

```bash
$ curators run pokemon-tcg --watch

🚀 Starting Pokemon TCG Curator (run_id: abc123)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[14:30:15] Phase: Planning
           ✓ Created plan with 5 todos

[14:30:20] Phase: Fetching
           [████████████████░░░░░░░░] 68% | 70/102 cards
           Fetching from pokemontcg.io API

[14:30:45] Phase: Downloading
           [████████████████████░░░░] 85% | 87/102 images
           Downloading: Charizard #4/102

[14:31:10] Phase: Thumbnail Generation
           [██████████████████████░░] 95% | 97/102 thumbnails
           Average size reduction: 97.6%

[14:31:30] Phase: Entity Creation
           [████████████████████████] 100% | 102/102 cards
           Creating card entities

[14:31:45] Phase: Complete
           ✅ Import completed successfully

           Summary:
           • Cards imported: 102
           • Success rate: 100%
           • Runtime: 90 seconds
           • Storage savings: 97.6% (thumbnails)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Self-Hosted Deployment

### Docker Compose Configuration

```yaml
# docker-compose.yml for self-hosted LangGraph Platform
version: '3.8'

services:
  # LangGraph API Server
  langgraph-api:
    build: .
    image: curator-agents:latest
    ports:
      - "8000:8000"
    environment:
      # LangGraph Platform
      REDIS_URI: redis://redis:6379
      POSTGRES_URI: postgresql://postgres:${DB_PASSWORD}@postgres:5432/curators
      LANGGRAPH_LICENSE_KEY: ${LANGGRAPH_LICENSE_KEY}

      # Memory & Observability
      MEM0_API_KEY: ${MEM0_API_KEY}
      MEM0_HOST: ${MEM0_HOST:-https://api.mem0.ai}
      LANGSMITH_API_KEY: ${LANGSMITH_API_KEY}
      LANGSMITH_TRACING: "true"

      # Supabase
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY}

      # Storage (S3 for persistent filesystem)
      AWS_ACCESS_KEY: ${AWS_ACCESS_KEY}
      AWS_SECRET_KEY: ${AWS_SECRET_KEY}
      S3_BUCKET_MEMORIES: curator-memories
      S3_BUCKET_WORKFLOWS: curator-workflows

    deploy:
      replicas: 3  # Horizontal scaling
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

    depends_on:
      - redis
      - postgres

  # Redis for state management
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

  # PostgreSQL for checkpointing
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: curators
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data

  # Nginx load balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - langgraph-api

volumes:
  redis-data:
  postgres-data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node.js (for collection-agnostic utilities)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Copy application code
COPY . .

# Install Node.js utilities
WORKDIR /app/scripts/toolkit
RUN npm install
WORKDIR /app/scripts/thumbnails
RUN npm install
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run LangGraph server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## MVP Success Factors

### Critical Success Criteria

**Phase 1 (Foundation):**
- [ ] Collection-agnostic utilities tested and working
- [ ] Mem0 integration storing/retrieving memories correctly
- [ ] Tiered importance scoring functioning as designed
- [ ] Database indexes created (use CONCURRENTLY)
- [ ] Progress tracker emitting structured events
- [ ] Token budget tracking operational

**Phase 2 (Reference Curator):**
- [ ] Pokemon TCG curator successfully imports Base Set (102 cards)
- [ ] All images and thumbnails generated (100% success rate)
- [ ] Mem0 auto-pruning maintains optimal memory size
- [ ] Manual approval workflow functions correctly
- [ ] Real-time progress displays in CLI
- [ ] Token usage stays within budget

**Phase 3 (Scaling):**
- [ ] 3+ curators running independently
- [ ] Scheduled runs execute autonomously
- [ ] No memory collision between curators
- [ ] Rate limiting prevents API blocks
- [ ] Self-hosted deployment stable

**Phase 4 (Optimization):**
- [ ] Query performance <100ms for typical lookups
- [ ] Database handles 100K+ entities efficiently
- [ ] Curators improve success rates over time

### Key Metrics to Monitor

**Performance Metrics:**
```python
# Track per curator
{
    "curator_id": "pokemon-tcg",
    "metrics": {
        "success_rate": 0.98,
        "avg_runtime_seconds": 120,
        "items_per_second": 0.85,
        "token_usage_per_run": 45000,
        "memory_retrieval_time_ms": 15,
        "db_query_time_ms": 30
    }
}
```

**Memory Metrics:**
```python
# Monitor Mem0 health
{
    "curator_id": "pokemon-tcg",
    "memory_stats": {
        "total_memories": 47,
        "protected_memories": 12,
        "auto_pruned_memories": 5,
        "avg_relevance_score": 0.78,
        "retrieval_accuracy": 0.95
    }
}
```

**Database Metrics:**
```sql
-- Monitor query performance
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;

-- Monitor index hit ratio (should be >99%)
SELECT
    sum(idx_blks_hit) / nullif(sum(idx_blks_hit + idx_blks_read), 0) AS index_hit_ratio
FROM pg_statio_user_indexes;
```

### Logging Strategy

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Comprehensive error logging
def log_error(curator_id: str, phase: str, error: Exception, context: dict):
    logger.error(
        "Curator execution error",
        curator_id=curator_id,
        phase=phase,
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        traceback=traceback.format_exc()
    )

# Performance logging
def log_performance(curator_id: str, metrics: dict):
    logger.info(
        "Curator performance",
        curator_id=curator_id,
        **metrics
    )
```

---

## Potential Challenges & Mitigations

### 1. Token Costs

**Challenge:** Multiple curators running daily could consume millions of tokens

**Mitigation:**
```python
class TokenBudgetManager:
    def __init__(self, daily_limit: int = 1_000_000):
        self.daily_limit = daily_limit
        self.redis_client = redis.Redis()

    def check_budget(self, curator_id: str, estimated_tokens: int) -> bool:
        today = datetime.now().date().isoformat()
        key = f"token_usage:{curator_id}:{today}"

        current_usage = int(self.redis_client.get(key) or 0)

        if current_usage + estimated_tokens > self.daily_limit:
            logger.warning(
                "Token budget exceeded",
                curator_id=curator_id,
                current_usage=current_usage,
                daily_limit=self.daily_limit
            )
            return False

        return True

    def record_usage(self, curator_id: str, tokens_used: int):
        today = datetime.now().date().isoformat()
        key = f"token_usage:{curator_id}:{today}"

        self.redis_client.incrby(key, tokens_used)
        self.redis_client.expire(key, 86400 * 7)  # Keep 7 days history
```

### 2. Memory Collision

**Challenge:** Mem0 user_ids must be unique to prevent cross-contamination

**Mitigation:**
```python
# Strict namespace isolation
def get_memory_user_id(curator_id: str, environment: str = "production") -> str:
    """Generate guaranteed-unique Mem0 user ID"""
    # Format: curator-{id}-{env}-{instance_id}
    instance_id = hashlib.md5(
        f"{curator_id}-{environment}".encode()
    ).hexdigest()[:8]

    return f"curator-{curator_id}-{environment}-{instance_id}"

# Validation
def validate_memory_isolation():
    curators = ["pokemon-tcg", "mmpr-toys", "marvel-comics"]
    user_ids = [get_memory_user_id(c) for c in curators]

    # Ensure no collisions
    assert len(user_ids) == len(set(user_ids)), "Memory user ID collision detected!"
```

### 3. Rate Limiting

**Challenge:** APIs and websites will block if requests are too frequent

**Mitigation:**
```python
import time
from functools import wraps

def rate_limited(max_per_second: float = 1.0):
    """Decorator for rate-limited API calls with exponential backoff"""
    min_interval = 1.0 / max_per_second

    def decorator(func):
        last_called = [0.0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed

            if left_to_wait > 0:
                time.sleep(left_to_wait)

            # Exponential backoff on failure
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    last_called[0] = time.time()
                    return result
                except RateLimitError as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = 2 ** attempt  # Exponential: 1s, 2s, 4s
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)

        return wrapper
    return decorator

# Usage
@rate_limited(max_per_second=0.5)  # Max 0.5 requests/second (2 second interval)
def fetch_from_api(endpoint: str):
    response = requests.get(endpoint)
    if response.status_code == 429:
        raise RateLimitError("API rate limit exceeded")
    return response.json()
```

### 4. Error Recovery

**Challenge:** No auto-retry, but need comprehensive logging for manual review

**Mitigation:**
```python
class ErrorRecoveryManager:
    def __init__(self, curator_id: str):
        self.curator_id = curator_id

    def log_for_manual_review(
        self,
        phase: str,
        error: Exception,
        context: dict,
        recovery_suggestion: str
    ):
        """Comprehensive error logging for manual intervention"""

        error_report = {
            "curator_id": self.curator_id,
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "traceback": traceback.format_exc(),
            "recovery_suggestion": recovery_suggestion,

            # Contextual information
            "memory_state": self.get_memory_snapshot(),
            "recent_actions": self.get_recent_actions(),
            "environment": {
                "python_version": sys.version,
                "dependencies": self.get_dependency_versions()
            }
        }

        # Log to file
        with open(f"errors/{self.curator_id}-{datetime.now().date()}.jsonl", "a") as f:
            f.write(json.dumps(error_report) + "\n")

        # Log to LangSmith for observability
        langsmith.log_error(error_report)

        # Store in dedicated error collection (optional)
        supabase.table("curator_errors").insert(error_report)

        return error_report
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Week 1:**
- [ ] Set up self-hosted LangGraph Platform (Docker Compose)
- [ ] Configure Mem0 with tiered strategy
- [ ] Implement collection-agnostic utilities:
  - [ ] Entity manager with batch operations
  - [ ] Image handler with rate limiting
  - [ ] Relationship builder with validation
  - [ ] Structured progress tracker

**Week 2:**
- [ ] Create database indexes (use CONCURRENTLY)
- [ ] Implement token budget tracking
- [ ] Set up comprehensive error logging
- [ ] Build curator CLI (basic commands)
- [ ] Implement curator setup wizard

**Deliverables:**
- Working utilities (tested with sample data)
- Mem0 storing/retrieving with correct importance scores
- Database indexes in place
- CLI wizard functional

---

### Phase 2: Reference Implementation (Weeks 3-4)

**Week 3:**
- [ ] Create Pokemon TCG curator via wizard
- [ ] Implement DeepAgent with composite backend
- [ ] Build pokemontcg.io API integration
- [ ] Add real-time progress monitoring
- [ ] Implement manual approval workflow

**Week 4:**
- [ ] Test import of Pokemon Base Set (102 cards)
- [ ] Verify all thumbnails generated
- [ ] Validate Mem0 auto-pruning behavior
- [ ] Monitor token usage
- [ ] Performance testing (query times)

**Deliverables:**
- Pokemon TCG curator successfully imports Base Set
- Real-time progress displays correctly
- Approval workflow functions
- Token budget respected
- Queries <100ms

---

### Phase 3: Scaling (Weeks 5-6)

**Week 5:**
- [ ] Create MMPR toys curator (scraping-based)
- [ ] Create Marvel Comics curator (API-based)
- [ ] Set up cron scheduling for all curators
- [ ] Implement memory isolation validation
- [ ] Enhance CLI with all commands

**Week 6:**
- [ ] Test concurrent curator execution
- [ ] Validate memory isolation (no collisions)
- [ ] Monitor rate limiting effectiveness
- [ ] Document Claude Code skill
- [ ] Production deployment testing

**Deliverables:**
- 3+ curators running independently
- Scheduled runs executing successfully
- No memory collisions observed
- CLI fully functional
- Skill documented

---

### Phase 4: Optimization (Weeks 7-8)

**Week 7:**
- [ ] Performance profiling at scale (100K+ entities)
- [ ] Optimize slow queries
- [ ] Tune Mem0 pruning thresholds
- [ ] Implement adaptive learning improvements

**Week 8:**
- [ ] Load testing (multiple curators + scheduled runs)
- [ ] Index maintenance procedures
- [ ] Monitoring dashboard setup
- [ ] Final documentation

**Deliverables:**
- System handles 100K+ entities efficiently
- Query performance optimized
- Curators improving over time
- Complete documentation

---

**END OF FINAL ARCHITECTURE PLAN v1.0**

*✅ Validated by technical research*
*✅ Enhanced with best practices*
*✅ Ready for Phase 1 implementation*

**Next Step:** Begin Phase 1, Week 1 - Set up self-hosted LangGraph Platform 🚀
