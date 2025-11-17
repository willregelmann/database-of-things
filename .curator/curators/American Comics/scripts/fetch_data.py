#!/usr/bin/env python3
"""
Fetch comic book data from Metron API.

Usage:
  # Fetch specific series by name
  python3 fetch_data.py --series "Monstress" --series "Saga"

  # Fetch all series from a publisher
  python3 fetch_data.py --publisher "Image"

  # Limit number of issues (for testing)
  python3 fetch_data.py --series "Monstress" --limit 10

  # Default: Fetch sample series for testing
  python3 fetch_data.py
"""

import argparse
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

OUTPUT_FILE = "fetched_data.json"


class MetronFetcher:
    """Fetch comics data from Metron API using Mokkari."""

    def __init__(self, username: str, password: str, limit: Optional[int] = None):
        self.api = mokkari.api(username=username, passwd=password)
        self.request_count = 0
        self.limit = limit
        self.total_issues_fetched = 0

    def fetch_series_list(self, series_configs: List[Dict]) -> List[Dict]:
        """Fetch specific series by name/publisher/year.

        Returns graph structure: parent entities (series) + child entities (issues).
        """
        print(f"\n{'=' * 60}")
        print(f"Fetching {len(series_configs)} Series")
        print(f"{'=' * 60}\n")

        all_entities = []

        for i, series_config in enumerate(series_configs, 1):
            if self.limit and self.total_issues_fetched >= self.limit:
                print(f"\n⚠️  Reached limit of {self.limit} issues")
                break

            print(f"\n[{i}/{len(series_configs)}] {series_config['name']}")
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

            # Create parent entity (series/collection)
            parent_entity = self._create_series_entity(series)
            all_entities.append(parent_entity)

            # Fetch all issues for this series (they reference the parent)
            issues = self._fetch_series_issues(series)
            all_entities.extend(issues)

            print(f"  ✓ Fetched 1 series + {len(issues)} issues")

        return all_entities

    def fetch_by_publisher(self, publisher_name: str) -> List[Dict]:
        """Fetch all series from a specific publisher.

        Returns graph structure: parent entities (series) + child entities (issues).
        """
        print(f"\n{'=' * 60}")
        print(f"Fetching All Series from Publisher: {publisher_name}")
        print(f"{'=' * 60}\n")

        all_entities = []

        try:
            # Search for publisher
            self.request_count += 1
            publishers = self.api.publisher_list(params={"name": publisher_name})

            if not publishers:
                print(f"  ⚠️  Publisher '{publisher_name}' not found")
                return []

            publisher = publishers[0]
            print(f"Found publisher: {publisher.name} (ID: {publisher.id})")

            # Get all series for this publisher
            self.request_count += 1
            series_list = self.api.series_list(params={"publisher_id": publisher.id})

            print(f"Found {len(series_list)} series from {publisher.name}\n")

            # Fetch issues for each series
            for i, base_series in enumerate(series_list, 1):
                if self.limit and self.total_issues_fetched >= self.limit:
                    print(f"\n⚠️  Reached limit of {self.limit} issues")
                    break

                print(f"[{i}/{len(series_list)}] {base_series.display_name}")
                print("-" * 60)

                # Get full series details
                self.request_count += 1
                series = self.api.series(base_series.id)

                # Create parent entity
                parent_entity = self._create_series_entity(series)
                all_entities.append(parent_entity)

                # Fetch issues
                issues = self._fetch_series_issues(series)
                all_entities.extend(issues)

                print(f"  ✓ Fetched 1 series + {len(issues)} issues")

        except Exception as e:
            print(f"  ⚠️  Error fetching publisher series: {e}")

        return all_entities

    def _create_series_entity(self, series) -> Dict:
        """Create parent entity for a series/collection."""
        # Get series name
        series_name = getattr(series, 'name', getattr(series, 'display_name', 'Unknown Series'))

        # Get year
        year = None
        if hasattr(series, 'year_began'):
            year = series.year_began

        # Get publisher name
        publisher = ''
        if hasattr(series, 'publisher') and hasattr(series.publisher, 'name'):
            publisher = series.publisher.name

        return {
            "name": series_name,
            "type": "collection",
            "year": year,
            "external_ids": {
                "metron_series_id": str(series.id)
            },
            "attributes": {
                "publisher": publisher
            }
        }

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
                # Check limit
                if self.limit and self.total_issues_fetched >= self.limit:
                    break

                # Fetch full issue details to get credits
                self.request_count += 1
                full_issue = self.api.issue(base_issue.id)

                comic_data = self._parse_issue(full_issue, series)
                if comic_data:
                    issues.append(comic_data)
                    self.total_issues_fetched += 1

            return issues

        except Exception as e:
            print(f"  ⚠️  Error fetching issues: {e}")
            return []

    def _parse_issue(self, issue, series) -> Optional[Dict]:
        """Parse issue data from Metron API (v2 format)."""
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

            # Return v2 format (graph structure)
            return {
                "name": name,
                "type": "comic",
                "year": year,
                "external_ids": {
                    "metron_id": str(issue.id)
                },
                "image_url": image_url,
                "source_url": source_url,
                "parent": {
                    "type": "collection",
                    "external_ids": {
                        "metron_series_id": str(series.id)
                    }
                },
                "relationship": {
                    "type": "contains",
                    "order": int(number) if number.isdigit() else None
                },
                "attributes": {
                    "issue_number": number,
                    "publisher": publisher,
                    "writers": writers,
                    "artists": artists
                }
            }

        except Exception as e:
            print(f"  ⚠️  Failed to parse issue: {e}")
            return None


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch comic book data from Metron API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch specific series
  python3 fetch_data.py --series "Monstress" --series "Saga"

  # Fetch all series from a publisher
  python3 fetch_data.py --publisher "Image Comics"

  # Limit number of issues (for testing)
  python3 fetch_data.py --series "Monstress" --limit 10

  # Default: Fetch sample series for testing
  python3 fetch_data.py
        """
    )
    parser.add_argument(
        "--series",
        action="append",
        help="Series name to fetch (can be specified multiple times)"
    )
    parser.add_argument(
        "--publisher",
        help="Fetch all series from this publisher"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit total number of issues to fetch (for testing)"
    )

    args = parser.parse_args()

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

    fetcher = MetronFetcher(username, password, limit=args.limit)

    # Determine what to fetch
    entities = []
    filters_applied = {}

    if args.publisher:
        # Fetch by publisher
        entities = fetcher.fetch_by_publisher(args.publisher)
        filters_applied["publisher"] = args.publisher
    elif args.series:
        # Fetch specific series
        series_configs = [{"name": name} for name in args.series]
        entities = fetcher.fetch_series_list(series_configs)
        filters_applied["series"] = args.series
    else:
        print("Error: Either --series or --publisher is required")
        print("\nExamples:")
        print("  python3 fetch_data.py --series 'Monstress' --series 'Saga'")
        print("  python3 fetch_data.py --publisher 'Image Comics'")
        print("  python3 fetch_data.py --series 'Monstress' --limit 10")
        sys.exit(1)

    if args.limit:
        filters_applied["limit"] = args.limit

    # Wrap in v2 format with metadata
    from datetime import datetime, timezone
    output_data = {
        "format_version": "1.0",
        "metadata": {
            "curator": "American Comics",
            "source": "https://metron.cloud",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(entities),
            "filters_applied": filters_applied
        },
        "items": entities
    }

    # Save to file
    output_path = Path(__file__).parent.parent / OUTPUT_FILE
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Fetched {len(entities)} entities → {output_path}")
    print(f"  Total API requests: {fetcher.request_count}")
    print("=" * 60)

    # Data quality report
    if entities:
        # Count different entity types
        collections = sum(1 for e in entities if e.get("type") == "collection")
        comics = sum(1 for e in entities if e.get("type") == "comic")

        # Count quality metrics (only for comics)
        with_images = sum(1 for e in entities if e.get("type") == "comic" and e.get("image_url"))
        with_years = sum(1 for e in entities if e.get("year"))
        with_writers = sum(1 for e in entities if e.get("type") == "comic" and e.get("attributes", {}).get("writers"))

        print(f"\nData quality:")
        print(f"  Total entities: {len(entities)} ({collections} collections, {comics} comics)")
        print(f"  Comics with images: {with_images}/{comics} ({with_images/comics*100:.1f}%)" if comics > 0 else "")
        print(f"  Entities with years: {with_years}/{len(entities)} ({with_years/len(entities)*100:.1f}%)")
        print(f"  Comics with writers: {with_writers}/{comics} ({with_writers/comics*100:.1f}%)" if comics > 0 else "")


if __name__ == "__main__":
    main()
