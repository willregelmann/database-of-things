#!/usr/bin/env python3
"""
Re-fetch and update cover art for games with incorrect platform covers.
"""

import os
import sys
import json
import time
from pathlib import Path

# Auto-install dependencies
try:
    from supabase import create_client, Client
    import requests
except ImportError:
    print("Installing dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "supabase", "requests"
    ])
    from supabase import create_client, Client
    import requests

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))
from image_utils import ImageLocalizer


class CoverArtUpdater:
    """Update cover art for games using platform-specific covers."""

    def __init__(self, supabase: Client, moby_api_key: str):
        self.supabase = supabase
        self.moby_api_key = moby_api_key
        self.image_localizer = ImageLocalizer(supabase)
        self.base_url = "https://api.mobygames.com/v1"

    def get_platform_cover(self, game_id: int, platform_id: int) -> str:
        """Fetch platform-specific cover art URL from MobyGames."""
        try:
            # Rate limiting: 1.5 seconds between requests
            time.sleep(1.5)

            # Fetch platform-specific covers
            url = f"{self.base_url}/games/{game_id}/platforms/{platform_id}/covers"
            response = requests.get(url, params={"api_key": self.moby_api_key})
            response.raise_for_status()

            covers_data = response.json()
            covers = covers_data.get("cover_groups", [])

            # Look for front cover from North American release
            for group in covers:
                countries = group.get("countries", [])
                if any(c in {"United States", "Canada"} for c in countries):
                    for cover in group.get("covers", []):
                        if cover.get("scan_of") == "Front Cover":
                            return cover.get("image")

            # Fallback to any front cover
            for group in covers:
                for cover in group.get("covers", []):
                    if cover.get("scan_of") == "Front Cover":
                        return cover.get("image")

            return None

        except Exception as e:
            print(f"      Error fetching covers: {e}")
            return None

    def update_game_cover(self, entity_id: str, game_name: str, new_cover_url: str):
        """Update a game's cover art with localized image."""
        print(f"    Processing: {game_name}")

        # Localize the new cover image
        print(f"      📥 Downloading new cover...")
        image_url, thumbnail_url = self.image_localizer.localize_image(
            new_cover_url,
            entity_id
        )

        if not image_url:
            print(f"      ⚠️  Failed to localize image")
            return False

        # Update entity with new image URLs
        self.supabase.table("entities").update({
            "image_url": image_url,
            "thumbnail_url": thumbnail_url
        }).eq("id", entity_id).execute()

        print(f"      ✓ Updated cover art")
        return True


def get_supabase_client() -> Client:
    """Get Supabase client from environment."""
    supabase_url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_key:
        print("Error: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    return create_client(supabase_url, supabase_key)


def main():
    print("=" * 60)
    print("Update Game Cover Art")
    print("=" * 60)

    # Load API key
    secrets_file = Path(__file__).parent.parent / "secrets.env"
    if secrets_file.exists():
        with open(secrets_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    moby_api_key = os.getenv("MOBY_GAMES_API_KEY")
    if not moby_api_key:
        print("Error: MOBY_GAMES_API_KEY not set")
        sys.exit(1)

    supabase = get_supabase_client()
    updater = CoverArtUpdater(supabase, moby_api_key)

    # Get all video games
    print("\nFinding video games to update...")
    result = supabase.table("entities").select(
        "id,name,external_ids,attributes"
    ).eq("type", "video_game").execute()

    # Extract games with MobyGames IDs
    games = []
    for entity in result.data:
        attrs = entity.get("attributes", {})
        platform = attrs.get("platform", "")

        # Extract MobyGames IDs from external_ids
        external_ids = entity.get("external_ids", {})
        moby_id = external_ids.get("moby_games", "")

        if moby_id and "-" in moby_id:
            game_id, platform_id = moby_id.split("-")
            games.append({
                "entity_id": entity["id"],
                "name": entity["name"],
                "game_id": int(game_id),
                "platform_id": int(platform_id),
                "platform": platform
            })

    if not games:
        print("No games with MobyGames IDs found!")
        return

    print(f"Found {len(games)} video games")
    print(f"\nUpdating cover art...")

    updated_count = 0
    failed_count = 0

    for game in games:
        # Fetch platform-specific cover
        new_cover_url = updater.get_platform_cover(
            game["game_id"],
            game["platform_id"]
        )

        if new_cover_url:
            success = updater.update_game_cover(
                game["entity_id"],
                game["name"],
                new_cover_url
            )
            if success:
                updated_count += 1
            else:
                failed_count += 1
        else:
            print(f"    ⊘ No cover found for: {game['name']}")
            failed_count += 1

    print("\n" + "=" * 60)
    print(f"✓ Update Complete!")
    print(f"  Updated: {updated_count}")
    print(f"  Failed: {failed_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
