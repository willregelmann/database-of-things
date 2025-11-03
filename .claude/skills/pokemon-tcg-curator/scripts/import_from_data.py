#!/usr/bin/env python3
"""
Import from Local Pokemon TCG Data

Imports sets and cards from the local pokemon-tcg-data repository.
This is a fallback when the API is unavailable and is much faster!

Data source: https://github.com/PokemonTCG/pokemon-tcg-data
"""

import argparse
import json
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import DatabaseClient
from sync_sets import format_set_name, parse_release_year
from sync_cards import format_card_name, parse_card_number


DATA_DIR = Path(__file__).parent.parent / "data"
SETS_FILE = DATA_DIR / "sets" / "en.json"
CARDS_DIR = DATA_DIR / "cards" / "en"


def load_sets() -> list:
    """Load all sets from local data"""
    if not SETS_FILE.exists():
        print(f"❌ Sets file not found: {SETS_FILE}")
        print("\nMake sure you've cloned the pokemon-tcg-data repository:")
        print("  cd .claude/skills/pokemon-tcg-curator")
        print("  git clone https://github.com/PokemonTCG/pokemon-tcg-data.git data")
        sys.exit(1)

    with open(SETS_FILE, 'r') as f:
        return json.load(f)


def load_cards_for_set(set_code: str) -> list:
    """Load all cards for a specific set from local data"""
    cards_file = CARDS_DIR / f"{set_code}.json"

    if not cards_file.exists():
        print(f"⚠️  Cards file not found: {cards_file}")
        return []

    with open(cards_file, 'r') as f:
        return json.load(f)


def import_set(db_client: DatabaseClient, set_data: dict, dry_run: bool = False) -> bool:
    """
    Import a single set

    Note: "Other" is a catch-all category in pokemontcg.io data, not a real series.
    We strip "Other - " prefix from set names.

    Args:
        db_client: Database client
        set_data: Set data from JSON
        dry_run: If True, don't make database changes

    Returns:
        True if created, False if updated/skipped
    """
    set_code = set_data["id"]
    set_name = format_set_name(set_data)

    # Remove "Other - " prefix (catch-all category, not a real series)
    if set_name.startswith("Other - "):
        set_name = set_name.replace("Other - ", "", 1)

    release_date = set_data.get("releaseDate", "")

    # Parse year from release date (format: YYYY/MM/DD or YYYY-MM-DD)
    year = None
    if release_date:
        year_str = release_date.split("/")[0].split("-")[0]
        try:
            year = int(year_str)
        except ValueError:
            year = None

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


def import_card(
    db_client: DatabaseClient,
    card_data: dict,
    set_entity_id: str,
    set_year: int,
    set_total: str,
    dry_run: bool = False
) -> bool:
    """
    Import a single card

    Args:
        db_client: Database client
        card_data: Card data from JSON
        set_entity_id: UUID of set entity
        set_year: Year of the set
        set_total: Total cards in set (e.g., "102")
        dry_run: If True, don't make database changes

    Returns:
        True if created, False if updated/skipped
    """
    card_id = card_data["id"]

    # Build card name with set info
    number = card_data.get("number", "")
    card_name = f"{card_data['name']} {number}/{set_total}"

    # Build attributes (only include rarity, artist, language, card_number)
    attributes = {
        "language": "en",
        "card_number": f"{number}/{set_total}",
    }

    if card_data.get("rarity"):
        attributes["rarity"] = card_data["rarity"]

    if card_data.get("artist"):
        attributes["artist"] = card_data["artist"]

    # High-res image
    images = card_data.get("images", {})
    image_key = images.get("large") or images.get("small")

    if dry_run:
        return False

    # Upsert entity
    entity_id, created = db_client.upsert_entity(
        external_system="pokemontcg.io",
        external_id=card_id,
        entity_type="trading_card",
        name=card_name,
        year=set_year,
        image_key=image_key,
        attributes=attributes
    )

    # Get numeric order from card number
    order = 0
    try:
        # Try to extract numeric part
        if number.isdigit():
            order = int(number)
        else:
            # Try to extract leading digits
            import re
            match = re.match(r'(\d+)', number)
            if match:
                order = int(match.group(1))
    except ValueError:
        pass

    # Link to set with order
    db_client.create_relationship(
        from_id=set_entity_id,
        to_id=entity_id,
        rel_type="contains",
        attributes={"order": order}
    )

    return created


def main():
    parser = argparse.ArgumentParser(description="Import Pokemon TCG data from local JSON files")
    parser.add_argument("--sets-limit", type=int, help="Import only first N sets")
    parser.add_argument("--cards-limit", type=int, help="Import only first N cards per set")
    parser.add_argument("--set", help="Import only specific set by code (e.g., 'swsh4')")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    args = parser.parse_args()

    # Initialize database client
    db_client = DatabaseClient()

    print("=" * 60)
    print("IMPORTING FROM LOCAL POKEMON TCG DATA")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Load sets
    print("\n📦 Loading sets from local data...")
    all_sets = load_sets()

    # Filter by specific set if requested
    if args.set:
        all_sets = [s for s in all_sets if s["id"] == args.set]
        if not all_sets:
            print(f"❌ Set '{args.set}' not found in local data")
            sys.exit(1)

    if args.sets_limit:
        all_sets = all_sets[:args.sets_limit]

    print(f"Found {len(all_sets)} sets to import\n")

    # Import sets
    sets_created = 0
    sets_updated = 0

    for i, set_data in enumerate(all_sets, 1):
        set_code = set_data["id"]
        set_name = format_set_name(set_data)

        print(f"[{i}/{len(all_sets)}] {set_name} ({set_code})")

        try:
            created = import_set(db_client, set_data, dry_run=args.dry_run)
            if created:
                sets_created += 1
                print(f"  ✅ Set created")
            else:
                sets_updated += 1
                if not args.dry_run:
                    print(f"  ♻️  Set updated")

            # Import cards for this set
            if not args.dry_run or args.dry_run:  # Import cards in both modes
                cards = load_cards_for_set(set_code)

                if args.cards_limit:
                    cards = cards[:args.cards_limit]

                if cards:
                    print(f"  📋 Importing {len(cards)} cards...")

                    # Get set entity to link cards
                    set_entity = db_client.find_entity_by_external_id("pokemontcg.io", set_code)
                    if not set_entity:
                        print(f"  ⚠️  Set entity not found, skipping cards")
                        continue

                    set_year = set_entity.get("year")
                    # Get set total from set_data
                    set_total = str(set_data.get("printedTotal", set_data.get("total", "0")))
                    cards_created = 0
                    cards_updated = 0

                    for card_data in cards:
                        try:
                            created = import_card(
                                db_client,
                                card_data,
                                set_entity["id"],
                                set_year,
                                set_total,
                                dry_run=args.dry_run
                            )

                            if created:
                                cards_created += 1
                            else:
                                cards_updated += 1

                        except Exception as e:
                            print(f"    ❌ Error importing card: {e}")
                            continue

                    print(f"  ✅ Cards: {cards_created} created, {cards_updated} updated")
                else:
                    print(f"  ⚠️  No cards found")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    # Summary
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print("DRY RUN COMPLETE")
    else:
        print("IMPORT COMPLETE")
    print(f"{'=' * 60}")
    print(f"\nSets:")
    print(f"  Processed: {len(all_sets)}")
    print(f"  Created: {sets_created}")
    print(f"  Updated: {sets_updated}")

    if not args.dry_run:
        print(f"\n💡 Tip: Run localize_images.py to download and store all images locally.")


if __name__ == "__main__":
    main()
