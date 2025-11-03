#!/usr/bin/env python3
"""
Sync Game from RAWG API

Import a single game by ID or name into the database.
"""

import argparse
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import MobyGamesClient, DatabaseClient


def sync_game(
    api_client: MobyGamesClient,
    db_client: DatabaseClient,
    game_id: int,
    platform_id: int = None,
    franchise_id: str = None,
    dry_run: bool = False
) -> bool:
    """
    Sync a single game from MobyGames

    Args:
        api_client: MobyGames API client
        db_client: Database client
        game_id: MobyGames game ID
        platform_id: Platform ID to get release details (optional)
        franchise_id: UUID of franchise entity to link to (optional)
        dry_run: If True, don't make database changes

    Returns:
        True if created, False if updated/skipped
    """
    # Get game details
    game_data = api_client.get_game(game_id)
    game_name = game_data["title"]

    # Get platforms to find release date and platform name
    platforms_data = api_client.get_game_platforms(game_id)
    platforms = platforms_data.get("platforms", [])

    # If platform_id specified, use that one, otherwise use first platform
    selected_platform = None
    if platform_id:
        selected_platform = next((p for p in platforms if p["platform_id"] == platform_id), None)
    if not selected_platform and platforms:
        selected_platform = platforms[0]

    # Parse release year from first_release_date
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

    # Get detailed platform release info to get publisher/developer
    developer = None
    publisher = None
    if selected_platform:
        try:
            platform_details = api_client.get_game_platform_details(game_id, selected_platform["platform_id"])
            releases = platform_details.get("releases", [])

            # Look for NA release first, otherwise use first release
            na_release = next((r for r in releases if any(
                c.get("company_name", "").startswith("Nintendo of America")
                for c in r.get("companies", [])
            )), None)

            release = na_release or (releases[0] if releases else None)

            if release:
                companies = release.get("companies", [])
                # Find developer
                dev_company = next((c for c in companies if "Developed by" in c.get("role", "")), None)
                if dev_company:
                    developer = dev_company["company_name"]

                # Find publisher
                pub_company = next((c for c in companies if "Published by" in c.get("role", "")), None)
                if pub_company:
                    publisher = pub_company["company_name"]
        except Exception as e:
            print(f"    Warning: Could not get platform details: {e}")

    # Extract language to dedicated column
    language = "en"  # Default to English

    # Build simplified attributes (region stays here)
    attributes = {
        "region": "na",  # Default to North America
    }

    if platform_name:
        attributes["platform"] = platform_name
    if developer:
        attributes["developer"] = developer
    if publisher:
        attributes["publisher"] = publisher

    # Get cover art if platform selected
    image_url = None
    if selected_platform:
        try:
            image_url = api_client.get_front_cover_url(
                game_id,
                selected_platform["platform_id"],
                country="United States"
            )
        except Exception as e:
            print(f"    Warning: Could not get cover art: {e}")

    if dry_run:
        print(f"  [DRY RUN] Would create/update: {game_name}")
        print(f"    Year: {year}")
        print(f"    Language: {language}")
        if attributes.get("platform"):
            print(f"    Platform: {attributes['platform']}")
        if attributes.get("developer"):
            print(f"    Developer: {attributes['developer']}")
        if attributes.get("publisher"):
            print(f"    Publisher: {attributes['publisher']}")
        if image_url:
            print(f"    Cover Art: {image_url}")
        return False

    # Upsert entity
    entity_id, created = db_client.upsert_entity(
        external_system="mobygames",
        external_id=str(game_id),
        entity_type="video_game",
        name=game_name,
        year=year,
        language=language,
        image_url=image_url,
        attributes=attributes
    )

    # Link to franchise if provided
    if franchise_id:
        db_client.create_relationship(
            from_id=franchise_id,
            to_id=entity_id,
            rel_type="contains"
        )

    return created


def main():
    parser = argparse.ArgumentParser(description="Import a game from MobyGames API")
    parser.add_argument("game", help="MobyGames game ID (numeric) or game name to search")
    parser.add_argument("--platform", type=int, help="Platform ID to import (optional)")
    parser.add_argument("--franchise", help="Franchise name to link to (e.g., 'Pokémon')")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    args = parser.parse_args()

    # Initialize clients
    try:
        api_client = MobyGamesClient()
        db_client = DatabaseClient()
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nPlease set MOBY_GAMES_API_KEY environment variable.")
        sys.exit(1)

    # Determine if input is game ID or name
    game_id = None
    try:
        game_id = int(args.game)
        print(f"🔍 Using game ID {game_id}...")
    except ValueError:
        # It's a game name, search for it
        print(f"🔍 Searching for '{args.game}'...")
        results = api_client.search_games(args.game, limit=5)
        games = results.get("games", [])

        if not games:
            print(f"❌ No games found for '{args.game}'")
            sys.exit(1)

        # Show results and use first one
        if len(games) > 1:
            print(f"\nFound {len(games)} games:")
            for i, game in enumerate(games, 1):
                platforms = [p["platform_name"] for p in game.get("platforms", [])]
                print(f"  [{i}] {game['title']} (ID: {game['game_id']}) - {', '.join(platforms[:2])}")
            print(f"\nUsing first result: {games[0]['title']}")

        game_id = games[0]["game_id"]

    if not game_id:
        print("❌ Failed to get game ID")
        sys.exit(1)

    # Get game info for display
    print(f"\n🔍 Fetching game details...")
    game_data = api_client.get_game(game_id)
    print(f"\n📦 Game: {game_data['title']}")
    print(f"    ID: {game_id}")

    # Get platforms
    platforms_data = api_client.get_game_platforms(game_id)
    platforms = platforms_data.get("platforms", [])

    if platforms:
        print(f"\n🎮 Available platforms:")
        for p in platforms:
            marker = " ← Selected" if args.platform == p["platform_id"] else ""
            print(f"  - {p['platform_name']} (ID: {p['platform_id']}) - Released: {p.get('first_release_date', 'N/A')}{marker}")

        if not args.platform:
            print(f"\nUsing first platform: {platforms[0]['platform_name']}")

    # Find franchise if specified
    franchise_id = None
    if args.franchise:
        print(f"\n🔍 Finding franchise: {args.franchise}")
        franchise = db_client.find_entity_by_name_and_type(args.franchise, "franchise")

        if not franchise:
            print(f"❌ Franchise '{args.franchise}' not found")
            print("   Create it first using collectibles-manager skill")
            sys.exit(1)

        franchise_id = franchise["id"]
        print(f"✅ Found franchise: {franchise['name']}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Sync the game
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Importing game...")

    try:
        created = sync_game(
            api_client,
            db_client,
            game_id,
            platform_id=args.platform,
            franchise_id=franchise_id,
            dry_run=args.dry_run
        )

        if not args.dry_run:
            if created:
                print(f"✅ Created game: {game_data['title']}")
            else:
                print(f"♻️  Updated game: {game_data['title']}")

            if franchise_id:
                print(f"🔗 Linked to franchise")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 50)
    print("COMPLETE")


if __name__ == "__main__":
    main()
