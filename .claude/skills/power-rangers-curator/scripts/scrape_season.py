#!/usr/bin/env python3
"""
Scrape Power Rangers toys from GRNRngr.com

This script scrapes all toy lines and individual toys from a specific
Power Rangers season page.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def scrape_season(season_slug, dry_run=False):
    """Scrape all toys from a Power Rangers season"""

    url = f"https://www.grnrngr.com/toys/power-rangers/{season_slug}"
    print(f"Fetching {url}...")

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')

    # Storage for scraped data
    toy_lines = []

    # Find all h2 tags (these are toy line headers like "2200 Mighty Morphin Power Rangers")
    h2_tags = soup.find_all('h2')

    for h2 in h2_tags:
        h2_text = h2.get_text(strip=True)

        # Skip non-toy-line headings
        if not re.match(r'^\d{4}', h2_text):
            continue

        # Extract assortment number and name
        match = re.match(r'^(\d{4})\s+(.+)$', h2_text)
        if not match:
            continue

        asst_no = match.group(1)
        toy_line_name = match.group(2)

        print(f"\n📦 Toy Line: {asst_no} {toy_line_name}")

        # Find metadata (SRP, Case Count) - should be in next text node or element
        metadata = {}
        next_elem = h2.next_sibling
        while next_elem:
            if hasattr(next_elem, 'get_text'):
                text = next_elem.get_text(strip=True)
            else:
                text = str(next_elem).strip()

            # Look for [SRP: $X.XX; Case Count: XX] pattern
            srp_match = re.search(r'\[SRP:\s*\$?([\d.]+)', text)
            case_match = re.search(r'Case Count:\s*(\d+)', text)

            if srp_match:
                metadata['srp'] = srp_match.group(1)
            if case_match:
                metadata['case_count'] = int(case_match.group(1))

            # Stop when we hit a list or another heading
            if next_elem.name in ['ul', 'ol', 'h2', 'h3']:
                break

            next_elem = next_elem.next_sibling

        print(f"  Metadata: SRP=${metadata.get('srp', 'N/A')}, Case Count={metadata.get('case_count', 'N/A')}")

        # Find the next UL after this h2 (but before next h2)
        toys = []
        ul = h2.find_next('ul')
        next_h2 = h2.find_next('h2')

        # Make sure this UL belongs to this toy line
        # Check if next_h2 comes before the ul (meaning ul belongs to next section)
        if ul:
            ul_is_for_this_section = True
            if next_h2:
                # Check if ul comes after next_h2 in document order
                # We do this by checking if next_h2 appears when searching backwards from ul
                h2_before_ul = ul.find_previous('h2')
                if h2_before_ul and h2_before_ul != h2:
                    ul_is_for_this_section = False

            if ul_is_for_this_section:
                # Found the list of toys for this toy line
                for li in ul.find_all('li', recursive=False):
                    toy = parse_toy_item(li, asst_no)
                    if toy:
                        toys.append(toy)
                        print(f"    • {toy['item_no']} - {toy['name']}")

        # Store toy line data
        toy_lines.append({
            'asst_no': asst_no,
            'name': toy_line_name,
            'metadata': metadata,
            'toys': toys
        })

    print(f"\n✅ Found {len(toy_lines)} toy lines with {sum(len(tl['toys']) for tl in toy_lines)} total toys")

    return {
        'season': season_slug,
        'url': url,
        'toy_lines': toy_lines
    }


def parse_toy_item(li, asst_no):
    """Parse a single toy item from an li element"""

    # Extract item number from <span class="itemnum">
    item_no = None
    itemnum_span = li.find('span', class_='itemnum')
    if itemnum_span:
        item_no = itemnum_span.get_text(strip=True)

    if not item_no:
        return None

    # Extract product name from <a class="itemlink">
    name = None
    image_url = None
    itemlink = li.find('a', class_='itemlink')
    if itemlink:
        name = itemlink.get_text(strip=True)
        # Image URL is in the href
        href = itemlink.get('href', '')
        if href:
            image_url = f"https://www.grnrngr.com{href}" if href.startswith('/') else href

    if not name:
        return None

    # Extract release date from <span class="iteminfo">
    release_date = None
    iteminfo_span = li.find('span', class_='iteminfo')
    if iteminfo_span:
        info_text = iteminfo_span.get_text(strip=True)
        # Remove brackets
        release_date = info_text.strip('[]')

    return {
        'asst_no': asst_no,
        'item_no': item_no,
        'name': name,
        'image_url': image_url,
        'release_date': release_date
    }


def main():
    parser = argparse.ArgumentParser(description='Scrape Power Rangers toys from GRNRngr.com')
    parser.add_argument('season', help='Season slug (e.g., mighty-morphin, zeo, turbo)')
    parser.add_argument('--output', '-o', help='Output JSON file (default: <season>_toys.json)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')

    args = parser.parse_args()

    # Scrape the season
    data = scrape_season(args.season, dry_run=args.dry_run)

    if args.dry_run:
        print("\n🔍 DRY RUN - No files written")
        return

    # Determine output file
    output_file = args.output or f"{args.season.replace('-', '_')}_toys.json"

    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n💾 Saved to {output_file}")


if __name__ == '__main__':
    main()
