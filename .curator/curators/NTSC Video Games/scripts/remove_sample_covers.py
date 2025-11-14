#!/usr/bin/env python3
"""
Remove video games that don't have platform-specific cover art.
These were imported with fallback sample covers from different platforms.
"""

import os
import sys

# Auto-install dependencies
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing supabase...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "supabase"])
    from supabase import create_client, Client


# Games to remove (no platform-specific covers available)
GAMES_TO_REMOVE = [
    "Centipede",
    "The Blues Brothers",
    "NHL 95",
    "Speedball 2: Brutal Deluxe",
    "Xenon 2: Megablast",
]


def get_supabase_client() -> Client:
    """Get Supabase client from environment."""
    supabase_url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_key:
        print("Error: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    return create_client(supabase_url, supabase_key)


def find_games_to_remove(supabase: Client) -> list:
    """Find all video game entities matching the removal list."""
    result = supabase.table("entities").select("id,name,attributes").eq(
        "type", "video_game"
    ).execute()

    # Filter for games in removal list
    games_to_remove = []
    for entity in result.data:
        name = entity.get("name", "")
        if name in GAMES_TO_REMOVE:
            games_to_remove.append(entity)

    return games_to_remove


def delete_entity_and_relationships(supabase: Client, entity_id: str, entity_name: str):
    """Delete an entity and all its relationships."""
    # Delete relationships where this entity is the target
    result = supabase.table("relationships").delete().eq("to_id", entity_id).execute()
    rel_count = len(result.data) if result.data else 0

    # Delete relationships where this entity is the source
    result2 = supabase.table("relationships").delete().eq("from_id", entity_id).execute()
    rel_count += len(result2.data) if result2.data else 0

    # Delete the entity itself
    supabase.table("entities").delete().eq("id", entity_id).execute()

    return rel_count


def main():
    print("=" * 60)
    print("Remove Games with Sample Covers")
    print("=" * 60)

    supabase = get_supabase_client()

    # Find games to remove
    print("\nFinding games without platform-specific covers...")
    games_to_delete = find_games_to_remove(supabase)

    if not games_to_delete:
        print("✓ No games found to remove!")
        return

    print(f"Found {len(games_to_delete)} games to delete:\n")
    for game in sorted(games_to_delete, key=lambda x: x["name"]):
        platform = game["attributes"].get("platform", "Unknown")
        print(f"  - {game['name']} ({platform})")

    # Delete games
    print("\nDeleting games...")
    total_relationships = 0

    for game in games_to_delete:
        rel_count = delete_entity_and_relationships(supabase, game["id"], game["name"])
        total_relationships += rel_count
        print(f"  ✓ Deleted: {game['name']} ({rel_count} relationships)")

    print("\n" + "=" * 60)
    print(f"✓ Cleanup Complete!")
    print(f"  Deleted: {len(games_to_delete)} games")
    print(f"  Removed: {total_relationships} relationships")
    print("=" * 60)


if __name__ == "__main__":
    main()
