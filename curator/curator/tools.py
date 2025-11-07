"""Generic tools for curator agents to manage collections."""

from typing import Dict, List, Optional, Any
from uuid import UUID
import logging
import os
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

    def execute_script(
        self,
        script_name: str,
        args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a curator script from the scripts/ directory.

        Args:
            script_name: Name of the script file (e.g., "fetch_rangerwiki.py")
            args: Optional arguments to pass to the script as JSON

        Returns:
            {
                "success": bool,
                "output": str,
                "error": str or None,
                "exit_code": int
            }

        Example:
            execute_script("fetch_rangerwiki.py", {"series": "Mighty Morphin"})
        """
        import subprocess
        import json
        from pathlib import Path

        # Get curator scripts directory - use absolute path
        curator_home = Path(os.getenv("CURATOR_HOME", ".curator")).resolve()

        # Find curator name by collection_id
        # This is a bit hacky - we should pass curator_name to __init__
        # For now, scan curator directories
        curator_name = None
        curators_dir = curator_home / "curators"
        if curators_dir.exists():
            for curator_dir in curators_dir.iterdir():
                if curator_dir.is_dir():
                    config_file = curator_dir / "config.json"
                    if config_file.exists():
                        with open(config_file) as f:
                            config = json.load(f)
                            if config.get("collection_id") == self.collection_id:
                                curator_name = curator_dir.name
                                break

        if not curator_name:
            return {
                "success": False,
                "output": "",
                "error": f"Could not find curator for collection {self.collection_id}",
                "exit_code": -1
            }

        script_path = curator_home / "curators" / curator_name / "scripts" / script_name

        if not script_path.exists():
            return {
                "success": False,
                "output": "",
                "error": f"Script not found: {script_path}",
                "exit_code": -1
            }

        # Build command
        cmd = ["python3", str(script_path.resolve())]

        # Add args as JSON if provided
        if args:
            cmd.extend(["--json-args", json.dumps(args)])

        try:
            # Execute script from the scripts directory
            scripts_dir = script_path.parent
            logger.info(f"Executing script: {' '.join(cmd)} from {scripts_dir}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(scripts_dir.resolve())
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "exit_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Script execution timeout (5 minutes)",
                "exit_code": -1
            }
        except Exception as e:
            logger.error(f"Error executing script {script_name}: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }

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
            },
            {
                "name": "execute_script",
                "description": "Execute a curator-specific Python script from the scripts/ directory. Use this to run data fetching, import, validation, or deduplication scripts that were generated during discovery.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "script_name": {
                            "type": "string",
                            "description": "Name of the script file (e.g., 'fetch_rangerwiki.py', 'import_toylines.py')"
                        },
                        "args": {
                            "type": "object",
                            "description": "Optional arguments to pass to the script as JSON"
                        }
                    },
                    "required": ["script_name"]
                }
            }
        ]
