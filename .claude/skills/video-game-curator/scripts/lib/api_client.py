#!/usr/bin/env python3
"""
MobyGames API Client

Wrapper for MobyGames API (https://www.mobygames.com/info/api/)
"""

import os
import time
from typing import Optional, Dict, List
import requests
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../../.env'))


class MobyGamesClient:
    """Client for MobyGames API"""

    BASE_URL = "https://api.mobygames.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize MobyGames API client

        Args:
            api_key: MobyGames API key (optional, will use MOBY_GAMES_API_KEY env var if not provided)
        """
        self.api_key = api_key or os.getenv("MOBY_GAMES_API_KEY")
        if not self.api_key:
            raise ValueError("MobyGames API key is required. Set MOBY_GAMES_API_KEY environment variable or pass api_key parameter.")

        self.session = requests.Session()
        self.last_request_time = 0
        # 720 requests/hour = 5 seconds per request, use 5.5 for safety
        self.min_request_interval = 5.5

    def _rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make API request with rate limiting and error handling

        Args:
            endpoint: API endpoint (e.g., "/games")
            params: Query parameters

        Returns:
            API response as dict
        """
        self._rate_limit()

        if params is None:
            params = {}

        # Add API key to all requests
        params["api_key"] = self.api_key

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {}
            if e.response.status_code == 429:
                raise Exception("Rate limit exceeded. MobyGames requires 1 second between requests.")
            raise Exception(f"HTTP error: {e.response.status_code} - {e.response.text}")

        except requests.exceptions.Timeout:
            raise Exception("Request timed out")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    def search_games(self, query: str, limit: int = 20, platform: Optional[int] = None) -> Dict:
        """
        Search for games by title

        Args:
            query: Game title to search for (case-sensitive, supports partial matches)
            limit: Number of results (default: 20, max: 100)
            platform: Platform ID to filter by (optional)

        Returns:
            API response with games list in format:
            {
                "games": [
                    {
                        "game_id": int,
                        "title": str,
                        "platforms": [{"platform_id": int, "platform_name": str}, ...]
                    }
                ]
            }
        """
        params = {
            "title": query,
            "limit": min(limit, 100),
        }

        if platform:
            params["platform"] = platform

        return self._request("/games", params)

    def get_game(self, game_id: int) -> Dict:
        """
        Get detailed game information

        Args:
            game_id: MobyGames game ID

        Returns:
            Game data with fields:
            {
                "game_id": int,
                "title": str,
                "description": str,
                "genres": [{"genre_id": int, "genre_name": str}, ...],
                "alternate_titles": [{"title": str, "description": str}, ...]
            }
        """
        return self._request(f"/games/{game_id}")

    def get_game_platforms(self, game_id: int) -> Dict:
        """
        Get platforms for a specific game

        Args:
            game_id: MobyGames game ID

        Returns:
            Platforms data:
            {
                "platforms": [
                    {
                        "platform_id": int,
                        "platform_name": str,
                        "first_release_date": str (YYYY-MM-DD)
                    }
                ]
            }
        """
        return self._request(f"/games/{game_id}/platforms")

    def get_game_platform_details(self, game_id: int, platform_id: int) -> Dict:
        """
        Get detailed release information for a game on a specific platform

        Args:
            game_id: MobyGames game ID
            platform_id: Platform ID

        Returns:
            Platform release details:
            {
                "game_id": int,
                "platform_id": int,
                "platform_name": str,
                "first_release_date": str,
                "releases": [
                    {
                        "release_date": str,
                        "country_code": str (may be null),
                        "product_code": str (may be null),
                        "companies": [
                            {
                                "company_id": int,
                                "company_name": str,
                                "role": str (e.g., "Published by", "Developed by")
                            }
                        ]
                    }
                ],
                "attributes": [...],
                "ratings": [...]
            }
        """
        return self._request(f"/games/{game_id}/platforms/{platform_id}")

    def get_platforms(self) -> Dict:
        """
        Get list of all gaming platforms

        Returns:
            {
                "platforms": [
                    {
                        "platform_id": int,
                        "platform_name": str
                    }
                ]
            }
        """
        return self._request("/platforms")

    def get_game_covers(self, game_id: int, platform_id: int) -> Dict:
        """
        Get cover art for a game on a specific platform

        Args:
            game_id: MobyGames game ID
            platform_id: Platform ID

        Returns:
            Cover art data:
            {
                "cover_groups": [
                    {
                        "countries": ["United States"],
                        "covers": [
                            {
                                "scan_of": str (e.g., "Front Cover", "Back Cover"),
                                "image": str (full resolution URL),
                                "thumbnail_image": str (thumbnail URL),
                                "width": int,
                                "height": int
                            }
                        ]
                    }
                ]
            }
        """
        return self._request(f"/games/{game_id}/platforms/{platform_id}/covers")

    def get_front_cover_url(self, game_id: int, platform_id: int, country: str = "United States") -> Optional[str]:
        """
        Get front cover art URL for a game

        Args:
            game_id: MobyGames game ID
            platform_id: Platform ID
            country: Country to get cover for (default: "United States")

        Returns:
            Front cover image URL, or None if not found
        """
        covers_data = self.get_game_covers(game_id, platform_id)

        # Find cover group for the specified country
        for group in covers_data.get("cover_groups", []):
            if country in group.get("countries", []):
                # Find front cover in this group
                for cover in group.get("covers", []):
                    if cover.get("scan_of") == "Front Cover":
                        return cover.get("image")

        # Fallback: try first cover group's front cover
        for group in covers_data.get("cover_groups", []):
            for cover in group.get("covers", []):
                if cover.get("scan_of") == "Front Cover":
                    return cover.get("image")

        return None


def main():
    """Test the API client"""
    try:
        client = MobyGamesClient()

        print("Testing MobyGames API Client\n")
        print("=" * 50)

        # Search for games
        print("\n1. Searching for 'Pokémon Sword'...")
        results = client.search_games("Pokémon Sword", limit=5)
        print(f"Found {len(results.get('games', []))} games")
        print("\nResults:")
        for game in results.get("games", [])[:5]:
            print(f"  - {game['title']} (ID: {game['game_id']})")
            if 'platforms' in game:
                platforms = [p['platform_name'] for p in game.get('platforms', [])]
                print(f"    Platforms: {', '.join(platforms[:3])}")

        # Get detailed game info
        if results.get("games"):
            game_id = results["games"][0]["game_id"]
            print(f"\n2. Getting details for game ID {game_id}...")
            game_details = client.get_game(game_id)
            print(f"Title: {game_details['title']}")

            # Get platforms
            print(f"\n3. Getting platforms for this game...")
            platforms_data = client.get_game_platforms(game_id)
            print(f"Available on {len(platforms_data.get('platforms', []))} platforms:")
            for p in platforms_data.get('platforms', [])[:3]:
                print(f"  - {p['platform_name']} (ID: {p['platform_id']}) - Released: {p.get('first_release_date', 'N/A')}")

        print("\n" + "=" * 50)
        print("✅ API client test successful!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
