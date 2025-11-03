#!/usr/bin/env python3
"""
Search MobyGames API

Search for games without modifying the database.
"""

import argparse
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import MobyGamesClient


def main():
    parser = argparse.ArgumentParser(description="Search for video games on MobyGames API")
    parser.add_argument("query", help="Game name to search for")
    parser.add_argument("--limit", type=int, default=20, help="Number of results (default: 20, max: 100)")
    parser.add_argument("--platform", type=int, help="Filter by platform ID (e.g., 203 for Nintendo Switch)")

    args = parser.parse_args()

    # Initialize API client
    try:
        client = MobyGamesClient()
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nPlease set MOBY_GAMES_API_KEY environment variable.")
        print("Get your API key at: https://www.mobygames.com/info/api/")
        sys.exit(1)

    print(f"🔍 Searching for '{args.query}'...")
    if args.platform:
        print(f"   Filtering by platform ID: {args.platform}")
    print()

    # Search for games
    try:
        results = client.search_games(
            args.query,
            limit=min(args.limit, 100),
            platform=args.platform
        )

        games = results.get("games", [])

        print(f"📦 Found {len(games)} games\n")

        if not games:
            print("No games found.")
            return

        # Display results
        for i, game in enumerate(games, 1):
            print(f"[{i}] {game['title']}")
            print(f"    ID: {game['game_id']}")

            # Platforms
            platforms = game.get("platforms", [])
            if platforms:
                platform_names = [p["platform_name"] for p in platforms[:5]]
                more_platforms = len(platforms) - 5
                platforms_str = ", ".join(platform_names)
                if more_platforms > 0:
                    platforms_str += f" (+{more_platforms} more)"
                print(f"    Platforms: {platforms_str}")

            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
