#!/usr/bin/env python3
"""
Database Client for Video Game Curator

Handles entity and relationship operations for video games in Supabase PostgreSQL.
"""

import json
import subprocess
from typing import Optional, Dict, Tuple, List


class DatabaseClient:
    """Client for database operations via Docker psql"""

    def __init__(self, container_name: str = "supabase_db_database-of-things"):
        """
        Initialize database client

        Args:
            container_name: Docker container name for PostgreSQL
        """
        self.container_name = container_name

    def _exec_sql(self, sql: str) -> str:
        """
        Execute SQL command and return output

        Args:
            sql: SQL statement to execute

        Returns:
            Command output
        """
        cmd = [
            "docker", "exec", self.container_name,
            "psql", "-U", "postgres", "-d", "postgres",
            "-c", sql
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"SQL execution failed: {result.stderr}")

        return result.stdout

    def _exec_sql_json(self, sql: str) -> List[Dict]:
        """
        Execute SQL and return results as JSON

        Args:
            sql: SQL query to execute

        Returns:
            Query results as list of dicts
        """
        cmd = [
            "docker", "exec", self.container_name,
            "psql", "-U", "postgres", "-d", "postgres",
            "-t", "-A", "-F", "|",
            "-c", sql
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"SQL execution failed: {result.stderr}")

        # Parse pipe-delimited output
        lines = result.stdout.strip().split("\n")
        if not lines or not lines[0]:
            return []

        # First line is headers
        headers = lines[0].split("|")

        # Parse rows
        rows = []
        for line in lines[1:]:
            if not line:
                continue
            values = line.split("|")
            row = {}
            for i, header in enumerate(headers):
                if i < len(values):
                    value = values[i]
                    # Try to parse JSON fields
                    if value and (value.startswith("{") or value.startswith("[")):
                        try:
                            row[header] = json.loads(value)
                        except json.JSONDecodeError:
                            row[header] = value
                    else:
                        row[header] = value if value else None
                else:
                    row[header] = None
            rows.append(row)

        return rows

    def find_entity_by_external_id(self, external_system: str, external_id: str) -> Optional[Dict]:
        """
        Find entity by external ID

        Args:
            external_system: External system name (e.g., "rawg")
            external_id: External ID value

        Returns:
            Entity dict or None if not found
        """
        sql = f"""
            SELECT id, name, type, COALESCE(attributes, '{{}}'::jsonb) as attributes,
                   COALESCE(external_ids, '{{}}'::jsonb) as external_ids
            FROM entities
            WHERE external_ids @> '{{"{{external_system}}": "{{external_id}}"}}'::jsonb
            LIMIT 1;
        """.replace("{{external_system}}", external_system).replace("{{external_id}}", external_id)

        results = self._exec_sql_json(sql)
        return results[0] if results else None

    def find_entity_by_name_and_type(self, name: str, entity_type: str) -> Optional[Dict]:
        """
        Find entity by name and type

        Args:
            name: Entity name
            entity_type: Entity type (e.g., "video_game", "franchise")

        Returns:
            Entity dict or None if not found
        """
        # Escape single quotes in name
        safe_name = name.replace("'", "''")

        sql = f"""
            SELECT id, name, type, COALESCE(attributes, '{{}}'::jsonb) as attributes,
                   COALESCE(external_ids, '{{}}'::jsonb) as external_ids
            FROM entities
            WHERE name = '{safe_name}' AND type = '{entity_type}'
            LIMIT 1;
        """

        results = self._exec_sql_json(sql)
        return results[0] if results else None

    def create_entity(
        self,
        entity_type: str,
        name: str,
        year: Optional[int] = None,
        image_key: Optional[str] = None,
        attributes: Optional[Dict] = None,
        external_ids: Optional[Dict] = None
    ) -> str:
        """
        Create new entity

        Args:
            entity_type: Entity type (e.g., "video_game", "franchise")
            name: Entity name
            year: Year (optional)
            image_key: Image storage key or URL (optional)
            attributes: JSONB attributes (optional)
            external_ids: External system IDs (optional)

        Returns:
            Entity UUID
        """
        # Escape single quotes
        safe_name = name.replace("'", "''")

        # Build SQL
        fields = ["type", "name"]
        values = [f"'{entity_type}'", f"'{safe_name}'"]

        if year is not None:
            fields.append("year")
            values.append(str(year))

        if image_key:
            safe_image_key = image_key.replace("'", "''")
            fields.append("image_key")
            values.append(f"'{safe_image_key}'")

        if attributes:
            fields.append("attributes")
            values.append(f"'{json.dumps(attributes)}'::jsonb")

        if external_ids:
            fields.append("external_ids")
            values.append(f"'{json.dumps(external_ids)}'::jsonb")

        sql = f"""
            INSERT INTO entities ({', '.join(fields)})
            VALUES ({', '.join(values)})
            RETURNING id;
        """

        result = self._exec_sql(sql)
        # Extract UUID from output
        lines = [line for line in result.split("\n") if line.strip() and not line.startswith("-") and "row" not in line.lower()]
        if lines:
            return lines[0].strip()
        raise Exception("Failed to get entity ID from insert")

    def update_entity(
        self,
        entity_id: str,
        name: Optional[str] = None,
        year: Optional[int] = None,
        image_key: Optional[str] = None,
        attributes: Optional[Dict] = None,
        external_ids: Optional[Dict] = None
    ):
        """
        Update existing entity

        Args:
            entity_id: Entity UUID
            name: Entity name (optional)
            year: Year (optional)
            image_key: Image storage key or URL (optional)
            attributes: JSONB attributes (optional)
            external_ids: External system IDs (optional)
        """
        updates = []

        if name:
            safe_name = name.replace("'", "''")
            updates.append(f"name = '{safe_name}'")

        if year is not None:
            updates.append(f"year = {year}")

        if image_key is not None:
            safe_image_key = image_key.replace("'", "''")
            updates.append(f"image_key = '{safe_image_key}'")

        if attributes is not None:
            updates.append(f"attributes = '{json.dumps(attributes)}'::jsonb")

        if external_ids is not None:
            updates.append(f"external_ids = '{json.dumps(external_ids)}'::jsonb")

        updates.append("updated_at = NOW()")

        if updates:
            sql = f"""
                UPDATE entities
                SET {', '.join(updates)}
                WHERE id = '{entity_id}';
            """
            self._exec_sql(sql)

    def upsert_entity(
        self,
        external_system: str,
        external_id: str,
        entity_type: str,
        name: str,
        year: Optional[int] = None,
        image_key: Optional[str] = None,
        attributes: Optional[Dict] = None
    ) -> Tuple[str, bool]:
        """
        Create or update entity based on external ID

        Args:
            external_system: External system name (e.g., "rawg")
            external_id: External ID value
            entity_type: Entity type
            name: Entity name
            year: Year (optional)
            image_key: Image storage key or URL (optional)
            attributes: JSONB attributes (optional)

        Returns:
            Tuple of (entity_id, created)
        """
        # Check if entity exists
        existing = self.find_entity_by_external_id(external_system, external_id)

        external_ids = {external_system: external_id}

        if existing:
            # Update existing entity
            self.update_entity(
                existing["id"],
                name=name,
                year=year,
                image_key=image_key,
                attributes=attributes,
                external_ids=external_ids
            )
            return (existing["id"], False)
        else:
            # Create new entity
            entity_id = self.create_entity(
                entity_type=entity_type,
                name=name,
                year=year,
                image_key=image_key,
                attributes=attributes,
                external_ids=external_ids
            )
            return (entity_id, True)

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        attributes: Optional[Dict] = None
    ):
        """
        Create relationship between entities (with deduplication)

        Args:
            from_id: Source entity UUID
            to_id: Target entity UUID
            rel_type: Relationship type (e.g., "contains")
            attributes: JSONB attributes (optional)
        """
        # Check if relationship already exists
        check_sql = f"""
            SELECT id FROM relationships
            WHERE from_id = '{from_id}'
              AND to_id = '{to_id}'
              AND type = '{rel_type}'
            LIMIT 1;
        """

        existing = self._exec_sql_json(check_sql)
        if existing:
            # Relationship already exists, skip
            return

        # Create new relationship
        if attributes:
            sql = f"""
                INSERT INTO relationships (from_id, to_id, type, attributes)
                VALUES ('{from_id}', '{to_id}', '{rel_type}', '{json.dumps(attributes)}'::jsonb)
                ON CONFLICT DO NOTHING;
            """
        else:
            sql = f"""
                INSERT INTO relationships (from_id, to_id, type)
                VALUES ('{from_id}', '{to_id}', '{rel_type}')
                ON CONFLICT DO NOTHING;
            """

        self._exec_sql(sql)


def main():
    """Test database client"""
    print("Testing database client...")
    client = DatabaseClient()

    # Test entity creation
    print("\nTesting entity operations...")

    # This is just a test - we won't actually create anything
    print("✅ Database client initialized successfully")


if __name__ == "__main__":
    main()
