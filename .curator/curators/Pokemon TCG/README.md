# Pokemon TCG Curator

Autonomous data import agent for Pokemon Trading Card Game cards from pokemontcg.io API.

## Overview

- **Collection:** Pokemon Trading Card Game (all cards, sets, and series)
- **Data Source:** https://github.com/PokemonTCG/pokemon-tcg-data (GitHub repository)
- **Organization:** Hierarchical - Series → Expansion/Set → Card → Variants
- **Deduplication:** `external_ids.pokemontcg_io` (card ID like "base1-4")

## Terms of Service & Attribution

### Compliance Status
✅ **Compliant**

### Compliance Requirements
- **Rate Limits:** 20,000 requests/day (authenticated), 1,000/day (unauthenticated)
- **Commercial Use:** Allowed (requires company/team API key)
- **Attribution Required:** No
- **Linking Requirements:** None
- **Restrictions:** One API key per person/team/company, standard acceptable use

### Attribution Text
```
None required
```

### Compliance Notes
- API is not affiliated with Nintendo or The Pokémon Company
- Data provided "as-is" for informational purposes only
- No guarantees on price or legality data
- ToS reviewed: 2025-11-16
- Source: https://dev.pokemontcg.io/terms

## Setup

### 1. Get API Credentials

1. Visit https://dev.pokemontcg.io
2. Create account
3. Get API key from dashboard

### 2. Configure Secrets

```bash
cd ".curator/curators/Pokemon TCG"
cp secrets.env.example secrets.env
cp secrets.local.env.example secrets.local.env
```

Edit `secrets.env`:
```bash
POKEMONTCG_API_KEY=your_api_key_here
```

Edit `secrets.local.env`:
```bash
COLLECTION_ID=your_local_collection_uuid
```

### 3. Test Fetch via MCP

Use Claude with MCP tools to test the fetch:

```
/curator:run "Pokemon TCG" --limit 10
```

Or via MCP tools directly in Claude Code:
```
mcp__database-of-things-local__run_curator_fetch(name="Pokemon TCG", options={"limit": 10})
mcp__database-of-things-local__validate_curator_data(name="Pokemon TCG")
```

## How It Works

### 1. Fetch (`fetch_data.py`)
- Authenticates with pokemontcg.io API
- Fetches series, sets, and cards in hierarchical structure
- Handles variants (reverse holo, 1st edition, etc.)
- Outputs to `fetched_data.json` in v2 format

### 2. Import (via Claude + MCP)
- Deduplication using `external_ids.pokemontcg_io`
- Entity creation with high-res images
- Hierarchical relationship linking (series → set → card)
- Variant creation
- Embedding generation (automatic)

## Metadata Structure

### Series (type: "collection")

Top-level grouping (e.g., "Scarlet & Violet", "Sun & Moon", "XY"):

```json
{
  "name": "Scarlet & Violet",
  "type": "collection",
  "external_ids": {
    "pokemontcg_io_series": "scarlet-violet"
  },
  "attributes": {}
}
```

### Set/Expansion (type: "collection")

Mid-level grouping within a series:

```json
{
  "name": "Base Set",
  "type": "collection",
  "year": 1999,
  "external_ids": {
    "pokemontcg_io_set": "base1"
  },
  "image_url": "https://images.pokemontcg.io/base1/logo.png",
  "source_url": "https://pokemontcg.io/sets/base1",
  "parent": {
    "type": "collection",
    "external_ids": {
      "pokemontcg_io_series": "original-series"
    }
  },
  "relationship": {
    "type": "contains",
    "order": 1
  },
  "attributes": {
    "total_cards": 102,
    "printed_total": 102,
    "release_date": "1999-01-09"
  }
}
```

### Card (type: "card")

Individual trading card:

```json
{
  "name": "Charizard",
  "type": "card",
  "year": 1999,
  "external_ids": {
    "pokemontcg_io": "base1-4",
    "tcgplayer_id": "1234",
    "cardmarket_id": "5678"
  },
  "image_url": "https://images.pokemontcg.io/base1/4_hires.png",
  "source_url": "https://pokemontcg.io/card/base1-4",
  "parent": {
    "type": "collection",
    "external_ids": {
      "pokemontcg_io_set": "base1"
    }
  },
  "relationship": {
    "type": "contains",
    "order": 4
  },
  "attributes": {
    "rarity": "Rare Holo",
    "artist": "Mitsuhiro Arita"
  }
}
```

### Variant (stored in variants table)

Alternative version of a card:

```json
{
  "variant_of": "card-uuid-here",
  "name": "Reverse Holo",
  "image_url": "https://images.pokemontcg.io/base1/4_hires_reverse.png",
  "attributes": {
    "variant_type": "reverse_holo"
  }
}
```

## Usage Examples

**Via Claude (recommended):**

```bash
# Test with 10 cards
/curator:run "Pokemon TCG" --limit 10

# Fetch specific set
/curator:run "Pokemon TCG" --set "Base Set"

# Fetch entire series
/curator:run "Pokemon TCG" --series "Scarlet & Violet"

# Full import (all cards, all sets, all series)
/curator:run "Pokemon TCG"
```

**Via MCP tools (in Claude Code):**

```
# Test fetch only (no import)
mcp__database-of-things-local__run_curator_fetch(
  name="Pokemon TCG",
  options={"limit": 10, "series": "Base"}
)

# Validate fetched data
mcp__database-of-things-local__validate_curator_data(name="Pokemon TCG")
```

## Troubleshooting

### "API error: Invalid API key"
- Check `POKEMONTCG_API_KEY` in `secrets.env`
- Verify key at https://dev.pokemontcg.io

### "Rate limit exceeded"
- Wait for daily reset or contact API for higher limits
- Current limit: 20,000 requests/day

### "No collection_id found"
- Create collection in database first
- Set `COLLECTION_ID` in `secrets.local.env`

## See Also

- [Curator Best Practices](../../README.md)
- [pokemontcg.io API Documentation](https://docs.pokemontcg.io)
- [pokemontcg.io Developer Portal](https://dev.pokemontcg.io)
