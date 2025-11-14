#!/usr/bin/env python3
"""
Import American comic books into Supabase with multi-collection structure.

Architecture:
  Publisher Collections (independent top-level)
  └─ Series Collections
     └─ Comic Issues (with order = issue number)

Follows all curator best practices from .curator/README.md.
"""

import argparse
import os
import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple
from collections import defaultdict

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
from curator_utils import check_exists_by_semantic_search, MetadataValidator, load_environment_config

FETCHED_FILE = "fetched_data.json"
CURATOR_NAME = "American Comics"


class ComicImporter:
    """Import comic books to Supabase with multi-collection architecture."""

    def __init__(self, supabase: Client):
        self.supabase = supabase

        # REQUIRED: Use shared libraries
        self.image_localizer = ImageLocalizer(supabase)
        self.embedding_generator = EmbeddingGenerator()

        # Caches
        self.publisher_collections = {}  # publisher_name -> collection_id
        self.series_collections = {}  # (publisher_id, series_name) -> collection_id

        # Metadata validation for comic books
        self.required_metadata_fields = ["series_name", "issue_number", "publisher_name"]
        self.metadata_validator = MetadataValidator(self.required_metadata_fields)

    def check_exists(self, metron_id: str, comic_name: str = None) -> Optional[str]:
        """
        Check if comic exists by Metron ID, with semantic search fallback.
        """
        # Try external ID first (fastest, most reliable)
        if metron_id:
            result = self.supabase.table("entities").select("id").eq(
                "external_ids->>metron",
                str(metron_id)
            ).execute()

            if result.data:
                return result.data[0]["id"]

        # Fallback to semantic search if external ID not found/available
        if comic_name:
            return check_exists_by_semantic_search(
                self.supabase,
                comic_name,
                entity_type="comic",
                threshold=0.95
            )

        return None

    def find_or_create_publisher_collection(self, publisher_name: str) -> str:
        """
        Find or create a publisher collection (independent top-level).
        """
        # Check cache
        if publisher_name in self.publisher_collections:
            return self.publisher_collections[publisher_name]

        # Search for existing publisher collection
        result = self.supabase.table("entities").select("id").eq(
            "name", publisher_name
        ).eq("type", "collection").execute()

        if result.data:
            collection_id = result.data[0]["id"]
            self.publisher_collections[publisher_name] = collection_id
            return collection_id

        # Create new publisher collection
        collection_id = str(uuid.uuid4())

        entity_data = {
            "id": collection_id,
            "name": publisher_name,
            "type": "collection",
            "attributes": {}  # No metadata for publisher collections
        }

        self.supabase.table("entities").insert(entity_data).execute()
        print(f"    Created publisher collection: {publisher_name}")

        self.publisher_collections[publisher_name] = collection_id
        return collection_id

    def find_or_create_series_collection(
        self,
        series_name: str,
        publisher_id: str,
        year: Optional[int] = None,
        publisher_name: Optional[str] = None,
        writers: Optional[list] = None,
        artists: Optional[list] = None
    ) -> str:
        """
        Find or create a series collection under a publisher.
        """
        cache_key = (publisher_id, series_name)

        # Check cache
        if cache_key in self.series_collections:
            return self.series_collections[cache_key]

        # Search for existing series collection
        # First try exact name match
        result = self.supabase.table("entities").select("id").eq(
            "name", series_name
        ).eq("type", "collection").execute()

        # If found, verify it's under the right publisher
        if result.data:
            series_id = result.data[0]["id"]

            # Check if it's already linked to this publisher
            rel_check = self.supabase.table("relationships").select("id").eq(
                "from_id", publisher_id
            ).eq("to_id", series_id).eq("type", "contains").execute()

            if rel_check.data:
                self.series_collections[cache_key] = series_id
                return series_id

        # Create new series collection
        series_id = str(uuid.uuid4())

        # Add year to series name if provided
        display_name = f"{series_name} ({year})" if year else series_name

        # Build attributes
        attributes = {}
        if publisher_name:
            attributes["publisher"] = publisher_name
        if writers:
            attributes["writers"] = writers
        if artists:
            attributes["artists"] = artists

        entity_data = {
            "id": series_id,
            "name": display_name,
            "type": "collection",
            "year": year,
            "attributes": attributes
        }

        # Clean up None values
        entity_data = {k: v for k, v in entity_data.items() if v is not None}

        self.supabase.table("entities").insert(entity_data).execute()

        # Link to publisher
        self.supabase.table("relationships").insert({
            "from_id": publisher_id,
            "to_id": series_id,
            "type": "contains"
        }).execute()

        print(f"    Created series collection: {display_name}")

        self.series_collections[cache_key] = series_id
        return series_id

    def import_comic(
        self,
        comic_data: Dict,
        series_id: str
    ) -> Tuple[bool, str]:
        """
        Import a single comic issue.
        """
        name = comic_data.get("name")
        metron_id = comic_data.get("id")
        issue_number = comic_data.get("issue_number", "")

        # Validate metadata
        if self.required_metadata_fields:
            validation_warnings = self.metadata_validator.validate(comic_data, name)
            # Warnings are collected, import continues

        # REQUIRED: Check for duplicates (external ID first, semantic search fallback)
        existing_id = self.check_exists(metron_id, comic_name=name)
        if existing_id:
            return True, f"Exists: {name}"

        # REQUIRED: Generate entity ID upfront
        entity_id = str(uuid.uuid4())

        # REQUIRED: Localize image if present
        image_url = None
        thumbnail_url = None
        external_image_url = comic_data.get("image_url")

        if external_image_url:
            image_url, thumbnail_url = self.image_localizer.localize_image(
                external_image_url,
                entity_id
            )

            if not image_url:
                # Fallback to external URL if localization failed
                image_url = external_image_url

        # REQUIRED: Generate embedding for semantic search
        name_embedding = self.embedding_generator.generate_embedding(name)

        # Build attributes
        attributes = {}
        if comic_data.get("publisher"):
            attributes["publisher"] = comic_data["publisher"]
        if comic_data.get("writers"):
            attributes["writers"] = comic_data["writers"]
        if comic_data.get("artists"):
            attributes["artists"] = comic_data["artists"]

        # REQUIRED: Follow metadata schema
        entity_data = {
            "id": entity_id,
            "name": name,
            "type": "comic",

            # UNIVERSAL FIELDS
            "year": comic_data.get("year"),

            # IMAGES
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,

            # METADATA
            "name_embedding": name_embedding,
            "source_url": comic_data.get("source_url"),

            # EXTERNAL IDS
            "external_ids": {
                "metron": metron_id
            },

            # ATTRIBUTES
            "attributes": attributes
        }

        # Clean up None values
        entity_data = {k: v for k, v in entity_data.items() if v is not None}

        try:
            # Create entity
            self.supabase.table("entities").insert(entity_data).execute()

            # Parse issue number for order column (must be integer for DB)
            order_value = None
            if issue_number:
                try:
                    # Try to parse as integer first
                    order_value = int(float(issue_number))  # Handle "1.0" -> 1
                except ValueError:
                    # Handle issue numbers like "1A", "Annual 1", etc.
                    # Extract leading numeric part
                    import re
                    match = re.match(r'(\d+)', str(issue_number))
                    if match:
                        order_value = int(match.group(1))

            # Link to series with order
            relationship_data = {
                "from_id": series_id,
                "to_id": entity_id,
                "type": "contains"
            }
            if order_value is not None:
                relationship_data["order"] = order_value

            self.supabase.table("relationships").insert(relationship_data).execute()

            # Progress reporting
            thumb_status = (
                "with thumbnail" if thumbnail_url
                else "original only" if image_url
                else "no image"
            )
            return True, f"✓ Imported: {name} - {thumb_status}"

        except Exception as e:
            return False, f"Error importing {name}: {str(e)}"

    def import_all(self, comics: list) -> Tuple[int, int, int]:
        """
        Import all comics with progress tracking.

        Returns (created, skipped, failed) counts.
        """
        # Group comics by publisher and series
        grouped = defaultdict(lambda: defaultdict(list))

        for comic in comics:
            publisher = comic.get("publisher", "Unknown Publisher")
            series_name = comic.get("series_name", "Unknown Series")
            grouped[publisher][series_name].append(comic)

        created = 0
        skipped = 0
        failed = 0

        for publisher_name, series_dict in grouped.items():
            print(f"\n{'=' * 60}")
            print(f"Publisher: {publisher_name}")
            print(f"{'=' * 60}")

            # Find or create publisher collection
            publisher_id = self.find_or_create_publisher_collection(publisher_name)

            for series_name, issues in series_dict.items():
                print(f"\n  Series: {series_name} ({len(issues)} issues)")

                # Get series metadata from first issue
                first_issue = issues[0]
                year = first_issue.get("year")
                writers = first_issue.get("writers", [])
                artists = first_issue.get("artists", [])

                # Find or create series collection
                series_id = self.find_or_create_series_collection(
                    series_name,
                    publisher_id,
                    year=year,
                    publisher_name=publisher_name,
                    writers=writers,
                    artists=artists
                )

                # Import each issue
                for i, issue in enumerate(issues, 1):
                    success, message = self.import_comic(issue, series_id)
                    print(f"    [{i}/{len(issues)}] {message}")

                    if success:
                        if "Exists" in message:
                            skipped += 1
                        else:
                            created += 1
                    else:
                        failed += 1

        # Report metadata validation issues
        if self.metadata_validator.has_warnings():
            print()
            print(self.metadata_validator.get_summary())

        return created, skipped, failed


def main():
    parser = argparse.ArgumentParser(
        description="Import American comics from Metron API data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate images without importing"
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
    print("American Comics - Import to Supabase")
    print(f"Environment: {args.env}")
    print("=" * 60)
    print()

    # Load configuration
    supabase_url, supabase_key, collection_id = load_environment_config(
        CURATOR_NAME,
        args.env
    )

    # Initialize Supabase client
    supabase = create_client(supabase_url, supabase_key)

    # Load fetched data
    fetched_path = Path(__file__).parent.parent / FETCHED_FILE
    if not fetched_path.exists():
        print(f"Error: {fetched_path} not found")
        print("Run fetch_data.py first to fetch comic data")
        sys.exit(1)

    with open(fetched_path) as f:
        comics = json.load(f)

    print(f"Loaded {len(comics)} comics from {fetched_path.name}")
    print()

    # Create importer
    importer = ComicImporter(supabase)

    if args.dry_run:
        print("DRY RUN MODE - Validating images only")
        print()
        # TODO: Add dry run validation logic
        print("Dry run not yet implemented")
        return

    # Import all comics
    created, skipped, failed = importer.import_all(comics)

    # Final report
    print()
    print("=" * 60)
    print("Import Complete")
    print("=" * 60)
    print(f"  Created: {created}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(comics)}")


if __name__ == "__main__":
    main()
