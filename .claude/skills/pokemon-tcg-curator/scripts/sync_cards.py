#!/usr/bin/env python3
"""
Sync Pokémon TCG Cards

Discovers and imports cards for a specific set from pokemontcg.io API.
Creates card entities and links them to the set.
"""

import argparse
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import PokemonTCGClient, DatabaseClient


def format_card_name(card_data: dict) -> str:
    """
    Format card name as "<name> <number>/<total>"

    Args:
        card_data: Card data from API

    Returns:
        Formatted name
    """
    name = card_data.get("name", "")
    number = card_data.get("number", "")
    set_total = card_data.get("set", {}).get("printedTotal", "")

    # Zero-pad number to 3 digits
    if number.isdigit() and set_total:
        number = number.zfill(3)

    return f"{name} {number}/{set_total}"


def parse_card_number(card_data: dict) -> str:
    """
    Get card number in format "number/total"

    Args:
        card_data: Card data from API

    Returns:
        Card number string
    """
    number = card_data.get("number", "")
    set_total = card_data.get("set", {}).get("printedTotal", "")

    # Zero-pad number to 3 digits if numeric
    if number.isdigit() and set_total:
        number = number.zfill(3)

    return f"{number}/{set_total}"


def sync_card(
    api_client: PokemonTCGClient,
    db_client: DatabaseClient,
    card_data: dict,
    set_entity_id: str,
    set_year: int,
    dry_run: bool = False
) -> bool:
    """
    Sync a single card

    Args:
        api_client: Pokémon TCG API client
        db_client: Database client
        card_data: Card data from API
        set_entity_id: UUID of set entity
        set_year: Year of the set
        dry_run: If True, don't make database changes

    Returns:
        True if created, False if updated/skipped
    """
    card_id = card_data["id"]
    card_name = format_card_name(card_data)
    card_number = parse_card_number(card_data)

    # Build attributes (only include rarity, artist, language, card_number)
    attributes = {
        "language": "en",
        "card_number": card_number,
    }

    if card_data.get("rarity"):
        attributes["rarity"] = card_data["rarity"]

    if card_data.get("artist"):
        attributes["artist"] = card_data["artist"]

    # High-res image
    images = card_data.get("images", {})
    image_key = images.get("large") or images.get("small")

    if dry_run:
        print(f"  [DRY RUN] Would create/update: {card_name}")
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
    number_str = card_data.get("number", "0")
    order = int(number_str) if number_str.isdigit() else 0

    # Link to set with order
    db_client.create_relationship(
        from_id=set_entity_id,
        to_id=entity_id,
        rel_type="contains",
        attributes={"order": order}
    )

    return created


def main():
    parser = argparse.ArgumentParser(description="Sync cards for a Pokémon TCG set")
    parser.add_argument("set_identifier", help="Set name or code (e.g., 'swsh4' or 'Sword & Shield - Vivid Voltage')")
    parser.add_argument("--limit", type=int, help="Process only first N cards")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    args = parser.parse_args()

    # Initialize clients
    api_client = PokemonTCGClient()
    db_client = DatabaseClient()

    print(f"🔍 Finding set: {args.set_identifier}")

    # Try to find set by external ID first (if looks like a code)
    set_entity = None
    set_code = None

    if len(args.set_identifier) <= 15:
        # Looks like a set code (e.g., "swsh4", "base1", "sm1-1")
        # Try finding by external_id first
        set_entity = db_client.find_entity_by_external_id("pokemontcg.io", args.set_identifier)
        if set_entity:
            set_code = args.set_identifier

    # If not found, try by name
    if not set_entity:
        set_entity = db_client.find_entity_by_name_and_type(args.set_identifier, "collection")

    if not set_entity:
        print(f"❌ Set not found: {args.set_identifier}")
        print("\nTip: First sync the set using sync_sets.py, then sync its cards.")
        sys.exit(1)

    # Get set code from external_ids
    if not set_code:
        external_ids = set_entity.get("external_ids", {})
        set_code = external_ids.get("pokemontcg.io")

    if not set_code:
        print(f"❌ Set has no pokemontcg.io external ID")
        sys.exit(1)

    set_name = set_entity["name"]
    set_year = set_entity.get("year")
    print(f"✅ Found set: {set_name} ({set_code})")

    print(f"\n🔍 Fetching cards for {set_code}...")

    # Fetch all cards for set
    all_cards = api_client.get_cards_for_set(set_code)

    if args.limit:
        all_cards = all_cards[:args.limit]

    print(f"📦 Found {len(all_cards)} cards")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Sync each card
    created_count = 0
    updated_count = 0

    for i, card_data in enumerate(all_cards, 1):
        card_name = format_card_name(card_data)
        print(f"[{i}/{len(all_cards)}] {card_name}")

        try:
            created = sync_card(
                api_client,
                db_client,
                card_data,
                set_entity["id"],
                set_year,
                dry_run=args.dry_run
            )

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
    print(f"Total cards: {len(all_cards)}")
    print(f"Created: {created_count}")
    print(f"Updated: {updated_count}")


if __name__ == "__main__":
    main()
