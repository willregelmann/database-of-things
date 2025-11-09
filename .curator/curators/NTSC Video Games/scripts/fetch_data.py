#!/usr/bin/env python3
"""
Fetch NTSC video game data from MobyGames API.

Rate limits: ~1 request per 1.5 seconds (360/hour free tier)
Strategy: Small batch imports to respect limits
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, List, Dict

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

    def fetch_games(
        self,
        platform_id: Optional[int] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict]:
        """
        Fetch games from MobyGames.

        Args:
            platform_id: Specific platform ID (None = all platforms)
            limit: Max number of games to fetch
            offset: Pagination offset

        Returns:
            List of game data dictionaries
        """
        print(f"\nFetching up to {limit} games from MobyGames...")
        if platform_id:
            platform_name = self.NTSC_PLATFORMS.get(platform_id, f"Platform {platform_id}")
            print(f"Platform: {platform_name} (ID: {platform_id})")
        else:
            print("Platform: All NTSC platforms")
        print(f"Offset: {offset}")
        print("-" * 60)

        params = {
            "limit": min(limit, 100),  # API max is 100
            "offset": offset,
            "format": "normal"
        }

        if platform_id:
            params["platform"] = platform_id

        try:
            data = self._make_request("/games", params)
        except requests.exceptions.HTTPError as e:
            print(f"Error fetching games: {e}")
            if e.response.status_code == 429:
                print("Rate limit exceeded. Wait 1 hour and try again.")
            return []

        games = data.get("games", [])
        print(f"Found {len(games)} games in response")

        # Enrich with platform-specific details
        enriched_games = []
        for i, game in enumerate(games, 1):
            print(f"  [{i}/{len(games)}] Processing: {game.get('title', 'Unknown')}")

            try:
                enriched = self._enrich_game_data(game, platform_id)
                if enriched:
                    enriched_games.append(enriched)
            except Exception as e:
                print(f"    ⚠️  Error processing game: {e}")
                continue

        print(f"\n✓ Successfully processed {len(enriched_games)} games")
        print(f"  Total API requests: {self.request_count}")

        return enriched_games

    def _enrich_game_data(self, game: dict, target_platform_id: Optional[int]) -> Optional[Dict]:
        """
        Enrich game data with platform-specific details and North American release info.

        Returns None if game has no North American release.
        """
        game_id = game["game_id"]
        title = game["title"]

        # Get detailed game info
        try:
            details = self._make_request(f"/games/{game_id}")
        except Exception as e:
            print(f"    ⚠️  Failed to fetch details: {e}")
            return None

        # Find North American platforms
        platforms = details.get("platforms", [])

        # If target_platform_id specified, filter to that platform
        if target_platform_id:
            platforms = [p for p in platforms if p["platform_id"] == target_platform_id]

        if not platforms:
            print(f"    ⊘ No matching platforms")
            return None

        # Use first platform (or specified platform)
        platform = platforms[0]
        platform_id = platform["platform_id"]
        platform_name = platform["platform_name"]

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
            # Check if any North American country is in the list
            # US releases, Canadian releases, or Worldwide releases
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

        # Extract metadata
        year = na_release.get("release_date", "")[:4] if na_release.get("release_date") else None
        if year:
            try:
                year = int(year)
            except ValueError:
                year = None

        # Extract publisher and developer (from release companies with roles)
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

        # Build enriched game data
        enriched = {
            "id": f"{game_id}-{platform_id}",  # Compound ID
            "game_id": game_id,
            "name": title,  # Just the game title, platform stored in attributes
            "platform": platform_name,
            "year": year,
            "country": "US",
            "language": "en",
            "image_url": cover_url,
            "source_url": f"https://www.mobygames.com/game/{game_id}",
            "publisher": publisher,
            "developer": developer,
        }

        print(f"    ✓ {title} ({platform_name}, {year or 'Unknown year'})")
        return enriched


def main():
    """Fetch games from MobyGames API."""
    print("=" * 60)
    print("NTSC Video Games - MobyGames Fetcher")
    print("=" * 60)
    print()

    # Load API key from environment or secrets.env
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
        print("Set in environment or create secrets.env file")
        sys.exit(1)

    # Parse command-line arguments (simple approach)
    limit = int(os.getenv("FETCH_LIMIT", "10"))
    offset = int(os.getenv("FETCH_OFFSET", "0"))
    platform_id = os.getenv("PLATFORM_ID")  # Optional

    if platform_id:
        platform_id = int(platform_id)

    print(f"Configuration:")
    print(f"  Limit: {limit}")
    print(f"  Offset: {offset}")
    if platform_id:
        print(f"  Platform ID: {platform_id}")
    print()

    # Fetch games
    fetcher = MobyGamesFetcher(api_key)
    games = fetcher.fetch_games(
        platform_id=platform_id,
        limit=limit,
        offset=offset
    )

    # Save to fetched_data.json
    output_file = Path(__file__).parent.parent / "fetched_data.json"
    with open(output_file, "w") as f:
        json.dump(games, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Saved {len(games)} games to fetched_data.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
