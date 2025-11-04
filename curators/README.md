# Collectible Curators

Autonomous agents for discovering, scraping, and importing collectibles into the graph database.

## Overview

Curators are AI agents powered by **DeepAgents** and **LangGraph** that autonomously manage collection imports. Each curator is assigned to a single collection (e.g., Pokémon TCG, Power Rangers toys) and learns the best strategies for importing items over time.

### Key Features

- **🤖 Autonomous Operation**: Curators discover, scrape, and import items with minimal supervision
- **🧠 Long-Term Memory**: Powered by Mem0 with tiered importance strategy
- **📊 Real-Time Progress**: Structured event system for monitoring
- **💰 Token Budget Management**: Automatic cost control with daily limits
- **⚡ Rate Limiting**: Built-in rate limiting with exponential backoff
- **🎨 Collection-Agnostic**: Reusable utilities for any collectible type
- **🔒 Self-Hosted**: Complete control over infrastructure and data

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Curator CLI                          │
│         (Setup, Run, Monitor, Budget)                   │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                 LangGraph Platform                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  DeepAgents  │  │  LangGraph   │  │   Mem0       │ │
│  │   (Core)     │  │  (Workflows) │  │  (Memory)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│              Collection Utilities                       │
│  • Supabase Client  • Image Processor                  │
│  • Rate Limiter     • Token Budget                      │
│  • Progress Events  • Memory Manager                    │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                  Supabase Database                      │
│         (Entities, Relationships, Storage)              │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Supabase (local or cloud)
- OpenAI API key

### 1. Installation

```bash
cd curators

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
vim .env
```

### 2. Start Services

```bash
# Start LangGraph Platform, Redis, and Qdrant
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 3. Apply Database Migrations

```bash
# From project root
cd ..
./scripts/safe-migrate push
```

This applies the curator-optimized database indexes.

### 4. Create Your First Curator

```bash
# Interactive setup wizard
curator setup

# Follow the prompts to configure your curator
```

### 5. Run the Curator

```bash
# Run a curator
curator run pokemon-tcg

# Run with custom instructions
curator run pokemon-tcg --instructions "Import only cards from 2023"

# Dry run (no changes)
curator run pokemon-tcg --dry-run
```

## CLI Commands

### `curator setup`

Interactive wizard for creating new curators.

Guides you through:
1. Collection naming and type
2. Base prompt/instructions
3. API credentials (optional)
4. Initial memory setup
5. Schedule configuration (optional)

### `curator list`

List all configured curators with status.

```bash
curator list
```

### `curator run <curator-id>`

Run a curator agent.

```bash
# Basic run
curator run pokemon-tcg

# With runtime instructions
curator run pokemon-tcg --instructions "Focus on Base Set only"

# Dry run (no changes)
curator run pokemon-tcg --dry-run
```

### `curator status <curator-id>`

Check curator status and statistics.

```bash
curator status pokemon-tcg
```

### `curator budget <curator-id>`

View token budget and usage.

```bash
curator budget pokemon-tcg
```

### `curator init`

Initialize curator environment (create .env, check services).

```bash
curator init
```

## Configuration

### Environment Variables

See `.env.example` for all configuration options:

- **Supabase**: Database and storage credentials
- **OpenAI**: API key for LLM calls
- **Mem0**: Memory system configuration
- **Redis**: Rate limiting and caching
- **AWS S3**: Persistent storage for DeepAgents (optional)
- **Token Budget**: Daily limits and thresholds
- **Rate Limiting**: API call throttling

### Curator Configuration

Curators are configured in `config/curators/{curator-id}.json`:

```json
{
  "curator_id": "pokemon-tcg",
  "collection_name": "Pokémon Trading Card Game",
  "collection_type": "cards",
  "base_prompt": "You are a curator for Pokémon TCG...",
  "api_credentials": {
    "pokemontcg_api": "your-api-key"
  },
  "initial_memories": [
    {
      "content": "Use pokemontcg.io API for card data",
      "category": "strategy"
    }
  ],
  "schedule": "0 2 * * *"
}
```

### Mem0 Configuration

Memory system is configured in `config/mem0_config.json`:

- **LLM**: Model for memory operations
- **Embedder**: Embedding model
- **Vector Store**: Qdrant configuration
- **Custom Prompt**: Memory management instructions

## Collection-Agnostic Utilities

The curator framework provides reusable utilities for any collection type:

### Supabase Client

```python
from utilities.supabase_client import SupabaseClient

client = SupabaseClient()

# Create entity
entity_id = await client.create_entity(
    name="Charizard",
    entity_type="card",
    year=1999,
    attributes={"hp": 120}
)

# Create relationship
await client.create_relationship(
    from_id=collection_id,
    to_id=entity_id,
    relationship_type="contains"
)
```

### Image Processor

```python
from utilities.image_processor import ImageProcessor

processor = ImageProcessor()

# Download and upload with thumbnail
image_url, thumbnail_url = await processor.download_and_upload(
    url="https://example.com/charizard.jpg",
    generate_thumbnail=True
)
```

### Rate Limiter

```python
from utilities.rate_limiter import api_call
import httpx

@api_call("pokemontcg_api", exception_types=(httpx.HTTPError,))
async def fetch_cards(curator_id: str):
    # Automatically rate-limited with exponential backoff
    response = await client.get("https://api.pokemontcg.io/v2/cards")
    return response.json()
```

### Token Budget

```python
from utilities.token_budget import check_and_record_tokens

# Check budget before operation
await check_and_record_tokens(
    curator_id="pokemon-tcg",
    estimated_tokens=5000,
    actual_tokens=4800  # After operation completes
)
```

### Progress Events

```python
from utilities.progress import ProgressEmitter

emitter = ProgressEmitter(run_id="run-123", curator_id="pokemon-tcg")

# Emit structured events
emitter.emit_fetching("Fetching cards from API", url="https://api.pokemontcg.io")
emitter.emit_downloading("Downloading images", total=100, completed=50)
emitter.emit_database("Creating entities", entities=100)
emitter.emit_complete("Import complete", entities=100, tokens=50000)
```

### Memory Manager

```python
from core.memory import TieredMemoryManager

memory = TieredMemoryManager(curator_id="pokemon-tcg")

# Protected memory (never pruned)
memory.add_collection_structure("Pokemon TCG", {
    "type": "trading_cards",
    "hierarchy": ["franchise", "game", "expansion", "card"]
})

# Strategic memory (decays slowly)
memory.add_strategy(
    "api_import",
    "Use pokemontcg.io API for complete card data",
    success_rate=0.98
)

# Tactical memory (pruned aggressively)
memory.add_execution_state({"current_page": 5, "total_pages": 20})
```

## Database Indexes

Curator-optimized indexes are applied via migration `20251103000000_add_curator_indexes.sql`:

- **Composite indexes**: Optimize hierarchy queries
- **Covering indexes**: Reduce heap fetches
- **BRIN indexes**: Space-efficient time-series queries
- **GIN indexes**: Fast JSONB attribute searches
- **Partial indexes**: Targeted optimization (e.g., entities needing thumbnails)

All indexes are created with `CONCURRENTLY` to avoid locking.

## Development

### Project Structure

```
curators/
├── cli/                    # CLI commands
│   ├── main.py            # Entry point
│   └── setup_wizard.py    # Interactive setup
├── core/                  # Core functionality
│   ├── config.py          # Configuration management
│   └── memory.py          # Tiered memory system
├── utilities/             # Collection-agnostic utilities
│   ├── supabase_client.py # Database operations
│   ├── image_processor.py # Image downloading/processing
│   ├── rate_limiter.py    # Rate limiting + backoff
│   ├── token_budget.py    # Budget management
│   └── progress.py        # Progress event system
├── workflows/             # LangGraph workflows (to be created)
├── config/                # Configuration files
│   ├── mem0_config.json   # Mem0 configuration
│   └── curators/          # Per-curator configs
├── docker-compose.yml     # Services orchestration
├── pyproject.toml         # Python project config
└── README.md              # This file
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=curators
```

### Code Quality

```bash
# Format code
black curators/

# Lint
ruff check curators/

# Type checking
mypy curators/
```

## Deployment

### Self-Hosted (Docker Compose)

The included `docker-compose.yml` provides a complete self-hosted stack:

- **LangGraph Platform**: Agent orchestration
- **PostgreSQL**: LangGraph state persistence
- **Redis**: Rate limiting, caching, task queue
- **Qdrant**: Vector database for Mem0

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Scaling

For production, consider:

1. **Horizontal scaling**: Multiple LangGraph API replicas
2. **Persistent volumes**: Use named volumes or external storage
3. **Resource limits**: Configure memory/CPU limits in docker-compose.yml
4. **Monitoring**: Add Prometheus + Grafana for observability
5. **Secrets**: Use Docker secrets or external secret management

## Monitoring

### Token Budget

```bash
# Check daily usage
curator budget pokemon-tcg
```

### Service Health

```bash
# Docker services
docker-compose ps

# Individual service logs
docker-compose logs -f langgraph-api
docker-compose logs -f redis
docker-compose logs -f qdrant
```

### Progress Events

Real-time progress is logged to console during curator runs. In production, these events can be sent to:

- Log aggregation (e.g., Loki, ELK)
- Time-series database (e.g., InfluxDB)
- Message queue (e.g., RabbitMQ, Kafka)

## Next Steps

### Phase 1 Complete ✅

- [x] Project structure
- [x] Docker configuration
- [x] Collection-agnostic utilities
- [x] Database indexes
- [x] CLI with setup wizard
- [x] Configuration management

### Phase 2: Reference Curator (Weeks 3-4)

- [ ] Implement Pokemon TCG reference curator
- [ ] Test full workflow end-to-end
- [ ] Refine memory strategies
- [ ] Document best practices

### Phase 3: Multiple Curators (Weeks 5-6)

- [ ] Add scheduling support
- [ ] Implement curator coordination
- [ ] Add approval workflow (manual mode)
- [ ] Create curator dashboard

### Phase 4: Optimization (Weeks 7-8)

- [ ] Performance tuning
- [ ] Memory optimization
- [ ] Cost reduction strategies
- [ ] Production deployment guide

## Troubleshooting

### Services won't start

```bash
# Check Docker
docker-compose ps

# View logs
docker-compose logs

# Restart services
docker-compose restart
```

### Database connection issues

```bash
# Verify Supabase is running
docker ps | grep supabase

# Check connection from curators directory
python -c "from core.config import settings; print(settings.supabase_url)"
```

### Memory not persisting

```bash
# Check Qdrant
curl http://localhost:6333/collections

# View Qdrant logs
docker-compose logs qdrant
```

### Token budget exceeded

```bash
# View current usage
curator budget pokemon-tcg

# Reset budget (for testing only)
redis-cli DEL "token_budget:pokemon-tcg:2024-11-03"
```

## Contributing

This is a self-contained project, but contributions are welcome:

1. Follow existing code structure
2. Use type hints (mypy compatible)
3. Format with Black
4. Add tests for new features
5. Update documentation

## License

See LICENSE file in project root.

## Support

For issues, questions, or feature requests, please file an issue in the project repository.
