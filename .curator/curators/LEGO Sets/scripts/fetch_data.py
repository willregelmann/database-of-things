#!/usr/bin/env python3
"""
Fetch LEGO sets from Rebrickable API.

Usage:
  # Fetch specific theme
  python3 fetch_data.py --theme "Star Wars"
  python3 fetch_data.py --theme "Space"

  # Limit number of sets (for testing)
  python3 fetch_data.py --theme "Star Wars" --limit 10

  # Default: Fetch sample theme for testing
  python3 fetch_data.py
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Auto-install dependencies if missing
try:
    import requests
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "requests"
    ])
    import requests

API_BASE = "https://rebrickable.com/api/v3/lego"
OUTPUT_FILE = "fetched_data.json"


class RebrickableFetcher:
    """Fetch LEGO sets from Rebrickable API."""

    def __init__(self, api_key: str, limit: Optional[int] = None):
        self.api_key = api_key
        self.headers = {"Authorization": f"key {api_key}"}
        self.limit = limit
        self.request_count = 0

    def get_theme_by_name(self, theme_name: str) -> Optional[Dict]:
        """Look up theme by name from Rebrickable API.

        Returns:
            Theme dict with id, name, parent_id
        """
        print(f"  Looking up theme: {theme_name}")

        page = 1
        page_size = 100

        while True:
            self.request_count += 1
            response = requests.get(
                f"{API_BASE}/themes/",
                headers=self.headers,
                params={"page": page, "page_size": page_size},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            themes = data.get("results", [])

            # Search for matching theme (case-insensitive)
            for theme in themes:
                if theme["name"].lower() == theme_name.lower():
                    print(f"  ✓ Found: {theme['name']} (ID: {theme['id']})")
                    return theme

            # Check if there are more pages
            if not data.get("next"):
                break

            page += 1

        return None

    def fetch_sets_by_theme(self, theme_id: int, theme_name: str) -> List[Dict]:
        """Fetch all sets for a theme.

        Returns graph structure: parent entity (theme) + child entities (sets).
        """
        print(f"\n{'=' * 60}")
        print(f"Fetching LEGO Sets for Theme: {theme_name}")
        print(f"{'=' * 60}\n")

        all_entities = []

        # Fetch raw sets from API
        sets = self._fetch_sets_paginated(theme_id)

        if not sets:
            print(f"  ⚠️  No sets found for theme")
            return []

        # Create parent entity (theme/collection)
        parent_entity = {
            "name": theme_name,
            "type": "collection",
            "external_ids": {
                "rebrickable_theme_id": str(theme_id)
            },
            "attributes": {}
        }
        all_entities.append(parent_entity)

        # Convert sets to child entities with parent reference
        for raw_set in sets:
            set_entity = self._parse_set(raw_set, theme_id)
            if set_entity:
                all_entities.append(set_entity)

        print(f"\n  ✓ Fetched 1 theme + {len(sets)} sets")
        return all_entities

    def _fetch_sets_paginated(self, theme_id: int) -> List[Dict]:
        """Fetch all sets for a theme (handles pagination)."""
        sets = []
        page = 1
        page_size = 1000  # Rebrickable max page size

        while True:
            params = {
                "theme_id": theme_id,
                "page": page,
                "page_size": page_size,
                "ordering": "year"
            }

            print(f"  Fetching page {page}...", end=" ", flush=True)

            self.request_count += 1
            response = requests.get(
                f"{API_BASE}/sets/",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            page_sets = data.get("results", [])
            total_count = data.get("count", 0)

            print(f"✓ {len(page_sets)} sets (total in theme: {total_count})")

            if not page_sets:
                break

            sets.extend(page_sets)

            # Check if we've hit the limit
            if self.limit and len(sets) >= self.limit:
                sets = sets[:self.limit]
                print(f"  ⚠️  Reached limit of {self.limit} sets")
                break

            # Check if there are more pages
            if not data.get("next"):
                break

            page += 1

        return sets

    def _parse_set(self, raw_set: Dict, theme_id: int) -> Optional[Dict]:
        """Parse set data from Rebrickable API (v2 format).

        Returns:
            Entity dict with parent reference and relationship metadata.
        """
        try:
            set_num = raw_set.get("set_num")
            name = raw_set.get("name")
            year = raw_set.get("year")
            num_parts = raw_set.get("num_parts")
            image_url = raw_set.get("set_img_url")
            source_url = raw_set.get("set_url")

            # Return v2 format (graph structure)
            return {
                "name": name,
                "type": "lego_set",
                "year": year,
                "external_ids": {
                    "rebrickable_set_num": set_num
                },
                "image_url": image_url,
                "source_url": source_url,
                "parent": {
                    "type": "collection",
                    "external_ids": {
                        "rebrickable_theme_id": str(theme_id)
                    }
                },
                "relationship": {
                    "type": "contains",
                    "order": year  # Sort by year within theme
                },
                "attributes": {
                    "pieces": num_parts
                }
            }

        except Exception as e:
            print(f"  ⚠️  Failed to parse set: {e}")
            return None


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch LEGO sets from Rebrickable API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch specific theme
  python3 fetch_data.py --theme "Star Wars"
  python3 fetch_data.py --theme "Space"

  # Limit number of sets (for testing)
  python3 fetch_data.py --theme "Star Wars" --limit 10

  # Default: Fetch sample theme for testing
  python3 fetch_data.py
        """
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="LEGO theme to fetch (e.g., 'Space', 'Star Wars', 'City')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit total number of sets to fetch (for testing)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("LEGO Sets - Rebrickable API Fetcher")
    print("=" * 60)
    print()

    # Load credentials from environment
    api_key = os.getenv("REBRICKABLE_API_KEY")

    if not api_key:
        print("Error: REBRICKABLE_API_KEY not set")
        print("Get your API key from: https://rebrickable.com/api/")
        sys.exit(1)

    fetcher = RebrickableFetcher(api_key, limit=args.limit)

    # Determine what to fetch
    entities = []
    filters_applied = {}

    if not args.theme:
        print("Error: THEME argument is required")
        print("\nExamples:")
        print("  python3 fetch_data.py 'Star Wars'")
        print("  python3 fetch_data.py 'Space' --limit 10")
        print("  python3 fetch_data.py 'Harry Potter'")
        sys.exit(1)

    theme_name = args.theme

    # Look up theme
    theme = fetcher.get_theme_by_name(theme_name)
    if not theme:
        print(f"\n❌ Error: Theme '{theme_name}' not found in Rebrickable database")
        sys.exit(1)

    theme_id = theme["id"]
    filters_applied["theme"] = theme_name

    if args.limit:
        filters_applied["limit"] = args.limit

    # Fetch sets
    entities = fetcher.fetch_sets_by_theme(theme_id, theme_name)

    if not entities:
        print(f"\n⚠️  No sets found for theme: {theme_name}")
        sys.exit(1)

    # Wrap in v2 format with metadata
    from datetime import datetime, timezone
    output_data = {
        "format_version": "1.0",
        "metadata": {
            "curator": "LEGO Sets",
            "source": "https://rebrickable.com",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(entities),
            "filters_applied": filters_applied
        },
        "items": entities
    }

    # Save to file
    output_path = Path(__file__).parent.parent / OUTPUT_FILE
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Fetched {len(entities)} entities → {output_path}")
    print(f"  Total API requests: {fetcher.request_count}")
    print("=" * 60)

    # Data quality report
    if entities:
        # Count different entity types
        collections = sum(1 for e in entities if e.get("type") == "collection")
        sets = sum(1 for e in entities if e.get("type") == "lego_set")

        # Count quality metrics (only for sets)
        with_images = sum(1 for e in entities if e.get("type") == "lego_set" and e.get("image_url"))
        with_years = sum(1 for e in entities if e.get("year"))
        with_pieces = sum(1 for e in entities if e.get("type") == "lego_set" and e.get("attributes", {}).get("pieces"))

        print(f"\nData quality:")
        print(f"  Total entities: {len(entities)} ({collections} collections, {sets} sets)")
        print(f"  Sets with images: {with_images}/{sets} ({with_images/sets*100:.1f}%)" if sets > 0 else "")
        print(f"  Entities with years: {with_years}/{len(entities)} ({with_years/len(entities)*100:.1f}%)")
        print(f"  Sets with piece count: {with_pieces}/{sets} ({with_pieces/sets*100:.1f}%)" if sets > 0 else "")


if __name__ == "__main__":
    main()
