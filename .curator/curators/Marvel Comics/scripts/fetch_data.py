#!/usr/bin/env python3
"""
Fetch Marvel Comics data from the Marvel API.

Requires Marvel API keys from developer.marvel.com
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

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

# Marvel API configuration
API_BASE = "https://gateway.marvel.com/v1/public"
OUTPUT_FILE = "fetched_data.json"


class MarvelAPIFetcher:
    """Fetch comics data from Marvel API."""

    def __init__(self, public_key: str, private_key: str):
        self.public_key = public_key
        self.private_key = private_key
        self.session = requests.Session()

    def generate_auth_params(self) -> Dict[str, str]:
        """
        Generate Marvel API authentication parameters.

        Marvel requires: timestamp, public key, and MD5 hash of timestamp+private+public.
        """
        ts = str(int(time.time()))
        hash_input = f"{ts}{self.private_key}{self.public_key}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()

        return {
            "ts": ts,
            "apikey": self.public_key,
            "hash": hash_value
        }

    def fetch_comics(self, limit: Optional[int] = None, offset: int = 0, series_title: Optional[str] = None) -> List[Dict]:
        """
        Fetch comics from Marvel API.

        Args:
            limit: Maximum number of comics to fetch (None = all)
            offset: Starting offset for pagination
            series_title: Filter by series title (e.g., "Journey Into Mystery")

        Returns:
            List of comic dictionaries
        """
        comics = []
        page_size = 100  # Marvel API max per page

        while True:
            # Build request parameters
            params = self.generate_auth_params()
            params.update({
                "format": "comic",  # Exclude graphic novels, magazines
                "formatType": "comic",  # Individual issues only
                "noVariants": "true",  # Exclude variant covers
                "orderBy": "-onsaleDate",  # Newest first
                "limit": page_size,
                "offset": offset
            })

            # Add series title filter if provided
            if series_title:
                params["titleStartsWith"] = series_title

            print(f"  Fetching comics {offset}-{offset + page_size}...")

            try:
                response = self.session.get(
                    f"{API_BASE}/comics",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                if data["code"] != 200:
                    print(f"  ⚠️  API error: {data.get('status', 'Unknown error')}")
                    break

                results = data["data"]["results"]
                if not results:
                    break

                # Parse each comic
                for comic_data in results:
                    comic = self.parse_comic(comic_data)
                    if comic:
                        comics.append(comic)

                offset += len(results)

                # Check if we've reached the limit
                if limit and len(comics) >= limit:
                    comics = comics[:limit]
                    break

                # Check if there are more results
                total = data["data"]["total"]
                if offset >= total:
                    break

                # Rate limiting: small pause between requests
                time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                print(f"  ⚠️  Request failed: {e}")
                break

        return comics

    def parse_comic(self, comic_data: Dict) -> Optional[Dict]:
        """
        Parse comic data from Marvel API response.

        Extracts:
        - ID, title, issue number
        - Series name and year
        - Writers and artists
        - Cover image URL
        - Publication date
        """
        try:
            comic_id = comic_data["id"]
            title = comic_data.get("title", "")
            issue_number = comic_data.get("issueNumber", 0)

            # Extract series information
            series = comic_data.get("series", {})
            series_name = series.get("name", "Unknown Series")

            # Extract year from on-sale date
            dates = comic_data.get("dates", [])
            year = None
            for date in dates:
                if date["type"] == "onsaleDate":
                    date_str = date.get("date", "")
                    if date_str:
                        year = int(date_str[:4])
                    break

            # Extract creators (writers and artists)
            creators = comic_data.get("creators", {}).get("items", [])
            writers = [c["name"] for c in creators if c["role"].lower() in ["writer", "plotter"]]
            artists = [c["name"] for c in creators if c["role"].lower() in ["artist", "penciller", "penciler", "inker", "colorist"]]

            # Extract cover image
            thumbnail = comic_data.get("thumbnail", {})
            image_url = None
            if thumbnail.get("path") and thumbnail.get("extension"):
                # Marvel provides path and extension separately
                image_url = f"{thumbnail['path']}.{thumbnail['extension']}"

            # Build source URL
            urls = comic_data.get("urls", [])
            source_url = None
            for url in urls:
                if url["type"] == "detail":
                    source_url = url.get("url")
                    break

            return {
                "id": comic_id,
                "name": title,
                "series_name": series_name,
                "issue_number": issue_number,
                "year": year,
                "writers": writers,
                "artists": artists,
                "image_url": image_url,
                "source_url": source_url
            }

        except Exception as e:
            print(f"  ⚠️  Failed to parse comic: {e}")
            return None


def main():
    print("=" * 60)
    print("Marvel Comics API Fetcher")
    print("=" * 60)
    print()

    # Load API keys from environment
    public_key = os.getenv("MARVEL_PUBLIC_KEY")
    private_key = os.getenv("MARVEL_PRIVATE_KEY")

    if not public_key or not private_key:
        print("Error: MARVEL_PUBLIC_KEY and MARVEL_PRIVATE_KEY must be set")
        print("Get your keys from: https://developer.marvel.com")
        sys.exit(1)

    # Allow limiting for testing
    limit = os.getenv("FETCH_LIMIT")
    limit = int(limit) if limit else None

    # Allow series filtering
    series_title = os.getenv("SERIES_TITLE")

    fetcher = MarvelAPIFetcher(public_key, private_key)

    print(f"Fetching comics from Marvel API...")
    if series_title:
        print(f"  Series: {series_title}")
    if limit:
        print(f"  Limit: {limit} comics (for testing)")
    print()

    comics = fetcher.fetch_comics(limit=limit, series_title=series_title)

    # Save to file
    output_path = Path(__file__).parent.parent / OUTPUT_FILE
    with open(output_path, "w") as f:
        json.dump(comics, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Fetched {len(comics)} comics → {output_path}")
    print("=" * 60)

    # Data quality report
    if comics:
        with_images = sum(1 for c in comics if c.get("image_url"))
        with_years = sum(1 for c in comics if c.get("year"))
        with_writers = sum(1 for c in comics if c.get("writers"))

        print(f"\nData quality:")
        print(f"  Total comics: {len(comics)}")
        print(f"  With images: {with_images}/{len(comics)} ({with_images/len(comics)*100:.1f}%)")
        print(f"  With years: {with_years}/{len(comics)} ({with_years/len(comics)*100:.1f}%)")
        print(f"  With writers: {with_writers}/{len(comics)} ({with_writers/len(comics)*100:.1f}%)")


if __name__ == "__main__":
    main()
