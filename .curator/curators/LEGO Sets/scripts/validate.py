#!/usr/bin/env python3
"""Validate imported LEGO sets data."""

import os
import sys

# Auto-install dependencies if missing
try:
    from supabase import create_client
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "supabase"
    ])
    from supabase import create_client


def validate_collection(collection_id):
    """Check collection integrity."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    print("=" * 60)
    print("LEGO Sets Collection Validator")
    print("=" * 60)
    print()

    # Count sets in collection
    result = supabase.table("relationships").select(
        "id", count="exact"
    ).eq("from_id", collection_id).eq("type", "contains").execute()

    total = result.count

    # Get collection details
    collection = supabase.table("entities").select("name").eq("id", collection_id).execute()
    collection_name = collection.data[0]["name"] if collection.data else "Unknown"

    print(f"Collection: {collection_name}")
    print(f"Total sets: {total}")
    print()

    # Check for sets missing images
    entities = supabase.table("relationships").select(
        "entities!relationships_to_id_fkey(id, name, image_url, thumbnail_url)"
    ).eq("from_id", collection_id).eq("type", "contains").execute()

    missing_images = []
    missing_thumbnails = []

    for e in entities.data:
        entity = e["entities"]
        if not entity.get("image_url"):
            missing_images.append(entity["name"])
        elif not entity.get("thumbnail_url"):
            missing_thumbnails.append(entity["name"])

    # Check for sets missing embeddings
    entities_data = supabase.table("relationships").select(
        "entities!relationships_to_id_fkey(id, name, name_embedding)"
    ).eq("from_id", collection_id).eq("type", "contains").execute()

    missing_embeddings = [
        e["entities"]["name"]
        for e in entities_data.data
        if not e["entities"].get("name_embedding")
    ]

    # Check for sets missing external IDs
    entities_ids = supabase.table("relationships").select(
        "entities!relationships_to_id_fkey(id, name, external_ids)"
    ).eq("from_id", collection_id).eq("type", "contains").execute()

    missing_lego_number = [
        e["entities"]["name"]
        for e in entities_ids.data
        if not e["entities"].get("external_ids", {}).get("lego_number")
    ]

    # Print validation results
    print("Validation Results:")
    print(f"  ✓ Sets with images: {total - len(missing_images)}/{total}")
    print(f"  ✓ Sets with thumbnails: {total - len(missing_thumbnails)}/{total}")
    print(f"  ✓ Sets with embeddings: {total - len(missing_embeddings)}/{total}")
    print(f"  ✓ Sets with LEGO numbers: {total - len(missing_lego_number)}/{total}")
    print()

    # Show issues if any
    issues_found = False

    if missing_images:
        issues_found = True
        print("⚠️  Sets missing images:")
        for name in missing_images[:10]:
            print(f"  - {name}")
        if len(missing_images) > 10:
            print(f"  ... and {len(missing_images) - 10} more")
        print()

    if missing_thumbnails:
        issues_found = True
        print("⚠️  Sets missing thumbnails:")
        for name in missing_thumbnails[:10]:
            print(f"  - {name}")
        if len(missing_thumbnails) > 10:
            print(f"  ... and {len(missing_thumbnails) - 10} more")
        print()

    if missing_embeddings:
        issues_found = True
        print("⚠️  Sets missing embeddings:")
        for name in missing_embeddings[:10]:
            print(f"  - {name}")
        if len(missing_embeddings) > 10:
            print(f"  ... and {len(missing_embeddings) - 10} more")
        print()

    if missing_lego_number:
        issues_found = True
        print("⚠️  Sets missing LEGO numbers:")
        for name in missing_lego_number[:10]:
            print(f"  - {name}")
        if len(missing_lego_number) > 10:
            print(f"  ... and {len(missing_lego_number) - 10} more")
        print()

    if not issues_found:
        print("✓ All validation checks passed!")
        print()

    print("=" * 60)


def main():
    collection_id = os.getenv("COLLECTION_ID")
    if not collection_id:
        print("❌ Error: COLLECTION_ID required")
        print("Set the collection ID in secrets.env:")
        print("  COLLECTION_ID=uuid-from-database")
        sys.exit(1)

    validate_collection(collection_id)


if __name__ == "__main__":
    main()
