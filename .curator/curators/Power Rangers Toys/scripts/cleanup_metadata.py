#!/usr/bin/env python3
"""
Clean up metadata for Power Rangers toys.

Fixes:
1. Remove item_number from attributes (already in external_ids)
2. Remove release_date from attributes (redundant with year column)
3. Add manufacturer to attributes (from toy line parent)
"""

import os
import sys
from pathlib import Path

# Auto-install dependencies if missing
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "supabase"
    ])
    from supabase import create_client, Client


def load_config():
    """Load Supabase configuration from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    return supabase_url, supabase_key


def cleanup_toy_metadata(supabase: Client) -> tuple[int, int]:
    """
    Clean up metadata for all Power Rangers toys.

    Returns (toys_cleaned, toys_skipped).
    """
    print("Fetching all Power Rangers toys...")

    # Get all toys with grnrngr external ID (fetch in batches)
    all_toys = []
    offset = 0
    batch_size = 1000

    while True:
        result = supabase.table("entities").select(
            "id, name, attributes, external_ids"
        ).eq("type", "toy").not_.is_("external_ids->>grnrngr", "null"
        ).range(offset, offset + batch_size - 1).execute()

        if not result.data:
            break

        all_toys.extend(result.data)
        print(f"  Fetched {len(all_toys)} toys so far...")

        if len(result.data) < batch_size:
            break

        offset += batch_size

    toys = all_toys
    print(f"Found {len(toys)} toys total to check\n")

    cleaned = 0
    skipped = 0

    for toy in toys:
        needs_update = False
        new_attributes = dict(toy.get("attributes", {}))

        # Check if item_number or release_date exist in attributes
        removed_fields = []
        if "item_number" in new_attributes:
            del new_attributes["item_number"]
            removed_fields.append("item_number")
            needs_update = True

        if "release_date" in new_attributes:
            del new_attributes["release_date"]
            removed_fields.append("release_date")
            needs_update = True

        # Get manufacturer from toy line parent
        if "manufacturer" not in new_attributes:
            # Find parent toy line via relationship
            rel_result = supabase.table("relationships").select(
                "from_id, entities!relationships_from_id_fkey(attributes)"
            ).eq("to_id", toy["id"]).eq("type", "contains").execute()

            if rel_result.data:
                parent_attrs = rel_result.data[0]["entities"]["attributes"]
                manufacturer = parent_attrs.get("manufacturer")

                if manufacturer:
                    new_attributes["manufacturer"] = manufacturer
                    needs_update = True
                    removed_fields.append(f"+manufacturer:{manufacturer}")

        if needs_update:
            # Update the entity
            supabase.table("entities").update({
                "attributes": new_attributes
            }).eq("id", toy["id"]).execute()

            changes = ", ".join(removed_fields)
            print(f"  ✓ Cleaned: {toy['name'][:50]:50} ({changes})")
            cleaned += 1
        else:
            skipped += 1

    return cleaned, skipped


def main():
    print("=" * 70)
    print("Power Rangers Toys Metadata Cleanup")
    print("=" * 70)
    print()

    # Load configuration
    supabase_url, supabase_key = load_config()
    supabase = create_client(supabase_url, supabase_key)

    # Clean up metadata
    cleaned, skipped = cleanup_toy_metadata(supabase)

    print()
    print("=" * 70)
    print(f"✓ Complete:")
    print(f"  Cleaned: {cleaned}")
    print(f"  Skipped (already clean): {skipped}")
    print(f"  Total: {cleaned + skipped}")
    print("=" * 70)


if __name__ == "__main__":
    main()
