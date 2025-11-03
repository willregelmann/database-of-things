#!/usr/bin/env python3
"""
Import a specific Marvel comic series and issues into the database

Usage:
    python3 import_comic.py "Doomwar" --issues 1
    python3 import_comic.py "Amazing Spider-Man" --start-year 1999 --issues 1-10
"""

import os
import sys
import argparse
import hashlib
import time
import json
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Marvel API configuration
MARVEL_PUBLIC_KEY = os.getenv("MARVEL_COMICS_API_PUBLIC_KEY")
MARVEL_PRIVATE_KEY = os.getenv("MARVEL_COMICS_API_PRIVATE_KEY")
BASE_URL = "https://gateway.marvel.com/v1/public"

# Database configuration
CONTAINER_NAME = "supabase_db_database-of-things"
DB_NAME = "postgres"
DB_USER = "postgres"


def generate_auth_params():
    """Generate authentication parameters for Marvel API"""
    ts = str(int(time.time()))
    hash_input = f"{ts}{MARVEL_PRIVATE_KEY}{MARVEL_PUBLIC_KEY}"
    hash_md5 = hashlib.md5(hash_input.encode()).hexdigest()

    return {
        "apikey": MARVEL_PUBLIC_KEY,
        "ts": ts,
        "hash": hash_md5
    }


def make_request(endpoint, params=None):
    """Make authenticated request to Marvel API"""
    if params is None:
        params = {}

    auth_params = generate_auth_params()
    params.update(auth_params)

    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def exec_sql(sql):
    """Execute SQL in the Supabase PostgreSQL container"""
    cmd = [
        "docker", "exec",
        CONTAINER_NAME,
        "psql",
        "-U", DB_USER,
        "-d", DB_NAME,
        "-t",  # tuples only (no header/footer)
        "-c", sql
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ SQL Error: {result.stderr}")
        return None

    return result.stdout.strip()


def find_entity_by_external_id(external_system, external_id):
    """Find entity by external ID (e.g., marvel_series_id, marvel_comic_id)"""
    sql = f"""
    SELECT id
    FROM entities
    WHERE external_ids->'{external_system}' = '"{external_id}"';
    """
    result = exec_sql(sql)
    return result if result else None


def find_entity_by_name(name):
    """Find entity by exact name match"""
    safe_name = name.replace("'", "''")
    sql = f"""
    SELECT id
    FROM entities
    WHERE name = '{safe_name}';
    """
    result = exec_sql(sql)
    return result.strip() if result else None


def create_entity(entity_type, name, year, image_key, external_ids, attributes):
    """Create a new entity"""
    safe_name = name.replace("'", "''")
    safe_image_key = image_key.replace("'", "''") if image_key else None
    external_ids_json = json.dumps(external_ids).replace("'", "''") if external_ids else "{}"
    attr_json = json.dumps(attributes).replace("'", "''")

    sql = f"""
    INSERT INTO entities (type, name, year, country, image_key, external_ids, attributes)
    VALUES (
        '{entity_type}',
        '{safe_name}',
        {year if year else 'NULL'},
        'US',
        {f"'{safe_image_key}'" if safe_image_key else 'NULL'},
        '{external_ids_json}'::jsonb,
        '{attr_json}'::jsonb
    )
    RETURNING id;
    """

    result = exec_sql(sql)
    if not result:
        return None

    # Extract UUID
    for line in result.split('\n'):
        line = line.strip()
        if line and '-' in line and len(line) == 36:
            return line

    return None


def create_relationship(from_id, to_id, rel_type):
    """Create a relationship between entities"""
    sql = f"""
    INSERT INTO relationships (from_id, to_id, type, attributes)
    VALUES ('{from_id}', '{to_id}', '{rel_type}', '{{}}'::jsonb)
    ON CONFLICT (from_id, to_id, type) DO NOTHING;
    """
    exec_sql(sql)


def find_or_create_franchise():
    """Find or create the Marvel Comics franchise entity"""
    # Check if Marvel Comics franchise exists
    sql = """
    SELECT id
    FROM entities
    WHERE name = 'Marvel Comics' AND type = 'franchise';
    """
    result = exec_sql(sql)

    if result:
        print(f"✅ Found existing Marvel Comics franchise: {result}")
        return result.strip()

    # Create it
    print("📦 Creating Marvel Comics franchise...")
    franchise_id = create_entity(
        entity_type='franchise',
        name='Marvel Comics',
        year=1939,
        image_key=None,
        external_ids=None,
        attributes={
            "publisher": "Marvel Comics",
            "description": "Marvel Comics is an American comic book publisher and the property of The Walt Disney Company."
        }
    )

    print(f"✅ Created Marvel Comics franchise: {franchise_id}")
    return franchise_id


def search_series(title, start_year=None):
    """Search for a comic series by title"""
    print(f"\n🔍 Searching for series: {title}")
    if start_year:
        print(f"   Start year: {start_year}")

    params = {
        "title": title,
        "limit": 10
    }

    if start_year:
        params["startYear"] = start_year

    data = make_request("series", params)

    total = data['data']['total']
    results = data['data']['results']

    print(f"   Found {total} matching series")

    if not results:
        return None

    # Show options
    print("\n📖 Available series:")
    for i, series in enumerate(results, 1):
        print(f"   {i}. {series['title']}")
        print(f"      Years: {series.get('startYear', '?')} - {series.get('endYear', 'Present')}")
        print(f"      Type: {series.get('type', 'N/A')}")
        print(f"      ID: {series['id']}")
        print()

    return results


def get_series_comics(series_id, issue_numbers=None):
    """Get comics from a series"""
    print(f"\n📚 Fetching comics from series {series_id}...")

    params = {
        "limit": 100
    }

    data = make_request(f"series/{series_id}/comics", params)

    comics = data['data']['results']

    # Filter by issue numbers if specified
    if issue_numbers:
        comics = [c for c in comics if c.get('issueNumber') in issue_numbers]

    print(f"   Found {len(comics)} comics")

    return comics


def import_series(series_data, franchise_id):
    """Import a series entity"""
    series_id = series_data['id']
    title = series_data['title']
    start_year = series_data.get('startYear')
    end_year = series_data.get('endYear')

    print(f"\n📖 Importing series: {title}")

    # Check if already exists
    existing_id = find_entity_by_external_id('marvel_series_id', str(series_id))

    if existing_id:
        print(f"   ♻️  Series already exists: {existing_id}")
        return existing_id

    # Build external_ids (dedicated column)
    external_ids = {
        "marvel_series_id": str(series_id)
    }

    # Build attributes (simplified - just publisher)
    attributes = {
        "publisher": "Marvel Comics"
    }

    # Get image URL
    image_url = None
    if series_data.get('thumbnail'):
        thumb = series_data['thumbnail']
        path = thumb['path']
        ext = thumb['extension']
        # Skip image_not_available placeholder
        if 'image_not_available' not in path:
            image_url = f"{path}.{ext}"

    # Create series entity
    entity_id = create_entity(
        entity_type='collection',
        name=title,
        year=start_year,
        image_key=image_url,
        external_ids=external_ids,
        attributes=attributes
    )

    print(f"   ✅ Created series: {entity_id}")

    # Link to franchise
    create_relationship(franchise_id, entity_id, 'contains')
    print(f"   🔗 Linked to franchise")

    return entity_id


def import_comic(comic_data, series_id):
    """Import a comic issue"""
    comic_id = comic_data['id']
    title = comic_data['title']
    issue_number = comic_data.get('issueNumber', 0)

    print(f"\n📕 Importing comic: {title}")
    print(f"   Issue #{issue_number}")

    # Check if already exists
    existing_id = find_entity_by_external_id('marvel_comic_id', str(comic_id))

    if existing_id:
        print(f"   ♻️  Comic already exists: {existing_id}")
        return existing_id

    # Build external_ids (dedicated column)
    external_ids = {
        "marvel_comic_id": str(comic_id)
    }

    # Build attributes (simplified - publisher + writer only)
    attributes = {
        "publisher": "Marvel Comics"
    }

    # Extract primary writer
    if comic_data.get('creators') and comic_data['creators'].get('items'):
        for creator in comic_data['creators']['items']:
            if creator['role'] == 'writer':
                attributes['writer'] = creator['name']
                break  # Just use first writer

    # Get image URL
    image_url = None
    if comic_data.get('thumbnail'):
        thumb = comic_data['thumbnail']
        path = thumb['path']
        ext = thumb['extension']
        # Skip image_not_available placeholder
        if 'image_not_available' not in path:
            image_url = f"{path}.{ext}"

    # Determine year from dates
    year = None
    if comic_data.get('dates'):
        for date_obj in comic_data['dates']:
            if date_obj['type'] == 'onsaleDate':
                year_str = date_obj['date'][:4]
                year = int(year_str) if year_str.isdigit() else None
                break

    # Create comic entity
    entity_id = create_entity(
        entity_type='comic_issue',
        name=title,
        year=year,
        image_key=image_url,
        external_ids=external_ids,
        attributes=attributes
    )

    print(f"   ✅ Created comic: {entity_id}")

    # Check if this is a variant (has text in parentheses after issue number)
    # Example: "Doomwar (2010) #4 (HEROIC AGE VARIANT)"
    is_variant = ' (' in title.split('#')[-1] if '#' in title else False

    if is_variant:
        # Extract base issue name by removing the variant suffix
        # "Doomwar (2010) #4 (HEROIC AGE VARIANT)" -> "Doomwar (2010) #4"
        base_title = title.rsplit(' (', 1)[0]

        # Find base issue
        base_issue_id = find_entity_by_name(base_title)

        if base_issue_id:
            # Link variant to base issue
            create_relationship(base_issue_id, entity_id, 'variant')
            print(f"   🔗 Linked as variant of: {base_title}")
        else:
            # Fallback: link to series if base issue not found
            create_relationship(series_id, entity_id, 'contains')
            print(f"   ⚠️  Base issue not found, linked to series")
    else:
        # Regular issue: link to series
        create_relationship(series_id, entity_id, 'contains')
        print(f"   🔗 Linked to series")

    return entity_id


def main():
    parser = argparse.ArgumentParser(description='Import Marvel comics')
    parser.add_argument('series_title', help='Title of the series to import')
    parser.add_argument('--start-year', type=int, help='Start year to filter series')
    parser.add_argument('--issues', help='Issue numbers to import (e.g., "1" or "1,2,3")')
    parser.add_argument('--series-index', type=int, default=0, help='Which series result to use (0-based)')

    args = parser.parse_args()

    # Verify credentials
    if not MARVEL_PUBLIC_KEY or not MARVEL_PRIVATE_KEY:
        print("❌ Error: Marvel API credentials not found in .env file")
        sys.exit(1)

    print("=" * 70)
    print("MARVEL COMICS IMPORTER")
    print("=" * 70)

    # Parse issue numbers
    issue_numbers = None
    if args.issues:
        issue_numbers = [int(x.strip()) for x in args.issues.split(',')]
        print(f"\n📋 Will import issues: {issue_numbers}")

    try:
        # Find or create franchise
        franchise_id = find_or_create_franchise()

        # Search for series
        series_results = search_series(args.series_title, args.start_year)

        if not series_results:
            print("\n❌ No series found")
            sys.exit(1)

        # Use specified series (default to first)
        if args.series_index >= len(series_results):
            print(f"\n❌ Series index {args.series_index} out of range")
            sys.exit(1)

        selected_series = series_results[args.series_index]
        print(f"\n✅ Selected: {selected_series['title']}")

        # Import the series
        series_entity_id = import_series(selected_series, franchise_id)

        # Get comics from series
        comics = get_series_comics(selected_series['id'], issue_numbers)

        if not comics:
            print("\n⚠️  No comics found matching criteria")
            sys.exit(0)

        # Import each comic
        print("\n" + "=" * 70)
        print(f"IMPORTING {len(comics)} COMICS")
        print("=" * 70)

        for comic in comics:
            import_comic(comic, series_entity_id)

        print("\n" + "=" * 70)
        print("✅ IMPORT COMPLETE")
        print("=" * 70)

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
