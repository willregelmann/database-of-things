#!/usr/bin/env python3
"""
Search Pokémon TCG API

Search for cards and sets without modifying the database.
Useful for exploring the API and finding specific items.
"""

import argparse
import sys
from pathlib import Path
import json

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import PokemonTCGClient


def print_card(card: dict, index: int = None):
    """Pretty print card information"""
    prefix = f"[{index}] " if index is not None else ""

    print(f"{prefix}{card['name']}")
    print(f"  Set: {card['set']['name']} ({card['set']['id']})")
    print(f"  Number: {card.get('number', 'N/A')}/{card['set'].get('printedTotal', 'N/A')}")

    if card.get('rarity'):
        print(f"  Rarity: {card['rarity']}")

    if card.get('artist'):
        print(f"  Artist: {card['artist']}")

    if card.get('hp'):
        print(f"  HP: {card['hp']}")

    if card.get('types'):
        print(f"  Types: {', '.join(card['types'])}")

    print(f"  ID: {card['id']}")
    print()


def print_set(set_data: dict, index: int = None):
    """Pretty print set information"""
    prefix = f"[{index}] " if index is not None else ""

    name = set_data['name']
    series = set_data.get('series', 'N/A')

    print(f"{prefix}{name}")
    print(f"  Series: {series}")
    print(f"  Code: {set_data['id']}")

    if set_data.get('releaseDate'):
        print(f"  Release: {set_data['releaseDate']}")

    if set_data.get('printedTotal'):
        print(f"  Cards: {set_data['printedTotal']}")

    if set_data.get('total'):
        print(f"  Total (with secrets): {set_data['total']}")

    print()


def search_cards(api_client: PokemonTCGClient, query: str, limit: int):
    """Search for cards by name"""
    print(f"🔍 Searching for cards matching: {query}\n")

    cards = api_client.search_cards(query, limit=limit)

    if not cards:
        print("No cards found.")
        return

    print(f"Found {len(cards)} cards:\n")
    for i, card in enumerate(cards, 1):
        print_card(card, index=i)


def search_sets(api_client: PokemonTCGClient, query: str, limit: int):
    """Search for sets by name"""
    print(f"🔍 Searching for sets matching: {query}\n")

    sets = api_client.search_sets(query, limit=limit)

    if not sets:
        print("No sets found.")
        return

    print(f"Found {len(sets)} sets:\n")
    for i, set_data in enumerate(sets, 1):
        print_set(set_data, index=i)


def search_by_artist(api_client: PokemonTCGClient, artist: str, limit: int):
    """Search for cards by artist"""
    print(f"🔍 Searching for cards by artist: {artist}\n")

    response = api_client.get_cards(query=f"artist:{artist}*", page_size=limit)
    cards = response.get("data", [])

    if not cards:
        print("No cards found.")
        return

    print(f"Found {len(cards)} cards:\n")
    for i, card in enumerate(cards, 1):
        print_card(card, index=i)


def search_by_type(api_client: PokemonTCGClient, type_name: str, limit: int):
    """Search for cards by type"""
    print(f"🔍 Searching for {type_name}-type cards\n")

    response = api_client.get_cards(query=f"types:{type_name}", page_size=limit)
    cards = response.get("data", [])

    if not cards:
        print("No cards found.")
        return

    print(f"Found {len(cards)} cards:\n")
    for i, card in enumerate(cards, 1):
        print_card(card, index=i)


def main():
    parser = argparse.ArgumentParser(description="Search Pokémon TCG API")
    parser.add_argument("query_type", choices=["card", "set", "artist", "type"],
                        help="Type of search to perform")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results (default: 10)")

    args = parser.parse_args()

    # Initialize client
    api_client = PokemonTCGClient()

    # Perform search
    if args.query_type == "card":
        search_cards(api_client, args.query, args.limit)
    elif args.query_type == "set":
        search_sets(api_client, args.query, args.limit)
    elif args.query_type == "artist":
        search_by_artist(api_client, args.query, args.limit)
    elif args.query_type == "type":
        search_by_type(api_client, args.query, args.limit)


if __name__ == "__main__":
    main()
