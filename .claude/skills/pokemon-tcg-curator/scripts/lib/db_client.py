"""
Database Client for Pokémon TCG Curator

Handles database operations including:
- Entity CRUD operations
- Relationship management
- Deduplication by external_ids
"""

import subprocess
import json
from typing import Dict, List, Optional, Tuple
import uuid


class DatabaseClient:
    """Client for PostgreSQL database operations via Docker"""

    CONTAINER_NAME = "supabase_db_database-of-things"
    DB_USER = "postgres"
    DB_NAME = "postgres"
    TCG_ROOT_ID = "55bc90fb-22e9-4715-bdde-2e004d0d5ee2"  # Pokémon Trading Card Game entity

    def __init__(self):
        """Initialize database client"""
        pass

    def _exec_sql(self, sql: str) -> str:
        """
        Execute SQL command via Docker

        Args:
            sql: SQL command to execute

        Returns:
            Command output
        """
        cmd = [
            "docker", "exec",
            self.CONTAINER_NAME,
            "psql",
            "-U", self.DB_USER,
            "-d", self.DB_NAME,
            "-t",  # Tuples only (no headers/footers)
            "-c", sql
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def _exec_sql_json(self, sql: str) -> List[Dict]:
        """
        Execute SQL and return results as JSON

        Args:
            sql: SQL SELECT query

        Returns:
            List of row dictionaries
        """
        # Wrap query to return JSON
        json_sql = f"SELECT json_agg(t) FROM ({sql}) t;"
        result = self._exec_sql(json_sql)

        if not result or result == "null":
            return []

        return json.loads(result)

    def find_entity_by_external_id(self, system: str, external_id: str) -> Optional[Dict]:
        """
        Find entity by external_id

        Args:
            system: External system name (e.g., "pokemontcg.io")
            external_id: External ID value

        Returns:
            Entity dict or None
        """
        sql = f"""
            SELECT id, type, name, year, country, image_key, attributes, external_ids
            FROM entities
            WHERE external_ids @> '{{"{ system}": "{external_id}"}}'::jsonb
            LIMIT 1
        """
        results = self._exec_sql_json(sql)
        return results[0] if results else None

    def find_entity_by_name_and_type(self, name: str, entity_type: str) -> Optional[Dict]:
        """
        Find entity by name and type

        Args:
            name: Entity name
            entity_type: Entity type

        Returns:
            Entity dict or None
        """
        # Escape single quotes in name
        name_escaped = name.replace("'", "''")

        sql = f"""
            SELECT id, type, name, year, country, image_key, attributes, external_ids
            FROM entities
            WHERE name = '{name_escaped}' AND type = '{entity_type}'
            LIMIT 1
        """
        results = self._exec_sql_json(sql)
        return results[0] if results else None

    def create_entity(
        self,
        entity_type: str,
        name: str,
        year: Optional[int] = None,
        country: Optional[str] = None,
        image_key: Optional[str] = None,
        attributes: Optional[Dict] = None,
        external_ids: Optional[Dict] = None
    ) -> str:
        """
        Create new entity

        Args:
            entity_type: Type of entity
            name: Entity name
            year: Optional year
            country: Optional ISO country code
            image_key: Optional image path/URL
            attributes: Optional JSONB attributes
            external_ids: Optional external system IDs

        Returns:
            Entity UUID
        """
        entity_id = str(uuid.uuid4())

        # Escape single quotes
        name_escaped = name.replace("'", "''")
        image_key_escaped = image_key.replace("'", "''") if image_key else None

        # Build SQL
        sql_parts = [
            f"INSERT INTO entities (id, type, name"
        ]
        values_parts = [
            f"VALUES ('{entity_id}', '{entity_type}', '{name_escaped}'"
        ]

        if year is not None:
            sql_parts.append(", year")
            values_parts.append(f", {year}")

        if country:
            sql_parts.append(", country")
            values_parts.append(f", '{country}'")

        if image_key:
            sql_parts.append(", image_key")
            values_parts.append(f", '{image_key_escaped}'")

        if attributes:
            sql_parts.append(", attributes")
            values_parts.append(f", '{json.dumps(attributes)}'::jsonb")

        if external_ids:
            sql_parts.append(", external_ids")
            values_parts.append(f", '{json.dumps(external_ids)}'::jsonb")

        sql = "".join(sql_parts) + ") " + "".join(values_parts) + ");"

        self._exec_sql(sql)
        return entity_id

    def update_entity(
        self,
        entity_id: str,
        year: Optional[int] = None,
        country: Optional[str] = None,
        image_key: Optional[str] = None,
        attributes: Optional[Dict] = None,
        external_ids: Optional[Dict] = None
    ):
        """
        Update existing entity

        Args:
            entity_id: Entity UUID
            year: Optional year
            country: Optional ISO country code
            image_key: Optional image path/URL
            attributes: Optional JSONB attributes
            external_ids: Optional external system IDs
        """
        updates = []

        if year is not None:
            updates.append(f"year = {year}")

        if country is not None:
            updates.append(f"country = '{country}'")

        if image_key is not None:
            image_key_escaped = image_key.replace("'", "''")
            updates.append(f"image_key = '{image_key_escaped}'")

        if attributes is not None:
            updates.append(f"attributes = '{json.dumps(attributes)}'::jsonb")

        if external_ids is not None:
            updates.append(f"external_ids = '{json.dumps(external_ids)}'::jsonb")

        if not updates:
            return

        updates.append("updated_at = NOW()")

        sql = f"""
            UPDATE entities
            SET {', '.join(updates)}
            WHERE id = '{entity_id}'
        """

        self._exec_sql(sql)

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        attributes: Optional[Dict] = None
    ) -> bool:
        """
        Create relationship between entities

        Args:
            from_id: Parent entity UUID
            to_id: Child entity UUID
            rel_type: Relationship type (e.g., "contains")
            attributes: Optional relationship attributes

        Returns:
            True if created, False if already exists
        """
        # Check if relationship already exists
        check_sql = f"""
            SELECT COUNT(*) as count
            FROM relationships
            WHERE from_id = '{from_id}' AND to_id = '{to_id}' AND type = '{rel_type}'
        """
        result = self._exec_sql_json(check_sql)

        if result and result[0].get("count", 0) > 0:
            return False

        # Create relationship
        rel_id = str(uuid.uuid4())
        attr_json = json.dumps(attributes) if attributes else "{}"

        sql = f"""
            INSERT INTO relationships (id, from_id, to_id, type, attributes)
            VALUES ('{rel_id}', '{from_id}', '{to_id}', '{rel_type}', '{attr_json}'::jsonb)
        """

        self._exec_sql(sql)
        return True

    def upsert_entity(
        self,
        external_system: str,
        external_id: str,
        entity_type: str,
        name: str,
        year: Optional[int] = None,
        country: Optional[str] = None,
        image_key: Optional[str] = None,
        attributes: Optional[Dict] = None
    ) -> Tuple[str, bool]:
        """
        Create or update entity based on external_id

        Args:
            external_system: External system name (e.g., "pokemontcg.io")
            external_id: External ID
            entity_type: Type of entity
            name: Entity name
            year: Optional year
            country: Optional ISO country code
            image_key: Optional image path/URL
            attributes: Optional JSONB attributes

        Returns:
            (entity_id, created) tuple where created=True if new entity
        """
        external_ids_dict = {external_system: external_id}

        # Check if entity exists
        existing = self.find_entity_by_external_id(external_system, external_id)

        if existing:
            # Update existing entity
            self.update_entity(
                entity_id=existing["id"],
                year=year,
                country=country,
                image_key=image_key,
                attributes=attributes,
                external_ids=external_ids_dict
            )
            return existing["id"], False
        else:
            # Create new entity
            entity_id = self.create_entity(
                entity_type=entity_type,
                name=name,
                year=year,
                country=country,
                image_key=image_key,
                attributes=attributes,
                external_ids=external_ids_dict
            )
            return entity_id, True


if __name__ == "__main__":
    # Quick test
    db = DatabaseClient()

    print("Testing database client...")
    print(f"\nTCG Root ID: {db.TCG_ROOT_ID}")

    # Test finding existing entity
    existing = db.find_entity_by_external_id("pokemontcg.io", "swsh4")
    if existing:
        print(f"\nFound existing set: {existing['name']}")
    else:
        print("\nNo existing set found with code 'swsh4'")
