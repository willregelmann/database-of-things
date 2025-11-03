#!/usr/bin/env python3
"""
Test script to explore the Marvel Comics API

Authentication requires:
- apikey: public key
- ts: timestamp
- hash: MD5(ts + private_key + public_key)
"""

import os
import sys
import hashlib
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
# Go up 5 levels: scripts → marvel-comics-curator → skills → .claude → database-of-things
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Marvel API configuration
MARVEL_PUBLIC_KEY = os.getenv("MARVEL_COMICS_API_PUBLIC_KEY")
MARVEL_PRIVATE_KEY = os.getenv("MARVEL_COMICS_API_PRIVATE_KEY")
BASE_URL = "https://gateway.marvel.com/v1/public"


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

    # Add authentication parameters
    auth_params = generate_auth_params()
    params.update(auth_params)

    url = f"{BASE_URL}/{endpoint}"

    print(f"\n🔍 Requesting: {url}")
    print(f"   Parameters: {json.dumps({k: v for k, v in params.items() if k not in ['apikey', 'hash']}, indent=2)}")

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def explore_comics():
    """Explore the comics endpoint"""
    print("\n" + "=" * 70)
    print("EXPLORING COMICS ENDPOINT")
    print("=" * 70)

    # Get first 5 comics
    data = make_request("comics", {"limit": 5})

    print(f"\n📊 Total comics available: {data['data']['total']}")
    print(f"   Returned in this request: {data['data']['count']}")

    print("\n📚 Sample Comics:")
    for comic in data['data']['results']:
        print(f"\n  • {comic['title']}")
        print(f"    ID: {comic['id']}")
        print(f"    Issue Number: {comic.get('issueNumber', 'N/A')}")
        print(f"    Format: {comic.get('format', 'N/A')}")
        print(f"    Page Count: {comic.get('pageCount', 'N/A')}")

        # Series info
        if comic.get('series'):
            print(f"    Series: {comic['series']['name']}")

        # Cover image
        if comic.get('thumbnail'):
            thumb = comic['thumbnail']
            print(f"    Image: {thumb['path']}.{thumb['extension']}")

        # Dates
        if comic.get('dates'):
            for date_obj in comic['dates']:
                print(f"    {date_obj['type']}: {date_obj['date']}")


def explore_series():
    """Explore the series endpoint"""
    print("\n" + "=" * 70)
    print("EXPLORING SERIES ENDPOINT")
    print("=" * 70)

    # Get first 5 series
    data = make_request("series", {"limit": 5})

    print(f"\n📊 Total series available: {data['data']['total']}")
    print(f"   Returned in this request: {data['data']['count']}")

    print("\n📖 Sample Series:")
    for series in data['data']['results']:
        print(f"\n  • {series['title']}")
        print(f"    ID: {series['id']}")
        print(f"    Start Year: {series.get('startYear', 'N/A')}")
        print(f"    End Year: {series.get('endYear', 'N/A')}")
        print(f"    Type: {series.get('type', 'N/A')}")

        # Cover image
        if series.get('thumbnail'):
            thumb = series['thumbnail']
            print(f"    Image: {thumb['path']}.{thumb['extension']}")


def explore_characters():
    """Explore the characters endpoint"""
    print("\n" + "=" * 70)
    print("EXPLORING CHARACTERS ENDPOINT")
    print("=" * 70)

    # Get first 5 characters
    data = make_request("characters", {"limit": 5})

    print(f"\n📊 Total characters available: {data['data']['total']}")
    print(f"   Returned in this request: {data['data']['count']}")

    print("\n🦸 Sample Characters:")
    for character in data['data']['results']:
        print(f"\n  • {character['name']}")
        print(f"    ID: {character['id']}")
        if character.get('description'):
            print(f"    Description: {character['description'][:100]}...")

        # Image
        if character.get('thumbnail'):
            thumb = character['thumbnail']
            print(f"    Image: {thumb['path']}.{thumb['extension']}")


def explore_creators():
    """Explore the creators endpoint"""
    print("\n" + "=" * 70)
    print("EXPLORING CREATORS ENDPOINT")
    print("=" * 70)

    # Get first 5 creators
    data = make_request("creators", {"limit": 5})

    print(f"\n📊 Total creators available: {data['data']['total']}")
    print(f"   Returned in this request: {data['data']['count']}")

    print("\n✍️ Sample Creators:")
    for creator in data['data']['results']:
        print(f"\n  • {creator['fullName']}")
        print(f"    ID: {creator['id']}")

        # Image
        if creator.get('thumbnail'):
            thumb = creator['thumbnail']
            print(f"    Image: {thumb['path']}.{thumb['extension']}")


def search_specific_series():
    """Search for a specific series (e.g., Amazing Spider-Man)"""
    print("\n" + "=" * 70)
    print("SEARCHING FOR SPECIFIC SERIES: Amazing Spider-Man")
    print("=" * 70)

    data = make_request("series", {
        "title": "Amazing Spider-Man",
        "limit": 5
    })

    print(f"\n📊 Found {data['data']['total']} matching series")

    print("\n📖 Results:")
    for series in data['data']['results']:
        print(f"\n  • {series['title']}")
        print(f"    ID: {series['id']}")
        print(f"    Years: {series.get('startYear', '?')} - {series.get('endYear', 'Present')}")
        print(f"    Type: {series.get('type', 'N/A')}")


def main():
    print("\n" + "=" * 70)
    print("MARVEL COMICS API EXPLORER")
    print("=" * 70)

    # Verify credentials
    if not MARVEL_PUBLIC_KEY or not MARVEL_PRIVATE_KEY:
        print("❌ Error: Marvel API credentials not found in .env file")
        sys.exit(1)

    print(f"\n✅ Public Key: {MARVEL_PUBLIC_KEY}")
    print(f"✅ Private Key: {'*' * len(MARVEL_PRIVATE_KEY)} (hidden)")

    try:
        # Explore different endpoints
        explore_comics()
        explore_series()
        explore_characters()
        explore_creators()
        search_specific_series()

        print("\n" + "=" * 70)
        print("✅ API EXPLORATION COMPLETE")
        print("=" * 70)
        print("\nAvailable Endpoints:")
        print("  • /comics - Comic issues, collections, graphic novels")
        print("  • /series - Comic series")
        print("  • /characters - Marvel characters")
        print("  • /creators - Writers, artists, editors")
        print("  • /events - Major storyline events")
        print("  • /stories - Story components")

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
