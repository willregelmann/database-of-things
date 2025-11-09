#!/usr/bin/env python3
"""
Re-localize images for existing entities.

Useful after fixing image localization bugs or updating storage configuration.
"""

import os
import sys
from pathlib import Path

# Auto-install dependencies
try:
    from supabase import create_client
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "supabase"])
    from supabase import create_client

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from image_utils import ImageLocalizer

def main():
    # Get credentials from environment
    supabase_url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    collection_id = os.getenv("COLLECTION_ID")

    if not supabase_key or not collection_id:
        print("Error: SUPABASE_SERVICE_KEY and COLLECTION_ID must be set")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)
    localizer = ImageLocalizer(supabase)

    # Get all games in the collection with external image URLs
    print("Fetching games from database...")
    result = supabase.table("entities").select(
        "id, name, image_url, external_ids"
    ).eq("type", "video_game").execute()

    games = [
        g for g in result.data
        if g.get("image_url") and g["image_url"].startswith("http")
    ]

    print(f"Found {len(games)} games with external images\n")

    success = 0
    failed = 0

    for i, game in enumerate(games, 1):
        name = game["name"]
        entity_id = game["id"]
        external_url = game["image_url"]

        print(f"[{i}/{len(games)}] {name}")
        print(f"  External: {external_url}")

        # Localize image
        image_url, thumbnail_url = localizer.localize_image(external_url, entity_id)

        if image_url:
            # Update entity with localized URLs
            update_data = {"image_url": image_url}
            if thumbnail_url:
                update_data["thumbnail_url"] = thumbnail_url

            supabase.table("entities").update(update_data).eq("id", entity_id).execute()

            print(f"  ✓ Localized: {image_url}")
            if thumbnail_url:
                print(f"  ✓ Thumbnail: {thumbnail_url}")
            success += 1
        else:
            print(f"  ✗ Failed to localize")
            failed += 1

        print()

    print("=" * 60)
    print(f"✓ Complete:")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
