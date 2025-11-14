#!/usr/bin/env python3
"""
Update generation collection names and years:
- Prefix names with "Pokémon"
- Set year based on earliest game in that generation
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


POKEMON_FRANCHISE_ID = "044eef5c-491c-43f2-84ae-0900a6938305"


def get_supabase_client() -> Client:
    """Get Supabase client from environment."""
    supabase_url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_key:
        print("Error: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    return create_client(supabase_url, supabase_key)


def get_generation_collections(supabase: Client) -> list:
    """Get all generation collections under Pokemon franchise."""
    # Get all children of Pokemon franchise
    result = supabase.table("relationships").select("to_id").eq(
        "from_id", POKEMON_FRANCHISE_ID
    ).eq("type", "contains").execute()

    if not result.data:
        return []

    child_ids = [rel["to_id"] for rel in result.data]

    # Get collection entities that match "Generation" pattern
    entities_result = supabase.table("entities").select("id,name,type,year").in_(
        "id", child_ids
    ).eq("type", "collection").execute()

    # Filter for generation collections
    generations = [e for e in entities_result.data if "Generation" in e["name"]]

    return generations


def get_earliest_game_year(supabase: Client, generation_id: str) -> int:
    """Get the earliest year from games in this generation."""
    # Get all games in this generation
    result = supabase.table("relationships").select("to_id").eq(
        "from_id", generation_id
    ).eq("type", "contains").execute()

    if not result.data:
        return None

    game_ids = [rel["to_id"] for rel in result.data]

    # Get years from these games
    games_result = supabase.table("entities").select("year").in_(
        "id", game_ids
    ).execute()

    # Find earliest year
    years = [g["year"] for g in games_result.data if g["year"] is not None]

    if not years:
        return None

    return min(years)


def update_generation_collection(supabase: Client, collection_id: str, old_name: str, new_name: str, year: int):
    """Update a generation collection's name and year."""
    supabase.table("entities").update({
        "name": new_name,
        "year": year
    }).eq("id", collection_id).execute()


def main():
    print("=" * 60)
    print("Update Pokemon Generation Collections")
    print("=" * 60)

    supabase = get_supabase_client()

    # Get generation collections
    print("\nFinding generation collections...")
    generations = get_generation_collections(supabase)

    if not generations:
        print("No generation collections found!")
        return

    print(f"Found {len(generations)} generation collections\n")

    # Update each generation
    for gen in sorted(generations, key=lambda x: x["name"]):
        old_name = gen["name"]

        # Get earliest year from games in this generation
        earliest_year = get_earliest_game_year(supabase, gen["id"])

        if earliest_year is None:
            print(f"⚠️  {old_name}: No games with year data, skipping")
            continue

        # Create new name with "Pokémon" prefix
        if old_name.startswith("Pokémon"):
            new_name = old_name
        else:
            new_name = f"Pokémon {old_name}"

        # Update the collection
        update_generation_collection(supabase, gen["id"], old_name, new_name, earliest_year)

        print(f"✓ Updated: '{old_name}' → '{new_name}' (year: {earliest_year})")

    print("\n" + "=" * 60)
    print("✓ Update Complete!")
    print("=" * 60)

    # Verify the changes
    print("\nVerification:")
    updated_gens = get_generation_collections(supabase)
    for gen in sorted(updated_gens, key=lambda x: x.get("year") or 9999):
        year_str = gen.get("year") or "N/A"
        print(f"  - {gen['name']} ({year_str})")


if __name__ == "__main__":
    main()
