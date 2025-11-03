#!/usr/bin/env python3
"""
Import Main Series Pokemon Games

This script imports the main series Pokemon games from MobyGames API.
Respects rate limits with 1.5 second delays between imports.
"""

import sys
import time
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import MobyGamesClient, DatabaseClient

# Main series Pokemon games by generation
POKEMON_GAMES = [
    # Generation 1
    {"id": 5129, "name": "Pokémon Red Version", "gen": 1},
    {"id": 4397, "name": "Pokémon Blue Version", "gen": 1},
    {"id": 5053, "name": "Pokémon Yellow Version: Special Pikachu Edition", "gen": 1},

    # Generation 2
    {"id": 5515, "name": "Pokémon Gold Version", "gen": 2},
    {"id": 5426, "name": "Pokémon Silver Version", "gen": 2},
    {"id": 12055, "name": "Pokémon Crystal Version", "gen": 2},

    # Generation 3
    {"id": 8459, "name": "Pokémon Ruby Version", "gen": 3},
    {"id": 8460, "name": "Pokémon Sapphire Version", "gen": 3},
    {"id": 17653, "name": "Pokémon Emerald Version", "gen": 3},
    {"id": 15034, "name": "Pokémon FireRed Version", "gen": 3},
    {"id": 14757, "name": "Pokémon LeafGreen Version", "gen": 3},

    # Generation 4
    {"id": 27727, "name": "Pokémon Diamond Version", "gen": 4},
    {"id": 27755, "name": "Pokémon Pearl Version", "gen": 4},
    {"id": 41397, "name": "Pokémon Platinum Version", "gen": 4},
    {"id": 44513, "name": "Pokémon HeartGold Version", "gen": 4},
    {"id": 44546, "name": "Pokémon SoulSilver Version", "gen": 4},

    # Generation 5
    {"id": 50752, "name": "Pokémon Black Version", "gen": 5},
    {"id": 50753, "name": "Pokémon White Version", "gen": 5},
    {"id": 59629, "name": "Pokémon Black Version 2", "gen": 5},
    {"id": 58348, "name": "Pokémon White Version 2", "gen": 5},

    # Generation 6
    {"id": 62267, "name": "Pokémon X", "gen": 6},
    {"id": 62270, "name": "Pokémon Y", "gen": 6},
    {"id": 70942, "name": "Pokémon Omega Ruby", "gen": 6},
    {"id": 70943, "name": "Pokémon Alpha Sapphire", "gen": 6},

    # Generation 7
    {"id": 81798, "name": "Pokémon Sun", "gen": 7},
    {"id": 81793, "name": "Pokémon Moon", "gen": 7},
    {"id": 97263, "name": "Pokémon Ultra Sun", "gen": 7},
    {"id": 97268, "name": "Pokémon Ultra Moon", "gen": 7},

    # Generation 7.5 (Let's Go)
    {"id": 114379, "name": "Pokémon: Let's Go, Pikachu!", "gen": 7},
    {"id": 114380, "name": "Pokémon: Let's Go, Eevee!", "gen": 7},

    # Generation 8
    {"id": 137306, "name": "Pokémon Sword", "gen": 8},
    {"id": 137307, "name": "Pokémon Shield", "gen": 8},
    {"id": 178684, "name": "Pokémon Legends: Arceus", "gen": 8},

    # Generation 9
    {"id": 195388, "name": "Pokémon Scarlet", "gen": 9},
    {"id": 195389, "name": "Pokémon Violet", "gen": 9},
]


def sync_game(api_client, db_client, game_id, platform_id=None, franchise_id=None):
    """Import a single game (simplified version of sync_game.py)"""

    # Get game details
    game_data = api_client.get_game(game_id)
    game_name = game_data["title"]

    # Get platforms
    platforms_data = api_client.get_game_platforms(game_id)
    platforms = platforms_data.get("platforms", [])

    # Use specified platform or first platform
    selected_platform = None
    if platform_id:
        selected_platform = next((p for p in platforms if p["platform_id"] == platform_id), None)
    if not selected_platform and platforms:
        selected_platform = platforms[0]

    # Parse release year
    year = None
    platform_name = None
    if selected_platform:
        platform_name = selected_platform["platform_name"]
        release_date = selected_platform.get("first_release_date")
        if release_date:
            try:
                year = int(release_date.split("-")[0])
            except (ValueError, IndexError):
                year = None

    # Get detailed platform release info for publisher/developer
    developer = None
    publisher = None
    if selected_platform:
        try:
            platform_details = api_client.get_game_platform_details(game_id, selected_platform["platform_id"])
            releases = platform_details.get("releases", [])

            # Prefer NA release
            na_release = next((r for r in releases if any(
                c.get("company_name", "").startswith("Nintendo of America")
                for c in r.get("companies", [])
            )), None)

            release = na_release or (releases[0] if releases else None)

            if release:
                companies = release.get("companies", [])
                dev_company = next((c for c in companies if "Developed by" in c.get("role", "")), None)
                if dev_company:
                    developer = dev_company["company_name"]

                pub_company = next((c for c in companies if "Published by" in c.get("role", "")), None)
                if pub_company:
                    publisher = pub_company["company_name"]
        except Exception as e:
            print(f"    Warning: Could not get platform details: {e}")

    # Build attributes
    attributes = {
        "region": "na",
        "language": "en",
    }

    if platform_name:
        attributes["platform"] = platform_name
    if developer:
        attributes["developer"] = developer
    if publisher:
        attributes["publisher"] = publisher

    # Upsert entity
    entity_id, created = db_client.upsert_entity(
        external_system="mobygames",
        external_id=str(game_id),
        entity_type="video_game",
        name=game_name,
        year=year,
        image_key=None,
        attributes=attributes
    )

    # Link to franchise if provided
    if franchise_id:
        db_client.create_relationship(
            from_id=franchise_id,
            to_id=entity_id,
            rel_type="contains"
        )

    return created, entity_id


def main():
    print("=" * 70)
    print("POKÉMON GAMES BATCH IMPORT")
    print("=" * 70)
    print(f"\nImporting {len(POKEMON_GAMES)} main series Pokémon games")
    print("This will take approximately {:.1f} minutes due to rate limiting\n".format(
        len(POKEMON_GAMES) * 3 * 1.5 / 60  # 3 API calls per game, 1.5s between calls
    ))

    # Initialize clients
    try:
        api_client = MobyGamesClient()
        db_client = DatabaseClient()
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nPlease set MOBY_GAMES_API_KEY environment variable.")
        sys.exit(1)

    # Use Pokemon franchise ID (hardcoded for now due to db client bug)
    franchise_id = "e3a12e69-74d6-4f26-983e-220ca0eb3dac"
    print(f"✅ Using Pokémon franchise: {franchise_id}\n")

    # Import games
    created_count = 0
    updated_count = 0
    failed_count = 0

    for i, game in enumerate(POKEMON_GAMES, 1):
        game_id = game["id"]
        game_name = game["name"]
        gen = game["gen"]

        print(f"[{i}/{len(POKEMON_GAMES)}] Generation {gen}: {game_name} (ID: {game_id})")

        try:
            created, entity_id = sync_game(
                api_client,
                db_client,
                game_id,
                franchise_id=franchise_id
            )

            if created:
                print(f"    ✅ Created")
                created_count += 1
            else:
                print(f"    ♻️  Updated")
                updated_count += 1

        except Exception as e:
            print(f"    ❌ Error: {e}")
            failed_count += 1
            continue

        # Rate limiting - wait 2 seconds between games to be safe
        if i < len(POKEMON_GAMES):
            print()
            time.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"✅ Created: {created_count}")
    print(f"♻️  Updated: {updated_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📊 Total: {len(POKEMON_GAMES)}")


if __name__ == "__main__":
    main()
