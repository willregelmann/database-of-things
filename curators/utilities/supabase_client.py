"""
Supabase client utilities for curator agents.

Provides collection-agnostic operations for entities and relationships.
"""

from typing import Dict, List, Optional, Any, Literal
from uuid import UUID, uuid4
from datetime import datetime

from supabase import create_client, Client
from core.config import settings


EntityType = Literal[
    "collection", "card", "figure", "game", "toy", "variant", "component"
]
RelationshipType = Literal["contains", "variant_of", "part_of"]


class SupabaseClient:
    """Collection-agnostic Supabase database client."""

    def __init__(self):
        """Initialize Supabase client with service role key."""
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )

    # ==================== Entity Operations ====================

    async def create_entity(
        self,
        name: str,
        entity_type: EntityType,
        year: Optional[int] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Create a new entity in the database.

        Args:
            name: Display name
            entity_type: Type of entity
            year: Optional year
            country: Optional ISO country code (2 chars)
            language: Optional ISO language code (2 chars)
            image_url: Optional image URL/path
            thumbnail_url: Optional thumbnail URL/path
            attributes: Optional JSONB attributes

        Returns:
            UUID of created entity
        """
        entity_id = uuid4()

        data = {
            "id": str(entity_id),
            "name": name,
            "type": entity_type,
            "year": year,
            "country": country,
            "language": language,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "attributes": attributes or {},
        }

        result = self.client.table("entities").insert(data).execute()
        return entity_id

    async def get_entity(self, entity_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity UUID

        Returns:
            Entity data or None if not found
        """
        result = self.client.table("entities").select("*").eq("id", str(entity_id)).execute()

        if result.data:
            return result.data[0]
        return None

    async def find_entities(
        self,
        entity_type: Optional[EntityType] = None,
        name_contains: Optional[str] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Find entities by filters.

        Args:
            entity_type: Filter by type
            name_contains: Filter by name (case-insensitive LIKE)
            year: Filter by year
            language: Filter by language
            limit: Maximum results

        Returns:
            List of matching entities
        """
        query = self.client.table("entities").select("*")

        if entity_type:
            query = query.eq("type", entity_type)
        if name_contains:
            query = query.ilike("name", f"%{name_contains}%")
        if year:
            query = query.eq("year", year)
        if language:
            query = query.eq("language", language)

        query = query.limit(limit)
        result = query.execute()

        return result.data

    async def update_entity(
        self, entity_id: UUID, updates: Dict[str, Any]
    ) -> None:
        """
        Update entity fields.

        Args:
            entity_id: Entity UUID
            updates: Fields to update
        """
        self.client.table("entities").update(updates).eq("id", str(entity_id)).execute()

    async def delete_entity(self, entity_id: UUID) -> None:
        """
        Delete entity (cascades to relationships).

        Args:
            entity_id: Entity UUID
        """
        self.client.table("entities").delete().eq("id", str(entity_id)).execute()

    # ==================== Relationship Operations ====================

    async def create_relationship(
        self,
        from_id: UUID,
        to_id: UUID,
        relationship_type: RelationshipType,
        order: Optional[int] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Create a relationship between entities.

        Args:
            from_id: Source entity UUID
            to_id: Target entity UUID
            relationship_type: Type of relationship
            order: Optional sort order
            attributes: Optional JSONB attributes

        Returns:
            UUID of created relationship
        """
        relationship_id = uuid4()

        data = {
            "id": str(relationship_id),
            "from_id": str(from_id),
            "to_id": str(to_id),
            "type": relationship_type,
            "order": order,
            "attributes": attributes or {},
        }

        result = self.client.table("relationships").insert(data).execute()
        return relationship_id

    async def get_relationships(
        self,
        from_id: Optional[UUID] = None,
        to_id: Optional[UUID] = None,
        relationship_type: Optional[RelationshipType] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get relationships by filters.

        Args:
            from_id: Filter by source entity
            to_id: Filter by target entity
            relationship_type: Filter by type

        Returns:
            List of matching relationships
        """
        query = self.client.table("relationships").select("*")

        if from_id:
            query = query.eq("from_id", str(from_id))
        if to_id:
            query = query.eq("to_id", str(to_id))
        if relationship_type:
            query = query.eq("type", relationship_type)

        result = query.execute()
        return result.data

    async def get_children(
        self,
        parent_id: UUID,
        relationship_type: RelationshipType = "contains",
    ) -> List[Dict[str, Any]]:
        """
        Get all child entities of a parent (forward traversal).

        Args:
            parent_id: Parent entity UUID
            relationship_type: Type of relationship (default: "contains")

        Returns:
            List of child entities
        """
        result = (
            self.client.table("relationships")
            .select("to_id, entities(*)")
            .eq("from_id", str(parent_id))
            .eq("type", relationship_type)
            .order("order")
            .execute()
        )

        # Extract entities from joined data
        return [r["entities"] for r in result.data if r.get("entities")]

    async def get_parents(
        self,
        child_id: UUID,
        relationship_type: RelationshipType = "contains",
    ) -> List[Dict[str, Any]]:
        """
        Get all parent entities of a child (reverse traversal).

        Args:
            child_id: Child entity UUID
            relationship_type: Type of relationship (default: "contains")

        Returns:
            List of parent entities
        """
        result = (
            self.client.table("relationships")
            .select("from_id, entities(*)")
            .eq("to_id", str(child_id))
            .eq("type", relationship_type)
            .execute()
        )

        # Extract entities from joined data
        return [r["entities"] for r in result.data if r.get("entities")]

    # ==================== Bulk Operations ====================

    async def bulk_create_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[UUID]:
        """
        Bulk create entities.

        Args:
            entities: List of entity data dicts

        Returns:
            List of created entity UUIDs
        """
        # Generate UUIDs
        for entity in entities:
            if "id" not in entity:
                entity["id"] = str(uuid4())
            if "attributes" not in entity:
                entity["attributes"] = {}

        result = self.client.table("entities").insert(entities).execute()
        return [UUID(e["id"]) for e in result.data]

    async def bulk_create_relationships(
        self, relationships: List[Dict[str, Any]]
    ) -> List[UUID]:
        """
        Bulk create relationships.

        Args:
            relationships: List of relationship data dicts

        Returns:
            List of created relationship UUIDs
        """
        # Generate UUIDs and convert entity IDs to strings
        for rel in relationships:
            if "id" not in rel:
                rel["id"] = str(uuid4())
            rel["from_id"] = str(rel["from_id"])
            rel["to_id"] = str(rel["to_id"])
            if "attributes" not in rel:
                rel["attributes"] = {}

        result = self.client.table("relationships").insert(relationships).execute()
        return [UUID(r["id"]) for r in result.data]
