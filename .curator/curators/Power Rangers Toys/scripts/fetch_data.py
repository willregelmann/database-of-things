#!/usr/bin/env python3
"""Fetch Power Rangers toy data from grnrngr.com (v2 format)."""

import json
import re
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Auto-install dependencies if missing
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "requests", "beautifulsoup4", "lxml"
    ])
    import requests
    from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.grnrngr.com"
RATE_LIMIT = 1  # seconds between requests
USER_AGENT = "Power Rangers Collector Database Bot (Educational/Personal Project)"

# Available seasons (for --season argument)
AVAILABLE_SEASONS = {
    "mighty-morphin": "Mighty Morphin Power Rangers",
    "zeo": "Power Rangers Zeo",
    "turbo": "Power Rangers Turbo",
    "in-space": "Power Rangers in Space",
    "lost-galaxy": "Power Rangers Lost Galaxy",
    "lightspeed-rescue": "Power Rangers Lightspeed Rescue",
    "time-force": "Power Rangers Time Force",
    "wild-force": "Power Rangers Wild Force",
    "ninja-storm": "Power Rangers Ninja Storm",
    "dino-thunder": "Power Rangers Dino Thunder",
    "spd": "Power Rangers SPD",
    "mystic-force": "Power Rangers Mystic Force",
    "operation-overdrive": "Power Rangers Operation Overdrive",
    "jungle-fury": "Power Rangers Jungle Fury",
    "rpm": "Power Rangers RPM",
    "samurai": "Power Rangers Samurai",
    "megaforce": "Power Rangers Megaforce",
    "dino-charge": "Power Rangers Dino Charge",
    "ninja-steel": "Power Rangers Ninja Steel",
    "beast-morphers": "Power Rangers Beast Morphers",
    "dino-fury": "Power Rangers Dino Fury",
    "cosmic-fury": "Power Rangers Cosmic Fury"
}


class PowerRangersScraper:
    """Scrape toy data from grnrngr.com."""

    def __init__(self, limit: Optional[int] = None):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.season_cache = {}
        self.limit = limit
        self.total_toys_fetched = 0

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page."""
        try:
            full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
            print(f"  Fetching: {full_url}")

            response = self.session.get(full_url, timeout=10)
            response.raise_for_status()

            time.sleep(RATE_LIMIT)
            return BeautifulSoup(response.text, "lxml")

        except Exception as e:
            print(f"  ⚠️  Error fetching {url}: {e}")
            return None

    def extract_year(self, text: str) -> Optional[int]:
        """Extract year from text like '[Fall 1993]' or '[1994]'."""
        if not text:
            return None

        match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        if match:
            return int(match.group(1))
        return None

    def extract_price(self, text: str) -> Optional[str]:
        """Extract price from text like 'SRP: $14.99'."""
        if not text:
            return None

        match = re.search(r'\$[\d,.]+', text)
        if match:
            return match.group(0)
        return None

    def fetch_season(
        self,
        season_slug: str,
        season_name: str
    ) -> Tuple[Dict, List[Dict]]:
        """
        Fetch toys for a specific season.

        Returns:
            Tuple of (season_entity, toy_entities)
        """
        season_url = f"/toys/power-rangers/{season_slug}"

        print(f"\nFetching {season_name}...")
        print(f"  URL: {BASE_URL}{season_url}")
        print("-" * 60)

        soup = self.fetch_page(season_url)
        if not soup:
            return (None, [])

        # Create season parent entity
        season_entity = {
            "name": season_name,
            "type": "collection",
            "source_url": f"{BASE_URL}{season_url}",
            "external_ids": {
                "grnrngr_season_slug": season_slug
            },
            "attributes": {}
        }

        # Extract toys from all assortments on the page
        toy_entities = []

        # Find all h2 headers (assortments) and their associated toys
        for h2 in soup.find_all("h2"):
            # Find the next ul after this h2
            ul = h2.find_next("ul")
            if not ul:
                continue

            # Parse each toy in this assortment
            for li in ul.find_all("li", recursive=False):
                # Check limit
                if self.limit and self.total_toys_fetched >= self.limit:
                    break

                li_text = li.get_text(separator='\n', strip=True)

                # Extract item number
                number_match = re.match(r'^(\d+)', li_text)
                if not number_match:
                    continue

                item_number = number_match.group(1)

                # Parse toy
                toy_entity = self._parse_toy(
                    item_number,
                    li_text,
                    li,
                    season_slug,
                    season_name,
                    season_url
                )

                if toy_entity:
                    toy_entities.append(toy_entity)
                    self.total_toys_fetched += 1
                    print(f"  ✓ {toy_entity['name']} (#{item_number})")

                    # Check limit after adding
                    if self.limit and self.total_toys_fetched >= self.limit:
                        break

            # Break outer loop if limit reached
            if self.limit and self.total_toys_fetched >= self.limit:
                print(f"\n⚠️  Reached limit of {self.limit} toys")
                break

        print(f"\n✓ Found {len(toy_entities)} toys")
        return (season_entity, toy_entities)

    def _parse_toy(
        self,
        item_number: str,
        item_text: str,
        li_element,
        season_slug: str,
        season_name: str,
        season_url: str
    ) -> Optional[Dict]:
        """Parse a toy entry."""
        # Extract name - remove item number and metadata
        name = item_text
        name = re.sub(r'^' + re.escape(item_number) + r'\s*', '', name)
        name = re.sub(r'\(off-site link\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'View\s+(Photo|Barcode|Instructions)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Browse\s+eBay', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Instructions\s+\(PDF\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Buy\s+Item', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\[(Fall|Spring|Summer|Winter)?\s*(19\d{2}|20\d{2})\]', '', name)
        name = re.sub(r'\[\?\]', '', name)
        name = ' '.join(name.split())
        name = name.strip()

        if not name or len(name) < 2:
            return None

        # Extract metadata
        year = self.extract_year(item_text)

        # Scrape actual image URL from "View Photo" link
        image_url = None
        photo_link = li_element.find('a', string=re.compile(r'View\s+Photo', re.IGNORECASE))
        if photo_link and photo_link.get('href'):
            href = photo_link['href']
            image_url = href if href.startswith('http') else f"{BASE_URL}{href}"

        # Fallback to pattern if no link found
        if not image_url:
            padded_number = item_number.zfill(5)
            image_url = f"{BASE_URL}/toys/pictures/bandai/{padded_number}.jpg"

        # Create toy entity
        toy_entity = {
            "name": name,
            "type": "action_figure",
            "year": year,
            "image_url": image_url,
            "source_url": f"{BASE_URL}{season_url}",
            "external_ids": {
                "grnrngr_item_number": item_number
            },
            "parent": {
                "type": "collection",
                "external_ids": {
                    "grnrngr_season_slug": season_slug
                }
            },
            "relationship": {
                "type": "contains"
            },
            "attributes": {
                "manufacturer": "Bandai America"
            }
        }

        return toy_entity


def main():
    """Fetch Power Rangers toys (v2 format)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch Power Rangers toys from grnrngr.com (v2 format)"
    )
    parser.add_argument(
        "--season",
        help="Season slug (e.g., 'mighty-morphin', 'zeo')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of seasons to fetch"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Power Rangers Toy Fetcher (v2)")
    print("=" * 60)
    print()

    scraper = PowerRangersScraper(limit=args.limit)

    # Determine which seasons to fetch
    if args.season:
        if args.season not in AVAILABLE_SEASONS:
            print(f"Error: Unknown season '{args.season}'")
            print("\nAvailable seasons:")
            for slug, name in sorted(AVAILABLE_SEASONS.items()):
                print(f"  {slug}: {name}")
            sys.exit(1)

        seasons_to_fetch = [(args.season, AVAILABLE_SEASONS[args.season])]
    else:
        print("Error: --season is required")
        print("\nAvailable seasons:")
        for slug, name in sorted(AVAILABLE_SEASONS.items()):
            print(f"  {slug}: {name}")
        print("\nExamples:")
        print("  python3 scripts/fetch_data.py --season mighty-morphin")
        print("  python3 scripts/fetch_data.py --season mighty-morphin --limit 10")
        sys.exit(1)

    print(f"Fetching season(s): {', '.join([name for _, name in seasons_to_fetch])}...")
    if args.limit:
        print(f"Limiting to {args.limit} total toys\n")
    else:
        print()

    # Fetch all seasons
    all_items = []
    total_toys = 0

    for season_slug, season_name in seasons_to_fetch:
        # Check if limit already reached
        if scraper.limit and scraper.total_toys_fetched >= scraper.limit:
            break

        season_entity, toy_entities = scraper.fetch_season(season_slug, season_name)

        if season_entity:
            all_items.append(season_entity)
            all_items.extend(toy_entities)
            total_toys += len(toy_entities)

    if not all_items:
        print("\n⚠️  No data fetched")
        sys.exit(1)

    # Build v2 output
    output = {
        "format_version": "1.0",
        "metadata": {
            "source": "GrnRngr.com",
            "source_url": "https://www.grnrngr.com/toys/power-rangers/",
            "fetched_at": datetime.now().isoformat() + "Z",
            "total_items": len(all_items),
            "curator_version": "2.0"
        },
        "items": all_items
    }

    # Save to file
    output_file = Path(__file__).parent.parent / "fetched_data.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Saved {len(seasons_to_fetch)} season(s) + {total_toys} toys to fetched_data.json")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  /curator:run \"Power Rangers Toys\"  # Import via MCP tools")
    print()
    print("Examples:")
    print("  python3 scripts/fetch_data.py --season mighty-morphin")
    print("  python3 scripts/fetch_data.py --season mighty-morphin --limit 10  # First 10 toys")
    print("  python3 scripts/fetch_data.py --season zeo")


if __name__ == "__main__":
    main()
