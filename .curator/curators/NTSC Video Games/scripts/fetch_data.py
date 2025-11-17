#!/usr/bin/env python3
"""Fetch NTSC video game data from MobyGames API (v2 format).

Rate limits: ~1 request per 1.5 seconds (360/hour free tier)
Strategy: Small batch imports to respect limits
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# Auto-install dependencies if missing
try:
    import requests
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "requests"
    ])
    import requests


class MobyGamesFetcher:
    """Fetch game data from MobyGames API with rate limiting."""

    BASE_URL = "https://api.mobygames.com/v1"
    RATE_LIMIT_DELAY = 1.5  # Seconds between requests (conservative)

    # Common NTSC platforms (MobyGames platform IDs)
    NTSC_PLATFORMS = {
        15: "3DO",
        1: "DOS",
        3: "Amiga",
        18: "NES",
        10: "Game Boy",
        12: "SNES",
        16: "Genesis",
        11: "Game Boy Color",
        14: "Game Boy Advance",
        9: "Nintendo 64",
        7: "PlayStation",
        13: "Xbox",
        8: "Dreamcast",
        20: "GameCube",
        21: "PlayStation 2",
        46: "PSP",
        44: "Nintendo DS",
        82: "Wii",
        69: "Xbox 360",
        81: "PlayStation 3",
        101: "Nintendo 3DS",
        142: "Xbox One",
        141: "PlayStation 4",
        203: "Nintendo Switch",
        144: "Xbox Series",
        145: "PlayStation 5"
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.request_count = 0
        self.platform_cache = {}  # Cache platform parents

    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make API request with rate limiting."""
        if params is None:
            params = {}

        params["api_key"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"

        # Rate limiting
        if self.request_count > 0:
            time.sleep(self.RATE_LIMIT_DELAY)

        print(f"  API Request: {endpoint}")
        response = self.session.get(url, params=params)
        response.raise_for_status()

        self.request_count += 1
        return response.json()

    def fetch_platform_games(
        self,
        platform_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[Dict, List[Dict]]:
        """
        Fetch games for a specific platform.

        Returns:
            Tuple of (platform_entity, game_entities)
        """
        platform_name = self.NTSC_PLATFORMS.get(platform_id, f"Platform {platform_id}")

        print(f"\nFetching games for {platform_name} (ID: {platform_id})...")
        print(f"Limit: {limit}, Offset: {offset}")
        print("-" * 60)

        # Create platform parent entity (cached)
        if platform_id not in self.platform_cache:
            platform_entity = {
                "name": platform_name,
                "type": "collection",
                "source_url": f"https://www.mobygames.com/platform/{platform_id}",
                "external_ids": {
                    "mobygames_platform_id": str(platform_id)
                },
                "attributes": {
                    "region": "North America"
                }
            }
            self.platform_cache[platform_id] = platform_entity
        else:
            platform_entity = self.platform_cache[platform_id]

        # Fetch games for this platform
        params = {
            "limit": min(limit, 100),  # API max is 100
            "offset": offset,
            "platform": platform_id,
            "format": "normal"
        }

        try:
            data = self._make_request("/games", params)
        except requests.exceptions.HTTPError as e:
            print(f"Error fetching games: {e}")
            if e.response.status_code == 429:
                print("Rate limit exceeded. Wait 1 hour and try again.")
            return (platform_entity, [])

        games = data.get("games", [])
        print(f"Found {len(games)} games in response")

        # Process each game
        game_entities = []
        for i, game in enumerate(games, 1):
            print(f"  [{i}/{len(games)}] Processing: {game.get('title', 'Unknown')}")

            try:
                game_entity = self._create_game_entity(game, platform_id, platform_name)
                if game_entity:
                    game_entities.append(game_entity)
            except Exception as e:
                print(f"    ⚠️  Error processing game: {e}")
                continue

        print(f"\n✓ Successfully processed {len(game_entities)} games")
        print(f"  Total API requests: {self.request_count}")

        return (platform_entity, game_entities)

    def _create_game_entity(
        self,
        game: dict,
        platform_id: int,
        platform_name: str
    ) -> Optional[Dict]:
        """Create game entity with North American release info."""
        game_id = game["game_id"]
        title = game["title"]

        # Get detailed game info
        try:
            details = self._make_request(f"/games/{game_id}")
        except Exception as e:
            print(f"    ⚠️  Failed to fetch details: {e}")
            return None

        # Get platform-specific release info
        try:
            release_data = self._make_request(
                f"/games/{game_id}/platforms/{platform_id}"
            )
        except Exception as e:
            print(f"    ⚠️  Failed to fetch release info: {e}")
            return None

        # Check for North American release
        releases = release_data.get("releases", [])
        na_release = None

        for release in releases:
            countries = release.get("countries", [])
            na_countries = {"United States", "Canada", "Worldwide"}
            if any(c in na_countries for c in countries):
                na_release = release
                break

        if not na_release:
            print(f"    ⊘ No North American release")
            return None

        # Extract cover art
        cover_url = None
        covers = details.get("sample_cover", {})
        if covers:
            cover_url = covers.get("image")

        # Extract year
        year = na_release.get("release_date", "")[:4] if na_release.get("release_date") else None
        if year:
            try:
                year = int(year)
            except ValueError:
                year = None

        # Extract publisher and developer
        publisher = None
        developer = None

        if "companies" in na_release:
            for company in na_release["companies"]:
                role = company.get("role", "")
                company_name = company.get("company_name")

                if "Published by" in role and not publisher:
                    publisher = company_name
                elif "Developed by" in role and not developer:
                    developer = company_name

        # Create game entity
        game_entity = {
            "name": title,
            "type": "video_game",
            "year": year,
            "country": "US",
            "language": "en",
            "source_url": f"https://www.mobygames.com/game/{game_id}",
            "external_ids": {
                "mobygames_game_id": str(game_id),
                "mobygames_game_platform_id": f"{game_id}-{platform_id}"
            },
            "parent": {
                "type": "collection",
                "external_ids": {
                    "mobygames_platform_id": str(platform_id)
                }
            },
            "relationship": {
                "type": "contains"
            },
            "attributes": {}
        }

        # Add optional fields
        if cover_url:
            game_entity["image_url"] = cover_url
        if publisher:
            game_entity["attributes"]["publisher"] = publisher
        if developer:
            game_entity["attributes"]["developer"] = developer

        print(f"    ✓ {title} ({year or 'Unknown year'})")
        return game_entity


def main():
    """Fetch games from MobyGames API (v2 format)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch NTSC video games from MobyGames (v2 format)"
    )
    parser.add_argument(
        "--platform",
        help="Platform name or ID (e.g., 'PlayStation 2' or '21')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of games to fetch (default: 10)"
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Pagination offset (default: 0)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("NTSC Video Games - MobyGames Fetcher (v2)")
    print("=" * 60)
    print()

    # Load API key from secrets.env
    secrets_file = Path(__file__).parent.parent / "secrets.env"
    if secrets_file.exists():
        print("Loading secrets from secrets.env...")
        with open(secrets_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    api_key = os.getenv("MOBY_GAMES_API_KEY")
    if not api_key:
        print("Error: MOBY_GAMES_API_KEY not set")
        print("Set in secrets.env file")
        sys.exit(1)

    # Parse platform argument
    fetcher = MobyGamesFetcher(api_key)

    platform_id = None
    if args.platform:
        # Try as ID first
        try:
            platform_id = int(args.platform)
        except ValueError:
            # Try matching by name
            for pid, pname in fetcher.NTSC_PLATFORMS.items():
                if pname.lower() == args.platform.lower():
                    platform_id = pid
                    break

            if platform_id is None:
                print(f"Error: Unknown platform '{args.platform}'")
                print("\nAvailable platforms:")
                for pid, pname in sorted(fetcher.NTSC_PLATFORMS.items(), key=lambda x: x[1]):
                    print(f"  {pid}: {pname}")
                sys.exit(1)
    else:
        print("Error: --platform is required")
        print("\nAvailable platforms:")
        for pid, pname in sorted(fetcher.NTSC_PLATFORMS.items(), key=lambda x: x[1]):
            print(f"  {pid}: {pname}")
        print("\nExamples:")
        print("  python3 scripts/fetch_data.py --platform 'PlayStation 2' --limit 10")
        print("  python3 scripts/fetch_data.py --platform 21 --limit 10")
        print("  python3 scripts/fetch_data.py --platform 'Nintendo Switch'")
        sys.exit(1)

    # Fetch games
    platform_entity, game_entities = fetcher.fetch_platform_games(
        platform_id=platform_id,
        limit=args.limit,
        offset=args.offset
    )

    # Build v2 output format
    all_items = [platform_entity] + game_entities

    output = {
        "format_version": "1.0",
        "metadata": {
            "source": "MobyGames",
            "source_url": "https://www.mobygames.com",
            "fetched_at": datetime.now().isoformat() + "Z",
            "total_items": len(all_items),
            "curator_version": "2.0"
        },
        "items": all_items
    }

    # Save to fetched_data.json
    output_file = Path(__file__).parent.parent / "fetched_data.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Saved 1 platform + {len(game_entities)} games to fetched_data.json")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  /curator:run \"NTSC Video Games\"  # Import via MCP tools")
    print()
    print("To fetch specific platforms:")
    print("  python3 scripts/fetch_data.py --platform 'PlayStation 2' --limit 5")
    print("  python3 scripts/fetch_data.py --platform 203 --limit 5  # Nintendo Switch")


if __name__ == "__main__":
    main()
