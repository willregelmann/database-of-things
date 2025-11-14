#!/usr/bin/env python3
"""Import Labubu figures to Supabase database."""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

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

# Add curator lib to path
curator_lib = Path(__file__).parent.parent.parent.parent / "lib"
sys.path.insert(0, str(curator_lib))

try:
    from image_utils import ImageLocalizer
    from embedding_utils import EmbeddingGenerator
    from curator_utils import check_exists_by_semantic_search, load_environment_config
except ImportError as e:
    print(f"❌ Error: Could not import curator utilities: {e}")
    print(f"Expected path: {curator_lib}")
    sys.exit(1)

FETCHED_DATA_FILE = Path(__file__).parent.parent / "fetched_data.json"
CURATOR_NAME = "Labubu"


class MockSupabaseClient:
    """Mock Supabase client for dry run testing."""

    def __init__(self):
        self.entities_created = []
        self.relationships_created = []

    def table(self, name: str):
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, field: str, value):
        # Return empty for dry run
        self.data = []
        return self

    def execute(self):
        return self

    def insert(self, data):
        if isinstance(data, dict):
            self.entities_created.append(data)
        return self


class LabubuImporter:
    """Imports Labubu figures from fetched data to Supabase."""

    def __init__(self, supabase: Client, collection_id: str, dry_run: bool = False):
        self.supabase = supabase
        self.collection_id = collection_id
        self.dry_run = dry_run

        # Initialize utilities
        if not dry_run:
            self.image_localizer = ImageLocalizer(supabase)
            self.embedding_generator = EmbeddingGenerator()
        else:
            self.image_localizer = None
            self.embedding_generator = None

        # Track statistics
        self.stats = {
            "series_created": 0,
            "series_updated": 0,
            "figures_created": 0,
            "figures_updated": 0,
            "figures_failed": 0,
            "relationships_created": 0
        }

    def check_series_exists(self, series_slug: str) -> Optional[str]:
        """Check if series already exists by external ID.

        Args:
            series_slug: Series slug for lookup

        Returns:
            Entity ID if exists, None otherwise
        """
        if self.dry_run:
            return None

        result = self.supabase.table("entities").select("id").eq(
            "external_ids->>popmartworld_slug",
            series_slug
        ).execute()

        if result.data:
            return result.data[0]["id"]

        return None

    def check_figure_exists(self, figure_slug: str, figure_name: str, series_name: str) -> Optional[str]:
        """Check if figure already exists by external ID or semantic search.

        Args:
            figure_slug: Figure slug for lookup
            figure_name: Figure name for semantic search fallback
            series_name: Series name to include in semantic search

        Returns:
            Entity ID if exists, None otherwise
        """
        if self.dry_run:
            return None

        # Try external ID first (fastest)
        result = self.supabase.table("entities").select("id").eq(
            "external_ids->>popmartworld_slug",
            figure_slug
        ).execute()

        if result.data:
            return result.data[0]["id"]

        # Fallback to semantic search
        search_name = f"{series_name} - {figure_name}"
        return check_exists_by_semantic_search(
            self.supabase,
            search_name,
            entity_type="figure",
            threshold=0.95
        )

    def create_or_update_series(self, series_data: dict) -> Tuple[str, bool]:
        """Create or update a series collection entity.

        Args:
            series_data: Series data from fetched_data.json

        Returns:
            Tuple of (entity_id, is_new)
        """
        series_slug = series_data["slug"]
        series_name = series_data.get("name") or series_slug.replace('-', ' ').title()

        # Check if series exists
        existing_id = self.check_series_exists(series_slug)

        if existing_id:
            self.stats["series_updated"] += 1
            return existing_id, False

        # Create new series entity
        entity_data = {
            "name": series_name,
            "type": "collection",
            "year": series_data.get("year"),
            "source_url": series_data["url"],
            "external_ids": {
                "popmartworld_slug": series_slug,
                "popmartworld_url": series_data["url"]
            },
            "attributes": {}
        }

        # Add optional metadata
        if series_data.get("size"):
            entity_data["attributes"]["size"] = series_data["size"]
        if series_data.get("release_date"):
            entity_data["attributes"]["release_date"] = series_data["release_date"]

        if self.dry_run:
            print(f"    [DRY RUN] Would create series: {series_name}")
            self.stats["series_created"] += 1
            return "dry-run-series-id", True

        # Create entity
        result = self.supabase.table("entities").insert(entity_data).execute()
        series_id = result.data[0]["id"]

        # Create relationship to main collection
        self.supabase.table("relationships").insert({
            "from_id": self.collection_id,
            "to_id": series_id,
            "type": "contains"
        }).execute()

        self.stats["series_created"] += 1
        self.stats["relationships_created"] += 1

        return series_id, True

    def create_or_update_figure(self, figure_data: dict, series_data: dict, series_id: str) -> bool:
        """Create or update a figure entity.

        Args:
            figure_data: Figure data from fetched_data.json
            series_data: Parent series data
            series_id: Parent series entity ID

        Returns:
            True if successful, False otherwise
        """
        figure_slug = figure_data["slug"]
        figure_name = figure_data["name"]
        series_name = series_data.get("name", series_data["slug"])

        try:
            # Check if figure exists
            existing_id = self.check_figure_exists(figure_slug, figure_name, series_name)

            if existing_id:
                # Update parent relationship (figure can belong to multiple series)
                if not self.dry_run:
                    self.supabase.table("relationships").insert({
                        "from_id": series_id,
                        "to_id": existing_id,
                        "type": "contains"
                    }).execute()
                    self.stats["relationships_created"] += 1

                self.stats["figures_updated"] += 1
                return True

            # Localize image if not dry run
            image_url = None
            thumbnail_url = None

            if not self.dry_run and figure_data.get("image_url"):
                image_url, thumbnail_url = self.image_localizer.localize_image(
                    figure_data["image_url"],
                    f"labubu-{figure_slug}"
                )

            # Generate embedding if not dry run
            name_embedding = None
            if not self.dry_run:
                search_name = f"{series_name} - {figure_name}"
                name_embedding = self.embedding_generator.generate_embedding(search_name)

            # Create figure entity
            entity_data = {
                "name": figure_name,
                "type": "figure",
                "year": series_data.get("year"),
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "source_url": series_data["url"],
                "name_embedding": name_embedding,
                "external_ids": {
                    "popmartworld_slug": figure_slug,
                    "popmartworld_series": series_data["slug"]
                },
                "attributes": {}
            }

            if self.dry_run:
                print(f"      [DRY RUN] Would create figure: {figure_name}")
                self.stats["figures_created"] += 1
                return True

            # Create entity
            result = self.supabase.table("entities").insert(entity_data).execute()
            figure_id = result.data[0]["id"]

            # Create relationship to series
            self.supabase.table("relationships").insert({
                "from_id": series_id,
                "to_id": figure_id,
                "type": "contains"
            }).execute()

            self.stats["figures_created"] += 1
            self.stats["relationships_created"] += 1

            return True

        except Exception as e:
            print(f"      ❌ Error creating {figure_name}: {e}")
            self.stats["figures_failed"] += 1
            return False

    def import_all(self, data: list):
        """Import all series and figures.

        Args:
            data: List of series data from fetched_data.json
        """
        print(f"\\nImporting {len(data)} series...")
        print()

        for series_data in data:
            series_name = series_data.get("name", series_data["slug"])
            figures = series_data.get("figures", [])

            print(f"  {series_name} ({len(figures)} figures)")

            # Create or update series
            series_id, is_new = self.create_or_update_series(series_data)

            # Import figures
            for figure_data in figures:
                self.create_or_update_figure(figure_data, series_data, series_id)

        print()
        print("=" * 60)
        print("Import Summary")
        print("=" * 60)
        print(f"Series created:     {self.stats['series_created']}")
        print(f"Series updated:     {self.stats['series_updated']}")
        print(f"Figures created:    {self.stats['figures_created']}")
        print(f"Figures updated:    {self.stats['figures_updated']}")
        print(f"Figures failed:     {self.stats['figures_failed']}")
        print(f"Relationships:      {self.stats['relationships_created']}")
        print()

        total_figures = self.stats["figures_created"] + self.stats["figures_updated"]
        success_rate = (total_figures / (total_figures + self.stats["figures_failed"]) * 100) if total_figures + self.stats["figures_failed"] > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")


def main():
    import argparse

    # Parse arguments
    parser = argparse.ArgumentParser(description="Import Labubu figures to Supabase")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test import without writing to database"
    )
    parser.add_argument(
        "--env",
        choices=["local", "prod"],
        default="local",
        help="Environment to import to (default: local)"
    )
    args = parser.parse_args()

    # Warn if using default environment
    if not any(arg.startswith('--env') for arg in sys.argv):
        print("⚠️  No --env specified, defaulting to local")
        print()

    # Load environment-specific configuration
    supabase_url, supabase_key, collection_id = load_environment_config(
        CURATOR_NAME,
        args.env
    )

    # Check if fetched data exists
    if not FETCHED_DATA_FILE.exists():
        print(f"❌ Error: {FETCHED_DATA_FILE} not found")
        print("\\nRun fetch_data.py first:")
        print("  python3 scripts/fetch_data.py")
        sys.exit(1)

    # Load fetched data
    with open(FETCHED_DATA_FILE) as f:
        data = json.load(f)

    if not data:
        print("⚠️  No data to import")
        sys.exit(1)

    print("=" * 60)
    print("Labubu Figure Importer")
    print("=" * 60)
    print()
    print(f"Environment: {args.env}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE IMPORT'}")
    print(f"Series to import: {len(data)}")
    print(f"Total figures: {sum(len(s.get('figures', [])) for s in data)}")
    print()

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No database changes will be made")
        print()
        supabase = MockSupabaseClient()
    else:
        supabase = create_client(supabase_url, supabase_key)

    # Create importer and run
    importer = LabubuImporter(supabase, collection_id, args.dry_run)
    importer.import_all(data)

    if args.dry_run:
        print()
        print("✓ Dry run complete. Ready to run live import:")
        print("  python3 scripts/import_items.py")
    else:
        print()
        print("✓ Import complete!")


if __name__ == "__main__":
    main()
