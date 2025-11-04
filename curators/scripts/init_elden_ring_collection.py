"""
Initialize Elden Ring collection structure in the database.

This creates the base collection and category structure before the curator imports items.
"""

import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utilities.supabase_client import SupabaseClient
from rich.console import Console

console = Console()


async def main():
    """Create Elden Ring collection structure."""

    console.print("[bold cyan]🎮 Initializing Elden Ring Collection[/bold cyan]\n")

    client = SupabaseClient()

    try:
        # 1. Create root collection
        console.print("Creating root collection...")
        root_id = await client.create_entity(
            entity_type="collection",
            name="Elden Ring Merchandise",
            attributes={
                "description": "Official Elden Ring merchandise from Bandai Namco Store",
                "source": "https://store.bandainamcoent.eu/games/brands/elden-ring/",
                "brand": "Elden Ring",
                "publisher": "Bandai Namco Entertainment",
                "developer": "FromSoftware",
                "total_products": 66,
                "created_by": "manual"
            }
        )
        console.print(f"  ✅ Created: Elden Ring Merchandise (ID: {str(root_id)[:8]}...)\n")

        # 2. Create category collections
        categories = [
            {
                "name": "Elden Ring Figurines",
                "description": "Vinyl figures, plush toys, and collectible figurines",
                "attributes": {
                    "category": "figurines",
                    "product_types": ["vinyl", "plush", "cute-style", "statue"]
                }
            },
            {
                "name": "Elden Ring Accessories",
                "description": "Blankets, lamps, goblets, and other accessories",
                "attributes": {
                    "category": "accessories",
                    "product_types": ["blanket", "lamp", "goblet", "decoration"]
                }
            },
            {
                "name": "Elden Ring Apparel",
                "description": "Clothing and wearable merchandise",
                "attributes": {
                    "category": "apparel",
                    "product_types": ["jacket", "t-shirt", "hoodie"]
                }
            },
            {
                "name": "Elden Ring Board Games",
                "description": "Board game base sets and expansions",
                "attributes": {
                    "category": "board_games",
                    "product_types": ["base_game", "expansion"]
                }
            }
        ]

        console.print("Creating category collections...")
        for category in categories:
            cat_id = await client.create_entity(
                entity_type="collection",
                name=category["name"],
                attributes={
                    **category["attributes"],
                    "description": category["description"],
                    "parent_collection": "Elden Ring Merchandise"
                }
            )

            # Create relationship: root contains category
            await client.create_relationship(
                from_id=root_id,
                to_id=cat_id,
                relationship_type="contains",
                attributes={
                    "hierarchy_level": 1,
                    "category": category["attributes"]["category"]
                }
            )

            console.print(f"  ✅ Created: {category['name']} (ID: {str(cat_id)[:8]}...)")

        console.print(f"\n[bold green]✅ Collection structure created successfully![/bold green]")
        console.print(f"\n[cyan]Root Collection ID: {root_id}[/cyan]")
        console.print(f"[dim]Ready for curator to import products from Bandai Namco Store[/dim]")

    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())
