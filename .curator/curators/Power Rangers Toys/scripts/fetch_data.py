#!/usr/bin/env python3
"""Fetch Power Rangers toy data from RangerWiki."""

import json
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
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests", "beautifulsoup4", "lxml"])
    import requests
    from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://powerrangers.fandom.com"
OUTPUT_FILE = "fetched_data.json"
RATE_LIMIT = 1  # seconds between requests

# Starting points for toy discovery
CATEGORY_URLS = [
    "/wiki/Category:Toys",
    "/wiki/Category:Action_Figures",
    "/wiki/Category:Zords_(toys)"
]

USER_AGENT = "Power Rangers Collector Database Bot (Educational/Personal Project)"


class RangerWikiScraper:
    """Scrape toy data from RangerWiki."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.scraped_urls = set()

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a wiki page."""
        if url in self.scraped_urls:
            return None

        try:
            full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
            print(f"Fetching: {full_url}")

            response = self.session.get(full_url, timeout=10)
            response.raise_for_status()

            self.scraped_urls.add(url)
            time.sleep(RATE_LIMIT)

            return BeautifulSoup(response.text, "lxml")

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_category_members(self, soup: BeautifulSoup) -> List[str]:
        """Extract page URLs from a category page."""
        members = []

        # Find category member links
        category_div = soup.find("div", class_="mw-category")
        if category_div:
            for link in category_div.find_all("a"):
                href = link.get("href")
                if href and href.startswith("/wiki/") and ":" not in href:
                    members.append(href)

        # Handle pagination (next page link)
        next_link = soup.find("a", string="next page")
        if next_link and next_link.get("href"):
            members.append(next_link["href"])

        return members

    def extract_toy_data(self, url: str, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract toy data from a wiki page."""
        # Get title
        title_elem = soup.find("h1", class_="page-header__title")
        if not title_elem:
            return None

        name = title_elem.get_text(strip=True)

        # Look for infobox
        infobox = soup.find("aside", class_="portable-infobox")

        # Extract year from infobox or page content
        year = None
        series = None
        toy_type = None
        manufacturer = None
        description = None
        image_url = None

        if infobox:
            # Extract image
            img = infobox.find("img")
            if img and img.get("src"):
                image_url = img["src"].split("/revision/")[0]  # Remove version suffix

            # Extract data from infobox rows
            for row in infobox.find_all("div", class_="pi-item"):
                label_elem = row.find("h3", class_="pi-data-label")
                value_elem = row.find("div", class_="pi-data-value")

                if not label_elem or not value_elem:
                    continue

                label = label_elem.get_text(strip=True).lower()
                value = value_elem.get_text(strip=True)

                if "year" in label or "release" in label:
                    # Extract year from text like "1993" or "1993-1995"
                    import re
                    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", value)
                    if year_match:
                        year = int(year_match.group(1))

                elif "series" in label or "line" in label:
                    series = value

                elif "type" in label:
                    toy_type = value

                elif "manufacturer" in label or "company" in label:
                    manufacturer = value

        # Get first paragraph as description
        content_div = soup.find("div", class_="mw-parser-output")
        if content_div:
            paragraphs = content_div.find_all("p", recursive=False)
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    description = text
                    break

        # Determine series from URL or title if not found in infobox
        if not series:
            # Try to extract from breadcrumbs or categories
            categories = soup.find("div", id="mw-normal-catlinks")
            if categories:
                for link in categories.find_all("a"):
                    link_text = link.get_text(strip=True)
                    if "Power Rangers" in link_text and link_text != "Power Rangers":
                        series = link_text
                        break

        return {
            "name": name,
            "url": url,
            "year": year,
            "series": series,
            "toy_type": toy_type or "unknown",
            "manufacturer": manufacturer,
            "description": description,
            "image_url": image_url,
            "source_url": f"{BASE_URL}{url}"
        }

    def crawl_category(self, category_url: str) -> List[Dict]:
        """Crawl a category and extract all toy pages."""
        toys = []
        pages_to_visit = [category_url]
        visited = set()

        while pages_to_visit:
            url = pages_to_visit.pop(0)

            if url in visited:
                continue
            visited.add(url)

            soup = self.fetch_page(url)
            if not soup:
                continue

            # If this is a category page, get member pages
            if "Category:" in url:
                member_urls = self.extract_category_members(soup)
                for member_url in member_urls:
                    if "Category:" in member_url:
                        # It's a subcategory
                        pages_to_visit.append(member_url)
                    else:
                        # It's a toy page
                        toy_data = self.extract_toy_data(member_url, self.fetch_page(member_url))
                        if toy_data:
                            toys.append(toy_data)
                            print(f"  ✓ Extracted: {toy_data['name']}")

        return toys

    def fetch_all_toys(self) -> List[Dict]:
        """Fetch all Power Rangers toys from configured categories."""
        all_toys = []

        for category_url in CATEGORY_URLS:
            print(f"\nCrawling category: {category_url}")
            toys = self.crawl_category(category_url)
            all_toys.extend(toys)

        # Deduplicate by URL
        seen_urls = set()
        unique_toys = []
        for toy in all_toys:
            if toy["url"] not in seen_urls:
                seen_urls.add(toy["url"])
                unique_toys.append(toy)

        return unique_toys


def main():
    print("=" * 60)
    print("Power Rangers Toy Data Fetcher")
    print("=" * 60)
    print()

    scraper = RangerWikiScraper()
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


if __name__ == "__main__":
    main()
