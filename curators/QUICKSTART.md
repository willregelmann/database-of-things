# Curator Quickstart

Get your first curator running in 5 minutes.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key
- Supabase (local or cloud)

## Step 1: Install (1 minute)

```bash
cd curators

# Install Python dependencies
pip install -e .

# Initialize environment
curator init
```

This creates `.env` from `.env.example`. Edit it with your credentials:

```bash
vim .env
```

**Minimum required**:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `OPENAI_API_KEY`

## Step 2: Start Services (1 minute)

```bash
# Start LangGraph Platform, Redis, Qdrant
docker-compose up -d

# Verify services
docker-compose ps
```

You should see:
- ✅ curator_langgraph_api
- ✅ curator_langgraph_db
- ✅ curator_redis
- ✅ curator_qdrant

## Step 3: Apply Database Indexes (30 seconds)

```bash
# From project root
cd ..
./scripts/safe-migrate push
```

This applies curator-optimized indexes for fast queries.

## Step 4: Create a Curator (2 minutes)

```bash
cd curators

# Interactive setup wizard
curator setup
```

Example configuration:

```
Curator ID: pokemon-tcg
Collection Name: Pokémon Trading Card Game
Collection Type: cards
Use default prompt? Yes
Add API credentials? Yes
  API Name: pokemontcg_api
  API Key: [your-key]
Add initial memory? No
Enable schedule? No
```

## Step 5: Run Your Curator (30 seconds)

```bash
# Dry run first (no changes)
curator run pokemon-tcg --dry-run

# Real run
curator run pokemon-tcg
```

Watch the real-time progress:

```
[10:30:15] 📋 PLANNING: Analyzing collection structure
[10:30:18] 🌐 FETCHING: Fetching from pokemontcg.io API
[10:30:22] ⬇️ DOWNLOADING: Downloading images (0/100)
[10:30:45] ⚙️ PROCESSING: Processing card data (50/100)
[10:31:10] 💾 DATABASE: Creating entities (100 created)
[10:31:15] 🎉 COMPLETE: Import complete!
```

## Next Steps

### Monitor Your Curator

```bash
# Check status
curator status pokemon-tcg

# View token budget
curator budget pokemon-tcg

# List all curators
curator list
```

### Create More Curators

```bash
curator setup
```

Create curators for:
- Power Rangers toys
- Marvel Comics
- Video games
- Any collectible type!

### Schedule Automatic Runs

Edit `config/curators/pokemon-tcg.json` and add:

```json
{
  "schedule": "0 2 * * *"
}
```

Cron format: `minute hour day month weekday`

Examples:
- `0 2 * * *` - Daily at 2am
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday

### Customize Behavior

Edit the curator's `base_prompt` in `config/curators/pokemon-tcg.json`:

```json
{
  "base_prompt": "You are a Pokemon TCG curator specializing in vintage cards from 1999-2003..."
}
```

### Add Runtime Instructions

```bash
# Override behavior for specific run
curator run pokemon-tcg --instructions "Only import Base Set cards"
```

## Troubleshooting

### "Services not running"

```bash
docker-compose up -d
docker-compose ps
```

### "Database connection failed"

Check Supabase is running:

```bash
# From project root
./bin/supabase status
```

### "Token budget exceeded"

```bash
# Check usage
curator budget pokemon-tcg

# Increase limit in .env
DAILY_TOKEN_LIMIT=2000000
```

### "Rate limit errors"

Adjust rate limiting in `.env`:

```bash
API_RATE_LIMIT_PER_SECOND=0.5
MAX_RETRY_ATTEMPTS=5
```

## Tips

### Dry Run First

Always test with `--dry-run` before real imports:

```bash
curator run pokemon-tcg --dry-run
```

### Monitor Costs

```bash
# Check token usage regularly
curator budget pokemon-tcg
```

### Start Small

Use runtime instructions to limit scope:

```bash
curator run pokemon-tcg --instructions "Import only 10 cards for testing"
```

### Save API Keys Securely

Never commit `.env` to git:

```bash
# Already in .gitignore
echo ".env" >> .gitignore
```

## What's Next?

- **Phase 2**: We'll create a reference Pokemon TCG curator with full workflow
- **Phase 3**: Add scheduling and multiple curator coordination
- **Phase 4**: Production deployment and optimization

See `README.md` for detailed documentation.

## Need Help?

1. Check `README.md` for full documentation
2. View `CURATOR_ARCHITECTURE_FINAL.md` for design details
3. File an issue in the project repository

Happy curating! 🎨
