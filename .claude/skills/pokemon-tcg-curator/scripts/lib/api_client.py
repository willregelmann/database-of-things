"""
Pokémon TCG API Client

Handles communication with pokemontcg.io API using the official SDK:
- Authentication
- Rate limiting
- Error handling
- Data fetching
"""

import os
from typing import Dict, List, Optional
from pokemontcgsdk import Card, Set, RestClient


class PokemonTCGClient:
    """Client for pokemontcg.io API using official SDK"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize API client

        Args:
            api_key: Optional API key (will read from env if not provided)
        """
        self.api_key = api_key or os.getenv("POKEMON_TCG_API_KEY")
        if self.api_key:
            RestClient.configure(self.api_key)

    def _set_to_dict(self, set_obj: Set) -> Dict:
        """
        Convert SDK Set object to dictionary

        Args:
            set_obj: Set object from SDK

        Returns:
            Dictionary representation
        """
        return {
            "id": set_obj.id,
            "name": set_obj.name,
            "series": getattr(set_obj, "series", None),
            "printedTotal": getattr(set_obj, "printedTotal", None),
            "total": getattr(set_obj, "total", None),
            "releaseDate": getattr(set_obj, "releaseDate", None),
            "updatedAt": getattr(set_obj, "updatedAt", None),
            "images": {
                "symbol": getattr(set_obj.images, "symbol", None) if hasattr(set_obj, "images") else None,
                "logo": getattr(set_obj.images, "logo", None) if hasattr(set_obj, "images") else None,
            } if hasattr(set_obj, "images") else {}
        }

    def _card_to_dict(self, card_obj: Card) -> Dict:
        """
        Convert SDK Card object to dictionary

        Args:
            card_obj: Card object from SDK

        Returns:
            Dictionary representation
        """
        card_dict = {
            "id": card_obj.id,
            "name": card_obj.name,
            "number": getattr(card_obj, "number", None),
            "rarity": getattr(card_obj, "rarity", None),
            "artist": getattr(card_obj, "artist", None),
            "hp": getattr(card_obj, "hp", None),
            "types": getattr(card_obj, "types", []),
            "supertype": getattr(card_obj, "supertype", None),
            "subtypes": getattr(card_obj, "subtypes", []),
        }

        # Add set info
        if hasattr(card_obj, "set"):
            card_dict["set"] = {
                "id": card_obj.set.id,
                "name": card_obj.set.name,
                "series": getattr(card_obj.set, "series", None),
                "printedTotal": getattr(card_obj.set, "printedTotal", None),
                "total": getattr(card_obj.set, "total", None),
                "releaseDate": getattr(card_obj.set, "releaseDate", None),
            }

        # Add images
        if hasattr(card_obj, "images"):
            card_dict["images"] = {
                "small": getattr(card_obj.images, "small", None),
                "large": getattr(card_obj.images, "large", None),
            }

        return card_dict

    def get_sets(self, page: int = 1, page_size: int = 250) -> Dict:
        """
        Fetch sets from API

        Args:
            page: Page number (1-indexed)
            page_size: Results per page (max 250)

        Returns:
            {
                "data": [list of sets],
                "page": current page,
                "pageSize": results per page,
                "count": results in this response,
                "totalCount": total sets available
            }
        """
        # SDK doesn't support pagination directly, so we fetch all and paginate manually
        all_sets = Set.all()
        sets_dicts = [self._set_to_dict(s) for s in all_sets]

        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_sets = sets_dicts[start_idx:end_idx]

        return {
            "data": page_sets,
            "page": page,
            "pageSize": page_size,
            "count": len(page_sets),
            "totalCount": len(sets_dicts)
        }

    def get_set_by_code(self, set_code: str) -> Optional[Dict]:
        """
        Fetch a specific set by its code

        Args:
            set_code: Set code (e.g., "swsh4", "base1")

        Returns:
            Set data or None if not found
        """
        try:
            set_obj = Set.find(set_code)
            return self._set_to_dict(set_obj)
        except Exception:
            return None

    def get_cards(self, query: Optional[str] = None, page: int = 1, page_size: int = 250) -> Dict:
        """
        Fetch cards from API

        Args:
            query: Optional query string (e.g., "set.id:swsh4")
            page: Page number (1-indexed)
            page_size: Results per page (max 250)

        Returns:
            {
                "data": [list of cards],
                "page": current page,
                "pageSize": results per page,
                "count": results in this response,
                "totalCount": total cards matching query
            }
        """
        # Build query parameters
        params = {
            "page": page,
            "pageSize": min(page_size, 250)
        }
        if query:
            params["q"] = query

        # Use SDK's where method
        cards = Card.where(**params)
        cards_dicts = [self._card_to_dict(c) for c in cards]

        return {
            "data": cards_dicts,
            "page": page,
            "pageSize": page_size,
            "count": len(cards_dicts),
            "totalCount": len(cards_dicts)  # SDK doesn't provide total count easily
        }

    def get_cards_for_set(self, set_code: str) -> List[Dict]:
        """
        Fetch all cards for a specific set

        Args:
            set_code: Set code (e.g., "swsh4", "base1")

        Returns:
            List of all cards in the set
        """
        all_cards = []
        page = 1

        while True:
            response = self.get_cards(query=f"set.id:{set_code}", page=page, page_size=250)
            cards = response.get("data", [])

            if not cards:
                break

            all_cards.extend(cards)

            # If we got less than page size, we're done
            if len(cards) < 250:
                break

            page += 1

        return all_cards

    def search_cards(self, name: str, limit: int = 50) -> List[Dict]:
        """
        Search for cards by name

        Args:
            name: Card name to search for
            limit: Maximum results to return

        Returns:
            List of matching cards
        """
        response = self.get_cards(query=f"name:{name}*", page_size=limit)
        return response.get("data", [])

    def search_sets(self, name: str, limit: int = 50) -> List[Dict]:
        """
        Search for sets by name

        Args:
            name: Set name to search for
            limit: Maximum results to return

        Returns:
            List of matching sets
        """
        # Fetch all sets and filter by name
        all_sets = Set.all()
        matching_sets = [
            self._set_to_dict(s) for s in all_sets
            if name.lower() in s.name.lower()
        ]

        return matching_sets[:limit]


if __name__ == "__main__":
    # Quick test
    client = PokemonTCGClient()

    print("Testing API client with SDK...")
    print("\nFetching first 5 sets:")
    response = client.get_sets(page_size=5)
    for set_data in response.get("data", []):
        print(f"  - {set_data['name']} ({set_data['id']})")

    print("\nSearching for 'Charizard' cards:")
    cards = client.search_cards("Charizard", limit=3)
    for card in cards:
        print(f"  - {card['name']} ({card.get('set', {}).get('name', 'Unknown')})")
