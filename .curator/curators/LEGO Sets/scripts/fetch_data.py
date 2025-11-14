#!/usr/bin/env python3
"""Fetch LEGO sets from Rebrickable API by theme."""

import os
import sys
import json
from pathlib import Path

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
OUTPUT_FILE = Path(__file__).parent.parent / "fetched_data.json"


def get_theme_id(api_key: str, theme_name: str) -> int:
    """Look up theme ID by name from Rebrickable API.

    Args:
        api_key: Rebrickable API key
        theme_name: Theme name to search for (e.g., "Space", "Star Wars")

    Returns:
        Theme ID integer

    Raises:
        ValueError: If theme not found
    """
    print(f"Looking up theme ID for: {theme_name}")

    headers = {"Authorization": f"key {api_key}"}
    page = 1
    page_size = 100

    while True:
        response = requests.get(
            f"{API_BASE}/themes/",
            headers=headers,
            params={"page": page, "page_size": page_size},
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        themes = data.get("results", [])

        # Search for matching theme (case-insensitive)
        for theme in themes:
            if theme["name"].lower() == theme_name.lower():
                theme_id = theme["id"]
                print(f"✓ Found theme '{theme['name']}' with ID: {theme_id}")
                return theme_id

        # Check if there are more pages
        if not data.get("next"):
            break

        page += 1

    raise ValueError(f"Theme '{theme_name}' not found in Rebrickable database")


def fetch_sets(api_key: str, theme_id: int, fetch_limit: int = None) -> list:
    """Fetch all sets for a given theme from Rebrickable API.

    Args:
        api_key: Rebrickable API key
        theme_id: Theme ID to filter
        fetch_limit: Optional limit for testing (default: fetch all)

    Returns:
        List of set dictionaries
    """
    sets = []
    page = 1
    page_size = 1000  # Rebrickable max page size

    print(f"Fetching LEGO sets for theme_id: {theme_id}")
    print(f"API endpoint: {API_BASE}/sets/")

    if fetch_limit:
        print(f"⚠️  FETCH_LIMIT set to {fetch_limit} - fetching sample only")

    headers = {"Authorization": f"key {api_key}"}

    while True:
        params = {
            "theme_id": theme_id,
            "page": page,
            "page_size": page_size,
            "ordering": "year"
        }

        print(f"  Fetching page {page}...", end=" ", flush=True)

        try:
            response = requests.get(
                f"{API_BASE}/sets/",
                headers=headers,
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

            # Check if we've hit the fetch limit
            if fetch_limit and len(sets) >= fetch_limit:
                sets = sets[:fetch_limit]
                print(f"  Reached FETCH_LIMIT ({fetch_limit}), stopping early")
                break

            # Check if there are more pages
            if not data.get("next"):
                break

            page += 1

        except requests.exceptions.RequestException as e:
            print(f"\n❌ Request failed: {e}")
            break

    return sets


def main():
    # Get configuration from environment
    api_key = os.getenv("REBRICKABLE_API_KEY")
    theme_name = os.getenv("THEME_NAME")
    fetch_limit = os.getenv("FETCH_LIMIT")

    if not api_key:
        print("❌ Error: REBRICKABLE_API_KEY not found in environment")
        print("Get your API key at: https://rebrickable.com/api/")
        print("\nThen set it in: .curator/curators/LEGO Sets/secrets.env")
        print("  REBRICKABLE_API_KEY=your_key_here")
        print("\nNote: Supabase credentials come from .curator/secrets.env")
        sys.exit(1)

    if not theme_name:
        print("❌ Error: THEME_NAME not found in environment")
        print("\nSet the theme in secrets.env:")
        print("  THEME_NAME=Space")
        print("\nOr pass it at runtime:")
        print("  THEME_NAME='Star Wars' python3 scripts/fetch_data.py")
        sys.exit(1)

    # Convert fetch_limit to int if provided
    if fetch_limit:
        try:
            fetch_limit = int(fetch_limit)
        except ValueError:
            print(f"⚠️  Warning: Invalid FETCH_LIMIT '{fetch_limit}', ignoring")
            fetch_limit = None

    print("=" * 60)
    print("LEGO Sets Fetcher - Rebrickable API")
    print("=" * 60)
    print()

    try:
        # Look up theme ID
        theme_id = get_theme_id(api_key, theme_name)
        print()

        # Fetch sets
        sets = fetch_sets(api_key, theme_id, fetch_limit)

        if not sets:
            print("\n⚠️  No sets found for theme:", theme_name)
            sys.exit(1)

        # Save to file
        print()
        print(f"Saving {len(sets)} sets to {OUTPUT_FILE.name}...")

        with open(OUTPUT_FILE, "w") as f:
            json.dump(sets, f, indent=2)

        print(f"✓ Complete! Fetched {len(sets)} sets for theme '{theme_name}'")
        print(f"  Output: {OUTPUT_FILE}")
        print()
        print("Next step:")
        print("  python3 scripts/import_items.py --dry-run  # Test import")
        print("  python3 scripts/import_items.py            # Real import")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
