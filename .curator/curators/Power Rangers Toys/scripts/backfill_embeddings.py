#!/usr/bin/env python3
"""
Backfill vector embeddings for existing Power Rangers toys.

This script generates name embeddings for all toys that don't have them yet,
enabling semantic search functionality.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict

# Auto-install dependencies if missing
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "supabase"])
    from supabase import create_client, Client

# Add lib directory to path for shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))
from embedding_utils import EmbeddingGenerator

BATCH_SIZE = 100  # Process 100 entities at a time


class EmbeddingBackfiller:
    """Backfill embeddings for existing entities."""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.embedding_generator = EmbeddingGenerator()

    def get_entities_without_embeddings(self, limit: int = None) -> List[Dict]:
        """Get all entities that don't have embeddings yet."""
        query = self.supabase.table("entities").select("id, name, type").is_("name_embedding", "null")

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data

    def backfill_batch(self, entities: List[Dict]) -> tuple[int, int]:
        """
        Generate embeddings for a batch of entities.

        Returns:
            Tuple of (success_count, error_count)
        """
        if not entities:
            return 0, 0

        # Extract names for batch processing
        names = [entity["name"] for entity in entities]

        # Generate embeddings in batch (more efficient than one-by-one)
        print(f"  Generating {len(names)} embeddings...")
        embeddings = self.embedding_generator.generate_embeddings_batch(names)

        # Update entities with embeddings
        success = 0
        errors = 0

        for entity, embedding in zip(entities, embeddings):
            if embedding is None:
                print(f"    ⚠️  Skipping {entity['name']} (empty name)")
                errors += 1
                continue

            try:
                self.supabase.table("entities").update({
                    "name_embedding": embedding
                }).eq("id", entity["id"]).execute()

                success += 1
                if success % 10 == 0:
                    print(f"    ✓ {success} embeddings generated...")
            except Exception as e:
                print(f"    ⚠️  Error updating {entity['name']}: {e}")
                errors += 1

        return success, errors

    def backfill_all(self) -> tuple[int, int]:
        """
        Backfill embeddings for all entities.

        Returns:
            Tuple of (total_success, total_errors)
        """
        # Get count first
        all_entities = self.get_entities_without_embeddings()
        total = len(all_entities)

        if total == 0:
            print("✓ All entities already have embeddings!")
            return 0, 0

        print(f"Found {total} entities without embeddings")
        print(f"Processing in batches of {BATCH_SIZE}...")
        print()

        total_success = 0
        total_errors = 0

        # Process in batches
        for i in range(0, total, BATCH_SIZE):
            batch = all_entities[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"Batch {batch_num}/{total_batches} ({len(batch)} entities)")
            success, errors = self.backfill_batch(batch)

            total_success += success
            total_errors += errors

            print(f"  Batch complete: {success} success, {errors} errors")
            print()

        return total_success, total_errors


def load_config():
    """Load Supabase configuration from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        print("Either:")
        print("  1. Set environment variables")
        print("  2. Create secrets.env file in curator directory")
        sys.exit(1)

    return supabase_url, supabase_key


def main():
    print("=" * 60)
    print("Power Rangers Toy Embedding Backfill")
    print("=" * 60)
    print()

    # Load configuration
    supabase_url, supabase_key = load_config()
    supabase = create_client(supabase_url, supabase_key)

    # Confirm action
    print("This will generate vector embeddings for all toys without embeddings.")
    print("This enables semantic search functionality.")
    print()
    confirm = input("Continue? (y/N): ").strip().lower()

    if confirm != 'y':
        print("Cancelled.")
        return

    print()

    # Run backfill
    backfiller = EmbeddingBackfiller(supabase)
    success, errors = backfiller.backfill_all()

    print()
    print("=" * 60)
    print(f"✓ Backfill complete: {success} success, {errors} errors")
    print("=" * 60)


if __name__ == "__main__":
    main()
