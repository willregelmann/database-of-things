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
        # Format: /toys/pictures/bandai/ITEMNUM.jpg OR /toys/pictures/bandai/ITEMNUM_1.jpg
        # Note: Some images have _1 suffix, others don't - backfill script tries both
        # Pad item number to 5 digits
        padded_number = item_number.zfill(5)
        # Store base URL without suffix - backfill will try both patterns
        image_url = f"{BASE_URL}/toys/pictures/bandai/{padded_number}.jpg"

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

    def parse_assortment_header(self, h3_text: str) -> Optional[Dict]:
        """Parse toy line assortment header like '3130 Morpher Assortment [SRP: $10.50]'."""
        if not h3_text:
            return None

        # Extract assortment number and name
        match = re.match(r'^(\d+)\s+(.+?)(?:\s+\[|$)', h3_text)
        if not match:
            return None

        assortment_number = match.group(1)
        assortment_name = match.group(2).strip()

        # Extract price
        price = self.extract_price(h3_text)

        return {
            "assortment_number": assortment_number,
            "name": f"{assortment_number} {assortment_name}",
            "price": price,
            "manufacturer": "Bandai America"  # Standard for Power Rangers toys
        }

    def scrape_season_page(self, season_url: str) -> List[Dict]:
        """Scrape all toy lines and toys from a season page."""
        soup = self.fetch_page(season_url)
        if not soup:
            return []

        # Extract series name from page title or heading
        title_elem = soup.find("h1") or soup.find("title")
        series_name = title_elem.get_text(strip=True) if title_elem else "Unknown Series"

        # Clean up series name
        series_name = series_name.replace(" - GrnRngr.com", "").strip()

        print(f"  Series: {series_name}")

        toy_lines = []

        # Find all h2 headers (toy line assortments)
        for h2 in soup.find_all("h2"):
            h2_text = h2.get_text(strip=True)

            # Parse assortment header
            assortment_info = self.parse_assortment_header(h2_text)
            if not assortment_info:
                continue

            print(f"    Toy Line: {assortment_info['name']}")

            # Find the next ul (may not be direct sibling due to div elements)
            ul = h2.find_next("ul")
            if not ul:
                continue

            toys = []

            # Parse all li items under this assortment
            for li in ul.find_all("li", recursive=False):
                li_text = li.get_text(separator='\n', strip=True)

                # Extract item number from start of text
                number_match = re.match(r'^(\d+)', li_text)
                if not number_match:
                    continue

                item_number = number_match.group(1)

                # Parse the toy entry
                toy_data = self.parse_toy_entry(item_number, li_text, series_name)

                if toy_data:
                    toys.append(toy_data)
                    print(f"      ✓ {toy_data['name']} (#{item_number})")

            if toys:
                toy_line_data = {
                    "series": series_name,
                    "assortment_number": assortment_info["assortment_number"],
                    "name": assortment_info["name"],
                    "manufacturer": assortment_info["manufacturer"],
                    "price": assortment_info["price"],
                    "source_url": f"{BASE_URL}{season_url}",
                    "toys": toys
                }
                toy_lines.append(toy_line_data)

        return toy_lines

    def fetch_all_toy_lines(self) -> List[Dict]:
        """Fetch all Power Rangers toy lines from configured season toylines."""
        all_toy_lines = []

        for season_url in SEASON_TOYLINES:
            print(f"\n{'='*60}")
            print(f"Scraping: {season_url}")
            print('='*60)

            toy_lines = self.scrape_season_page(season_url)
            all_toy_lines.extend(toy_lines)

            toy_count = sum(len(tl["toys"]) for tl in toy_lines)
            print(f"  Found {len(toy_lines)} toy lines with {toy_count} toys")

        # Deduplicate toy lines by assortment number
        seen_assortments = set()
        unique_toy_lines = []
        for toy_line in all_toy_lines:
            assort_num = toy_line.get("assortment_number")
            if assort_num and assort_num not in seen_assortments:
                seen_assortments.add(assort_num)
                unique_toy_lines.append(toy_line)

        return unique_toy_lines


def main():
    print("=" * 60)
    print("Power Rangers Toy Data Fetcher (grnrngr.com)")
    print("=" * 60)
    print()

    scraper = GrnRngrScraper()
    toy_lines = scraper.fetch_all_toy_lines()

    # Save to file
    output_path = Path(__file__).parent.parent / OUTPUT_FILE
    with open(output_path, "w") as f:
        json.dump(toy_lines, f, indent=2)

    print()
    print("=" * 60)
    total_toys = sum(len(tl["toys"]) for tl in toy_lines)
    print(f"✓ Fetched {len(toy_lines)} toy lines with {total_toys} toys → {output_path}")
    print("=" * 60)

    # Summary by series
    series_counts = {}
    for toy_line in toy_lines:
        series = toy_line.get("series") or "Unknown Series"
        toy_count = len(toy_line.get("toys", []))
        series_counts[series] = series_counts.get(series, 0) + toy_count

    print("\nToys by series:")
    for series, count in sorted(series_counts.items(), key=lambda x: -x[1]):
        print(f"  {series}: {count}")

    # Summary of data quality
    all_toys = [toy for tl in toy_lines for toy in tl.get("toys", [])]
    with_images = sum(1 for t in all_toys if t.get("image_url"))
    with_years = sum(1 for t in all_toys if t.get("year"))

    print(f"\nData quality:")
    print(f"  Toy lines: {len(toy_lines)}")
    print(f"  Total toys: {total_toys}")
    print(f"  With images: {with_images}/{total_toys} ({with_images/total_toys*100:.1f}%)")
    print(f"  With years: {with_years}/{total_toys} ({with_years/total_toys*100:.1f}%)")


if __name__ == "__main__":
    main()
