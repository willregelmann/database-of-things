#!/usr/bin/env python3
"""Fetch Pokemon TCG cards from pokemontcg.io API (v2 format)."""

import argparse
import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# Auto-install dependencies
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

API_URL = "https://api.pokemontcg.io/v2"
OUTPUT_FILE = Path(__file__).parent.parent / "fetched_data.json"

# Rate limiting (20 requests/second per pokemontcg.io recommendations)
RATE_LIMIT_DELAY = 0.05  # 50ms between requests


def fetch_with_rate_limit(url: str, headers: dict, params: dict = None) -> dict:
    """Fetch from API with rate limiting.

    Args:
        url: API endpoint URL
        headers: Request headers (including API key)
        params: Query parameters

    Returns:
        JSON response data
    """
    time.sleep(RATE_LIMIT_DELAY)
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_all_series(api_key: str) -> list:
    """Fetch all Pokemon TCG series.

    Args:
        api_key: pokemontcg.io API key

    Returns:
        List of series names
    """
    headers = {"X-Api-Key": api_key}

    # Get all sets first
    all_sets = []
    page = 1

    while True:
        data = fetch_with_rate_limit(
            f"{API_URL}/sets",
            headers=headers,
            params={"page": page, "pageSize": 250}
        )

        all_sets.extend(data.get("data", []))

        if page >= data.get("totalCount", 0) / 250:
            break
        page += 1

    # Extract unique series names
    series_names = list(set(s.get("series") for s in all_sets if s.get("series")))
    series_names.sort()

    return series_names


def fetch_sets(api_key: str, series_filter: str = None) -> list:
    """Fetch Pokemon TCG sets, optionally filtered by series.

    Args:
        api_key: pokemontcg.io API key
        series_filter: Optional series name to filter by

    Returns:
        List of set dictionaries
    """
    headers = {"X-Api-Key": api_key}
    all_sets = []
    page = 1

    params = {"page": page, "pageSize": 250}
    if series_filter:
        params["q"] = f'series:"{series_filter}"'

    while True:
        data = fetch_with_rate_limit(
            f"{API_URL}/sets",
            headers=headers,
            params=params
        )

        all_sets.extend(data.get("data", []))

        if page >= data.get("totalCount", 0) / 250:
            break
        page += 1
        params["page"] = page

    return all_sets


def fetch_cards(api_key: str, set_id: str = None, limit: int = None) -> list:
    """Fetch Pokemon TCG cards from API.

    Args:
        api_key: pokemontcg.io API key
        set_id: Optional set ID to filter by
        limit: Maximum cards to fetch

    Returns:
        List of card dictionaries
    """
    headers = {"X-Api-Key": api_key}
    all_cards = []
    page = 1

    params = {"page": page, "pageSize": 250}
    if set_id:
        params["q"] = f'set.id:"{set_id}"'

    while True:
        data = fetch_with_rate_limit(
            f"{API_URL}/cards",
            headers=headers,
            params=params
        )

        cards = data.get("data", [])
        all_cards.extend(cards)

        # Check limit
        if limit and len(all_cards) >= limit:
            all_cards = all_cards[:limit]
            break

        # Check for more pages
        if page >= data.get("totalCount", 0) / 250:
            break

        page += 1
        params["page"] = page

    return all_cards


def normalize_series(series_name: str, sets_in_series: list) -> dict:
    """Create a series collection entity.

    Args:
        series_name: Name of the series
        sets_in_series: List of sets in this series

    Returns:
        Normalized series entity
    """
    # Use first set's release date as series year
    years = [s.get("releaseDate", "")[:4] for s in sets_in_series if s.get("releaseDate")]
    year = int(min(years)) if years else None

    return {
        "name": series_name,
        "type": "collection",
        "year": year,
        "external_ids": {
            "pokemontcg_io_series": series_name.lower().replace(" ", "-").replace("&", "and")
        },
        "attributes": {}
    }


def normalize_set(set_data: dict, series_name: str) -> dict:
    """Transform set data to standard format.

    Args:
        set_data: Raw set data from API
        series_name: Name of parent series

    Returns:
        Normalized set entity
    """
    # Extract year from release date
    release_date = set_data.get("releaseDate", "")
    year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

    entity = {
        "name": set_data.get("name"),
        "type": "collection",
        "year": year,
        "external_ids": {
            "pokemontcg_io_set": set_data.get("id")
        },
        "source_url": f"https://pokemontcg.io/sets/{set_data.get('id')}",
        "parent": {
            "type": "collection",
            "external_ids": {
                "pokemontcg_io_series": series_name.lower().replace(" ", "-").replace("&", "and")
            }
        },
        "relationship": {
            "type": "contains"
        },
        "attributes": {
            "total_cards": set_data.get("total"),
            "printed_total": set_data.get("printedTotal"),
            "release_date": release_date
        }
    }

    # Add set logo image if available
    if set_data.get("images", {}).get("logo"):
        entity["image_url"] = set_data["images"]["logo"]

    return entity


def normalize_card(card_data: dict) -> dict:
    """Transform card data to standard format.

    Args:
        card_data: Raw card data from API

    Returns:
        Normalized card entity
    """
    # Extract year from set release date
    set_release = card_data.get("set", {}).get("releaseDate", "")
    year = int(set_release[:4]) if set_release and len(set_release) >= 4 else None

    # Build external IDs
    external_ids = {
        "pokemontcg_io": card_data.get("id")
    }

    # Add TCGPlayer ID if available
    tcgplayer = card_data.get("tcgplayer", {})
    if tcgplayer.get("url"):
        # Extract ID from URL
        import re
        match = re.search(r'/product/(\d+)/', tcgplayer["url"])
        if match:
            external_ids["tcgplayer_id"] = match.group(1)

    # Add Cardmarket ID if available
    cardmarket = card_data.get("cardmarket", {})
    if cardmarket.get("url"):
        import re
        match = re.search(r'/Products/Singles/[^/]+/[^/]+-(\d+)', cardmarket["url"])
        if match:
            external_ids["cardmarket_id"] = match.group(1)

    entity = {
        "name": card_data.get("name"),
        "type": "card",
        "year": year,
        "external_ids": external_ids,
        "source_url": f"https://pokemontcg.io/card/{card_data.get('id')}",
        "parent": {
            "type": "collection",
            "external_ids": {
                "pokemontcg_io_set": card_data.get("set", {}).get("id")
            }
        },
        "relationship": {
            "type": "contains",
            "order": int(card_data.get("number", "0").split("/")[0]) if card_data.get("number") else None
        },
        "attributes": {
            "rarity": card_data.get("rarity"),
            "artist": card_data.get("artist")
        }
    }

    # Add high-res image if available
    if card_data.get("images", {}).get("large"):
        entity["image_url"] = card_data["images"]["large"]

    return entity


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Pokemon TCG cards from pokemontcg.io API"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum cards to fetch (default: all)"
    )
    parser.add_argument(
        "--series",
        help='Filter by series name (e.g., "Scarlet & Violet")'
    )
    parser.add_argument(
        "--set",
        help='Filter by set name (e.g., "Base Set")'
    )
    args = parser.parse_args()

    # Load API key from environment
    api_key = os.getenv("POKEMONTCG_API_KEY")
    if not api_key:
        print("❌ Error: POKEMONTCG_API_KEY not found in environment")
        print("Set it in secrets.env")
        return 1

    print("=" * 60)
    print("Pokemon TCG Fetcher - pokemontcg.io API (v2)")
    print("=" * 60)
    print()

    # Determine what to fetch
    items = []

    if args.set:
        # Fetch specific set and its cards
        print(f"Fetching set: {args.set}...")

        # Find the set
        all_sets = fetch_sets(api_key)
        target_set = next((s for s in all_sets if s.get("name") == args.set), None)

        if not target_set:
            print(f"❌ Set '{args.set}' not found")
            return 1

        series_name = target_set.get("series")

        # Add series
        series_sets = [s for s in all_sets if s.get("series") == series_name]
        items.append(normalize_series(series_name, series_sets))

        # Add set
        items.append(normalize_set(target_set, series_name))

        # Add cards from this set
        print(f"Fetching cards from {args.set}...")
        cards = fetch_cards(api_key, target_set.get("id"), args.limit)
        items.extend([normalize_card(card) for card in cards])

    elif args.series:
        # Fetch entire series (all sets and cards)
        print(f"Fetching series: {args.series}...")

        # Get sets in this series
        sets = fetch_sets(api_key, args.series)

        if not sets:
            print(f"❌ Series '{args.series}' not found")
            return 1

        # Add series
        items.append(normalize_series(args.series, sets))

        # Add all sets
        for set_data in sets:
            items.append(normalize_set(set_data, args.series))

        # Add cards from all sets
        print(f"Fetching cards from {len(sets)} sets...")
        cards_remaining = args.limit

        for set_data in sets:
            if cards_remaining is not None and cards_remaining <= 0:
                break

            cards = fetch_cards(api_key, set_data.get("id"), cards_remaining)
            items.extend([normalize_card(card) for card in cards])

            if cards_remaining is not None:
                cards_remaining -= len(cards)

    else:
        # Full import: all series, sets, and cards
        print("Fetching all Pokemon TCG data...")

        # Get all sets
        all_sets = fetch_sets(api_key)

        # Group by series
        series_map = {}
        for set_data in all_sets:
            series_name = set_data.get("series")
            if series_name not in series_map:
                series_map[series_name] = []
            series_map[series_name].append(set_data)

        # Add all series
        for series_name, sets_in_series in series_map.items():
            items.append(normalize_series(series_name, sets_in_series))

        # Add all sets
        for set_data in all_sets:
            items.append(normalize_set(set_data, set_data.get("series")))

        # Add all cards
        print(f"Fetching cards from {len(all_sets)} sets...")
        cards = fetch_cards(api_key, limit=args.limit)
        items.extend([normalize_card(card) for card in cards])

    # Build output
    output = {
        "format_version": "1.0",
        "metadata": {
            "curator": "Pokemon TCG",
            "source": API_URL,
            "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "total_items": len(items),
            "filters_applied": {
                "limit": args.limit,
                "series": args.series,
                "set": args.set
            }
        },
        "items": items
    }

    # Save to file
    print()
    print(f"Saving {len(items)} items to {OUTPUT_FILE.name}...")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✓ Complete! Fetched {len(items)} items")
    print(f"  Output: {OUTPUT_FILE}")
    print()
    print("Next steps:")
    print('  /curator:run "Pokemon TCG"  # Import via MCP tools (Claude)')
    print()

    return 0


if __name__ == "__main__":
    exit(main())
