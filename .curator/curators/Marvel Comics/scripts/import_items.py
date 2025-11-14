#!/usr/bin/env python3
"""Import fetched Marvel Comics into Supabase with image localization and embeddings."""

import argparse
import json
import os
import sys
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
CURATOR_NAME = "Marvel Comics"


class MarvelComicsImporter:
    """Import Marvel Comics to Supabase with best practices."""

    def __init__(self, supabase: Client, collection_id: str):
        self.supabase = supabase
        self.collection_id = collection_id
        self.series_cache = {}  # Cache series entities to avoid repeated lookups
        self.image_localizer = ImageLocalizer(supabase)  # For image downloads
        self.embedding_generator = EmbeddingGenerator()  # For semantic search
        self.image_results = []  # Track image validation results (for dry run)

    def get_or_create_series(self, series_name: str, year: Optional[int] = None) -> str:
        """Get or create a series entity (comic series), return its ID."""
        if not series_name:
            return self.collection_id  # Default to main collection if no series

        # Check cache
        cache_key = f"{series_name}_{year}"
        if cache_key in self.series_cache:
            return self.series_cache[cache_key]

        # Check if series exists
        query = self.supabase.table("entities").select("id").eq("name", series_name).eq("type", "collection")

        if year:
            query = query.eq("year", year)

        result = query.execute()

        if result.data:
            series_id = result.data[0]["id"]
            self.series_cache[cache_key] = series_id
            return series_id

        # Create series as a collection
        series_data = {
            "name": series_name,
            "type": "collection",
            "year": year,
            "attributes": {
                "start_year": year
            }
        }

        result = self.supabase.table("entities").insert(series_data).execute()
        series_id = result.data[0]["id"]

        # Link series to Marvel Comics collection
        self.supabase.table("relationships").insert({
            "from_id": self.collection_id,
            "to_id": series_id,
            "type": "contains"
        }).execute()

        self.series_cache[cache_key] = series_id
        print(f"  Created series: {series_name}")
        return series_id

    def check_comic_exists(self, marvel_id: int) -> Optional[str]:
        """Check if comic already exists using Marvel API ID."""
        if not marvel_id:
            return None

        # Query for entity with matching Marvel API ID
        result = self.supabase.table("entities").select("id").eq(
            "external_ids->>marvel_api", str(marvel_id)
        ).execute()

        if result.data:
            return result.data[0]["id"]

        return None

    def update_comic_parent(self, comic_id: str, new_series_id: str, comic_name: str) -> str:
        """
        Update comic's parent relationship from old series to new series.

        This is critical for maintaining collections when hierarchy changes.
        """
        # Find current parent relationships
        existing_rels = self.supabase.table("relationships").select("id,from_id").eq(
            "to_id", comic_id
        ).eq("type", "contains").execute()

        # Delete old parent relationships (from old series)
        for rel in existing_rels.data:
            self.supabase.table("relationships").delete().eq("id", rel["id"]).execute()

        # Create new relationship to series
        try:
            self.supabase.table("relationships").insert({
                "from_id": new_series_id,
                "to_id": comic_id,
                "type": "contains"
            }).execute()
            return f"Updated parent: {comic_name} → series"
        except Exception as e:
            # Relationship might already exist
            if '409' in str(e) or 'unique' in str(e).lower():
                return f"Re-linked: {comic_name} (relationship already exists)"
            raise

    def import_comic(self, comic_data: Dict, series_id: str) -> Tuple[bool, str]:
        """Import a single comic. Returns (success, message)."""
        name = comic_data["name"]
        year = comic_data.get("year")
        marvel_id = comic_data.get("id")
        issue_number = comic_data.get("issue_number", 0)
        external_image_url = comic_data.get("image_url")

        # Check if comic already exists
        existing_id = self.check_comic_exists(marvel_id)
        if existing_id:
            # MAINTAIN MODE: Update relationship if parent changed
            message = self.update_comic_parent(existing_id, series_id, name)
            return True, message

        # CREATE MODE: Generate entity ID upfront (needed for image storage paths)
        entity_id = str(uuid.uuid4())

        # Localize image if present
        image_url = None
        thumbnail_url = None
        if external_image_url:
            print(f"      Processing images for: {name}")

            # Capture validation result if in dry run
            if hasattr(self.image_localizer, 'image_validator') and self.image_localizer.image_validator:
                result = self.image_localizer.image_validator.validate_image(external_image_url)
                self.image_results.append(result)

            image_url, thumbnail_url = self.image_localizer.localize_image(external_image_url, entity_id)
            if not image_url:
                print(f"        ⚠️  Image localization failed, using external URL")
                image_url = external_image_url

        # Generate embedding for semantic search
        name_embedding = self.embedding_generator.generate_embedding(name)

        # Prepare entity data with proper metadata structure
        entity_data = {
            "id": entity_id,
            "name": name,
            "type": "comic",
            "year": year,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "name_embedding": name_embedding,
            "source_url": comic_data.get("source_url"),
            "external_ids": {
                "marvel_api": str(marvel_id)
            },
            "attributes": {
                "writers": comic_data.get("writers", []),
                "artists": comic_data.get("artists", []),
                "issue_number": issue_number,
                "series_name": comic_data.get("series_name")
            }
        }

        try:
            # Create entity
            result = self.supabase.table("entities").insert(entity_data).execute()

            # Link to series with order = issue number
            self.supabase.table("relationships").insert({
                "from_id": series_id,
                "to_id": entity_id,
                "type": "contains",
                "order": int(issue_number) if issue_number else None
            }).execute()

            thumb_status = "with thumbnail" if thumbnail_url else "original only"
            return True, f"✓ Imported: {name} (#{issue_number}) - {thumb_status}"

        except Exception as e:
            return False, f"Error importing {name}: {str(e)}"

    def import_all_comics(self, comics: list) -> Tuple[int, int, int, int]:
        """
        Import all comics grouped by series.

        Returns (series_imported, comics_created, comics_updated, comics_skipped).
        """
        # Group comics by series
        series_comics = {}
        for comic in comics:
            series_name = comic.get("series_name", "Unknown Series")
            if series_name not in series_comics:
                series_comics[series_name] = []
            series_comics[series_name].append(comic)

        series_imported = 0
        comics_created = 0
        comics_updated = 0
        comics_skipped = 0

        for series_name, series_comic_list in series_comics.items():
            # Get year from first comic in series
            year = None
            for comic in series_comic_list:
                if comic.get("year"):
                    year = comic["year"]
                    break

            print(f"\nProcessing series: {series_name}")

            # Get or create series
            series_id = self.get_or_create_series(series_name, year)
            series_imported += 1

            # Import all comics in this series
            for comic_data in series_comic_list:
                success, message = self.import_comic(comic_data, series_id)
                print(f"    {message}")

                if success:
                    # Distinguish between created and updated
                    if "Updated parent" in message or "Re-linked" in message:
                        comics_updated += 1
                    else:
                        comics_created += 1
                else:
                    comics_skipped += 1

        return series_imported, comics_created, comics_updated, comics_skipped




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
        description="Import Marvel Comics to Supabase database"
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
    print("Marvel Comics Importer")
    print(f"Environment: {args.env}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be written to database")
    print("=" * 60)
    print()

    # DRY RUN: Run fetch script first to get real data
    if args.dry_run:
        print("Step 1: Fetching data from Marvel API...")
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
                print("Check your Marvel API keys in secrets.env")
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
    comics = load_fetched_data()
    print(f"Found {len(comics)} comics to import")
    print()

    # Import comics
    if not args.dry_run:
        print("Loading embedding model: sentence-transformers/all-MiniLM-L6-v2")

    importer = MarvelComicsImporter(supabase, collection_id)

    # Pass validator to image localizer if present
    if image_validator:
        importer.image_localizer = ImageLocalizer(supabase, image_validator=image_validator)

    if not args.dry_run:
        print("✓ Model loaded\n")

    series_imported, comics_created, comics_updated, comics_skipped = importer.import_all_comics(comics)

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
        print(f"  Series: {series_imported}")
        print(f"  Comics created: {comics_created}")
        print(f"  Comics updated (re-linked): {comics_updated}")
        print(f"  Comics skipped: {comics_skipped}")
        print(f"  Total comics processed: {comics_created + comics_updated}")

    print("=" * 60)


if __name__ == "__main__":
    main()
