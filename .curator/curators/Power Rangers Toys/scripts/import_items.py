#!/usr/bin/env python3
"""Import fetched Power Rangers toys into Supabase."""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

# Auto-install dependencies if missing
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "supabase"])
    from supabase import create_client, Client

FETCHED_FILE = "fetched_data.json"
FRANCHISE_ID = "d183e3a9-4eb7-40a5-b264-526b9a03ec30"


class ToyImporter:
    """Import Power Rangers toys to Supabase."""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.series_cache = {}  # Cache series entities to avoid repeated lookups

    def get_or_create_series(self, series_name: str, year: Optional[int] = None) -> str:
        """Get or create a series entity, return its ID."""
        if not series_name:
            return FRANCHISE_ID  # Default to franchise if no series specified

        # Check cache
        cache_key = f"{series_name}_{year}"
        if cache_key in self.series_cache:
            return self.series_cache[cache_key]

        # Check if series exists
        query = self.supabase.table("entities").select("id").eq("name", series_name).eq("type", "series")

        if year:
            query = query.eq("year", year)

        result = query.execute()

        if result.data:
            series_id = result.data[0]["id"]
            self.series_cache[cache_key] = series_id
            return series_id

        # Create series
        series_data = {
            "name": series_name,
            "type": "series",
            "year": year,
            "attributes": {}
        }

        result = self.supabase.table("entities").insert(series_data).execute()
        series_id = result.data[0]["id"]

        # Link series to franchise
        self.supabase.table("relationships").insert({
            "from_id": FRANCHISE_ID,
            "to_id": series_id,
            "type": "contains"
        }).execute()

        self.series_cache[cache_key] = series_id
        print(f"  Created series: {series_name}")
        return series_id

    def check_toy_exists(self, name: str, series_id: str, year: Optional[int]) -> Optional[str]:
        """Check if toy already exists using deduplication strategy: name + series + year."""
        # Find toys with matching name linked to this series
        result = self.supabase.table("relationships").select(
            "to_id, entities!relationships_to_id_fkey(id, name, year)"
        ).eq("from_id", series_id).eq("type", "contains").execute()

        for rel in result.data:
            entity = rel["entities"]
            if entity["name"] == name and entity.get("year") == year:
                return entity["id"]

        return None

    def import_toy(self, toy_data: Dict, series_id: str) -> Tuple[bool, str]:
        """Import a single toy. Returns (success, message)."""
        name = toy_data["name"]
        year = toy_data.get("year")

        # Check for duplicates
        existing_id = self.check_toy_exists(name, series_id, year)
        if existing_id:
            return False, f"Skip: {name} (already exists)"

        # Prepare entity data
        entity_data = {
            "name": name,
            "type": "toy",
            "year": year,
            "image_url": toy_data.get("image_url"),
            "external_ids": {
                "rangerwiki": toy_data["url"]
            },
            "attributes": {
                "toy_type": toy_data.get("toy_type"),
                "manufacturer": toy_data.get("manufacturer"),
                "description": toy_data.get("description"),
                "source_url": toy_data.get("source_url")
            }
        }

        # Remove None values from attributes
        entity_data["attributes"] = {k: v for k, v in entity_data["attributes"].items() if v is not None}

        try:
            # Create entity
            result = self.supabase.table("entities").insert(entity_data).execute()
            entity_id = result.data[0]["id"]

            # Link to series
            self.supabase.table("relationships").insert({
                "from_id": series_id,
                "to_id": entity_id,
                "type": "contains"
            }).execute()

            return True, f"✓ Imported: {name}"

        except Exception as e:
            return False, f"Error importing {name}: {str(e)}"

    def import_all_toys(self, toys: list) -> Tuple[int, int]:
        """Import all toys. Returns (imported_count, skipped_count)."""
        imported = 0
        skipped = 0

        for toy in toys:
            # Get or create series
            series_name = toy.get("series")
            year = toy.get("year")
            series_id = self.get_or_create_series(series_name, year)

            # Import toy
            success, message = self.import_toy(toy, series_id)
            print(f"  {message}")

            if success:
                imported += 1
            else:
                skipped += 1

        return imported, skipped


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
    print("=" * 60)
    print("Power Rangers Toy Importer")
    print("=" * 60)
    print()

    # Load configuration
    supabase_url, supabase_key = load_config()
    supabase = create_client(supabase_url, supabase_key)

    # Load fetched data
    print("Loading fetched data...")
    toys = load_fetched_data()
    print(f"Found {len(toys)} toys to import")
    print()

    # Import toys
    importer = ToyImporter(supabase)
    imported, skipped = importer.import_all_toys(toys)

    print()
    print("=" * 60)
    print(f"✓ Complete: {imported} imported, {skipped} skipped")
    print("=" * 60)


if __name__ == "__main__":
    main()
