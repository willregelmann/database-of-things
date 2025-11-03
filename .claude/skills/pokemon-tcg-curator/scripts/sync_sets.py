#!/usr/bin/env python3
"""
Sync Pokémon TCG Sets

Discovers and imports sets from pokemontcg.io API.
Creates set entities and links them to Pokémon Trading Card Game root.
"""

import argparse
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import PokemonTCGClient, DatabaseClient


def format_set_name(set_data: dict) -> str:
    """
    Format set name as "<series>[ - <name>]"

    Note: "Other" is a catch-all category in pokemontcg.io data, not a real series.
    We strip "Other - " prefix from set names.

    Args:
        set_data: Set data from API

    Returns:
        Formatted name
    """
    series = set_data.get("series", "")
    name = set_data.get("name", "")

    # If series is in the name, just use name
    if series and series in name:
        formatted = name
    elif series:
        # Otherwise combine
        formatted = f"{series} - {name}"
    else:
        formatted = name

    # Remove "Other - " prefix (catch-all category, not a real series)
    if formatted.startswith("Other - "):
        formatted = formatted.replace("Other - ", "", 1)

    return formatted


def parse_release_year(release_date: str) -> int:
    """
    Extract year from release date

    Args:
        release_date: ISO date string (YYYY-MM-DD or YYYY/MM/DD)

    Returns:
        Year as integer
    """
    # Handle both YYYY-MM-DD and YYYY/MM/DD formats
    year_str = release_date.split("-")[0].split("/")[0]
    return int(year_str)


def sync_set(api_client: PokemonTCGClient, db_client: DatabaseClient, set_data: dict, dry_run: bool = False) -> bool:
    """
    Sync a single set

    Args:
        api_client: Pokémon TCG API client
        db_client: Database client
        set_data: Set data from API
        dry_run: If True, don't make database changes

    Returns:
        True if created, False if updated/skipped
    """
    set_code = set_data["id"]
    set_name = format_set_name(set_data)
    release_date = set_data.get("releaseDate", "")
    year = parse_release_year(release_date) if release_date else None

    # Build attributes
    attributes = {
        "language": "en"
    }

    if set_data.get("series"):
        attributes["series"] = set_data["series"]

    if set_data.get("printedTotal"):
        attributes["printedTotal"] = set_data["printedTotal"]

    if set_data.get("total"):
        attributes["total"] = set_data["total"]

    if release_date:
        attributes["releaseDate"] = release_date

    # Image URL
    image_key = set_data.get("images", {}).get("logo")

    if dry_run:
        print(f"  [DRY RUN] Would create/update: {set_name} ({set_code})")
        return False

    # Upsert entity
    entity_id, created = db_client.upsert_entity(
        external_system="pokemontcg.io",
        external_id=set_code,
        entity_type="collection",
        name=set_name,
        year=year,
        image_key=image_key,
        attributes=attributes
    )

    # Link to Pokémon Trading Card Game root
    db_client.create_relationship(
        from_id=db_client.TCG_ROOT_ID,
        to_id=entity_id,
        rel_type="contains"
    )

    return created


def main():
    parser = argparse.ArgumentParser(description="Sync Pokémon TCG sets from API")
    parser.add_argument("--limit", type=int, help="Process only first N sets")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    args = parser.parse_args()

    # Initialize clients
    api_client = PokemonTCGClient()
    db_client = DatabaseClient()

    print("🔍 Fetching sets from pokemontcg.io API...")

    # Fetch all sets
    all_sets = []
    page = 1

    while True:
        response = api_client.get_sets(page=page, page_size=250)
        sets = response.get("data", [])

        if not sets:
            break

        all_sets.extend(sets)

        total_count = response.get("totalCount", 0)
        if len(all_sets) >= total_count:
            break

        page += 1

    if args.limit:
        all_sets = all_sets[:args.limit]

    print(f"📦 Found {len(all_sets)} sets")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Sync each set
    created_count = 0
    updated_count = 0

    for i, set_data in enumerate(all_sets, 1):
        set_name = format_set_name(set_data)
        print(f"[{i}/{len(all_sets)}] {set_name}")

        try:
            created = sync_set(api_client, db_client, set_data, dry_run=args.dry_run)
            if created:
                created_count += 1
                print(f"  ✅ Created")
            else:
                updated_count += 1
                if not args.dry_run:
                    print(f"  ♻️  Updated")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    # Summary
    print(f"\n{'=' * 50}")
    if args.dry_run:
        print("DRY RUN COMPLETE")
    else:
        print("SYNC COMPLETE")
    print(f"Total sets: {len(all_sets)}")
    print(f"Created: {created_count}")
    print(f"Updated: {updated_count}")


if __name__ == "__main__":
    main()
