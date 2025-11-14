#!/usr/bin/env python3
"""
Seed sample collectibles data for local development.

Creates:
- 5 collections (Pokemon TCG, Power Rangers Toys, Marvel Comics, Video Games, LEGO Sets)
- ~6 items per collection
- Variants demonstrating the variants table (1st edition cards, regional variants, etc.)
- Components demonstrating the components table (Megazord Dinozords, LEGO pieces, etc.)
- Relationships showing collection nesting
"""

import os
import sys
from supabase import create_client, Client

# Get Supabase credentials from environment or use defaults
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_SERVICE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
)


def create_supabase_client() -> Client:
    """Create Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def create_entity(supabase: Client, entity_data: dict) -> str:
    """Create an entity and return its ID."""
    result = supabase.table("entities").insert(entity_data).execute()
    return result.data[0]["id"]


def create_relationship(supabase: Client, from_id: str, to_id: str, rel_type: str = "contains", order: int = None):
    """Create a relationship between entities."""
    rel_data = {
        "from_id": from_id,
        "to_id": to_id,
        "type": rel_type
    }
    if order is not None:
        rel_data["order"] = order

    supabase.table("relationships").insert(rel_data).execute()


def create_variant(supabase: Client, variant_of: str, name: str, attributes: dict = None):
    """Create a variant of an entity."""
    variant_data = {
        "variant_of": variant_of,
        "name": name,
        "attributes": attributes or {}
    }
    result = supabase.table("variants").insert(variant_data).execute()
    return result.data[0]["id"]


def create_component(supabase: Client, component_of: str, name: str, quantity: int = 1, order: int = None, attributes: dict = None):
    """Create a component of an entity."""
    component_data = {
        "component_of": component_of,
        "name": name,
        "quantity": quantity,
        "attributes": attributes or {}
    }
    if order is not None:
        component_data["order"] = order

    result = supabase.table("components").insert(component_data).execute()
    return result.data[0]["id"]


def seed_pokemon_tcg(supabase: Client) -> str:
    """Seed Pokemon TCG collection."""
    print("\n📦 Creating Pokemon TCG collection...")

    # Create collection
    collection_id = create_entity(supabase, {
        "name": "Pokemon Trading Card Game",
        "type": "collection",
        "year": 1996,
        "country": "US",
        "language": "en",
        "source_url": "https://www.pokemon.com/us/pokemon-tcg/",
        "attributes": {
            "description": "The Pokemon Trading Card Game collectible card game"
        }
    })

    # Create Base Set sub-collection
    base_set_id = create_entity(supabase, {
        "name": "Base Set",
        "type": "collection",
        "year": 1999,
        "language": "en",
        "source_url": "https://bulbapedia.bulbagarden.net/wiki/Base_Set_(TCG)",
        "attributes": {
            "set_code": "base1",
            "total_cards": 102
        }
    })
    create_relationship(supabase, collection_id, base_set_id, order=1)

    # Create cards
    cards = [
        {"name": "Charizard", "hp": 120, "card_number": "4/102", "rarity": "Rare Holo"},
        {"name": "Blastoise", "hp": 100, "card_number": "2/102", "rarity": "Rare Holo"},
        {"name": "Venusaur", "hp": 100, "card_number": "15/102", "rarity": "Rare Holo"},
        {"name": "Pikachu", "hp": 40, "card_number": "58/102", "rarity": "Common"},
    ]

    card_ids = {}
    for i, card_data in enumerate(cards):
        card_id = create_entity(supabase, {
            "name": card_data["name"],
            "type": "card",
            "year": 1999,
            "language": "en",
            "source_url": f"https://bulbapedia.bulbagarden.net/wiki/{card_data['name']}",
            "external_ids": {"card_number": card_data["card_number"]},
            "attributes": {
                "hp": card_data["hp"],
                "rarity": card_data["rarity"],
                "set": "Base Set"
            }
        })
        create_relationship(supabase, base_set_id, card_id, order=i+1)
        card_ids[card_data["name"]] = card_id
        print(f"  ✓ Created {card_data['name']}")

    # Create variants for Charizard (shadowless, 1st edition)
    print("  📝 Creating Charizard variants...")
    create_variant(supabase, card_ids["Charizard"], "Charizard (Shadowless)", {
        "variant_type": "shadowless",
        "description": "Shadowless version from early print run"
    })
    create_variant(supabase, card_ids["Charizard"], "Charizard (1st Edition)", {
        "variant_type": "1st_edition",
        "description": "First edition print with stamp"
    })

    return collection_id


def seed_power_rangers(supabase: Client) -> str:
    """Seed Power Rangers Toys collection."""
    print("\n🦖 Creating Power Rangers Toys collection...")

    collection_id = create_entity(supabase, {
        "name": "Power Rangers Toys",
        "type": "collection",
        "year": 1993,
        "country": "US",
        "language": "en",
        "source_url": "https://powerrangers.fandom.com/wiki/Toys",
        "attributes": {
            "description": "Action figures and toys from the Power Rangers franchise",
            "manufacturer": "Bandai"
        }
    })

    # Create Mighty Morphin sub-collection
    mmpr_id = create_entity(supabase, {
        "name": "Mighty Morphin Power Rangers",
        "type": "collection",
        "year": 1993,
        "language": "en",
        "attributes": {
            "series": "Season 1",
            "manufacturer": "Bandai"
        }
    })
    create_relationship(supabase, collection_id, mmpr_id, order=1)

    # Create toys
    toys = [
        {"name": "Red Ranger Action Figure", "character": "Jason Lee Scott"},
        {"name": "Blue Ranger Action Figure", "character": "Billy Cranston"},
        {"name": "Pink Ranger Action Figure", "character": "Kimberly Hart"},
        {"name": "Megazord", "character": "Megazord", "type": "Zord"},
    ]

    toy_ids = {}
    for i, toy_data in enumerate(toys):
        toy_id = create_entity(supabase, {
            "name": toy_data["name"],
            "type": "figure",
            "year": 1993,
            "language": "en",
            "attributes": {
                "character": toy_data["character"],
                "series": "Mighty Morphin",
                "manufacturer": "Bandai",
                "product_type": toy_data.get("type", "Action Figure")
            }
        })
        create_relationship(supabase, mmpr_id, toy_id, order=i+1)
        toy_ids[toy_data["name"]] = toy_id
        print(f"  ✓ Created {toy_data['name']}")

    # Create variants for Red Ranger (metallic, talking)
    print("  📝 Creating Red Ranger variants...")
    create_variant(supabase, toy_ids["Red Ranger Action Figure"], "Red Ranger (Metallic)", {
        "variant_type": "metallic",
        "description": "Metallic finish variant"
    })
    create_variant(supabase, toy_ids["Red Ranger Action Figure"], "Red Ranger (Talking)", {
        "variant_type": "talking",
        "description": "Electronic talking action figure",
        "features": ["voice_chip", "batteries_included"]
    })

    # Create components for Megazord (individual Dinozords)
    print("  🔧 Creating Megazord components...")
    create_component(supabase, toy_ids["Megazord"], "Tyrannosaurus Dinozord", quantity=1, order=1, attributes={
        "color": "red",
        "pilot": "Jason Lee Scott",
        "forms": "torso_and_head"
    })
    create_component(supabase, toy_ids["Megazord"], "Mastodon Dinozord", quantity=1, order=2, attributes={
        "color": "black",
        "pilot": "Zack Taylor",
        "forms": "right_arm"
    })
    create_component(supabase, toy_ids["Megazord"], "Triceratops Dinozord", quantity=1, order=3, attributes={
        "color": "blue",
        "pilot": "Billy Cranston",
        "forms": "left_leg"
    })
    create_component(supabase, toy_ids["Megazord"], "Saber-Toothed Tiger Dinozord", quantity=1, order=4, attributes={
        "color": "yellow",
        "pilot": "Trini Kwan",
        "forms": "right_leg"
    })
    create_component(supabase, toy_ids["Megazord"], "Pterodactyl Dinozord", quantity=1, order=5, attributes={
        "color": "pink",
        "pilot": "Kimberly Hart",
        "forms": "chest_plate"
    })
    create_component(supabase, toy_ids["Megazord"], "Power Sword", quantity=1, order=6, attributes={
        "type": "weapon",
        "description": "Megazord's primary weapon"
    })

    return collection_id


def seed_marvel_comics(supabase: Client) -> str:
    """Seed Marvel Comics collection."""
    print("\n🦸 Creating Marvel Comics collection...")

    collection_id = create_entity(supabase, {
        "name": "Marvel Comics",
        "type": "collection",
        "year": 1939,
        "country": "US",
        "language": "en",
        "source_url": "https://www.marvel.com/comics",
        "attributes": {
            "description": "Marvel Comics publications",
            "publisher": "Marvel Comics"
        }
    })

    # Create Amazing Spider-Man series
    spiderman_id = create_entity(supabase, {
        "name": "The Amazing Spider-Man",
        "type": "collection",
        "year": 1963,
        "language": "en",
        "attributes": {
            "series_type": "ongoing",
            "publisher": "Marvel Comics"
        }
    })
    create_relationship(supabase, collection_id, spiderman_id, order=1)

    # Create comics
    comics = [
        {"issue": 1, "title": "Spider-Man!", "year": 1963},
        {"issue": 14, "title": "The Grotesque Adventure of the Green Goblin", "year": 1964},
        {"issue": 50, "title": "Spider-Man No More!", "year": 1967},
        {"issue": 121, "title": "The Night Gwen Stacy Died", "year": 1973},
    ]

    comic_ids = {}
    for i, comic_data in enumerate(comics):
        comic_id = create_entity(supabase, {
            "name": f"The Amazing Spider-Man #{comic_data['issue']}",
            "type": "comic",
            "year": comic_data["year"],
            "language": "en",
            "external_ids": {"issue_number": comic_data["issue"]},
            "attributes": {
                "series": "The Amazing Spider-Man",
                "issue_number": comic_data["issue"],
                "title": comic_data["title"],
                "publisher": "Marvel Comics"
            }
        })
        create_relationship(supabase, spiderman_id, comic_id, order=i+1)
        comic_ids[comic_data["issue"]] = comic_id
        print(f"  ✓ Created Issue #{comic_data['issue']}")

    # Create variants for ASM #1 (2nd printing, reprint)
    print("  📝 Creating ASM #1 variants...")
    create_variant(supabase, comic_ids[1], "The Amazing Spider-Man #1 (2nd Printing)", {
        "variant_type": "2nd_printing",
        "print_date": "1963-08"
    })

    return collection_id


def seed_video_games(supabase: Client) -> str:
    """Seed Video Games collection."""
    print("\n🎮 Creating Video Games collection...")

    collection_id = create_entity(supabase, {
        "name": "Video Games",
        "type": "collection",
        "year": 1972,
        "country": "US",
        "language": "en",
        "attributes": {
            "description": "Video game software and hardware"
        }
    })

    # Create Game Boy Games sub-collection
    gameboy_id = create_entity(supabase, {
        "name": "Game Boy Games",
        "type": "collection",
        "year": 1989,
        "language": "en",
        "attributes": {
            "platform": "Game Boy",
            "manufacturer": "Nintendo"
        }
    })
    create_relationship(supabase, collection_id, gameboy_id, order=1)

    # Create games
    games = [
        {"name": "Pokemon Red Version", "year": 1996, "publisher": "Nintendo", "developer": "Game Freak"},
        {"name": "Pokemon Blue Version", "year": 1996, "publisher": "Nintendo", "developer": "Game Freak"},
        {"name": "The Legend of Zelda: Link's Awakening", "year": 1993, "publisher": "Nintendo", "developer": "Nintendo EAD"},
        {"name": "Tetris", "year": 1989, "publisher": "Nintendo", "developer": "Bullet-Proof Software"},
    ]

    game_ids = {}
    for i, game_data in enumerate(games):
        game_id = create_entity(supabase, {
            "name": game_data["name"],
            "type": "video_game",
            "year": game_data["year"],
            "language": "en",
            "attributes": {
                "platform": "Game Boy",
                "publisher": game_data["publisher"],
                "developer": game_data["developer"],
                "region": "North America"
            }
        })
        create_relationship(supabase, gameboy_id, game_id, order=i+1)
        game_ids[game_data["name"]] = game_id
        print(f"  ✓ Created {game_data['name']}")

    # Create variants for Pokemon Red (Japanese version)
    print("  📝 Creating Pokemon Red variants...")
    create_variant(supabase, game_ids["Pokemon Red Version"], "Pocket Monsters Aka (Japan)", {
        "variant_type": "regional",
        "region": "Japan",
        "language": "ja",
        "release_date": "1996-02-27"
    })

    return collection_id


def seed_lego_sets(supabase: Client) -> str:
    """Seed LEGO Sets collection."""
    print("\n🧱 Creating LEGO Sets collection...")

    collection_id = create_entity(supabase, {
        "name": "LEGO Sets",
        "type": "collection",
        "year": 1949,
        "country": "DK",
        "source_url": "https://www.lego.com",
        "attributes": {
            "description": "LEGO building sets and themes"
        }
    })

    # Create Space theme sub-collection
    space_id = create_entity(supabase, {
        "name": "LEGO Space",
        "type": "collection",
        "year": 1978,
        "language": "en",
        "attributes": {
            "theme": "Space"
        }
    })
    create_relationship(supabase, collection_id, space_id, order=1)

    # Create a detailed LEGO set with components
    galaxy_explorer_id = create_entity(supabase, {
        "name": "Galaxy Explorer",
        "type": "lego_set",
        "year": 1979,
        "language": "en",
        "source_url": "https://rebrickable.com/sets/497-1/galaxy-explorer/",
        "external_ids": {"rebrickable_set_num": "497-1"},
        "attributes": {
            "set_number": "497",
            "pieces": 325,
            "theme": "Classic Space",
            "minifigures": 4
        }
    })
    create_relationship(supabase, space_id, galaxy_explorer_id, order=1)
    print(f"  ✓ Created Galaxy Explorer")

    # Create components for Galaxy Explorer
    print("  🔧 Creating Galaxy Explorer components...")
    create_component(supabase, galaxy_explorer_id, "Instruction Booklet", quantity=1, order=1, attributes={
        "type": "instructions",
        "pages": 32,
        "condition_sensitive": True
    })
    create_component(supabase, galaxy_explorer_id, "Classic Space Minifigures", quantity=4, order=2, attributes={
        "type": "minifigure",
        "color_scheme": "blue_and_grey",
        "helmet_type": "classic_space"
    })
    create_component(supabase, galaxy_explorer_id, "Blue Windscreen 6x6x2", quantity=1, order=3, attributes={
        "type": "brick",
        "part_number": "2418",
        "rare": True
    })
    create_component(supabase, galaxy_explorer_id, "Trans-Yellow Plates", quantity=6, order=4, attributes={
        "type": "brick",
        "color": "trans-yellow",
        "note": "Used for engines"
    })

    # Create another set
    moonbase_id = create_entity(supabase, {
        "name": "Lunar MPV Vehicle",
        "type": "lego_set",
        "year": 1986,
        "language": "en",
        "external_ids": {"rebrickable_set_num": "6750-1"},
        "attributes": {
            "set_number": "6750",
            "pieces": 38,
            "theme": "Classic Space"
        }
    })
    create_relationship(supabase, space_id, moonbase_id, order=2)
    print(f"  ✓ Created Lunar MPV Vehicle")

    return collection_id


def main():
    """Main seeding function."""
    print("🌱 Seeding sample collectibles data...")
    print(f"📍 Connecting to: {SUPABASE_URL}")

    try:
        supabase = create_supabase_client()

        # Seed all collections
        pokemon_id = seed_pokemon_tcg(supabase)
        rangers_id = seed_power_rangers(supabase)
        marvel_id = seed_marvel_comics(supabase)
        games_id = seed_video_games(supabase)
        lego_id = seed_lego_sets(supabase)

        print("\n" + "="*60)
        print("✅ Seeding complete!")
        print("="*60)
        print(f"""
📊 Summary:
  - 5 top-level collections created
  - 5 sub-collections created
  - 18 items created
  - 6 variants created
  - 10 components created

🔍 Try these queries:

  # View all collections
  SELECT name, type, year FROM entities WHERE type = 'collection' ORDER BY year;

  # View items with variants
  SELECT e.name, e.type, COUNT(v.id) as variant_count
  FROM entities e
  LEFT JOIN variants v ON v.variant_of = e.id
  WHERE e.type IN ('card', 'figure', 'comic', 'video_game')
  GROUP BY e.id, e.name, e.type
  HAVING COUNT(v.id) > 0;

  # Browse variants
  SELECT v.name, e.name as base_item, v.attributes
  FROM variants v
  JOIN entities e ON v.variant_of = e.id;

  # View items with components
  SELECT e.name, COUNT(c.id) as component_count
  FROM entities e
  LEFT JOIN components c ON c.component_of = e.id
  GROUP BY e.id, e.name
  HAVING COUNT(c.id) > 0;

  # Browse components with quantities
  SELECT e.name as parent_item, c.name as component, c.quantity, c.attributes
  FROM components c
  JOIN entities e ON c.component_of = e.id
  ORDER BY e.name, c."order";

🌐 GraphQL Explorer:
  http://127.0.0.1:54323
""")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
