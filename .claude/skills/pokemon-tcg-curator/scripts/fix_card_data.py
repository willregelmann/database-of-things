#!/usr/bin/env python3
"""
Fix Card Data

Fixes existing card data to match the correct format:
- Card names: "CardName number/total" (e.g., "Blastoise 2/102")
- card_number attribute: "number/total" (e.g., "2/102")
- Remove hp, types, subtypes, supertype from attributes
"""

import sys
from pathlib import Path
import json

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import DatabaseClient


def fix_card(db_client: DatabaseClient, card: dict, set_total: str) -> bool:
    """
    Fix a single card's name and attributes

    Args:
        db_client: Database client
        card: Card entity dict
        set_total: Total cards in set (e.g., "102")

    Returns:
        True if card was updated
    """
    card_id = card["id"]
    current_name = card["name"]
    current_attrs = card.get("attributes", {})

    # Get current card number from attributes
    card_number = current_attrs.get("card_number", "")

    # Check if card needs fixing
    needs_name_fix = "/" not in current_name
    needs_attr_fix = (
        "/" not in card_number or
        "hp" in current_attrs or
        "types" in current_attrs or
        "subtypes" in current_attrs or
        "supertype" in current_attrs
    )

    if not needs_name_fix and not needs_attr_fix:
        return False

    # Extract base name and number
    if "/" in current_name:
        # Already has format like "Charizard 025/185"
        parts = current_name.rsplit(" ", 1)
        base_name = parts[0]
        number_part = parts[1].split("/")[0] if len(parts) > 1 else card_number.split("/")[0]
    else:
        # Has format like "Alakazam 1"
        parts = current_name.rsplit(" ", 1)
        base_name = parts[0]
        number_part = parts[1] if len(parts) > 1 and parts[1].replace("-", "").isdigit() else card_number

    # Build correct name
    new_name = f"{base_name} {number_part}/{set_total}"

    # Build correct card_number
    new_card_number = f"{number_part}/{set_total}"

    # Build new attributes (remove unwanted fields)
    new_attrs = {}
    for key, value in current_attrs.items():
        if key not in ["hp", "types", "subtypes", "supertype"]:
            new_attrs[key] = value

    # Update card_number
    new_attrs["card_number"] = new_card_number

    print(f"  Fixing: {current_name} → {new_name}")
    print(f"    card_number: {card_number} → {new_card_number}")

    # Update in database
    sql = f"""
        UPDATE entities
        SET
            name = '{new_name.replace("'", "''")}',
            attributes = '{json.dumps(new_attrs)}'::jsonb,
            updated_at = NOW()
        WHERE id = '{card_id}'
    """

    db_client._exec_sql(sql)

    return True


def main():
    db_client = DatabaseClient()

    print("=" * 60)
    print("FIXING CARD DATA")
    print("=" * 60)
    print()

    # Get all collections with their total cards
    collections_sql = """
        SELECT id, name, COALESCE(attributes->>'printedTotal', attributes->>'total') as set_total
        FROM entities
        WHERE type = 'collection'
          AND (attributes->>'printedTotal' IS NOT NULL OR attributes->>'total' IS NOT NULL)
        ORDER BY name
    """

    collections = db_client._exec_sql_json(collections_sql)

    total_fixed = 0

    for collection in collections:
        collection_id = collection["id"]
        collection_name = collection["name"]
        set_total = collection.get("set_total")

        if not set_total:
            print(f"⚠️  {collection_name}: No total found, skipping")
            continue

        print(f"\n📦 {collection_name} (total: {set_total})")

        # Get all cards in this collection
        cards_sql = f"""
            SELECT e.id, e.name, COALESCE(e.attributes, '{{}}'::jsonb) as attributes
            FROM entities e
            JOIN relationships r ON r.to_id = e.id
            WHERE r.from_id = '{collection_id}'
              AND r.type = 'contains'
              AND e.type = 'trading_card'
            ORDER BY e.name
        """

        cards = db_client._exec_sql_json(cards_sql)

        if not cards:
            print(f"  No cards found")
            continue

        collection_fixed = 0
        for card in cards:
            if fix_card(db_client, card, set_total):
                collection_fixed += 1
                total_fixed += 1

        if collection_fixed == 0:
            print(f"  ✅ All {len(cards)} cards already correct")
        else:
            print(f"  ✅ Fixed {collection_fixed}/{len(cards)} cards")

    print(f"\n{'=' * 60}")
    print(f"COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total cards fixed: {total_fixed}")


if __name__ == "__main__":
    main()
