#!/usr/bin/env python3
"""Fetch Pokemon TCG cards from GitHub pokemon-tcg-data repository (v2 format)."""

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

# GitHub raw data URLs
GITHUB_BASE = "https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master"
SETS_URL = f"{GITHUB_BASE}/sets/en.json"
CARDS_BASE_URL = f"{GITHUB_BASE}/cards/en"

OUTPUT_FILE = Path(__file__).parent.parent / "fetched_data.json"


def fetch_json(url: str, max_retries: int = 3) -> dict:
    """Fetch JSON from URL with retry logic.

    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        JSON response data
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                print(f"⚠️  Request timeout/error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Request failed after {max_retries} attempts: {url}")
                raise


def fetch_all_sets() -> list:
    """Fetch all Pokemon TCG sets from GitHub.

    Returns:
        List of set dictionaries
    """
    print(f"Fetching sets from GitHub...")
    return fetch_json(SETS_URL)


def fetch_cards_for_set(set_id: str) -> list:
    """Fetch all cards for a specific set.

    Args:
        set_id: Set ID (e.g., "swsh12" for Silver Tempest)

    Returns:
        List of card dictionaries
    """
    url = f"{CARDS_BASE_URL}/{set_id}.json"
    print(f"Fetching cards for set {set_id}...")
    return fetch_json(url)


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
        set_data: Raw set data from GitHub
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


def normalize_card(card_data: dict, set_data: dict = None) -> dict:
    """Transform card data to standard format.

    Args:
        card_data: Raw card data from GitHub
        set_data: Set metadata (optional, for year and set ID)

    Returns:
        Normalized card entity
    """
    # Extract year from set data if available
    if set_data:
        set_release = set_data.get("releaseDate", "")
        year = int(set_release[:4]) if set_release and len(set_release) >= 4 else None
        set_id = set_data.get("id")
    else:
        year = None
        set_id = None

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

    # Build name with card number in format "Name 001/102"
    card_name = card_data.get("name")
    card_number = card_data.get("number")
    if card_number and set_data:
        printed_total = set_data.get("printedTotal") or set_data.get("total")
        # Try to parse card number as int for zero-padding
        try:
            num = int(card_number)
            card_name = f"{card_name} {num:03d}/{printed_total}"
        except ValueError:
            # Card number might be non-numeric (e.g., "SV001")
            card_name = f"{card_name} {card_number}/{printed_total}"
    elif card_number:
        card_name = f"{card_name} {card_number}"

    entity = {
        "name": card_name,
        "type": "card",
        "year": year,
        "external_ids": external_ids,
        "source_url": f"https://pokemontcg.io/card/{card_data.get('id')}",
        "parent": {
            "type": "collection",
            "external_ids": {
                "pokemontcg_io_set": set_id
            }
        },
        "relationship": {
            "type": "contains",
            "order": int(card_data.get("number", "0").split("/")[0]) if card_data.get("number") else None
        },
        "attributes": {
            k: v for k, v in {
                "rarity": card_data.get("rarity"),
                "artist": card_data.get("artist")
            }.items() if v is not None
        }
    }

    # Add high-res image if available
    if card_data.get("images", {}).get("large"):
        entity["image_url"] = card_data["images"]["large"]

    return entity


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Pokemon TCG cards from GitHub pokemon-tcg-data repository"
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
        help='Filter by set name (e.g., "Silver Tempest")'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Pokemon TCG Fetcher - GitHub pokemon-tcg-data (v2)")
    print("=" * 60)
    print()

    # Fetch all sets from GitHub
    all_sets = fetch_all_sets()
    print(f"✓ Loaded {len(all_sets)} sets from GitHub")
    print()

    # Determine what to fetch
    items = []

    if args.set:
        # Fetch specific set and its cards
        print(f"Fetching set: {args.set}...")

        # Find the set
        target_set = next((s for s in all_sets if s.get("name") == args.set), None)

        if not target_set:
            print(f"❌ Set '{args.set}' not found")
            return 1

        series_name = target_set.get("series")
        set_id = target_set.get("id")

        # Add series
        series_sets = [s for s in all_sets if s.get("series") == series_name]
        items.append(normalize_series(series_name, series_sets))

        # Add set
        items.append(normalize_set(target_set, series_name))

        # Add cards from this set
        cards = fetch_cards_for_set(set_id)
        print(f"✓ Fetched {len(cards)} cards from {args.set}")

        if args.limit:
            cards = cards[:args.limit]
            print(f"  Limited to {args.limit} cards")

        items.extend([normalize_card(card, target_set) for card in cards])

    elif args.series:
        # Fetch entire series (all sets and cards)
        print(f"Fetching series: {args.series}...")

        # Get sets in this series
        sets = [s for s in all_sets if s.get("series") == args.series]

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

            set_id = set_data.get("id")
            cards = fetch_cards_for_set(set_id)

            if cards_remaining is not None:
                cards = cards[:cards_remaining]
                cards_remaining -= len(cards)

            items.extend([normalize_card(card, set_data) for card in cards])
            print(f"  ✓ {set_data.get('name')}: {len(cards)} cards")

    else:
        # Full import: all series, sets, and cards
        print("Fetching all Pokemon TCG data...")

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
        cards_fetched = 0
        cards_remaining = args.limit

        for set_data in all_sets:
            if cards_remaining is not None and cards_remaining <= 0:
                break

            set_id = set_data.get("id")
            try:
                cards = fetch_cards_for_set(set_id)

                if cards_remaining is not None:
                    cards = cards[:cards_remaining]
                    cards_remaining -= len(cards)

                items.extend([normalize_card(card, set_data) for card in cards])
                cards_fetched += len(cards)
                print(f"  ✓ {set_data.get('name')}: {len(cards)} cards (total: {cards_fetched})")
            except Exception as e:
                print(f"  ⚠️  Failed to fetch cards for {set_data.get('name')}: {e}")
                continue

    # Build output
    output = {
        "format_version": "1.0",
        "metadata": {
            "curator": "Pokemon TCG",
            "source": "https://github.com/PokemonTCG/pokemon-tcg-data",
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
    print('  /curator-run "Pokemon TCG"  # Import via MCP tools (Claude)')
    print()

    return 0


if __name__ == "__main__":
    exit(main())
