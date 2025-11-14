#!/usr/bin/env python3
"""
Clean up duplicate Pokemon games by removing entries with 'region' metadata.
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


def get_supabase_client() -> Client:
    """Get Supabase client from environment."""
    supabase_url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_key:
        print("Error: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    return create_client(supabase_url, supabase_key)


def find_games_with_region(supabase: Client) -> list:
    """Find all Pokemon games with 'region' metadata."""
    result = supabase.table("entities").select("id,name,year,attributes").eq(
        "type", "video_game"
    ).execute()

    # Filter for Pokemon games with 'region' in attributes
    pokemon_with_region = []
    for entity in result.data:
        name = entity.get("name", "")
        attributes = entity.get("attributes", {})

        if ("pokémon" in name.lower() or "pokemon" in name.lower()) and "region" in attributes:
            pokemon_with_region.append(entity)

    return pokemon_with_region


def delete_entity_and_relationships(supabase: Client, entity_id: str, entity_name: str):
    """Delete an entity and all its relationships."""
    # Delete relationships where this entity is the target
    result = supabase.table("relationships").delete().eq("to_id", entity_id).execute()
    rel_count = len(result.data) if result.data else 0

    # Delete relationships where this entity is the source (shouldn't be any for games)
    result2 = supabase.table("relationships").delete().eq("from_id", entity_id).execute()
    rel_count += len(result2.data) if result2.data else 0

    # Delete the entity itself
    supabase.table("entities").delete().eq("id", entity_id).execute()

    return rel_count


def main():
    print("=" * 60)
    print("Pokemon Duplicate Cleanup Script")
    print("=" * 60)

    supabase = get_supabase_client()

    # Find games with region metadata
    print("\nFinding Pokemon games with 'region' metadata...")
    games_to_delete = find_games_with_region(supabase)

    if not games_to_delete:
        print("✓ No duplicates found!")
        return

    print(f"Found {len(games_to_delete)} games to delete:\n")
    for game in sorted(games_to_delete, key=lambda x: x["name"]):
        region = game["attributes"].get("region", "")
        print(f"  - {game['name']} ({game['year']}) [region: {region}]")

    # Confirm deletion
    print(f"\nThese {len(games_to_delete)} games will be deleted along with their relationships.")
    response = input("Continue? (yes/no): ")

    if response.lower() != "yes":
        print("Cancelled.")
        return

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
