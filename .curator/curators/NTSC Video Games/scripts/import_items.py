#!/usr/bin/env python3
"""
Import NTSC video games into Supabase with image localization and embeddings.

Follows all curator best practices from .curator/README.md.
"""

import argparse
import os
import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

# Auto-install dependencies if missing
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "supabase"
    ])
    from supabase import create_client, Client

# Add lib directory to path for shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))
from image_utils import ImageLocalizer
from embedding_utils import EmbeddingGenerator
from curator_utils import load_environment_config

FETCHED_FILE = "fetched_data.json"
CURATOR_NAME = "NTSC Video Games"


class GameImporter:
    """Import video games to Supabase with best practices."""

    def __init__(self, supabase: Client, collection_id: str):
        self.supabase = supabase
        self.collection_id = collection_id

        # REQUIRED: Use shared libraries
        self.image_localizer = ImageLocalizer(supabase)
        self.embedding_generator = EmbeddingGenerator()

        # Track image validation results (for dry run)
        self.image_results = []

    def check_exists(self, moby_id: str) -> Optional[str]:
        """
        Check if game exists by MobyGames compound ID (game_id-platform_id).
        """
        if not moby_id:
            return None

        result = self.supabase.table("entities").select("id").eq(
            "external_ids->>moby_games",
            moby_id
        ).execute()

        if result.data:
            return result.data[0]["id"]
        return None

    def update_parent_relationship(self, entity_id: str, new_parent_id: str, entity_name: str) -> str:
        """
        Update entity's parent relationship when hierarchy changes.
        """
        # Find current parent relationships
        existing_rels = self.supabase.table("relationships").select("id,from_id").eq(
            "to_id", entity_id
        ).eq("type", "contains").execute()

        # Delete old parent relationships
        for rel in existing_rels.data:
            self.supabase.table("relationships").delete().eq("id", rel["id"]).execute()

        # Create new relationship to correct parent
        try:
            self.supabase.table("relationships").insert({
                "from_id": new_parent_id,
                "to_id": entity_id,
                "type": "contains"
            }).execute()
            return f"Updated parent: {entity_name}"
        except Exception as e:
            # Relationship might already exist
            if '409' in str(e) or 'unique' in str(e).lower():
                return f"Re-linked: {entity_name} (relationship already exists)"
            raise

    def import_game(self, game_data: Dict) -> Tuple[bool, str]:
        """
        Import a single game with images and embeddings.
        """
        name = game_data.get("name")
        moby_id = game_data.get("id")  # Compound ID: "gameid-platformid"

        # REQUIRED: Check for duplicates
        existing_id = self.check_exists(moby_id)
        if existing_id:
            # MAINTAIN MODE: Update relationship if parent changed
            message = self.update_parent_relationship(existing_id, self.collection_id, name)
            return True, message

        # REQUIRED: Generate entity ID upfront (needed for storage paths)
        entity_id = str(uuid.uuid4())

        # REQUIRED: Localize image if present
        image_url = None
        thumbnail_url = None
        external_image_url = game_data.get("image_url")

        if external_image_url:
            print(f"    Processing images for: {name}")

            # Capture validation result if in dry run
            if hasattr(self.image_localizer, 'image_validator') and self.image_localizer.image_validator:
                result = self.image_localizer.image_validator.validate_image(external_image_url)
                self.image_results.append(result)

            image_url, thumbnail_url = self.image_localizer.localize_image(
                external_image_url,
                entity_id
            )

            if not image_url:
                # Fallback to external URL if localization failed
                print(f"      ⚠️  Image localization failed, using external URL")
                image_url = external_image_url

        # REQUIRED: Generate embedding for semantic search
        name_embedding = self.embedding_generator.generate_embedding(name)

        # REQUIRED: Follow metadata schema
        entity_data = {
            "id": entity_id,
            "name": name,
            "type": "video_game",

            # UNIVERSAL FIELDS: Use dedicated columns
            "year": game_data.get("year"),
            "language": game_data.get("language"),  # "en"
            "country": game_data.get("country"),    # "US"

            # IMAGES: Always use localized paths
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,

            # METADATA
            "name_embedding": name_embedding,
            "source_url": game_data.get("source_url"),

            # EXTERNAL IDS: For deduplication
            "external_ids": {
                "moby_games": moby_id  # Compound: "gameid-platformid"
            },

            # ATTRIBUTES: Domain-specific metadata
            "attributes": {
                "platform": game_data.get("platform"),
                "publisher": game_data.get("publisher"),
                "developer": game_data.get("developer"),
            }
        }

        # Clean up None values
        entity_data = {k: v for k, v in entity_data.items() if v is not None}
        if entity_data.get("attributes"):
            entity_data["attributes"] = {
                k: v for k, v in entity_data["attributes"].items()
                if v is not None
            }
        else:
            entity_data["attributes"] = {}

        try:
            # Create entity
            self.supabase.table("entities").insert(entity_data).execute()

            # Link to collection
            self.supabase.table("relationships").insert({
                "from_id": self.collection_id,
                "to_id": entity_id,
                "type": "contains"
            }).execute()

            # REQUIRED: Clear progress reporting
            thumb_status = (
                "with thumbnail" if thumbnail_url
                else "original only" if image_url
                else "no image"
            )
            return True, f"✓ Imported: {name} - {thumb_status}"

        except Exception as e:
            return False, f"Error importing {name}: {str(e)}"

    def import_all(self, games: list) -> Tuple[int, int, int]:
        """
        Import all games with progress tracking.

        Returns (created, updated, failed) counts.
        """
        created = 0
        updated = 0
        failed = 0

        total = len(games)
        for i, game in enumerate(games, 1):
            success, message = self.import_game(game)
            print(f"  [{i}/{total}] {message}")

            if success:
                # Distinguish between created and updated
                if "Updated parent" in message or "Re-linked" in message:
                    updated += 1
                else:
                    created += 1
            else:
                failed += 1

        return created, updated, failed




def load_fetched_data() -> list:
    """Load data from fetch script."""
    data_file = Path(__file__).parent.parent / FETCHED_FILE

    if not data_file.exists():
        print(f"Error: {FETCHED_FILE} not found")
        print("Run fetch_data.py first")
        sys.exit(1)

    with open(data_file) as f:
        return json.load(f)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Import NTSC video games to Supabase database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate import without writing to database'
    )
    parser.add_argument(
        '--env',
        choices=['local', 'prod'],
        default='local',
        help='Environment to import to (default: local)'
    )
    args = parser.parse_args()

    # Warn if using default environment
    if not any(arg.startswith('--env') for arg in sys.argv):
        print("⚠️  No --env specified, defaulting to local")
        print()

    print("=" * 60)
    print("NTSC Video Games Importer")
    print(f"Environment: {args.env}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be written to database")
    print("=" * 60)
    print()

    # DRY RUN: Run fetch script first to get real data
    if args.dry_run:
        print("Step 1: Fetching data from source...")
        print("-" * 60)
        fetch_script = Path(__file__).parent / "fetch_data.py"

        if fetch_script.exists():
            import subprocess
            result = subprocess.run(
                [sys.executable, str(fetch_script)],
                capture_output=False,
                cwd=Path(__file__).parent.parent
            )

            if result.returncode != 0:
                print("\n⚠️  Fetch failed - cannot proceed with dry run")
                print("Check your API keys/credentials in secrets.env")
                sys.exit(1)
        else:
            print("⚠️  fetch_data.py not found - skipping fetch step")

        print()
        print("=" * 60)
        print("Step 2: Validating import (dry run)")
        print("=" * 60)
        print()

    # Load configuration
    supabase_url, supabase_key, collection_id = load_environment_config(
        CURATOR_NAME,
        args.env
    )

    # Use mock or real client
    if args.dry_run:
        from dry_run_utils import MockSupabaseClient, ImageValidator, DryRunOutput
        supabase = MockSupabaseClient()
        image_validator = ImageValidator()
    else:
        supabase = create_client(supabase_url, supabase_key)
        image_validator = None

    # Load fetched data
    print("Loading fetched data...")
    games = load_fetched_data()
    print(f"Found {len(games)} games to import")
    print()

    # Import games
    if not args.dry_run:
        print("Loading embedding model: sentence-transformers/all-MiniLM-L6-v2")

    importer = GameImporter(supabase, collection_id)

    # Pass validator to image localizer if present
    if image_validator:
        importer.image_localizer = ImageLocalizer(supabase, image_validator=image_validator)

    if not args.dry_run:
        print("✓ Model loaded\n")

    created, updated, failed = importer.import_all(games)

    print()
    print("=" * 60)

    # Generate dry run output
    if args.dry_run:
        output = DryRunOutput(supabase, importer.image_results)
        output.print_yaml(max_entities=3)
        output.save_json('dry_run_results.json')
        print(f"\n✓ Dry run complete. Full results saved to dry_run_results.json")
    else:
        print(f"✓ Complete:")
        print(f"  Created: {created}")
        print(f"  Updated (re-linked): {updated}")
        print(f"  Failed: {failed}")
        print(f"  Total processed: {created + updated}")

    print("=" * 60)


if __name__ == "__main__":
    main()
