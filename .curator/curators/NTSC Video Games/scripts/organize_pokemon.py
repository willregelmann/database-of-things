#!/usr/bin/env python3
"""
Organize Pokemon video games into proper hierarchy:
- Main RPG series: organized by generation sub-collections
- Spin-offs: linked directly to Pokemon franchise
- All games keep their platform collection links
"""

import os
import sys
from pathlib import Path

# Auto-install dependencies
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing supabase...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "supabase"])
    from supabase import create_client, Client

# Pokemon franchise ID
POKEMON_FRANCHISE_ID = "044eef5c-491c-43f2-84ae-0900a6938305"

# Main RPG games organized by generation
MAIN_RPG_GAMES = {
    "Generation I": [
        "Pokémon Red Version",
        "Pokémon Blue Version",
        "Pokémon Yellow Version: Special Pikachu Edition",
    ],
    "Generation II": [
        "Pokémon Gold Version",
        "Pokémon Silver Version",
        "Pokémon Crystal Version",
    ],
    "Generation III": [
        "Pokémon Ruby Version",
        "Pokémon Sapphire Version",
        "Pokémon Emerald Version",
        "Pokémon FireRed Version",
        "Pokémon LeafGreen Version",
    ],
    "Generation IV": [
        "Pokémon Diamond Version",
        "Pokémon Pearl Version",
    ],
}

# Spin-off games (linked directly to Pokemon franchise)
SPINOFF_GAMES = [
    "Pokémon Stadium",
    "Pokémon Stadium 2",
    "Pokémon Snap",
    "Pokémon Pinball",
    "Pokémon Pinball: Ruby & Sapphire",
    "Pokémon Puzzle Challenge",
    "Pokémon Puzzle League",
    "Pokémon Trading Card Game",
    "Pokémon Channel",
    "Pokémon Box: Ruby & Sapphire",
    "Pokémon Colosseum",
    "Pokémon XD: Gale of Darkness",
    "Pokémon Trozei!",
    "Pokémon Mystery Dungeon: Blue Rescue Team",
    "Pokémon Mystery Dungeon: Red Rescue Team",
    "Pokémon Ranger",
    "Pokémon Dash",
]


def get_supabase_client() -> Client:
    """Get Supabase client from environment."""
    supabase_url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_key:
        print("Error: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    return create_client(supabase_url, supabase_key)


def find_or_create_generation(supabase: Client, generation_name: str) -> str:
    """Find or create a generation collection under Pokemon franchise."""
    # Search for existing generation collection
    result = supabase.table("relationships").select("to_id").eq(
        "from_id", POKEMON_FRANCHISE_ID
    ).eq("type", "contains").execute()

    if result.data:
        gen_ids = [rel["to_id"] for rel in result.data]
        entities_result = supabase.table("entities").select("id,name").in_(
            "id", gen_ids
        ).eq("name", generation_name).execute()

        if entities_result.data:
            print(f"  Found existing: {generation_name}")
            return entities_result.data[0]["id"]

    # Create new generation collection
    import uuid
    collection_id = str(uuid.uuid4())

    supabase.table("entities").insert({
        "id": collection_id,
        "name": generation_name,
        "type": "collection",
        "attributes": {}
    }).execute()

    # Link to Pokemon franchise
    supabase.table("relationships").insert({
        "from_id": POKEMON_FRANCHISE_ID,
        "to_id": collection_id,
        "type": "contains"
    }).execute()

    print(f"  Created: {generation_name}")
    return collection_id


def find_games_by_name(supabase: Client, game_name: str) -> list:
    """Find all video game entities with this name."""
    result = supabase.table("entities").select("id,name,attributes").eq(
        "name", game_name
    ).eq("type", "video_game").execute()

    return result.data


def delete_franchise_relationships(supabase: Client, entity_id: str):
    """Delete all 'contains' relationships for this entity (except platform ones)."""
    # Get all current relationships
    result = supabase.table("relationships").select("id,from_id").eq(
        "to_id", entity_id
    ).eq("type", "contains").execute()

    # Check which ones are platform collections vs generation/franchise collections
    for rel in result.data:
        from_id = rel["from_id"]

        # Check if this is a platform collection
        entity_result = supabase.table("entities").select("attributes").eq("id", from_id).execute()

        if entity_result.data:
            attributes = entity_result.data[0].get("attributes", {})
            is_platform = attributes.get("platform", False)

            # Only delete non-platform relationships (generation/franchise links)
            if not is_platform:
                supabase.table("relationships").delete().eq("id", rel["id"]).execute()


def organize_rpg_games(supabase: Client):
    """Organize main RPG games by generation."""
    print("\n" + "=" * 60)
    print("Organizing Main RPG Games by Generation")
    print("=" * 60)

    # Create/find generation collections
    generations = {}
    print("\nCreating/finding generation collections...")
    for gen_name in MAIN_RPG_GAMES.keys():
        generations[gen_name] = find_or_create_generation(supabase, gen_name)

    # Link games to their generations
    print("\nLinking games to generations...")
    for gen_name, game_names in MAIN_RPG_GAMES.items():
        gen_id = generations[gen_name]
        print(f"\n{gen_name}:")

        for game_name in game_names:
            games = find_games_by_name(supabase, game_name)

            if not games:
                print(f"  ⚠️  Not found: {game_name}")
                continue

            for game in games:
                entity_id = game["id"]

                # Delete old franchise/generation relationships (keep platform)
                delete_franchise_relationships(supabase, entity_id)

                # Create new relationship to generation
                try:
                    supabase.table("relationships").insert({
                        "from_id": gen_id,
                        "to_id": entity_id,
                        "type": "contains"
                    }).execute()
                    print(f"  ✓ Linked: {game_name}")
                except Exception as e:
                    if '409' in str(e) or 'unique' in str(e).lower():
                        print(f"  ✓ Already linked: {game_name}")
                    else:
                        print(f"  ✗ Error: {game_name} - {e}")


def organize_spinoff_games(supabase: Client):
    """Link spin-off games directly to Pokemon franchise."""
    print("\n" + "=" * 60)
    print("Organizing Spin-off Games")
    print("=" * 60)

    for game_name in SPINOFF_GAMES:
        games = find_games_by_name(supabase, game_name)

        if not games:
            print(f"  ⚠️  Not found: {game_name}")
            continue

        for game in games:
            entity_id = game["id"]

            # Delete old franchise/generation relationships (keep platform)
            delete_franchise_relationships(supabase, entity_id)

            # Create new relationship to Pokemon franchise
            try:
                supabase.table("relationships").insert({
                    "from_id": POKEMON_FRANCHISE_ID,
                    "to_id": entity_id,
                    "type": "contains"
                }).execute()
                print(f"  ✓ Linked: {game_name}")
            except Exception as e:
                if '409' in str(e) or 'unique' in str(e).lower():
                    print(f"  ✓ Already linked: {game_name}")
                else:
                    print(f"  ✗ Error: {game_name} - {e}")


def verify_organization(supabase: Client):
    """Verify the organization by showing the hierarchy."""
    print("\n" + "=" * 60)
    print("Verification: Pokemon Game Hierarchy")
    print("=" * 60)

    # Get all children of Pokemon franchise
    result = supabase.table("relationships").select("to_id").eq(
        "from_id", POKEMON_FRANCHISE_ID
    ).eq("type", "contains").execute()

    if not result.data:
        print("\n⚠️  No games linked to Pokemon franchise!")
        return

    child_ids = [rel["to_id"] for rel in result.data]

    # Get details
    entities_result = supabase.table("entities").select("id,name,type").in_(
        "id", child_ids
    ).execute()

    collections = [e for e in entities_result.data if e["type"] == "collection"]
    games = [e for e in entities_result.data if e["type"] == "video_game"]

    print(f"\nDirect children of Pokemon franchise:")
    print(f"  Collections: {len(collections)}")
    print(f"  Games (spin-offs): {len(games)}")

    # Show generation collections and their games
    for collection in sorted(collections, key=lambda x: x["name"]):
        gen_result = supabase.table("relationships").select("to_id").eq(
            "from_id", collection["id"]
        ).eq("type", "contains").execute()

        gen_game_ids = [rel["to_id"] for rel in gen_result.data]
        gen_games_result = supabase.table("entities").select("name").in_(
            "id", gen_game_ids
        ).execute()

        print(f"\n  {collection['name']}: {len(gen_games_result.data)} games")
        for game in sorted(gen_games_result.data, key=lambda x: x["name"]):
            print(f"    - {game['name']}")

    # Show spin-off games
    if games:
        print(f"\n  Spin-off Games: {len(games)}")
        for game in sorted(games, key=lambda x: x["name"]):
            print(f"    - {game['name']}")


def main():
    print("=" * 60)
    print("Pokemon Game Organization Script")
    print("=" * 60)

    supabase = get_supabase_client()

    # Organize RPG games by generation
    organize_rpg_games(supabase)

    # Organize spin-off games
    organize_spinoff_games(supabase)

    # Verify
    verify_organization(supabase)

    print("\n" + "=" * 60)
    print("✓ Organization Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
