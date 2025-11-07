# Curator Agent System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an agentic curator system where each curator manages a collection, uses conversational discovery to design workflows, generates domain-specific scripts, and runs autonomously on schedule with tools for collection management.

**Architecture:** Direct Anthropic API with tool use for both discovery and execution phases. Generic tools (CuratorTools) provide collection operations, while domain-specific scripts (generated during discovery) handle data fetching. Transaction log enables rollback/resume. No framework lock-in - just Python + Claude API + Supabase.

**Tech Stack:** Python 3.11+, Anthropic SDK, Supabase (PostgreSQL + Storage), Click (CLI), Python-dotenv (secrets)

---

## Prerequisites

Before starting, ensure:
- ✅ Supabase is running (`./bin/supabase start`)
- ✅ Thumbnail generation complete (20,345/20,345)
- ✅ Embedding system operational (100% coverage)
- ✅ Python 3.11+ installed
- ✅ Git worktree created for this feature (if not in main)

---

## Task 1: Database Schema for Curators

**Files:**
- Create: `supabase/migrations/20251106000000_create_curator_tables.sql`

**Step 1: Write migration SQL**

Create migration file with complete schema:

```sql
-- Curator registry
CREATE TABLE curators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    collection_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    config JSONB NOT NULL DEFAULT '{}',
    plan_version INT DEFAULT 1,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'error')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Operation log (for rollback/resume)
CREATE TABLE curator_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curator_id UUID REFERENCES curators(id) ON DELETE CASCADE,
    run_id UUID NOT NULL,
    operation_type TEXT NOT NULL,
    entity_id UUID,
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed', 'rolled_back')),
    data JSONB,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Run history
CREATE TABLE curator_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curator_id UUID REFERENCES curators(id) ON DELETE CASCADE,
    trigger TEXT NOT NULL CHECK (trigger IN ('manual', 'scheduled', 'mini-discovery')),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'rolled_back')),
    operations_count INT DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error TEXT,
    summary JSONB
);

-- Indexes for performance
CREATE INDEX idx_curator_operations_run ON curator_operations(run_id);
CREATE INDEX idx_curator_operations_status ON curator_operations(status) WHERE status IN ('pending', 'failed');
CREATE INDEX idx_curator_runs_curator ON curator_runs(curator_id, started_at DESC);
CREATE INDEX idx_curators_status ON curators(status) WHERE status != 'paused';
CREATE INDEX idx_curators_next_run ON curators(next_run_at) WHERE status = 'active' AND next_run_at IS NOT NULL;

-- Row Level Security (public read for curator metadata, service role write)
ALTER TABLE curators ENABLE ROW LEVEL SECURITY;
ALTER TABLE curator_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE curator_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access to curators"
    ON curators FOR SELECT USING (true);

CREATE POLICY "Public read access to curator_runs"
    ON curator_runs FOR SELECT USING (true);

-- No public access to operations (internal audit log)

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER curators_updated_at
    BEFORE UPDATE ON curators
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Comments for documentation
COMMENT ON TABLE curators IS 'Curator agents managing collections';
COMMENT ON TABLE curator_operations IS 'Audit log of all curator operations for rollback/resume';
COMMENT ON TABLE curator_runs IS 'History of curator run executions';
COMMENT ON COLUMN curators.config IS 'Curator configuration: {dedup_threshold: 0.93, schedule: "0 2 * * *", etc}';
COMMENT ON COLUMN curator_operations.data IS 'Operation details: entity data, image URLs, relationship info, etc';
COMMENT ON COLUMN curator_runs.summary IS 'Run summary: {entities_added: 42, duplicates_found: 3, errors: []}';
```

**Step 2: Apply migration**

Run: `./scripts/safe-migrate push`
Expected: Migration creates 3 tables with indexes, RLS policies, and trigger

**Step 3: Verify schema**

Run:
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\d curators"
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\d curator_operations"
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "\d curator_runs"
```
Expected: Tables exist with correct columns and constraints

**Step 4: Test RLS policies**

Run:
```bash
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "
SET ROLE anon;
SELECT * FROM curators;
INSERT INTO curators (name, collection_id) VALUES ('test', NULL);
"
```
Expected: SELECT succeeds (empty), INSERT fails (RLS blocks)

**Step 5: Commit**

```bash
git add supabase/migrations/20251106000000_create_curator_tables.sql
git commit -m "feat: add curator database schema with operations log"
```

---

## Task 2: Python Environment & Dependencies

**Files:**
- Create: `curator/requirements.txt`
- Create: `curator/pyproject.toml`
- Create: `curator/.env.example`
- Create: `curator/README.md`

**Step 1: Create requirements.txt**

```txt
# Curator System Dependencies
anthropic>=0.39.0
supabase>=2.9.0
python-dotenv>=1.0.0
click>=8.1.0
rich>=13.0.0
pydantic>=2.10.0
asyncpg>=0.29.0
requests>=2.31.0
Pillow>=10.0.0
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "curator"
version = "0.1.0"
description = "Agentic curator system for collectibles database"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.39.0",
    "supabase>=2.9.0",
    "python-dotenv>=1.0.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "pydantic>=2.10.0",
    "asyncpg>=0.29.0",
    "requests>=2.31.0",
    "Pillow>=10.0.0",
]

[project.scripts]
curator = "curator.cli:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["curator*"]
```

**Step 3: Create .env.example**

```bash
# Supabase Configuration
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_KEY=your-service-role-key-here

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-...

# Curator Storage Path
CURATOR_HOME=.curator
```

**Step 4: Create README.md**

```markdown
# Curator System

Agentic curator system for managing collectible database collections.

## Features

- 🤖 **Conversational Discovery** - Design curators through interactive sessions
- 📜 **Script Generation** - Auto-generate domain-specific data fetching scripts
- 🔄 **Autonomous Execution** - Scheduled runs with agent-driven decision making
- 🛠️ **Generic Tools** - Collection management tools work for any domain
- 🔐 **Secrets Management** - Secure API key storage per curator
- 📊 **Transaction Log** - Rollback/resume capability for all operations

## Quick Start

```bash
# Install
cd curator
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your credentials

# Initialize a curator
curator init "Pokemon TCG"

# Run manually
curator run "Pokemon TCG"

# Schedule automatic runs
curator schedule "Pokemon TCG" "0 2 * * *"  # Daily at 2 AM

# View status
curator status "Pokemon TCG"
```

## Architecture

See `docs/plans/2025-11-06-curator-system.md` for implementation details.
```

**Step 5: Create directory structure**

Run:
```bash
mkdir -p curator/curator
touch curator/curator/__init__.py
mkdir -p .curator
echo ".curator/" >> .gitignore
echo "curator/.env" >> .gitignore
```

**Step 6: Install dependencies**

Run: `cd curator && pip install -e .`
Expected: All dependencies install successfully

**Step 7: Commit**

```bash
git add curator/requirements.txt curator/pyproject.toml curator/.env.example curator/README.md curator/curator/__init__.py .gitignore
git commit -m "feat: add curator Python package structure and dependencies"
```

---

## Task 3: Generic Curator Tools (Part 1: Core Tools)

**Files:**
- Create: `curator/curator/tools.py`
- Create: `curator/tests/test_tools.py`

**Step 1: Write failing tests for CuratorTools**

Create test file:

```python
# curator/tests/test_tools.py
import pytest
from curator.tools import CuratorTools
from supabase import create_client
import os

@pytest.fixture
def supabase_client():
    """Create Supabase client for testing"""
    url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return create_client(url, key)

@pytest.fixture
def test_collection(supabase_client):
    """Create test collection entity"""
    result = supabase_client.table("entities").insert({
        "name": "Test Collection",
        "type": "collection"
    }).execute()
    collection_id = result.data[0]["id"]
    yield collection_id
    # Cleanup
    supabase_client.table("entities").delete().eq("id", collection_id).execute()

@pytest.fixture
def curator_tools(supabase_client, test_collection):
    """Create CuratorTools instance"""
    return CuratorTools(test_collection, supabase_client)

def test_get_collection_stats_empty(curator_tools):
    """Test stats for empty collection"""
    stats = curator_tools.get_collection_stats()
    assert stats["total_entities"] == 0
    assert stats["total_subcollections"] == 0
    assert stats["last_updated"] is None

def test_get_collection_stats_with_items(curator_tools, supabase_client, test_collection):
    """Test stats with items"""
    # Add items to collection
    card = supabase_client.table("entities").insert({
        "name": "Test Card",
        "type": "card"
    }).execute().data[0]

    supabase_client.table("relationships").insert({
        "from_id": test_collection,
        "to_id": card["id"],
        "type": "contains"
    }).execute()

    stats = curator_tools.get_collection_stats()
    assert stats["total_entities"] == 1
    assert stats["last_updated"] is not None

    # Cleanup
    supabase_client.table("entities").delete().eq("id", card["id"]).execute()

def test_search_entities(curator_tools, supabase_client, test_collection):
    """Test semantic search within collection"""
    # Add entity with embedding
    card = supabase_client.table("entities").insert({
        "name": "Charizard",
        "type": "card",
        "name_embedding": [0.1] * 384  # Dummy embedding
    }).execute().data[0]

    supabase_client.table("relationships").insert({
        "from_id": test_collection,
        "to_id": card["id"],
        "type": "contains"
    }).execute()

    results = curator_tools.search_entities("fire dragon", limit=5)
    assert len(results) <= 5
    assert all("similarity" in r for r in results)

    # Cleanup
    supabase_client.table("entities").delete().eq("id", card["id"]).execute()

def test_add_entity(curator_tools):
    """Test adding entity to collection"""
    entity_id = curator_tools.add_entity(
        name="Test Item",
        entity_type="card",
        attributes={"hp": 100}
    )

    assert entity_id is not None
    # Verify relationship created
    # Cleanup happens via fixture
```

**Step 2: Run tests to verify they fail**

Run: `cd curator && pytest tests/test_tools.py -v`
Expected: ImportError - curator.tools module doesn't exist

**Step 3: Implement CuratorTools class**

Create implementation file:

```python
# curator/curator/tools.py
"""Generic tools for curator agents to manage collections."""

from typing import Dict, List, Optional, Any
from uuid import UUID
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CuratorTools:
    """Generic collection management tools for curator agents.

    These tools work for any collection type (cards, figures, comics, etc).
    Domain-specific logic lives in curator scripts, not here.
    """

    def __init__(self, collection_id: str, supabase_client):
        """Initialize tools for a specific collection.

        Args:
            collection_id: UUID of the collection entity
            supabase_client: Supabase client instance
        """
        self.collection_id = collection_id
        self.db = supabase_client

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get high-level collection statistics.

        Returns:
            {
                "total_entities": int,
                "total_subcollections": int,
                "entities_by_type": {"card": 100, "figure": 20},
                "last_updated": datetime or None,
                "has_embeddings": int,
                "has_thumbnails": int
            }
        """
        # Count direct children (entities contained by this collection)
        relationships = self.db.table("relationships").select(
            "to_id, entities!relationships_to_id_fkey(id, type, updated_at, name_embedding, thumbnail_url)"
        ).eq("from_id", self.collection_id).eq("type", "contains").execute()

        entities = [r["entities"] for r in relationships.data if r["entities"]]

        # Aggregate stats
        stats = {
            "total_entities": len(entities),
            "total_subcollections": sum(1 for e in entities if e["type"] == "collection"),
            "entities_by_type": {},
            "last_updated": None,
            "has_embeddings": sum(1 for e in entities if e.get("name_embedding")),
            "has_thumbnails": sum(1 for e in entities if e.get("thumbnail_url"))
        }

        # Count by type
        for entity in entities:
            entity_type = entity.get("type", "unknown")
            stats["entities_by_type"][entity_type] = stats["entities_by_type"].get(entity_type, 0) + 1

        # Most recent update
        if entities:
            updated_dates = [e["updated_at"] for e in entities if e.get("updated_at")]
            if updated_dates:
                stats["last_updated"] = max(updated_dates)

        return stats

    def get_subcollections(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List subcollections with metadata.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of dicts with subcollection info:
            [{
                "id": UUID,
                "name": str,
                "type": str,
                "attributes": dict,
                "entity_count": int,
                "last_updated": datetime
            }, ...]
        """
        # Get subcollections (collections contained by this collection)
        query = self.db.table("relationships").select(
            "to_id, entities!relationships_to_id_fkey(id, name, type, attributes, updated_at)"
        ).eq("from_id", self.collection_id).eq("type", "contains")

        if limit:
            query = query.limit(limit)

        relationships = query.execute()

        subcollections = []
        for rel in relationships.data:
            entity = rel.get("entities")
            if not entity or entity.get("type") != "collection":
                continue

            # Count entities in this subcollection
            count_result = self.db.table("relationships").select(
                "id", count="exact"
            ).eq("from_id", entity["id"]).eq("type", "contains").execute()

            subcollections.append({
                "id": entity["id"],
                "name": entity["name"],
                "type": entity["type"],
                "attributes": entity.get("attributes", {}),
                "entity_count": count_result.count or 0,
                "last_updated": entity.get("updated_at")
            })

        return subcollections

    def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Semantic search within this collection.

        Args:
            query: Search query text
            entity_type: Optional filter by entity type
            limit: Max results to return

        Returns:
            List of entities with similarity scores:
            [{
                "id": UUID,
                "name": str,
                "type": str,
                "similarity": float,
                "attributes": dict
            }, ...]
        """
        # Get all entities in this collection (recursive)
        all_entity_ids = self._get_all_entity_ids_recursive()

        if not all_entity_ids:
            return []

        # Use search_by_text function with entity filter
        # Note: This searches globally, then we filter to our collection
        result = self.db.rpc("search_by_text", {
            "query_text": query,
            "entity_type_filter": entity_type,
            "result_limit": limit * 3  # Get more, then filter
        }).execute()

        # Filter to entities in this collection
        filtered = [
            e for e in result.data
            if e["id"] in all_entity_ids
        ][:limit]

        return filtered

    def get_recent_additions(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get entities added to collection in the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of recent entities with metadata
        """
        cutoff = datetime.now() - timedelta(days=days)

        relationships = self.db.table("relationships").select(
            "to_id, created_at, entities!relationships_to_id_fkey(id, name, type, attributes, created_at)"
        ).eq("from_id", self.collection_id).eq("type", "contains").gte(
            "created_at", cutoff.isoformat()
        ).order("created_at", desc=True).execute()

        return [
            {
                "id": rel["entities"]["id"],
                "name": rel["entities"]["name"],
                "type": rel["entities"]["type"],
                "attributes": rel["entities"].get("attributes", {}),
                "added_at": rel["created_at"]
            }
            for rel in relationships.data
            if rel.get("entities")
        ]

    def find_duplicates(self, threshold: float = 0.93) -> List[tuple]:
        """Find potential duplicate entities using semantic search.

        Args:
            threshold: Similarity threshold (0-1)

        Returns:
            List of (entity1, entity2, similarity) tuples
        """
        # Get all entities in collection with embeddings
        entity_ids = self._get_all_entity_ids_recursive()

        if not entity_ids:
            return []

        entities = self.db.table("entities").select(
            "id, name, type, name_embedding"
        ).in_("id", entity_ids).not_.is_("name_embedding", "null").execute()

        duplicates = []
        checked = set()

        # Compare each entity to all others
        for entity in entities.data:
            if entity["id"] in checked:
                continue

            # Search for similar entities
            similar = self.db.rpc("semantic_search", {
                "query_embedding": entity["name_embedding"],
                "entity_type_filter": entity["type"],
                "result_limit": 10
            }).execute()

            for match in similar.data:
                if match["id"] == entity["id"]:
                    continue
                if match["id"] not in entity_ids:
                    continue
                if match["similarity"] >= threshold:
                    pair = tuple(sorted([entity["id"], match["id"]]))
                    if pair not in checked:
                        duplicates.append((
                            entity,
                            match,
                            match["similarity"]
                        ))
                        checked.add(pair)

        return duplicates

    def add_entity(
        self,
        name: str,
        entity_type: str,
        attributes: Optional[Dict[str, Any]] = None,
        external_ids: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
        year: Optional[int] = None,
        country: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """Add entity to collection with automatic thumbnail + embedding.

        Args:
            name: Entity name
            entity_type: Type (e.g., "card", "figure", "collection")
            attributes: Additional JSONB attributes
            external_ids: External system IDs
            image_url: Image URL (triggers thumbnail generation)
            year: Optional year
            country: Optional ISO country code
            language: Optional ISO language code

        Returns:
            UUID of created entity

        Note:
            - Thumbnail generation happens automatically via trigger
            - Embedding generation happens automatically via trigger
            - Relationship to parent collection is created
        """
        # Create entity
        entity_data = {
            "name": name,
            "type": entity_type,
            "attributes": attributes or {},
            "external_ids": external_ids or {}
        }

        if image_url:
            entity_data["image_url"] = image_url
        if year:
            entity_data["year"] = year
        if country:
            entity_data["country"] = country
        if language:
            entity_data["language"] = language

        result = self.db.table("entities").insert(entity_data).execute()
        entity_id = result.data[0]["id"]

        # Create relationship to parent collection
        self.db.table("relationships").insert({
            "from_id": self.collection_id,
            "to_id": entity_id,
            "type": "contains"
        }).execute()

        logger.info(f"Added entity {entity_id} ({name}) to collection {self.collection_id}")

        return entity_id

    def _get_all_entity_ids_recursive(self) -> List[str]:
        """Get all entity IDs in collection tree (recursive).

        Returns:
            List of entity UUIDs
        """
        # Simple implementation: just direct children for now
        # TODO: Make truly recursive for nested collections
        relationships = self.db.table("relationships").select(
            "to_id"
        ).eq("from_id", self.collection_id).eq("type", "contains").execute()

        return [r["to_id"] for r in relationships.data]

    def to_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic tool use format.

        Returns:
            List of tool definitions for Claude API
        """
        return [
            {
                "name": "get_collection_stats",
                "description": "Get high-level statistics about the collection (entity count, types, last updated, etc)",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_subcollections",
                "description": "List subcollections with metadata (name, entity count, last updated)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Optional limit on number of results"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "search_entities",
                "description": "Semantic search for entities within the collection using natural language query",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text"
                        },
                        "entity_type": {
                            "type": "string",
                            "description": "Optional filter by entity type (e.g., 'card', 'figure')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results to return (default 20)",
                            "default": 20
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_recent_additions",
                "description": "Get entities added to collection in the last N days",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look back (default 30)",
                            "default": 30
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "find_duplicates",
                "description": "Find potential duplicate entities using semantic similarity",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "threshold": {
                            "type": "number",
                            "description": "Similarity threshold 0-1 (default 0.93)",
                            "default": 0.93
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "add_entity",
                "description": "Add a new entity to the collection (automatically generates thumbnail and embedding)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Entity name"},
                        "entity_type": {"type": "string", "description": "Type (e.g., 'card', 'figure', 'collection')"},
                        "attributes": {"type": "object", "description": "Additional JSONB attributes"},
                        "external_ids": {"type": "object", "description": "External system IDs"},
                        "image_url": {"type": "string", "description": "Image URL"},
                        "year": {"type": "integer", "description": "Year"},
                        "country": {"type": "string", "description": "ISO country code"},
                        "language": {"type": "string", "description": "ISO language code"}
                    },
                    "required": ["name", "entity_type"]
                }
            }
        ]
```

**Step 4: Run tests to verify they pass**

Run: `cd curator && pytest tests/test_tools.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add curator/curator/tools.py curator/tests/test_tools.py
git commit -m "feat: implement CuratorTools with collection management methods"
```

---

## Task 4: CLI Framework with Click

**Files:**
- Create: `curator/curator/cli.py`
- Create: `curator/tests/test_cli.py`

**Step 1: Write failing tests for CLI**

```python
# curator/tests/test_cli.py
import pytest
from click.testing import CliRunner
from curator.cli import main

@pytest.fixture
def runner():
    """CLI test runner"""
    return CliRunner()

def test_cli_help(runner):
    """Test that CLI shows help"""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "curator" in result.output.lower()
    assert "init" in result.output
    assert "run" in result.output
    assert "status" in result.output

def test_cli_init_requires_name(runner):
    """Test that init requires curator name"""
    result = runner.invoke(main, ["init"])
    assert result.exit_code != 0
    assert "name" in result.output.lower()

def test_cli_run_requires_name(runner):
    """Test that run requires curator name"""
    result = runner.invoke(main, ["run"])
    assert result.exit_code != 0

def test_cli_status_requires_name(runner):
    """Test that status requires curator name"""
    result = runner.invoke(main, ["status"])
    assert result.exit_code != 0
```

**Step 2: Run tests to verify they fail**

Run: `cd curator && pytest tests/test_cli.py -v`
Expected: ImportError or AttributeError

**Step 3: Implement CLI framework**

```python
# curator/curator/cli.py
"""CLI interface for curator system."""

import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
import os

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Curator - Agentic collection management system.

    Create and manage curator agents that autonomously maintain collections.
    """
    pass


@main.command()
@click.argument("name")
@click.option("--collection-id", help="Existing collection UUID to manage")
def init(name: str, collection_id: str = None):
    """Initialize a new curator with interactive discovery.

    NAME: Curator name (e.g., "Pokemon TCG")

    This starts an interactive discovery session where you'll design
    the curator's workflow, data sources, and organization strategy.
    """
    console.print(f"\n[bold blue]Initializing curator:[/] {name}\n")

    # TODO: Implement discovery session
    console.print("[yellow]Discovery session not yet implemented[/]")
    console.print("\nWill implement:")
    console.print("  1. Interactive conversation to design curator")
    console.print("  2. Generate plan document")
    console.print("  3. Generate data fetching scripts")
    console.print("  4. Collect API keys/secrets")
    console.print("  5. Save curator configuration")


@main.command()
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
def run(name: str, dry_run: bool = False):
    """Run a curator manually.

    NAME: Curator name to run

    This triggers a manual curator run, where the agent assesses the
    collection state and decides what actions to take.
    """
    console.print(f"\n[bold blue]Running curator:[/] {name}\n")

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/]\n")

    # TODO: Implement curator run
    console.print("[yellow]Curator run not yet implemented[/]")


@main.command()
@click.argument("name")
@click.argument("schedule")
def schedule(name: str, schedule: str):
    """Schedule automatic curator runs.

    NAME: Curator name
    SCHEDULE: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)

    Sets up scheduled execution for the curator.
    """
    console.print(f"\n[bold blue]Scheduling curator:[/] {name}")
    console.print(f"[bold]Schedule:[/] {schedule}\n")

    # TODO: Implement scheduling
    console.print("[yellow]Scheduling not yet implemented[/]")


@main.command()
@click.argument("name")
@click.option("--runs", type=int, default=10, help="Number of recent runs to show")
def status(name: str, runs: int = 10):
    """Show curator status and recent runs.

    NAME: Curator name
    """
    console.print(f"\n[bold blue]Status for:[/] {name}\n")

    # TODO: Implement status display
    console.print("[yellow]Status display not yet implemented[/]")
    console.print("\nWill show:")
    console.print("  • Curator configuration")
    console.print("  • Collection statistics")
    console.print("  • Last run time and result")
    console.print("  • Next scheduled run")
    console.print("  • Recent run history")


@main.command()
@click.argument("name")
def logs(name: str):
    """View curator logs.

    NAME: Curator name
    """
    console.print(f"\n[bold blue]Logs for:[/] {name}\n")

    # TODO: Implement log viewing
    console.print("[yellow]Log viewing not yet implemented[/]")


@main.group()
def secrets():
    """Manage curator secrets (API keys)."""
    pass


@secrets.command(name="add")
@click.argument("name")
@click.argument("key")
@click.argument("value")
def secrets_add(name: str, key: str, value: str):
    """Add a secret for a curator.

    NAME: Curator name
    KEY: Secret key (e.g., "POKEMONTCG_API_KEY")
    VALUE: Secret value
    """
    console.print(f"\n[bold blue]Adding secret for:[/] {name}")
    console.print(f"[bold]Key:[/] {key}\n")

    # TODO: Implement secret storage
    console.print("[yellow]Secret management not yet implemented[/]")


@secrets.command(name="list")
@click.argument("name")
def secrets_list(name: str):
    """List required secrets for a curator.

    NAME: Curator name
    """
    console.print(f"\n[bold blue]Required secrets for:[/] {name}\n")

    # TODO: Implement secret listing
    console.print("[yellow]Secret management not yet implemented[/]")


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `cd curator && pytest tests/test_cli.py -v`
Expected: All tests pass

**Step 5: Test CLI manually**

Run: `curator --help`
Expected: Shows help with all commands

**Step 6: Commit**

```bash
git add curator/curator/cli.py curator/tests/test_cli.py
git commit -m "feat: add CLI framework with Click and Rich"
```

---

## Task 5: Discovery Session Implementation

**Files:**
- Create: `curator/curator/discovery.py`
- Create: `curator/tests/test_discovery.py`

**Step 1: Write failing tests**

```python
# curator/tests/test_discovery.py
import pytest
from curator.discovery import DiscoverySession
from anthropic import Anthropic
from unittest.mock import Mock, patch

@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client"""
    with patch("curator.discovery.Anthropic") as mock:
        yield mock

def test_discovery_session_init():
    """Test discovery session initialization"""
    session = DiscoverySession(
        curator_name="Test Curator",
        collection_id="test-uuid",
        anthropic_key="test-key"
    )
    assert session.curator_name == "Test Curator"
    assert session.collection_id == "test-uuid"
    assert len(session.conversation_history) == 0

def test_discovery_generates_plan(mock_anthropic):
    """Test that discovery session generates a plan"""
    session = DiscoverySession(
        curator_name="Test Curator",
        collection_id="test-uuid",
        anthropic_key="test-key"
    )

    # Mock user responses
    with patch("builtins.input", side_effect=["Pokemon cards", "pokemontcg.io API", "done"]):
        result = session.run()

    assert result["plan"] is not None
    assert result["scripts"] is not None
    assert result["secrets"] is not None
```

**Step 2: Run tests to verify they fail**

Run: `cd curator && pytest tests/test_discovery.py -v`
Expected: ImportError

**Step 3: Implement DiscoverySession (Part 1: Basic structure)**

```python
# curator/curator/discovery.py
"""Interactive discovery session for curator design."""

from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
import json
import logging

console = Console()
logger = logging.getLogger(__name__)


class DiscoverySession:
    """Interactive session to design a curator through conversation.

    This uses Claude to conduct a Socratic discovery process, helping
    the user articulate their collection structure, data sources, and
    workflows. The result is a plan document and generated scripts.
    """

    def __init__(
        self,
        curator_name: str,
        collection_id: str,
        anthropic_key: str,
        supabase_client = None
    ):
        """Initialize discovery session.

        Args:
            curator_name: Name of curator being created
            collection_id: UUID of collection entity (or None to create)
            anthropic_key: Anthropic API key
            supabase_client: Supabase client for inspecting current state
        """
        self.curator_name = curator_name
        self.collection_id = collection_id
        self.client = Anthropic(api_key=anthropic_key)
        self.db = supabase_client
        self.conversation_history = []
        self.artifacts = {
            "plan": None,
            "scripts": [],
            "secrets": [],
            "config": {}
        }
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt for discovery agent."""
        return """You are helping a user design a curator agent for their collectibles database.

Your goal: Through Socratic questioning, understand their collection and help them design an autonomous curator.

Key areas to explore:
1. **Collection Scope** - What items belong in this collection? How are they organized?
2. **Data Sources** - Where does data come from? APIs? Web scraping? Manual entry?
3. **Organization** - Should items be in subcollections? How should they be hierarchical?
4. **Metadata** - What attributes are important? What makes items unique?
5. **Update Frequency** - How often should the curator check for updates?
6. **Deduplication** - How should duplicates be detected? What's the threshold?

Ask thoughtful questions. Listen to their answers. Build understanding incrementally.

When you have sufficient understanding, generate:

1. **Plan Document** (Markdown)
   - Collection structure
   - Data sources and APIs
   - Update workflow
   - Deduplication strategy

2. **Scripts** (Python)
   - fetch_data.py - Fetch new items from source
   - update_existing.py - Update existing item metadata
   - deduplicate.py - Find and handle duplicates

3. **Secrets List**
   - Required API keys
   - Validation instructions

Use tools to inspect the current database state when helpful.

Important: Generate COMPLETE, WORKING scripts. Don't use pseudocode or placeholders.
"""

    def run(self) -> Dict[str, Any]:
        """Run interactive discovery session.

        Returns:
            Dictionary with plan, scripts, secrets, and config
        """
        console.print(Panel.fit(
            f"[bold]Discovery Session: {self.curator_name}[/]\n\n"
            "I'll help you design this curator through conversation.\n"
            "Type 'done' when you're ready to generate the plan.",
            title="🤖 Curator Discovery",
            border_style="blue"
        ))

        # Initialize conversation
        self._add_message("assistant", self._get_initial_message())

        # Conversation loop
        while not self._is_discovery_complete():
            # Show assistant message
            last_message = self.conversation_history[-1]
            if last_message["role"] == "assistant":
                console.print()
                console.print(Markdown(last_message["content"]))
                console.print()

            # Get user input
            user_input = console.input("[bold blue]You:[/] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["done", "finish", "complete"]:
                console.print("\n[yellow]Generating plan and scripts...[/]\n")
                self._generate_artifacts()
                break

            # Add to conversation
            self._add_message("user", user_input)

            # Get Claude response
            response = self._get_claude_response()
            self._add_message("assistant", response)

        # Show results
        self._display_results()

        return self.artifacts

    def _get_initial_message(self) -> str:
        """Get initial discovery message."""
        return f"""Hi! I'm here to help you design the **{self.curator_name}** curator.

Let's start with the basics:

**What type of items will this collection contain?**

For example:
- Trading cards from a specific game?
- Action figures from a franchise?
- Comic books from a publisher?
- Something else entirely?

Tell me about what you're collecting!"""

    def _add_message(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def _get_claude_response(self) -> str:
        """Get Claude's response to the conversation.

        Returns:
            Assistant's response text
        """
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=self.system_prompt,
                messages=self.conversation_history
            )

            # Extract text from response
            text_blocks = [
                block.text for block in response.content
                if hasattr(block, "text")
            ]
            return "\n\n".join(text_blocks)

        except Exception as e:
            logger.error(f"Error getting Claude response: {e}")
            return "I'm having trouble connecting. Let's try again."

    def _is_discovery_complete(self) -> bool:
        """Check if discovery is complete.

        Returns:
            True if artifacts have been generated
        """
        return self.artifacts["plan"] is not None

    def _generate_artifacts(self):
        """Generate plan, scripts, and config from conversation.

        This sends a final message to Claude asking it to synthesize
        the conversation into concrete artifacts.
        """
        synthesis_prompt = """Based on our conversation, please generate:

1. A comprehensive plan document (Markdown format)
2. Python scripts for data fetching and management
3. List of required secrets/API keys
4. Configuration settings (dedup threshold, schedule, etc)

Format your response as JSON:

```json
{
  "plan": "# Plan Document\\n\\n...",
  "scripts": [
    {
      "filename": "fetch_data.py",
      "code": "import requests\\n..."
    }
  ],
  "secrets": [
    {
      "key": "API_KEY_NAME",
      "description": "What this key is for",
      "validation_url": "https://..."
    }
  ],
  "config": {
    "dedup_threshold": 0.93,
    "schedule": "0 2 * * *",
    "...": "..."
  }
}
```

Generate COMPLETE, WORKING code. No placeholders or pseudocode."""

        self._add_message("user", synthesis_prompt)

        response = self._get_claude_response()

        # Parse JSON from response
        try:
            # Extract JSON from markdown code block
            if "```json" in response:
                json_start = response.index("```json") + 7
                json_end = response.index("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response

            artifacts = json.loads(json_str)
            self.artifacts.update(artifacts)

        except Exception as e:
            logger.error(f"Error parsing artifacts: {e}")
            console.print(f"[red]Error parsing artifacts: {e}[/]")
            console.print("[yellow]Raw response:[/]")
            console.print(response)

    def _display_results(self):
        """Display generated artifacts to user."""
        console.print()
        console.print(Panel.fit(
            "[bold green]✓ Discovery Complete![/]\n\n"
            f"Generated:\n"
            f"  • Plan document\n"
            f"  • {len(self.artifacts.get('scripts', []))} Python scripts\n"
            f"  • {len(self.artifacts.get('secrets', []))} required secrets\n"
            f"  • Configuration settings",
            title="🎉 Results",
            border_style="green"
        ))

        # Show secrets that need to be configured
        secrets = self.artifacts.get("secrets", [])
        if secrets:
            console.print("\n[bold yellow]⚠️  Required Secrets:[/]\n")
            for secret in secrets:
                console.print(f"  • {secret['key']}: {secret['description']}")
```

**Step 4: Run tests**

Run: `cd curator && pytest tests/test_discovery.py -v`
Expected: Tests pass (with mocked Anthropic)

**Step 5: Commit**

```bash
git add curator/curator/discovery.py curator/tests/test_discovery.py
git commit -m "feat: implement discovery session with Claude API"
```

---

## Task 6: Curator Storage & Configuration

**Files:**
- Create: `curator/curator/storage.py`
- Create: `curator/tests/test_storage.py`

**Step 1: Write failing tests**

```python
# curator/tests/test_storage.py
import pytest
from pathlib import Path
from curator.storage import CuratorStorage
import tempfile
import shutil

@pytest.fixture
def temp_curator_home():
    """Create temporary curator home directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

def test_curator_storage_init(temp_curator_home):
    """Test storage initialization"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    assert storage.curator_home.exists()
    assert (storage.curator_home / "curators").exists()
    assert (storage.curator_home / "runs").exists()

def test_create_curator_directory(temp_curator_home):
    """Test creating curator directory structure"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    curator_dir = storage.create_curator_directory("test-curator")

    assert curator_dir.exists()
    assert (curator_dir / "scripts").exists()
    assert (curator_dir / "memory").exists()
    assert (curator_dir / "config.json").exists()

def test_save_curator_plan(temp_curator_home):
    """Test saving curator plan"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    curator_dir = storage.create_curator_directory("test-curator")

    plan = "# Test Plan\n\nThis is a test plan."
    storage.save_plan("test-curator", plan)

    plan_file = curator_dir / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text() == plan

def test_save_scripts(temp_curator_home):
    """Test saving curator scripts"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    storage.create_curator_directory("test-curator")

    scripts = [
        {"filename": "fetch.py", "code": "print('hello')"},
        {"filename": "update.py", "code": "print('world')"}
    ]

    storage.save_scripts("test-curator", scripts)

    curator_dir = storage.curator_home / "curators" / "test-curator"
    assert (curator_dir / "scripts" / "fetch.py").exists()
    assert (curator_dir / "scripts" / "update.py").exists()

def test_save_secrets(temp_curator_home):
    """Test saving secrets"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    storage.create_curator_directory("test-curator")

    secrets = {"API_KEY": "secret123", "TOKEN": "token456"}
    storage.save_secrets("test-curator", secrets)

    secrets_file = storage.curator_home / "curators" / "test-curator" / "secrets.env"
    assert secrets_file.exists()
    assert "API_KEY=secret123" in secrets_file.read_text()
```

**Step 2: Run tests to verify they fail**

Run: `cd curator && pytest tests/test_storage.py -v`
Expected: ImportError

**Step 3: Implement CuratorStorage**

```python
# curator/curator/storage.py
"""Filesystem storage for curator configuration and artifacts."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CuratorStorage:
    """Manages curator filesystem storage.

    Directory structure:
        .curator/
        ├── curators/
        │   ├── pokemon-tcg/
        │   │   ├── config.json
        │   │   ├── plan.md
        │   │   ├── scripts/
        │   │   │   ├── fetch_sets.py
        │   │   │   └── fetch_cards.py
        │   │   ├── secrets.env
        │   │   └── memory/
        │   │       └── episodes.jsonl
        │   └── marvel-comics/...
        └── runs/
            └── pokemon-tcg/
                ├── 2025-11-06_120000/
                │   ├── log.txt
                │   └── operations.json
                └── 2025-11-06_140000/...
    """

    def __init__(self, curator_home: Optional[Path] = None):
        """Initialize storage.

        Args:
            curator_home: Root directory for curator storage
                         (defaults to .curator in current directory)
        """
        if curator_home is None:
            curator_home = Path.cwd() / ".curator"

        self.curator_home = Path(curator_home)
        self._ensure_structure()

    def _ensure_structure(self):
        """Ensure base directory structure exists."""
        self.curator_home.mkdir(exist_ok=True)
        (self.curator_home / "curators").mkdir(exist_ok=True)
        (self.curator_home / "runs").mkdir(exist_ok=True)

    def create_curator_directory(self, curator_name: str) -> Path:
        """Create directory structure for a new curator.

        Args:
            curator_name: Curator name (used as directory name)

        Returns:
            Path to curator directory
        """
        curator_dir = self.curator_home / "curators" / curator_name
        curator_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (curator_dir / "scripts").mkdir(exist_ok=True)
        (curator_dir / "memory").mkdir(exist_ok=True)

        # Create initial config
        config_file = curator_dir / "config.json"
        if not config_file.exists():
            config = {
                "name": curator_name,
                "created_at": datetime.now().isoformat(),
                "version": 1
            }
            config_file.write_text(json.dumps(config, indent=2))

        logger.info(f"Created curator directory: {curator_dir}")
        return curator_dir

    def get_curator_directory(self, curator_name: str) -> Path:
        """Get path to curator directory.

        Args:
            curator_name: Curator name

        Returns:
            Path to curator directory

        Raises:
            FileNotFoundError: If curator doesn't exist
        """
        curator_dir = self.curator_home / "curators" / curator_name
        if not curator_dir.exists():
            raise FileNotFoundError(f"Curator '{curator_name}' not found")
        return curator_dir

    def save_plan(self, curator_name: str, plan: str):
        """Save curator plan document.

        Args:
            curator_name: Curator name
            plan: Plan markdown content
        """
        curator_dir = self.get_curator_directory(curator_name)
        plan_file = curator_dir / "plan.md"
        plan_file.write_text(plan)
        logger.info(f"Saved plan for {curator_name}")

    def load_plan(self, curator_name: str) -> str:
        """Load curator plan document.

        Args:
            curator_name: Curator name

        Returns:
            Plan markdown content
        """
        curator_dir = self.get_curator_directory(curator_name)
        plan_file = curator_dir / "plan.md"
        return plan_file.read_text()

    def save_scripts(self, curator_name: str, scripts: List[Dict[str, str]]):
        """Save curator scripts.

        Args:
            curator_name: Curator name
            scripts: List of {"filename": "...", "code": "..."} dicts
        """
        curator_dir = self.get_curator_directory(curator_name)
        scripts_dir = curator_dir / "scripts"

        for script in scripts:
            filename = script["filename"]
            code = script["code"]
            script_file = scripts_dir / filename
            script_file.write_text(code)
            logger.info(f"Saved script: {filename}")

    def list_scripts(self, curator_name: str) -> List[str]:
        """List available scripts for curator.

        Args:
            curator_name: Curator name

        Returns:
            List of script filenames
        """
        curator_dir = self.get_curator_directory(curator_name)
        scripts_dir = curator_dir / "scripts"
        return [f.name for f in scripts_dir.glob("*.py")]

    def save_secrets(self, curator_name: str, secrets: Dict[str, str]):
        """Save curator secrets to .env file.

        Args:
            curator_name: Curator name
            secrets: Dict of {KEY: value} pairs
        """
        curator_dir = self.get_curator_directory(curator_name)
        secrets_file = curator_dir / "secrets.env"

        lines = [f"{key}={value}" for key, value in secrets.items()]
        secrets_file.write_text("\n".join(lines) + "\n")

        # Set restrictive permissions (owner read/write only)
        secrets_file.chmod(0o600)

        logger.info(f"Saved {len(secrets)} secrets for {curator_name}")

    def load_secrets(self, curator_name: str) -> Dict[str, str]:
        """Load curator secrets from .env file.

        Args:
            curator_name: Curator name

        Returns:
            Dict of {KEY: value} pairs
        """
        curator_dir = self.get_curator_directory(curator_name)
        secrets_file = curator_dir / "secrets.env"

        if not secrets_file.exists():
            return {}

        secrets = {}
        for line in secrets_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                secrets[key.strip()] = value.strip()

        return secrets

    def save_config(self, curator_name: str, config: Dict[str, Any]):
        """Save curator configuration.

        Args:
            curator_name: Curator name
            config: Configuration dict
        """
        curator_dir = self.get_curator_directory(curator_name)
        config_file = curator_dir / "config.json"
        config_file.write_text(json.dumps(config, indent=2))
        logger.info(f"Saved config for {curator_name}")

    def load_config(self, curator_name: str) -> Dict[str, Any]:
        """Load curator configuration.

        Args:
            curator_name: Curator name

        Returns:
            Configuration dict
        """
        curator_dir = self.get_curator_directory(curator_name)
        config_file = curator_dir / "config.json"
        return json.loads(config_file.read_text())

    def create_run_directory(self, curator_name: str) -> Path:
        """Create directory for a curator run.

        Args:
            curator_name: Curator name

        Returns:
            Path to run directory (timestamped)
        """
        runs_dir = self.curator_home / "runs" / curator_name
        runs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        run_dir = runs_dir / timestamp
        run_dir.mkdir(exist_ok=True)

        return run_dir

    def list_curators(self) -> List[str]:
        """List all curator names.

        Returns:
            List of curator names
        """
        curators_dir = self.curator_home / "curators"
        return [d.name for d in curators_dir.iterdir() if d.is_dir()]

    def curator_exists(self, curator_name: str) -> bool:
        """Check if curator exists.

        Args:
            curator_name: Curator name

        Returns:
            True if curator directory exists
        """
        curator_dir = self.curator_home / "curators" / curator_name
        return curator_dir.exists()
```

**Step 4: Run tests**

Run: `cd curator && pytest tests/test_storage.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add curator/curator/storage.py curator/tests/test_storage.py
git commit -m "feat: implement curator filesystem storage"
```

---

## Task 7: Integrate Discovery with CLI

**Files:**
- Modify: `curator/curator/cli.py`

**Step 1: Import required modules**

Add to top of `cli.py`:

```python
from curator.discovery import DiscoverySession
from curator.storage import CuratorStorage
from curator.tools import CuratorTools
from supabase import create_client
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()
```

**Step 2: Update init command**

Replace the `init` command implementation:

```python
@main.command()
@click.argument("name")
@click.option("--collection-id", help="Existing collection UUID to manage")
def init(name: str, collection_id: str = None):
    """Initialize a new curator with interactive discovery.

    NAME: Curator name (e.g., "Pokemon TCG")
    """
    console.print(f"\n[bold blue]Initializing curator:[/] {name}\n")

    # Check if curator already exists
    storage = CuratorStorage()
    if storage.curator_exists(name):
        console.print(f"[red]Error: Curator '{name}' already exists[/]")
        return

    # Get credentials
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not anthropic_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment[/]")
        console.print("Set it in .env file or environment variables")
        return

    if not supabase_url or not supabase_key:
        console.print("[red]Error: Supabase credentials not found[/]")
        console.print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        return

    # Create Supabase client
    supabase = create_client(supabase_url, supabase_key)

    # Create or get collection
    if collection_id is None:
        console.print("[yellow]No collection ID provided. Creating new collection...[/]")
        result = supabase.table("entities").insert({
            "name": name,
            "type": "collection"
        }).execute()
        collection_id = result.data[0]["id"]
        console.print(f"[green]✓ Created collection: {collection_id}[/]\n")

    # Run discovery session
    session = DiscoverySession(
        curator_name=name,
        collection_id=collection_id,
        anthropic_key=anthropic_key,
        supabase_client=supabase
    )

    try:
        artifacts = session.run()

        # Save artifacts
        storage.create_curator_directory(name)
        storage.save_plan(name, artifacts["plan"])
        storage.save_scripts(name, artifacts["scripts"])

        # Save config
        config = artifacts.get("config", {})
        config["collection_id"] = collection_id
        storage.save_config(name, config)

        # Prompt for secrets
        secrets_list = artifacts.get("secrets", [])
        if secrets_list:
            console.print("\n[bold yellow]📝 Configure Secrets[/]\n")
            secrets = {}
            for secret in secrets_list:
                console.print(f"[bold]{secret['key']}[/]: {secret['description']}")
                value = console.input("  Value (or press Enter to skip): ").strip()
                if value:
                    secrets[secret['key']] = value

            if secrets:
                storage.save_secrets(name, secrets)
                console.print(f"\n[green]✓ Saved {len(secrets)} secrets[/]")

        # Save to database
        supabase.table("curators").insert({
            "name": name,
            "collection_id": collection_id,
            "config": config
        }).execute()

        console.print(f"\n[bold green]✓ Curator '{name}' initialized successfully![/]\n")
        console.print(f"Run with: [bold]curator run \"{name}\"[/]")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Discovery cancelled[/]")
    except Exception as e:
        console.print(f"\n[red]Error during discovery: {e}[/]")
        import traceback
        traceback.print_exc()
```

**Step 3: Test init command manually**

Run: `curator init "Test Curator"`
Expected: Starts discovery session, saves artifacts

**Step 4: Commit**

```bash
git add curator/curator/cli.py
git commit -m "feat: integrate discovery session with CLI init command"
```

---

## Task 8: Curator Runner Implementation (Part 1: Basic Execution)

**Files:**
- Create: `curator/curator/runner.py`
- Create: `curator/tests/test_runner.py`

**Step 1: Write failing tests**

```python
# curator/tests/test_runner.py
import pytest
from curator.runner import CuratorRunner
from unittest.mock import Mock, patch

@pytest.fixture
def mock_storage():
    """Mock curator storage"""
    storage = Mock()
    storage.load_config.return_value = {
        "collection_id": "test-uuid",
        "dedup_threshold": 0.93
    }
    storage.load_plan.return_value = "# Test Plan"
    storage.list_scripts.return_value = ["fetch_data.py"]
    return storage

@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    return Mock()

def test_runner_init(mock_storage, mock_supabase):
    """Test runner initialization"""
    runner = CuratorRunner(
        curator_name="test",
        storage=mock_storage,
        supabase_client=mock_supabase,
        anthropic_key="test-key"
    )
    assert runner.curator_name == "test"

def test_runner_executes_agent_loop(mock_storage, mock_supabase):
    """Test that runner executes agent decision loop"""
    runner = CuratorRunner(
        curator_name="test",
        storage=mock_storage,
        supabase_client=mock_supabase,
        anthropic_key="test-key"
    )

    with patch.object(runner, "_run_agent_loop") as mock_loop:
        mock_loop.return_value = {"status": "completed"}
        result = runner.run(dry_run=False)

        assert result["status"] == "completed"
        mock_loop.assert_called_once()
```

**Step 2: Run tests**

Run: `cd curator && pytest tests/test_runner.py -v`
Expected: ImportError

**Step 3: Implement CuratorRunner (Part 1)**

```python
# curator/curator/runner.py
"""Curator execution engine."""

from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from curator.storage import CuratorStorage
from curator.tools import CuratorTools
from datetime import datetime
from uuid import uuid4
import logging
import json

logger = logging.getLogger(__name__)


class CuratorRunner:
    """Executes curator runs with agent-driven decision making.

    The runner:
    1. Loads curator config and plan
    2. Creates tools for collection management
    3. Runs agent loop to decide actions
    4. Executes scripts as directed by agent
    5. Logs all operations for rollback/resume
    """

    def __init__(
        self,
        curator_name: str,
        storage: CuratorStorage,
        supabase_client,
        anthropic_key: str
    ):
        """Initialize runner.

        Args:
            curator_name: Name of curator to run
            storage: Curator storage instance
            supabase_client: Supabase client
            anthropic_key: Anthropic API key
        """
        self.curator_name = curator_name
        self.storage = storage
        self.db = supabase_client
        self.client = Anthropic(api_key=anthropic_key)

        # Load curator configuration
        self.config = storage.load_config(curator_name)
        self.collection_id = self.config["collection_id"]
        self.plan = storage.load_plan(curator_name)
        self.scripts = storage.list_scripts(curator_name)

        # Initialize tools
        self.tools = CuratorTools(self.collection_id, supabase_client)

        # Run tracking
        self.run_id = None
        self.operations = []

    def run(self, dry_run: bool = False) -> Dict[str, Any]:
        """Execute curator run.

        Args:
            dry_run: If True, show what would be done without executing

        Returns:
            Dict with run results:
            {
                "run_id": UUID,
                "status": "completed" | "failed",
                "operations_count": int,
                "summary": {...}
            }
        """
        # Create run record
        self.run_id = str(uuid4())
        run_start = datetime.now()

        logger.info(f"Starting curator run: {self.curator_name} (run_id: {self.run_id})")

        # Create run in database
        self.db.table("curator_runs").insert({
            "id": self.run_id,
            "curator_id": self._get_curator_db_id(),
            "trigger": "manual",
            "status": "running",
            "started_at": run_start.isoformat()
        }).execute()

        # Create run directory
        run_dir = self.storage.create_run_directory(self.curator_name)

        try:
            # Execute agent loop
            result = self._run_agent_loop(dry_run)

            # Mark run complete
            self.db.table("curator_runs").update({
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "operations_count": len(self.operations),
                "summary": result.get("summary", {})
            }).eq("id", self.run_id).execute()

            # Update curator last_run_at
            self.db.table("curators").update({
                "last_run_at": datetime.now().isoformat()
            }).eq("id", self._get_curator_db_id()).execute()

            logger.info(f"Curator run completed: {self.curator_name}")

            return {
                "run_id": self.run_id,
                "status": "completed",
                "operations_count": len(self.operations),
                "summary": result.get("summary", {})
            }

        except Exception as e:
            logger.error(f"Curator run failed: {e}")

            # Mark run failed
            self.db.table("curator_runs").update({
                "status": "failed",
                "completed_at": datetime.now().isoformat(),
                "error": str(e)
            }).eq("id", self.run_id).execute()

            return {
                "run_id": self.run_id,
                "status": "failed",
                "error": str(e)
            }

    def _run_agent_loop(self, dry_run: bool) -> Dict[str, Any]:
        """Run agent decision loop.

        Args:
            dry_run: If True, don't execute actions

        Returns:
            Dict with agent decisions and results
        """
        # Get current collection state
        stats = self.tools.get_collection_stats()

        # Build agent prompt
        system_prompt = self._build_agent_system_prompt()
        user_prompt = self._build_agent_user_prompt(stats)

        # Call Claude with tools
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=self.tools.to_anthropic_tools()
        )

        # Process tool calls
        result = self._process_agent_response(response, dry_run)

        return result

    def _build_agent_system_prompt(self) -> str:
        """Build system prompt for agent."""
        return f"""You are the {self.curator_name} curator agent.

Your plan:
{self.plan}

Your role: Assess the current state of your collection and decide what actions to take.

Available tools:
- Collection management (get_collection_stats, search_entities, etc.)
- Entity operations (add_entity, etc.)

Available scripts in scripts/:
{chr(10).join(f'  - {s}' for s in self.scripts)}

Process:
1. Use tools to assess current collection state
2. Decide what needs to be done (based on your plan)
3. Execute appropriate actions
4. Summarize what you did

Be autonomous but cautious. Don't make changes unless there's clear need."""

    def _build_agent_user_prompt(self, stats: Dict[str, Any]) -> str:
        """Build user prompt with context."""
        return f"""Time to run! Here's the current state:

**Collection Statistics:**
- Total entities: {stats['total_entities']}
- Subcollections: {stats['total_subcollections']}
- Entities by type: {stats['entities_by_type']}
- Last updated: {stats['last_updated']}
- Embedding coverage: {stats['has_embeddings']}/{stats['total_entities']}
- Thumbnail coverage: {stats['has_thumbnails']}/{stats['total_entities']}

**Your Task:**
1. Assess what needs to be done (check for new items, updates, etc.)
2. Use tools to investigate further if needed
3. Take appropriate actions
4. Summarize your work

What would you like to do?"""

    def _process_agent_response(
        self,
        response,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Process agent response and execute tool calls.

        Args:
            response: Anthropic API response
            dry_run: If True, don't execute actions

        Returns:
            Dict with execution results
        """
        results = {
            "tool_calls": [],
            "summary": {}
        }

        # Extract tool calls
        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                logger.info(f"Agent called: {tool_name}({tool_input})")

                if dry_run:
                    results["tool_calls"].append({
                        "tool": tool_name,
                        "input": tool_input,
                        "executed": False
                    })
                else:
                    # Execute tool
                    tool_result = self._execute_tool(tool_name, tool_input)
                    results["tool_calls"].append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": tool_result,
                        "executed": True
                    })

        return results

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool call.

        Args:
            tool_name: Name of tool to execute
            tool_input: Tool input parameters

        Returns:
            Tool execution result
        """
        # Map tool names to methods
        tool_methods = {
            "get_collection_stats": self.tools.get_collection_stats,
            "get_subcollections": self.tools.get_subcollections,
            "search_entities": self.tools.search_entities,
            "get_recent_additions": self.tools.get_recent_additions,
            "find_duplicates": self.tools.find_duplicates,
            "add_entity": self.tools.add_entity
        }

        tool_method = tool_methods.get(tool_name)
        if not tool_method:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Execute tool
        result = tool_method(**tool_input)

        # Log operation
        self._log_operation(tool_name, tool_input, result)

        return result

    def _log_operation(
        self,
        operation_type: str,
        data: Dict[str, Any],
        result: Any
    ):
        """Log operation for rollback/resume.

        Args:
            operation_type: Type of operation
            data: Operation input data
            result: Operation result
        """
        operation = {
            "id": str(uuid4()),
            "curator_id": self._get_curator_db_id(),
            "run_id": self.run_id,
            "operation_type": operation_type,
            "status": "completed",
            "data": {
                "input": data,
                "result": str(result)[:1000]  # Truncate for storage
            },
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }

        self.operations.append(operation)

        # Save to database
        self.db.table("curator_operations").insert(operation).execute()

    def _get_curator_db_id(self) -> str:
        """Get curator ID from database.

        Returns:
            Curator UUID
        """
        result = self.db.table("curators").select("id").eq(
            "name", self.curator_name
        ).single().execute()
        return result.data["id"]
```

**Step 4: Run tests**

Run: `cd curator && pytest tests/test_runner.py -v`
Expected: Tests pass

**Step 5: Commit**

```bash
git add curator/curator/runner.py curator/tests/test_runner.py
git commit -m "feat: implement curator runner with agent decision loop"
```

---

## Task 9: Integrate Runner with CLI

**Files:**
- Modify: `curator/curator/cli.py`

**Step 1: Import runner**

Add to imports:

```python
from curator.runner import CuratorRunner
```

**Step 2: Update run command**

Replace the `run` command implementation:

```python
@main.command()
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
def run(name: str, dry_run: bool = False):
    """Run a curator manually.

    NAME: Curator name to run
    """
    console.print(f"\n[bold blue]Running curator:[/] {name}\n")

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/]\n")

    # Get credentials
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not all([anthropic_key, supabase_url, supabase_key]):
        console.print("[red]Error: Missing credentials in environment[/]")
        return

    # Create clients
    storage = CuratorStorage()
    supabase = create_client(supabase_url, supabase_key)

    # Check curator exists
    if not storage.curator_exists(name):
        console.print(f"[red]Error: Curator '{name}' not found[/]")
        console.print(f"Run: [bold]curator init \"{name}\"[/]")
        return

    # Load secrets
    secrets = storage.load_secrets(name)
    for key, value in secrets.items():
        os.environ[key] = value

    # Create runner
    runner = CuratorRunner(
        curator_name=name,
        storage=storage,
        supabase_client=supabase,
        anthropic_key=anthropic_key
    )

    try:
        result = runner.run(dry_run=dry_run)

        if result["status"] == "completed":
            console.print(f"\n[bold green]✓ Run completed successfully[/]")
            console.print(f"Operations: {result['operations_count']}")
            console.print(f"Run ID: {result['run_id']}")
        else:
            console.print(f"\n[bold red]✗ Run failed[/]")
            console.print(f"Error: {result.get('error', 'Unknown')}")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Run cancelled[/]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/]")
        import traceback
        traceback.print_exc()
```

**Step 3: Test run command manually**

Run: `curator run "Test Curator" --dry-run`
Expected: Shows agent decisions without executing

**Step 4: Commit**

```bash
git add curator/curator/cli.py
git commit -m "feat: integrate curator runner with CLI run command"
```

---

## Task 10: Status Command Implementation

**Files:**
- Modify: `curator/curator/cli.py`

**Step 1: Update status command**

Replace the `status` command:

```python
@main.command()
@click.argument("name")
@click.option("--runs", type=int, default=10, help="Number of recent runs to show")
def status(name: str, runs: int = 10):
    """Show curator status and recent runs.

    NAME: Curator name
    """
    console.print(f"\n[bold blue]Status for:[/] {name}\n")

    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        console.print("[red]Error: Supabase credentials not found[/]")
        return

    # Create clients
    storage = CuratorStorage()
    supabase = create_client(supabase_url, supabase_key)

    # Check curator exists
    if not storage.curator_exists(name):
        console.print(f"[red]Error: Curator '{name}' not found[/]")
        return

    # Load config
    config = storage.load_config(name)

    # Get curator from database
    curator_result = supabase.table("curators").select("*").eq("name", name).single().execute()
    curator = curator_result.data

    # Get collection stats
    collection_id = curator["collection_id"]
    tools = CuratorTools(collection_id, supabase)
    stats = tools.get_collection_stats()

    # Display curator info
    console.print("[bold]Curator Configuration:[/]")
    console.print(f"  Collection ID: {collection_id}")
    console.print(f"  Status: {curator['status']}")
    console.print(f"  Created: {curator['created_at']}")
    console.print(f"  Last run: {curator['last_run_at'] or 'Never'}")
    console.print()

    # Display collection stats
    console.print("[bold]Collection Statistics:[/]")
    console.print(f"  Total entities: {stats['total_entities']}")
    console.print(f"  Subcollections: {stats['total_subcollections']}")
    console.print(f"  Embedding coverage: {stats['has_embeddings']}/{stats['total_entities']}")
    console.print(f"  Thumbnail coverage: {stats['has_thumbnails']}/{stats['total_entities']}")
    console.print()

    # Display entities by type
    if stats['entities_by_type']:
        console.print("[bold]Entities by Type:[/]")
        for entity_type, count in stats['entities_by_type'].items():
            console.print(f"  {entity_type}: {count}")
        console.print()

    # Get recent runs
    runs_result = supabase.table("curator_runs").select("*").eq(
        "curator_id", curator["id"]
    ).order("started_at", desc=True).limit(runs).execute()

    if runs_result.data:
        console.print(f"[bold]Recent Runs ({len(runs_result.data)}):[/]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Started")
        table.add_column("Trigger")
        table.add_column("Status")
        table.add_column("Operations")
        table.add_column("Duration")

        for run in runs_result.data:
            started = run["started_at"][:16].replace("T", " ")
            status_color = {"completed": "green", "failed": "red", "running": "yellow"}.get(run["status"], "white")
            status = f"[{status_color}]{run['status']}[/{status_color}]"

            duration = "?"
            if run.get("completed_at"):
                from datetime import datetime
                start = datetime.fromisoformat(run["started_at"])
                end = datetime.fromisoformat(run["completed_at"])
                duration = str(end - start)

            table.add_row(
                started,
                run["trigger"],
                status,
                str(run.get("operations_count", 0)),
                duration
            )

        console.print(table)
```

**Step 2: Test status command**

Run: `curator status "Test Curator"`
Expected: Shows curator configuration and stats

**Step 3: Commit**

```bash
git add curator/curator/cli.py
git commit -m "feat: implement status command with rich table display"
```

---

## Summary

**You've now implemented the core curator system!**

**What works:**
- ✅ Interactive discovery sessions with Claude
- ✅ Plan and script generation
- ✅ Filesystem storage for curators
- ✅ Generic collection management tools
- ✅ Agent-driven execution with tool use
- ✅ Operation logging for rollback
- ✅ CLI commands: init, run, status

**What's left for future tasks:**
- Scheduling (Task 11)
- Script execution from agent (Task 12)
- Mini-discovery for updates (Task 13)
- Agentic deduplication (Task 14)
- Rollback/resume (Task 15)
- Integration tests (Task 16)
- Documentation (Task 17)

---

## Testing the System

**End-to-end test:**

```bash
# 1. Initialize a curator
curator init "Test Collection"
# Follow discovery conversation
# Generate plan and scripts

# 2. Run the curator
curator run "Test Collection" --dry-run
# See what agent would do

curator run "Test Collection"
# Execute for real

# 3. Check status
curator status "Test Collection"
# View results and history
```

**Database verification:**

```bash
# Check curator created
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "SELECT * FROM curators;"

# Check runs logged
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "SELECT * FROM curator_runs;"

# Check operations
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres -c "SELECT * FROM curator_operations;"
```

---

## Next Steps

Choose your execution approach:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which would you prefer?
