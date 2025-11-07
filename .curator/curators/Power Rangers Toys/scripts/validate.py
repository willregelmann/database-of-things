#!/usr/bin/env python3
"""Validate Power Rangers toy collection in Supabase."""

import os
import sys

# Auto-install dependencies if missing
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "supabase"])
    from supabase import create_client, Client

FRANCHISE_ID = "d183e3a9-4eb7-40a5-b264-526b9a03ec30"


def load_config():
    """Load Supabase configuration from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    return supabase_url, supabase_key


def validate_collection(supabase: Client):
    """Validate the Power Rangers toy collection."""
    print("=" * 60)
    print("Power Rangers Collection Validation")
    print("=" * 60)
    print()

    # Get all series under Power Rangers franchise
    series_result = supabase.table("relationships").select(
        "to_id, entities!relationships_to_id_fkey(id, name, type, year)"
    ).eq("from_id", FRANCHISE_ID).eq("type", "contains").execute()

    series_count = len(series_result.data)
    print(f"Series found: {series_count}")
    print()

    total_toys = 0
    missing_images = 0
    missing_years = 0

    # For each series, count toys and check data quality
    for rel in series_result.data:
        series = rel["entities"]
        series_id = series["id"]
        series_name = series["name"]
        series_year = series.get("year", "unknown")

        # Get toys in this series
        toys_result = supabase.table("relationships").select(
            "to_id, entities!relationships_to_id_fkey(id, name, type, year, image_url)"
        ).eq("from_id", series_id).eq("type", "contains").execute()

        toy_count = len(toys_result.data)
        total_toys += toy_count

        # Check for data quality issues
        series_missing_images = 0
        series_missing_years = 0

        for toy_rel in toys_result.data:
            toy = toy_rel["entities"]
            if not toy.get("image_url"):
                series_missing_images += 1
                missing_images += 1
            if not toy.get("year"):
                series_missing_years += 1
                missing_years += 1

        print(f"📁 {series_name} ({series_year})")
        print(f"   Toys: {toy_count}")

        if series_missing_images > 0:
            print(f"   ⚠️  Missing images: {series_missing_images}")
        if series_missing_years > 0:
            print(f"   ⚠️  Missing years: {series_missing_years}")

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total series: {series_count}")
    print(f"Total toys: {total_toys}")
    print()

    if missing_images > 0:
        print(f"⚠️  Toys missing images: {missing_images} ({missing_images/total_toys*100:.1f}%)")
    else:
        print("✓ All toys have images")

    if missing_years > 0:
        print(f"⚠️  Toys missing years: {missing_years} ({missing_years/total_toys*100:.1f}%)")
    else:
        print("✓ All toys have years")

    print()

    # Check for orphaned toys (not linked to any series)
    orphaned_result = supabase.table("entities").select("id, name").eq("type", "toy").execute()

    orphaned_toys = []
    for toy in orphaned_result.data:
        # Check if this toy is linked to any series
        link_check = supabase.table("relationships").select("id").eq(
            "to_id", toy["id"]
        ).eq("type", "contains").execute()

        if not link_check.data:
            orphaned_toys.append(toy["name"])

    if orphaned_toys:
        print(f"⚠️  Orphaned toys (not linked to series): {len(orphaned_toys)}")
        for name in orphaned_toys[:10]:
            print(f"   - {name}")
        if len(orphaned_toys) > 10:
            print(f"   ... and {len(orphaned_toys) - 10} more")
    else:
        print("✓ No orphaned toys")

    print()
    print("=" * 60)


def main():
    supabase_url, supabase_key = load_config()
    supabase = create_client(supabase_url, supabase_key)

    validate_collection(supabase)


if __name__ == "__main__":
    main()
