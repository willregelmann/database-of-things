#!/usr/bin/env python3
"""Fetch Labubu figures from PopMart World by series."""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime

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

BASE_URL = "https://www.popmartworld.com"
OUTPUT_FILE = Path(__file__).parent.parent / "fetched_data.json"

# Rate limiting
RATE_LIMIT_DELAY = 0.5  # 500ms between requests (2 req/sec)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to convert

    Returns:
        Lowercase slug with hyphens
    """
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def fetch_series_list() -> list:
    """Fetch list of all Labubu/THE MONSTERS series from PopMart World.

    Returns:
        List of series dictionaries with name, slug, and URL
    """
    print("Fetching THE MONSTERS series list...")

    # The brand page lists all series for The Monsters (Labubu)
    brand_url = f"{BASE_URL}/brand/the-monsters"

    try:
        response = requests.get(brand_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')

        # Find all series links (this may need adjustment based on actual HTML structure)
        # Looking for links that match the pattern /collection/series-name
        series_links = soup.find_all('a', href=re.compile(r'/collection/[a-z-]+'))

        series_list = []
        seen_slugs = set()

        for link in series_links:
            href = link.get('href')
            if not href:
                continue

            # Extract series slug from URL
            match = re.search(r'/collection/([a-z-]+(?:-[a-z-]+)*)', href)
            if not match:
                continue

            slug = match.group(1)

            # Skip duplicates
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            # Get series name from link text or title attribute
            name = link.get_text(strip=True) or link.get('title', slug.replace('-', ' ').title())

            # Handle both absolute and relative URLs
            full_url = href if href.startswith('http') else f"{BASE_URL}{href}"

            series_list.append({
                "name": name,
                "slug": slug,
                "url": full_url
            })

        print(f"✓ Found {len(series_list)} series")
        return series_list

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch series list: {e}")
        return []


def fetch_series_details(series_slug: str, series_url: str) -> dict:
    """Fetch details for a specific series including all figures.

    Args:
        series_slug: URL slug for the series
        series_url: Full URL to series page

    Returns:
        Dictionary with series metadata and figures list
    """
    print(f"  Fetching {series_slug}...", end=" ", flush=True)

    try:
        time.sleep(RATE_LIMIT_DELAY)  # Rate limiting

        response = requests.get(series_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')

        # Extract series metadata
        series_data = {
            "slug": series_slug,
            "url": series_url,
            "name": None,
            "release_date": None,
            "size": None,
            "figures": []
        }

        # Try to find series name (usually in h1 or title)
        name_elem = soup.find('h1')
        if name_elem:
            series_data["name"] = name_elem.get_text(strip=True)

        # Try to find release date and size in metadata sections
        # This will need adjustment based on actual HTML structure
        metadata_text = soup.get_text()

        # Look for date pattern (e.g., "July 3, 2024" or "October 16, 2020")
        date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', metadata_text)
        if date_match:
            date_str = date_match.group(0)
            try:
                parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                series_data["release_date"] = date_str
                series_data["year"] = parsed_date.year
            except ValueError:
                pass

        # Look for size pattern (e.g., "3-4 inches" or "3.1-3.9 inches")
        size_match = re.search(r'(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)\s*inches?', metadata_text, re.IGNORECASE)
        if size_match:
            series_data["size"] = size_match.group(0)

        # Find all figure images and names
        # This will need adjustment based on actual HTML structure
        # Looking for common patterns: img tags with alt text, figure elements, product cards

        figures_found = []

        # Try multiple strategies to find figures

        # Strategy 1: Find img tags with descriptive alt text
        images = soup.find_all('img', alt=True)
        for img in images:
            alt_text = img.get('alt', '').strip()
            if alt_text and len(alt_text) > 2:  # Skip empty or very short alt text
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    # Check if this is a secret figure (usually marked in name or class)
                    is_secret = 'secret' in alt_text.lower() or 'hidden' in alt_text.lower()

                    figure_slug = slugify(alt_text)

                    figures_found.append({
                        "name": alt_text,
                        "slug": f"{series_slug}-{figure_slug}",
                        "image_url": img_url if img_url.startswith('http') else f"{BASE_URL}{img_url}",
                        "is_secret": is_secret
                    })

        series_data["figures"] = figures_found

        print(f"✓ {len(figures_found)} figures")
        return series_data

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None


def main():
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch Labubu figures from PopMart World"
    )
    parser.add_argument(
        "--series",
        help="Specific series to fetch (e.g., 'Art Series', 'Camping Series')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of series to fetch (useful for testing)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Labubu Figures Fetcher - PopMart World")
    print("=" * 60)
    print()

    # Fetch series list
    series_list = fetch_series_list()

    if not series_list:
        print("⚠️  No series found")
        sys.exit(1)

    # Filter by series name if specified
    if args.series:
        series_slug = slugify(args.series)
        series_list = [s for s in series_list if s["slug"] == series_slug or args.series.lower() in s["name"].lower()]
        if not series_list:
            print(f"⚠️  Series '{args.series}' not found")
            sys.exit(1)
        print(f"Filtered to {len(series_list)} series matching '{args.series}'")

    # Apply fetch limit if specified
    if args.limit:
        series_list = series_list[:args.limit]
        print(f"Limited to {args.limit} series for testing")

    print()
    print(f"Fetching details for {len(series_list)} series...")
    print()

    # Fetch details for each series
    all_data = []
    for series_info in series_list:
        series_data = fetch_series_details(series_info["slug"], series_info["url"])
        if series_data:
            all_data.append(series_data)

    if not all_data:
        print("\\n⚠️  No data fetched")
        sys.exit(1)

    # Calculate totals
    total_figures = sum(len(s.get("figures", [])) for s in all_data)

    # Save to file
    print()
    print(f"Saving {len(all_data)} series ({total_figures} figures) to {OUTPUT_FILE.name}...")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"✓ Complete! Fetched {len(all_data)} series with {total_figures} total figures")
    print(f"  Output: {OUTPUT_FILE}")
    print()
    print("Next steps:")
    print("  python3 scripts/import_items.py --dry-run  # Test import")
    print("  python3 scripts/import_items.py            # Real import")
    print()
    print("To fetch specific series:")
    print("  python3 scripts/fetch_data.py --series 'Art Series'")
    print("  python3 scripts/fetch_data.py --limit 3  # Test with 3 series")


if __name__ == "__main__":
    main()
