"""
Elden Ring Merchandise Curator

Scrapes and imports Elden Ring merchandise from Bandai Namco Store.
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.config import settings
from core.memory import TieredMemoryManager
from utilities.supabase_client import SupabaseClient
from utilities.rate_limiter import RateLimiter
from utilities.token_budget import TokenBudgetManager
from utilities.progress import ProgressEvent

console = Console()


class EldenRingCurator:
    """Autonomous curator for Elden Ring merchandise."""

    def __init__(self, collection_id: str):
        """
        Initialize the curator.

        Args:
            collection_id: Root collection UUID for Elden Ring Merchandise
        """
        self.collection_id = collection_id
        self.base_url = "https://store.bandainamcoent.eu"
        self.store_path = "/games/brands/elden-ring/"

        # Initialize utilities
        self.db = SupabaseClient()
        self.memory = TieredMemoryManager(curator_id="elden-ring-curator")
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )

        self.rate_limiter = None
        self.token_budget = None

        # Category mapping (will be populated with actual UUIDs)
        self.category_ids = {}

        self.category_keywords = {
            "figurines": ["figurine", "figure", "vinyl", "plush", "statue"],
            "accessories": ["blanket", "lamp", "goblet", "mug", "poster"],
            "apparel": ["jacket", "shirt", "hoodie", "clothing"],
            "board_games": ["board game", "expansion", "cards"]
        }

    async def load_category_ids(self) -> None:
        """Load category collection IDs from database."""
        console.print("[dim]Loading category collection IDs...[/dim]")

        # Query for Elden Ring category collections
        response = self.db.client.table("entities").select("id, name, attributes").eq("type", "collection").like("name", "Elden Ring %").execute()

        for row in response.data:
            category = row.get("attributes", {}).get("category")
            if category:
                self.category_ids[category] = row["id"]
                console.print(f"[dim]  {category}: {row['id'][:8]}...[/dim]")

        console.print(f"[dim]Loaded {len(self.category_ids)} categories[/dim]")

    async def __aenter__(self):
        """Async context manager entry."""
        console.print("[dim]Initializing utilities (rate limiter and token budget disabled for simple scraping)...[/dim]")
        # Skip rate limiter and token budget for simple web scraping
        # They require Redis which is overkill for this task
        self.rate_limiter = None
        self.token_budget = None

        # Load category IDs from database
        await self.load_category_ids()

        console.print("[dim]Curator initialized successfully[/dim]")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.http_client.aclose()
        # Rate limiter and token budget are disabled for simple scraping
        # if self.rate_limiter:
        #     await self.rate_limiter.close()
        # if self.token_budget:
        #     await self.token_budget.close()

    async def fetch_page(self, url: str) -> str:
        """
        Fetch a page with rate limiting.

        Args:
            url: URL to fetch

        Returns:
            HTML content
        """
        # Simple rate limiting: 1 request every 2 seconds
        await asyncio.sleep(2)

        console.print(f"[dim]Fetching: {url}[/dim]")
        response = await self.http_client.get(url)
        response.raise_for_status()
        return response.text

    def parse_product_listing(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse product listing page.

        Args:
            html: HTML content

        Returns:
            List of product data
        """
        soup = BeautifulSoup(html, "html.parser")
        products = []

        # Find product cards - they're <article class="card"> elements
        product_cards = soup.find_all("article", class_="card")

        console.print(f"[cyan]Found {len(product_cards)} product cards[/cyan]")

        for card in product_cards:
            try:
                product = self._extract_product_from_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to parse product card: {e}[/yellow]")

        return products

    def _extract_product_from_card(self, card) -> Optional[Dict[str, Any]]:
        """Extract product data from a card element."""

        # Extract name from card-title h2
        name_elem = card.find("h2", class_="card-title")
        if not name_elem:
            return None

        # Get both the brand and edition parts
        brand_elem = name_elem.find("a")
        edition_elem = name_elem.find("div", class_="card-edition")

        if not brand_elem and not edition_elem:
            return None

        brand = brand_elem.get_text(strip=True) if brand_elem else "ELDEN RING"
        edition = edition_elem.get_text(strip=True) if edition_elem else ""
        name = f"{brand} - {edition}" if edition else brand

        # Extract URL from card-figure__link
        link_elem = card.find("a", class_="card-figure__link")
        if not link_elem:
            return None

        url = link_elem["href"]

        # Extract price from data-productprice attribute
        price = None
        if link_elem and link_elem.get("data-productprice"):
            price_text = link_elem["data-productprice"]
            # Extract number from price (e.g., "69,99 €" -> "69.99")
            price_match = re.search(r'([\d.,]+)', price_text)
            if price_match:
                price = price_match.group(1).replace(',', '.')

        # Extract image from card-image img
        img_elem = card.find("img", class_="card-image")
        image_url = None
        if img_elem:
            # Use the highest resolution from srcset
            srcset = img_elem.get("data-srcset", "")
            if srcset:
                # Get the highest resolution URL (last one in srcset)
                urls = [u.strip().split()[0] for u in srcset.split(',')]
                image_url = urls[-1] if urls else None
            if not image_url:
                image_url = img_elem.get("src")

        # Extract SKU and category
        sku_elem = card.find("input", class_="product_sku")
        category_elem = card.find("input", class_="product_category")

        sku = sku_elem["value"] if sku_elem else None
        category = category_elem["value"] if category_elem else None

        # Check for pre-order badge
        availability = "in_stock"
        preorder_badge = card.find("div", class_="pre-order")
        if preorder_badge:
            availability = "preorder"

        return {
            "name": name,
            "url": url,
            "price": price,
            "image_url": image_url,
            "availability": availability,
            "sku": sku,
            "category": category
        }

    def categorize_product(self, product_name: str, product_desc: str = "") -> str:
        """
        Determine product category based on name and description.

        Args:
            product_name: Product name
            product_desc: Product description

        Returns:
            Category name
        """
        text = f"{product_name} {product_desc}".lower()

        for category, keywords in self.category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category

        return "accessories"  # Default

    async def import_product(self, product: Dict[str, Any], category_id: str) -> str:
        """
        Import a single product into the database.

        Args:
            product: Product data
            category_id: Category collection ID

        Returns:
            Product entity ID
        """
        # Create product entity
        product_id = await self.db.create_entity(
            entity_type="product",
            name=product["name"],
            attributes={
                "url": product["url"],
                "price": product.get("price"),
                "price_currency": "EUR",
                "availability": product.get("availability"),
                "sku": product.get("sku"),
                "store_category": product.get("category"),
                "source": "bandai_namco_store",
                "brand": "Elden Ring",
                "scraped_at": "2025-11-03"
            },
            image_url=product.get("image_url")
        )

        # Create relationship to category
        await self.db.create_relationship(
            from_id=category_id,
            to_id=product_id,
            relationship_type="contains"
        )

        return str(product_id)

    async def discover_and_import(self, max_pages: int = 4) -> Dict[str, Any]:
        """
        Discover and import all Elden Ring products.

        Args:
            max_pages: Maximum number of pages to scrape

        Returns:
            Import statistics
        """
        console.print("[bold cyan]🎮 Starting Elden Ring Curator[/bold cyan]\n")
        console.print(f"[dim]Will scrape up to {max_pages} pages[/dim]\n")

        stats = {
            "products_found": 0,
            "products_imported": 0,
            "products_skipped": 0,
            "categories": {}
        }

        try:
            # Fetch all pages
            console.print("[dim]Beginning page scraping...[/dim]")
            for page in range(1, max_pages + 1):
                page_url = f"{self.base_url}{self.store_path}?page={page}"

                console.print(f"\n[bold]Page {page}/{max_pages}[/bold]")

                try:
                    html = await self.fetch_page(page_url)
                    products = self.parse_product_listing(html)

                    if not products:
                        console.print("[yellow]No products found on this page, stopping[/yellow]")
                        break

                    stats["products_found"] += len(products)

                    # Import each product
                    for product in products:
                        try:
                            # Categorize
                            category = self.categorize_product(product["name"])

                            if category not in stats["categories"]:
                                stats["categories"][category] = 0

                            # Get category ID
                            category_id = self.category_ids.get(category)
                            if not category_id:
                                console.print(f"  • {product['name'][:50]}... [yellow]SKIP: Unknown category {category}[/yellow]")
                                stats["products_skipped"] += 1
                                continue

                            console.print(f"  • {product['name'][:50]}... [{category}]")

                            # Import product
                            product_id = await self.import_product(product, category_id)
                            stats["products_imported"] += 1
                            stats["categories"][category] += 1

                            console.print(f"    ✅ Imported: {product_id[:8]}...")

                        except Exception as e:
                            console.print(f"[red]    ❌ Error importing: {e}[/red]")
                            stats["products_skipped"] += 1

                except Exception as e:
                    console.print(f"[red]Error fetching page {page}: {e}[/red]")
                    break

            # Display stats
            console.print(f"\n[bold green]✅ Import Complete[/bold green]")
            console.print(f"\n[cyan]Statistics:[/cyan]")
            console.print(f"  Products Found: {stats['products_found']}")
            console.print(f"  Products Imported: {stats['products_imported']}")
            console.print(f"  Products Skipped: {stats['products_skipped']}")
            console.print(f"\n[cyan]By Category:[/cyan]")
            for category, count in stats["categories"].items():
                console.print(f"  {category}: {count}")

        except Exception as e:
            console.print(f"[bold red]❌ Fatal error: {e}[/bold red]")
            raise

        return stats


async def main():
    """Run the Elden Ring curator."""
    # Use the root collection ID we created
    collection_id = "c427fd49-97d1-427b-8126-cee2042fef63"

    async with EldenRingCurator(collection_id) as curator:
        await curator.discover_and_import(max_pages=1)  # Start with 1 page for testing


if __name__ == "__main__":
    asyncio.run(main())
