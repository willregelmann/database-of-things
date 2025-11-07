#!/usr/bin/env python3
"""Fetch Power Rangers toy data from grnrngr.com."""

import json
import re
import time
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Auto-install dependencies if missing
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "requests", "beautifulsoup4", "lxml"])
    import requests
    from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.grnrngr.com"
OUTPUT_FILE = "fetched_data.json"
RATE_LIMIT = 1  # seconds between requests

# Season toylines to scrape
SEASON_TOYLINES = [
    "/toys/power-rangers/mighty-morphin",
    "/toys/power-rangers/zeo",
    "/toys/power-rangers/turbo",
    "/toys/power-rangers/in-space",
    "/toys/power-rangers/lost-galaxy",
    "/toys/power-rangers/lightspeed-rescue",
    "/toys/power-rangers/time-force",
    "/toys/power-rangers/wild-force",
    "/toys/power-rangers/ninja-storm",
    "/toys/power-rangers/dino-thunder",
    "/toys/power-rangers/spd",
    "/toys/power-rangers/mystic-force",
    "/toys/power-rangers/operation-overdrive",
    "/toys/power-rangers/jungle-fury",
    "/toys/power-rangers/rpm",
    "/toys/power-rangers/samurai",
    "/toys/power-rangers/megaforce",
    "/toys/power-rangers/dino-charge",
    "/toys/power-rangers/ninja-steel",
    "/toys/power-rangers/beast-morphers",
    "/toys/power-rangers/dino-fury",
    "/toys/power-rangers/cosmic-fury"
]

USER_AGENT = "Power Rangers Collector Database Bot (Educational/Personal Project)"


class GrnRngrScraper:
    """Scrape toy data from grnrngr.com."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page."""
        try:
            full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
            print(f"Fetching: {full_url}")

            response = self.session.get(full_url, timeout=10)
            response.raise_for_status()

            time.sleep(RATE_LIMIT)
            return BeautifulSoup(response.text, "lxml")

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_year_from_release(self, release_text: str) -> Optional[int]:
        """Extract year from release date like '[Fall 1993]' or '[1994]'."""
        if not release_text:
            return None

        # Look for 4-digit year
        match = re.search(r'\b(19\d{2}|20\d{2})\b', release_text)
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

    def parse_toy_entry(self, item_number: str, item_text: str, series_name: str) -> Optional[Dict]:
        """Parse a toy entry from grnrngr.com."""
        if not item_text or not item_number:
            return None

        # Extract name - remove item number prefix and link texts
        name = item_text
        # Remove item number
        name = re.sub(r'^' + re.escape(item_number) + r'\s*', '', name)
        # Remove link texts
        name = re.sub(r'\(off-site link\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'View\s+(Photo|Barcode|Instructions)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Browse\s+eBay', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Instructions\s+\(PDF\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Buy\s+Item', '', name, flags=re.IGNORECASE)
        # Remove release dates in brackets
        name = re.sub(r'\[(Fall|Spring|Summer|Winter)?\s*(19\d{2}|20\d{2})\]', '', name)
        # Remove question marks used for unknown info
        name = re.sub(r'\[\?\]', '', name)
        # Clean up whitespace and newlines
        name = ' '.join(name.split())
        name = name.strip()

        if not name or len(name) < 2:
            return None

        # Extract release date and year
        release_match = re.search(r'\[(Fall|Spring|Summer|Winter)?\s*(19\d{2}|20\d{2})\]', item_text)
        release_date = release_match.group(0) if release_match else None
        year = self.extract_year_from_release(item_text)

        # Extract price
        price = self.extract_price(item_text)

        # Build image URL (grnrngr.com uses item numbers in image paths)
        # Format: /toys/pictures/bandai/ITEMNUM_1.jpg
        # Pad item number to 5 digits
        padded_number = item_number.zfill(5)
        image_url = f"{BASE_URL}/toys/pictures/bandai/{padded_number}_1.jpg"

        return {
            "name": name,
            "item_number": item_number,
            "series": series_name,
            "year": year,
            "release_date": release_date,
            "price": price,
            "image_url": image_url,
            "source_url": f"{BASE_URL}{SEASON_TOYLINES[0]}"  # Will be updated per season
        }

    def scrape_season_page(self, season_url: str) -> List[Dict]:
        """Scrape all toys from a season page."""
        soup = self.fetch_page(season_url)
        if not soup:
            return []

        # Extract series name from page title or heading
        title_elem = soup.find("h1") or soup.find("title")
        series_name = title_elem.get_text(strip=True) if title_elem else "Unknown Series"

        # Clean up series name
        series_name = series_name.replace(" - GrnRngr.com", "").strip()

        print(f"  Series: {series_name}")

        toys = []

        # Find all list items (li elements) containing toy data
        for li in soup.find_all("li"):
            li_text = li.get_text(separator='\n', strip=True)

            # Extract item number from start of text (e.g., "2200" from "2200 Jason Red Ranger")
            number_match = re.match(r'^(\d+)', li_text)
            if not number_match:
                continue

            item_number = number_match.group(1)

            # Parse the toy entry
            toy_data = self.parse_toy_entry(item_number, li_text, series_name)

            if toy_data:
                toy_data["source_url"] = f"{BASE_URL}{season_url}"
                toys.append(toy_data)
                print(f"    ✓ {toy_data['name']} ({item_number})")

        return toys

    def fetch_all_toys(self) -> List[Dict]:
        """Fetch all Power Rangers toys from configured season toylines."""
        all_toys = []

        for season_url in SEASON_TOYLINES:
            print(f"\n{'='*60}")
            print(f"Scraping: {season_url}")
            print('='*60)

            toys = self.scrape_season_page(season_url)
            all_toys.extend(toys)

            print(f"  Found {len(toys)} toys")

        # Deduplicate by item number
        seen_numbers = set()
        unique_toys = []
        for toy in all_toys:
            item_num = toy.get("item_number")
            if item_num and item_num not in seen_numbers:
                seen_numbers.add(item_num)
                unique_toys.append(toy)

        return unique_toys


def main():
    print("=" * 60)
    print("Power Rangers Toy Data Fetcher (grnrngr.com)")
    print("=" * 60)
    print()

    scraper = GrnRngrScraper()
    toys = scraper.fetch_all_toys()

    # Save to file
    output_path = Path(__file__).parent.parent / OUTPUT_FILE
    with open(output_path, "w") as f:
        json.dump(toys, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Fetched {len(toys)} toys → {output_path}")
    print("=" * 60)

    # Summary by series
    series_counts = {}
    for toy in toys:
        series = toy.get("series") or "Unknown Series"
        series_counts[series] = series_counts.get(series, 0) + 1

    print("\nToys by series:")
    for series, count in sorted(series_counts.items(), key=lambda x: -x[1]):
        print(f"  {series}: {count}")

    # Summary of data quality
    with_images = sum(1 for t in toys if t.get("image_url"))
    with_years = sum(1 for t in toys if t.get("year"))
    with_prices = sum(1 for t in toys if t.get("price"))

    print(f"\nData quality:")
    print(f"  With images: {with_images}/{len(toys)} ({with_images/len(toys)*100:.1f}%)")
    print(f"  With years: {with_years}/{len(toys)} ({with_years/len(toys)*100:.1f}%)")
    print(f"  With prices: {with_prices}/{len(toys)} ({with_prices/len(toys)*100:.1f}%)")


if __name__ == "__main__":
    main()
