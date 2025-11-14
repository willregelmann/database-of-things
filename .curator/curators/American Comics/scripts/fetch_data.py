#!/usr/bin/env python3
"""
Fetch comic book data from Metron API.

Phase C: Curated series import (hardcoded list)
Phase A: Single publisher import (--publisher flag)
Phase B: All publishers import (--all-publishers flag)
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

# Auto-install dependencies if missing
try:
    import mokkari
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "mokkari"
    ])
    import mokkari

# Target series for Phase C (curated import)
# Starting with just Monstress for testing (full series will be added after testing)
TARGET_SERIES = [
    {"name": "Monstress", "publisher": "Image", "year": 2015},
]

# Full Phase C list (uncomment after testing):
# TARGET_SERIES = [
#     # User's personal collection
#     {"name": "DOOMWAR", "publisher": "Marvel", "year": 2010},
#     {"name": "Loki: Agent of Asgard", "publisher": "Marvel", "year": 2014},
#     {"name": "Monstress", "publisher": "Image", "year": 2015},
#
#     # Popular modern series
#     {"name": "Saga", "publisher": "Image", "year": 2012},
#     {"name": "The Walking Dead", "publisher": "Image", "year": 2003},
#     {"name": "Invincible", "publisher": "Image", "year": 2003},
#     {"name": "Ms. Marvel", "publisher": "Marvel", "year": 2014},
#     {"name": "Hawkeye", "publisher": "Marvel", "year": 2012},
#     {"name": "Batman", "publisher": "DC", "year": 2011},
#     {"name": "Descender", "publisher": "Image", "year": 2015},
# ]

OUTPUT_FILE = "fetched_data.json"


class MetronFetcher:
    """Fetch comics data from Metron API using Mokkari."""

    def __init__(self, username: str, password: str):
        self.api = mokkari.api(username=username, passwd=password)
        self.request_count = 0

    def fetch_curated_series(self) -> List[Dict]:
        """Fetch hardcoded list of target series (Phase C)."""
        print(f"\n{'=' * 60}")
        print("Phase C: Fetching Curated Series")
        print(f"{'=' * 60}\n")

        all_comics = []

        for i, series_config in enumerate(TARGET_SERIES, 1):
            print(f"\n[{i}/{len(TARGET_SERIES)}] {series_config['name']}")
            print("-" * 60)

            # Search for series
            series = self._find_series(
                name=series_config["name"],
                publisher=series_config.get("publisher"),
                year=series_config.get("year")
            )

            if not series:
                print(f"  ⚠️  Series not found in Metron")
                continue

            # Fetch all issues for this series
            issues = self._fetch_series_issues(series)
            all_comics.extend(issues)

            print(f"  ✓ Fetched {len(issues)} issues")

        return all_comics

    def _find_series(self, name: str, publisher: Optional[str] = None, year: Optional[int] = None):
        """Find a series in Metron by name, publisher, and year."""
        params = {"name": name}

        try:
            self.request_count += 1
            results = self.api.series_list(params=params)

            if not results:
                return None

            # Filter by year if specified (publisher check requires full series details)
            for series in results:
                # Check year match
                if year:
                    if not hasattr(series, 'year_began') or series.year_began != year:
                        continue

                # Get full series details to check publisher
                if publisher:
                    self.request_count += 1
                    full_series = self.api.series(series.id)
                    if hasattr(full_series, 'publisher') and hasattr(full_series.publisher, 'name'):
                        series_publisher = full_series.publisher.name
                        if publisher.lower() not in series_publisher.lower():
                            continue
                    else:
                        continue  # Skip if publisher info not available

                    # Found a match with publisher check
                    series_name = getattr(full_series, 'name', getattr(series, 'display_name', 'Unknown'))
                    print(f"  Found: {series_name} (ID: {full_series.id}, Publisher: {series_publisher})")
                    return full_series

                # Found a match without publisher check
                print(f"  Found: {series.display_name} (ID: {series.id})")
                return series

            # No exact match found
            if results:
                print(f"  ⚠️  Found {len(results)} series but none matched filters")
                print(f"      First result: {results[0].display_name}")

            return None

        except Exception as e:
            print(f"  ⚠️  Error searching for series: {e}")
            return None

    def _fetch_series_issues(self, series) -> List[Dict]:
        """Fetch all issues for a series."""
        issues = []

        try:
            params = {"series_id": series.id}
            self.request_count += 1

            issue_list = self.api.issues_list(params=params)

            for base_issue in issue_list:
                # Fetch full issue details to get credits
                self.request_count += 1
                full_issue = self.api.issue(base_issue.id)

                comic_data = self._parse_issue(full_issue, series)
                if comic_data:
                    issues.append(comic_data)

            return issues

        except Exception as e:
            print(f"  ⚠️  Error fetching issues: {e}")
            return []

    def _parse_issue(self, issue, series) -> Optional[Dict]:
        """Parse issue data from Metron API."""
        try:
            # Extract issue number
            number = getattr(issue, 'number', '')

            # Get series name (handle both BaseSeries and full Series objects)
            series_name = getattr(series, 'name', getattr(series, 'display_name', 'Unknown Series'))

            # Build full title
            name = f"{series_name} #{number}"

            # Extract year from cover date
            year = None
            if hasattr(issue, 'cover_date') and issue.cover_date:
                # cover_date is a datetime.date object
                year = issue.cover_date.year if hasattr(issue.cover_date, 'year') else None

            # Extract credits (credits is a list of Credit objects)
            writers = []
            artists = []
            if hasattr(issue, 'credits') and issue.credits:
                for credit in issue.credits:
                    creator_name = credit.creator
                    # credit.role is a list of GenericItem objects
                    for role_item in credit.role:
                        role_name = role_item.name.lower()

                        if 'writer' in role_name or 'plotter' in role_name:
                            if creator_name not in writers:
                                writers.append(creator_name)
                        elif any(x in role_name for x in ['artist', 'pencil', 'ink', 'color']):
                            if creator_name not in artists:
                                artists.append(creator_name)

            # Extract image URL (convert HttpUrl to string)
            image_url = None
            if hasattr(issue, 'image') and issue.image:
                image_url = str(issue.image)

            # Build source URL
            source_url = f"https://metron.cloud/issue/{issue.id}/"

            # Get publisher name (if available on full Series object)
            publisher = ''
            if hasattr(series, 'publisher') and hasattr(series.publisher, 'name'):
                publisher = series.publisher.name

            return {
                "id": issue.id,
                "name": name,
                "series_name": series_name,
                "series_id": series.id,
                "issue_number": number,
                "year": year,
                "publisher": publisher,
                "writers": writers,
                "artists": artists,
                "image_url": image_url,
                "source_url": source_url
            }

        except Exception as e:
            print(f"  ⚠️  Failed to parse issue: {e}")
            return None


def main():
    print("=" * 60)
    print("American Comics - Metron API Fetcher")
    print("=" * 60)
    print()

    # Load credentials from environment
    username = os.getenv("METRON_USERNAME")
    password = os.getenv("METRON_PASSWORD")

    if not username or not password:
        print("Error: METRON_USERNAME and METRON_PASSWORD must be set")
        print("Get credentials from: https://metron.cloud/")
        sys.exit(1)

    fetcher = MetronFetcher(username, password)

    # Phase C: Fetch curated series
    comics = fetcher.fetch_curated_series()

    # Save to file
    output_path = Path(__file__).parent.parent / OUTPUT_FILE
    with open(output_path, "w") as f:
        json.dump(comics, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Fetched {len(comics)} comics → {output_path}")
    print(f"  Total API requests: {fetcher.request_count}")
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
