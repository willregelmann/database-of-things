#!/usr/bin/env python3
"""Import LEGO sets into Supabase with image localization and embeddings."""

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

FETCHED_FILE = "fetched_data.json"


class LegoSetImporter:
    """Import LEGO sets to Supabase with best practices."""

    def __init__(self, supabase: Client, collection_id: str):
        self.supabase = supabase
        self.collection_id = collection_id
        self.image_localizer = ImageLocalizer(supabase)
        self.embedding_generator = EmbeddingGenerator()

        # Track image validation results (for dry run)
        self.image_results = []

    def check_exists(self, set_num: str) -> Optional[str]:
        """Check if set exists by Rebrickable set_num."""
        if not set_num:
            return None

        result = self.supabase.table("entities").select("id").eq(
            "external_ids->>rebrickable_set_num",
            set_num
        ).execute()

        if result.data:
            return result.data[0]["id"]
        return None

    def update_parent_relationship(self, entity_id: str, new_parent_id: str, entity_name: str) -> str:
        """Update entity's parent relationship when hierarchy changes."""
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

    def import_set(self, set_data: Dict) -> Tuple[bool, str]:
        """Import a single LEGO set with images and embeddings."""
        name = set_data.get("name", "Unnamed Set")
        set_num = set_data.get("set_num")  # e.g., "10497-1"
        theme_id = set_data.get("theme_id")  # Rebrickable theme ID

        if not set_num:
            return False, f"Error: Missing set_num for {name}"

        # Check for duplicates
        existing_id = self.check_exists(set_num)
        if existing_id:
            # MAINTAIN MODE: Update relationship if parent changed
            message = self.update_parent_relationship(existing_id, self.collection_id, name)
            return True, message  # Return success, not skip!

        # Generate entity ID upfront (needed for storage paths)
        entity_id = str(uuid.uuid4())

        # Localize image if present
        image_url = None
        thumbnail_url = None
        external_image_url = set_data.get("set_img_url")

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

        # Generate embedding for semantic search
        name_embedding = self.embedding_generator.generate_embedding(name)

        # Build source URL (Rebrickable provides set_url)
        source_url = set_data.get("set_url")
        if not source_url and set_num:
            # Fallback: construct URL from set_num
            source_url = f"https://rebrickable.com/sets/{set_num}/"

        # Create entity with proper schema
        entity_data = {
            "id": entity_id,
            "name": name,
            "type": "lego_set",
            "year": set_data.get("year"),
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "name_embedding": name_embedding,
            "source_url": source_url,
            "external_ids": {
                "rebrickable_set_num": set_num,
                "rebrickable_theme_id": str(theme_id) if theme_id else None
            },
            "attributes": {
                "pieces": set_data.get("num_parts")
            }
        }

        # Remove None values from external_ids
        entity_data["external_ids"] = {k: v for k, v in entity_data["external_ids"].items() if v is not None}

        # Remove None values from attributes
        entity_data["attributes"] = {k: v for k, v in entity_data["attributes"].items() if v is not None}

        # Remove None values from top-level
        entity_data = {k: v for k, v in entity_data.items() if v is not None}

        try:
            # Create entity
            self.supabase.table("entities").insert(entity_data).execute()

            # Link to theme collection
            self.supabase.table("relationships").insert({
                "from_id": self.collection_id,
                "to_id": entity_id,
                "type": "contains"
            }).execute()

            thumb_status = "with thumbnail" if thumbnail_url else "original only" if image_url else "no image"
            return True, f"✓ Imported: {name} ({set_num}) - {thumb_status}"

        except Exception as e:
            return False, f"Error importing {name}: {str(e)}"

    def import_all(self, sets: list) -> Tuple[int, int, int]:
        """Import all sets with progress tracking."""
        created = 0
        updated = 0
        failed = 0

        total = len(sets)
        for i, set_data in enumerate(sets, 1):
            success, message = self.import_set(set_data)
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


def load_config():
    """Load Supabase configuration from environment.

    Supabase credentials are expected in the global .curator/secrets.env file.
    Collection ID and curator-specific config are in curator's secrets.env.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    collection_id = os.getenv("COLLECTION_ID")

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        print("\nSupabase credentials should be in: .curator/secrets.env")
        print("Curator-specific config should be in: .curator/curators/<name>/secrets.env")
        print("\nTo run with both:")
        print("  cd .curator/curators/<name>")
        print("  set -a && source ../../secrets.env && source secrets.env && set +a")
        print("  python3 scripts/import_items.py")
        sys.exit(1)

    if not collection_id:
        print("❌ Error: COLLECTION_ID must be set")
        print("\nCreate a theme collection entity first, then set its ID:")
        print("  COLLECTION_ID=uuid-from-database")
        sys.exit(1)

    return supabase_url, supabase_key, collection_id


def load_fetched_data() -> list:
    """Load data from fetch script."""
    data_file = Path(__file__).parent.parent / FETCHED_FILE

    if not data_file.exists():
        print(f"❌ Error: {FETCHED_FILE} not found")
        print("Run fetch_data.py first:")
        print("  python3 scripts/fetch_data.py")
        sys.exit(1)

    with open(data_file) as f:
        return json.load(f)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Import LEGO sets to Supabase database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate import without writing to database'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("LEGO Set Importer - Rebrickable")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be written to database")
    print("=" * 60)
    print()

    # Load configuration
    supabase_url, supabase_key, collection_id = load_config()

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
    sets = load_fetched_data()
    print(f"Found {len(sets)} sets to import")
    print()

    # Import sets
    if not args.dry_run:
        print("Loading embedding model: sentence-transformers/all-MiniLM-L6-v2")

    importer = LegoSetImporter(supabase, collection_id)

    # Pass validator to image localizer if present
    if image_validator:
        importer.image_localizer = ImageLocalizer(supabase, image_validator=image_validator)

    if not args.dry_run:
        print("✓ Model loaded\n")

    created, updated, failed = importer.import_all(sets)

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
