#!/usr/bin/env python3
"""Validate imported Labubu data for consistency and completeness."""

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
    collection_id = os.getenv("COLLECTION_ID")

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    if not collection_id:
        print("❌ Error: COLLECTION_ID not found in environment")
        sys.exit(1)

    return supabase_url, supabase_key, collection_id


def validate_collection(supabase: Client, collection_id: str):
    """Validate the Labubu collection structure and data.

    Args:
        supabase: Supabase client
        collection_id: Main collection entity ID
    """
    print("=" * 60)
    print("Labubu Collection Validator")
    print("=" * 60)
    print()

    issues = []

    # Get main collection
    collection = supabase.table("entities").select("*").eq("id", collection_id).execute()
    if not collection.data:
        print("❌ Main collection not found")
        sys.exit(1)

    collection_name = collection.data[0]["name"]
    print(f"Validating collection: {collection_name}")
    print()

    # Get all series (sub-collections)
    series_result = supabase.table("relationships").select(
        "to_id, entities!relationships_to_id_fkey(*)"
    ).eq("from_id", collection_id).eq("type", "contains").execute()

    series_list = [rel["entities"] for rel in series_result.data]
    print(f"✓ Found {len(series_list)} series")

    # Validate each series
    total_figures = 0
    missing_images = 0
    missing_thumbnails = 0
    missing_embeddings = 0
    missing_external_ids = 0

    for series in series_list:
        series_id = series["id"]
        series_name = series["name"]

        # Get figures in this series
        figures_result = supabase.table("relationships").select(
            "to_id, entities!relationships_to_id_fkey(*)"
        ).eq("from_id", series_id).eq("type", "contains").execute()

        figures = [rel["entities"] for rel in figures_result.data]
        total_figures += len(figures)

        print(f"  {series_name}: {len(figures)} figures")

        # Check each figure
        for figure in figures:
            # Check required fields
            if not figure.get("image_url"):
                missing_images += 1
                issues.append(f"Missing image: {series_name} - {figure['name']}")

            if not figure.get("thumbnail_url"):
                missing_thumbnails += 1

            if not figure.get("name_embedding"):
                missing_embeddings += 1

            # Check external IDs
            external_ids = figure.get("external_ids", {})
            if not external_ids.get("popmartworld_slug"):
                missing_external_ids += 1
                issues.append(f"Missing external ID: {series_name} - {figure['name']}")

            # Check attributes
            attributes = figure.get("attributes", {})
            if not attributes.get("series"):
                issues.append(f"Missing series attribute: {series_name} - {figure['name']}")

            if "is_secret" not in attributes:
                issues.append(f"Missing is_secret flag: {series_name} - {figure['name']}")

    print()
    print("=" * 60)
    print("Validation Summary")
    print("=" * 60)
    print(f"Total series:           {len(series_list)}")
    print(f"Total figures:          {total_figures}")
    print()
    print(f"Missing images:         {missing_images}")
    print(f"Missing thumbnails:     {missing_thumbnails}")
    print(f"Missing embeddings:     {missing_embeddings}")
    print(f"Missing external IDs:   {missing_external_ids}")
    print()

    if issues:
        print(f"❌ Found {len(issues)} issues:")
        print()
        for issue in issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
    else:
        print("✓ No issues found!")

    print()

    # Metadata consistency check
    print("Metadata Consistency:")
    print()

    # Check for consistent attribute fields
    all_figures = supabase.table("entities").select(
        "attributes"
    ).eq("type", "figure").execute()

    attribute_keys = set()
    for figure in all_figures.data:
        attrs = figure.get("attributes", {})
        attribute_keys.update(attrs.keys())

    print(f"  Unique attribute keys: {', '.join(sorted(attribute_keys))}")
    print()

    if len(attribute_keys) > 5:
        print("⚠️  Many different attribute keys detected - check for consistency")
    else:
        print("✓ Attribute keys look consistent")


def main():
    # Load configuration
    supabase_url, supabase_key, collection_id = load_config()

    # Create Supabase client
    supabase = create_client(supabase_url, supabase_key)

    # Run validation
    validate_collection(supabase, collection_id)


if __name__ == "__main__":
    main()
