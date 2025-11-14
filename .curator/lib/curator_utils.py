#!/usr/bin/env python3
"""
Reusable curator utilities for managing curator-collection relationships.

Provides functions to register curators with collections and discover
existing curator-collection mappings.

Usage:
    from ...lib.curator_utils import register_curator, get_curator_collections

    register_curator(
        supabase_client,
        curator_name="NTSC Video Games",
        collection_id="uuid-here",
        config={"platform_id": 10}
    )
"""

from pathlib import Path
from typing import Optional, Dict, List, Tuple


def register_curator(
    supabase_client,
    curator_name: str,
    collection_id: str,
    config: Optional[Dict] = None
) -> bool:
    """
    Register a curator-collection relationship.

    This function is idempotent - it will not create duplicates. If the
    relationship already exists, it returns True without error.

    Args:
        supabase_client: Supabase client instance
        curator_name: Name of the curator (matches .curator/curators/ directory)
        collection_id: UUID of the collection entity
        config: Optional curator-specific configuration (JSONB)

    Returns:
        True if registration succeeded or already exists

    Example:
        # Single-collection curator
        register_curator(supabase, "Marvel Comics", collection_uuid)

        # Multi-collection curator with config
        register_curator(
            supabase,
            "NTSC Video Games",
            game_boy_uuid,
            {"platform_id": 10}
        )
    """
    if config is None:
        config = {}

    try:
        # Check if relationship already exists
        existing = supabase_client.table("curator_collections").select("id").match({
            "curator_name": curator_name,
            "collection_id": collection_id
        }).execute()

        if existing.data:
            # Already registered
            return True

        # Register new curator-collection relationship
        supabase_client.table("curator_collections").insert({
            "curator_name": curator_name,
            "collection_id": collection_id,
            "config": config
        }).execute()

        return True

    except Exception as e:
        # If conflict error (unique constraint), relationship already exists
        error_str = str(e).lower()
        if '409' in error_str or 'unique' in error_str or 'conflict' in error_str:
            return True

        # Other errors - log and return False
        print(f"Warning: Failed to register curator: {e}")
        return False


def get_curator_collections(
    supabase_client,
    curator_name: str
) -> List[Dict]:
    """
    Get all collections managed by a curator.

    Args:
        supabase_client: Supabase client instance
        curator_name: Name of the curator

    Returns:
        List of collection records with id, collection_id, and config

    Example:
        collections = get_curator_collections(supabase, "NTSC Video Games")
        for coll in collections:
            print(f"Collection: {coll['collection_id']}")
            print(f"Config: {coll['config']}")
    """
    try:
        result = supabase_client.table("curator_collections").select(
            "id, collection_id, config"
        ).eq("curator_name", curator_name).execute()

        return result.data

    except Exception as e:
        print(f"Warning: Failed to get curator collections: {e}")
        return []


def get_collection_curator(
    supabase_client,
    collection_id: str
) -> Optional[Dict]:
    """
    Get the curator that manages a specific collection.

    Args:
        supabase_client: Supabase client instance
        collection_id: UUID of the collection entity

    Returns:
        Curator record with curator_name and config, or None if not found

    Example:
        curator = get_collection_curator(supabase, collection_uuid)
        if curator:
            print(f"Managed by: {curator['curator_name']}")
    """
    try:
        result = supabase_client.table("curator_collections").select(
            "curator_name, config"
        ).eq("collection_id", collection_id).execute()

        if result.data:
            return result.data[0]
        return None

    except Exception as e:
        print(f"Warning: Failed to get collection curator: {e}")
        return None


def update_curator_config(
    supabase_client,
    curator_name: str,
    collection_id: str,
    config: Dict
) -> bool:
    """
    Update the config for an existing curator-collection relationship.

    Args:
        supabase_client: Supabase client instance
        curator_name: Name of the curator
        collection_id: UUID of the collection entity
        config: New configuration (completely replaces existing)

    Returns:
        True if update succeeded

    Example:
        update_curator_config(
            supabase,
            "NTSC Video Games",
            nes_uuid,
            {"platform_id": 18, "last_import": "2025-11-09"}
        )
    """
    try:
        supabase_client.table("curator_collections").update({
            "config": config,
            "updated_at": "NOW()"
        }).match({
            "curator_name": curator_name,
            "collection_id": collection_id
        }).execute()

        return True

    except Exception as e:
        print(f"Warning: Failed to update curator config: {e}")
        return False


def check_exists_by_semantic_search(
    supabase_client,
    name: str,
    entity_type: Optional[str] = None,
    threshold: float = 0.95
) -> Optional[str]:
    """
    Check if entity exists using semantic search on name embeddings.

    This is a fallback deduplication strategy when external IDs are not available.
    Uses the semantic_search() database function to find similar entity names.

    Args:
        supabase_client: Supabase client instance
        name: Entity name to search for
        entity_type: Optional entity type filter (e.g., "card", "game")
        threshold: Similarity threshold (0.0-1.0). Default 0.95 for high confidence.
                   - 0.98+: Very high confidence (exact match or minor typo)
                   - 0.95-0.98: High confidence (same item, different formatting)
                   - 0.90-0.95: Medium confidence (possibly same, needs review)

    Returns:
        Entity ID if match found above threshold, None otherwise

    Example:
        # Check if "Charizard" exists
        existing_id = check_exists_by_semantic_search(
            supabase,
            "Charizard",
            entity_type="card",
            threshold=0.95
        )

        if existing_id:
            print(f"Found existing entity: {existing_id}")
        else:
            print("No match found, safe to create")
    """
    try:
        # Import here to avoid circular dependency
        import sys
        from pathlib import Path

        # Add lib directory to path if not already there
        lib_path = str(Path(__file__).parent)
        if lib_path not in sys.path:
            sys.path.insert(0, lib_path)

        from embedding_utils import EmbeddingGenerator

        # Generate embedding for the query name
        generator = EmbeddingGenerator()
        query_embedding = generator.generate_embedding(name)

        # Convert embedding to string format for PostgreSQL
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Call semantic_search function
        result = supabase_client.rpc('semantic_search', {
            'query_embedding': embedding_str,
            'entity_type_filter': entity_type,
            'result_limit': 1
        }).execute()

        # Check if we found a match above threshold
        if result.data and len(result.data) > 0:
            top_match = result.data[0]
            similarity = top_match.get('similarity', 0)

            # Note: semantic_search returns distance (lower is better)
            # Convert to similarity if needed (depends on function implementation)
            # If it returns cosine distance: similarity = 1 - distance
            # If it returns similarity score: use directly

            if similarity >= threshold:
                return top_match['id']

        return None

    except Exception as e:
        print(f"Warning: Semantic search failed: {e}")
        return None


def validate_collection_exists(
    supabase_client,
    collection_id: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a collection entity exists in the database.

    Args:
        supabase_client: Supabase client instance
        collection_id: UUID of the collection to validate

    Returns:
        Tuple of (exists: bool, error_message: Optional[str])
        - (True, None) if collection exists
        - (False, error_message) if collection doesn't exist or query failed

    Example:
        exists, error = validate_collection_exists(supabase, collection_uuid)

        if not exists:
            print(f"Error: {error}")
            print("Create collection first:")
            print(f"  INSERT INTO entities (id, name, type) VALUES ('{collection_uuid}', 'My Collection', 'collection');")
            sys.exit(1)
    """
    try:
        result = supabase_client.table("entities").select(
            "id, name, type"
        ).eq("id", collection_id).execute()

        if not result.data or len(result.data) == 0:
            return False, f"Collection {collection_id} does not exist in database"

        collection = result.data[0]

        # Verify it's actually a collection type
        if collection.get("type") != "collection":
            return False, f"Entity {collection_id} exists but is not a collection (type: {collection.get('type')})"

        return True, None

    except Exception as e:
        return False, f"Failed to validate collection: {e}"


class MetadataValidator:
    """
    Validates that entities have required metadata fields.

    Helps ensure curator-specific metadata consistency by checking that all
    items in a collection have the same required fields.

    Example:
        # For video games curator
        validator = MetadataValidator(["publisher", "developers"])

        # Validate each item
        for game in games:
            warnings = validator.validate(game, game["name"])

        # Get report
        if validator.has_warnings():
            print(validator.get_summary())
    """

    def __init__(self, required_fields: List[str]):
        """
        Initialize validator with required metadata fields.

        Args:
            required_fields: List of field names that must exist in attributes
                            Example: ["publisher", "developers"] for games
                                     ["set", "card_number", "rarity"] for cards
        """
        self.required_fields = required_fields
        self.warnings: List[str] = []

    def validate(self, item_data: Dict, item_name: str) -> List[str]:
        """
        Validate a single item's metadata.

        Args:
            item_data: Item data dictionary with "attributes" key
            item_name: Name of the item (for warning messages)

        Returns:
            List of warning messages for this item
        """
        item_warnings = []
        attributes = item_data.get("attributes", {})

        for field in self.required_fields:
            if field not in attributes:
                warning = f"Missing {field}: {item_name}"
                item_warnings.append(warning)
                self.warnings.append(warning)
            elif attributes[field] is None or attributes[field] == "":
                warning = f"Empty {field}: {item_name}"
                item_warnings.append(warning)
                self.warnings.append(warning)

        return item_warnings

    def has_warnings(self) -> bool:
        """Check if any warnings were collected."""
        return len(self.warnings) > 0

    def get_warnings(self) -> List[str]:
        """Get all warnings collected."""
        return self.warnings

    def get_summary(self, max_warnings: int = 20) -> str:
        """
        Get formatted summary of metadata issues.

        Args:
            max_warnings: Maximum number of warnings to include (default 20)

        Returns:
            Formatted string with summary
        """
        if not self.warnings:
            return "✓ All items have required metadata fields"

        summary = f"⚠️  Metadata Issues ({len(self.warnings)} total):\n"

        # Show first N warnings
        for warning in self.warnings[:max_warnings]:
            summary += f"   {warning}\n"

        # Show count of remaining
        if len(self.warnings) > max_warnings:
            remaining = len(self.warnings) - max_warnings
            summary += f"   ... and {remaining} more\n"

        return summary


def load_environment_config(
    curator_name: str,
    environment: str = "local"
) -> Tuple[str, str, str]:
    """
    Load environment-specific Supabase configuration and collection ID.

    Loads secrets in this order:
    1. Global environment file (.curator/secrets.{env}.env)
    2. Curator shared secrets (.curator/curators/{name}/secrets.env)
    3. Curator environment file (.curator/curators/{name}/secrets.{env}.env)

    Args:
        curator_name: Name of the curator (directory name)
        environment: Environment to load ("local" or "prod")

    Returns:
        Tuple of (supabase_url, supabase_key, collection_id)

    Raises:
        SystemExit: If required configuration is missing

    Example:
        url, key, coll_id = load_environment_config("LEGO Sets", "prod")
        supabase = create_client(url, key)
    """
    import os
    import sys
    from pathlib import Path

    # Validate environment
    if environment not in ["local", "prod"]:
        print(f"❌ Error: Invalid environment '{environment}'")
        print("   Valid options: local, prod")
        sys.exit(1)

    # Determine paths
    curator_root = Path(__file__).parent.parent
    global_env_file = curator_root / f"secrets.{environment}.env"
    curator_dir = curator_root / "curators" / curator_name
    curator_shared_file = curator_dir / "secrets.env"
    curator_env_file = curator_dir / f"secrets.{environment}.env"

    # Load global environment file
    if not global_env_file.exists():
        print(f"❌ Error: Global secrets file not found: {global_env_file}")
        print(f"   Create from template: cp {curator_root}/secrets.{environment}.env.example {global_env_file}")
        sys.exit(1)

    _load_env_file(global_env_file)

    # Load curator shared secrets (API keys, etc.)
    if curator_shared_file.exists():
        _load_env_file(curator_shared_file)

    # Load curator environment-specific file (collection ID)
    if not curator_env_file.exists():
        print(f"❌ Error: Curator environment secrets not found: {curator_env_file}")
        print(f"   Create from template: cp {curator_dir}/secrets.{environment}.env.example {curator_env_file}")
        sys.exit(1)

    _load_env_file(curator_env_file)

    # Validate required variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    collection_id = os.getenv("COLLECTION_ID")

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        print(f"   Check: {global_env_file}")
        sys.exit(1)

    if not collection_id:
        print("❌ Error: COLLECTION_ID not found")
        print(f"   Check: {curator_env_file}")
        print()
        print("   Create collection first:")
        print(f"     INSERT INTO entities (name, type) VALUES ('{curator_name}', 'collection');")
        print("   Then set COLLECTION_ID in the secrets file")
        sys.exit(1)

    return supabase_url, supabase_key, collection_id


def _load_env_file(file_path: Path):
    """
    Load environment variables from a file.

    Args:
        file_path: Path to the .env file
    """
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Set environment variable (don't override existing)
                import os
                if key not in os.environ:
                    os.environ[key] = value
