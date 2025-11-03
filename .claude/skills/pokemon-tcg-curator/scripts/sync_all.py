#!/usr/bin/env python3
"""
Sync All Pokémon TCG Data

Syncs all sets and their cards from pokemontcg.io API in one command.
"""

import argparse
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import PokemonTCGClient, DatabaseClient
from sync_sets import sync_set, format_set_name
from sync_cards import sync_card


def main():
    parser = argparse.ArgumentParser(description="Sync all Pokémon TCG sets and cards")
    parser.add_argument("--sets-limit", type=int, help="Process only first N sets")
    parser.add_argument("--cards-limit", type=int, help="Process only first N cards per set")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    args = parser.parse_args()

    # Initialize clients
    api_client = PokemonTCGClient()
    db_client = DatabaseClient()

    print("=" * 60)
    print("SYNCING ALL POKÉMON TCG DATA")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # STEP 1: Sync Sets
    print("\n📦 STEP 1: Syncing sets...")
    print("-" * 60)

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

    if args.sets_limit:
        all_sets = all_sets[:args.sets_limit]

    print(f"Found {len(all_sets)} sets\n")

    sets_created = 0
    sets_updated = 0

    for i, set_data in enumerate(all_sets, 1):
        set_name = format_set_name(set_data)
        print(f"[{i}/{len(all_sets)}] {set_name}")

        try:
            created = sync_set(api_client, db_client, set_data, dry_run=args.dry_run)
            if created:
                sets_created += 1
                print(f"  ✅ Created")
            else:
                sets_updated += 1
                if not args.dry_run:
                    print(f"  ♻️  Updated")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    print(f"\nSets Summary: {sets_created} created, {sets_updated} updated")

    # STEP 2: Sync Cards for Each Set
    print(f"\n🃏 STEP 2: Syncing cards for each set...")
    print("-" * 60)

    total_cards_created = 0
    total_cards_updated = 0
    total_cards_processed = 0

    for i, set_data in enumerate(all_sets, 1):
        set_code = set_data["id"]
        set_name = format_set_name(set_data)

        print(f"\n[{i}/{len(all_sets)}] {set_name} ({set_code})")

        # Get set entity
        set_entity = db_client.find_entity_by_external_id("pokemontcg.io", set_code)
        if not set_entity:
            print(f"  ⚠️  Set not found in database, skipping")
            continue

        set_year = set_entity.get("year")

        # Fetch cards
        try:
            all_cards = api_client.get_cards_for_set(set_code)
        except Exception as e:
            print(f"  ❌ Error fetching cards: {e}")
            continue

        if args.cards_limit:
            all_cards = all_cards[:args.cards_limit]

        print(f"  Found {len(all_cards)} cards")

        cards_created = 0
        cards_updated = 0

        for j, card_data in enumerate(all_cards, 1):
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
                    cards_created += 1
                else:
                    cards_updated += 1

                # Progress indicator every 10 cards
                if j % 10 == 0:
                    print(f"    Progress: {j}/{len(all_cards)} cards")

            except Exception as e:
                print(f"    ❌ Error syncing card {j}: {e}")
                continue

        total_cards_created += cards_created
        total_cards_updated += cards_updated
        total_cards_processed += len(all_cards)

        print(f"  ✅ {cards_created} created, {cards_updated} updated")

    # Final Summary
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print("DRY RUN COMPLETE")
    else:
        print("SYNC COMPLETE")
    print(f"{'=' * 60}")
    print(f"\nSets:")
    print(f"  Total: {len(all_sets)}")
    print(f"  Created: {sets_created}")
    print(f"  Updated: {sets_updated}")
    print(f"\nCards:")
    print(f"  Total: {total_cards_processed}")
    print(f"  Created: {total_cards_created}")
    print(f"  Updated: {total_cards_updated}")

    if not args.dry_run:
        print(f"\n💡 Tip: Run localize_images.py to download and store all images locally.")


if __name__ == "__main__":
    main()
