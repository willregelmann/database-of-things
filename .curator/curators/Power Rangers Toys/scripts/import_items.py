#!/usr/bin/env python3
"""Import fetched Power Rangers toys into Supabase."""

import argparse
import json
import os
import sys
import uuid
import io
from pathlib import Path
from typing import Dict, Optional, Tuple

# Auto-install dependencies if missing
try:
    from supabase import create_client, Client
    import requests
    from PIL import Image
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "supabase", "requests", "pillow"])
    from supabase import create_client, Client
    import requests
    from PIL import Image

# Add lib directory to path for shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))
from image_utils import ImageLocalizer
from embedding_utils import EmbeddingGenerator

FETCHED_FILE = "fetched_data.json"
FRANCHISE_ID = "d183e3a9-4eb7-40a5-b264-526b9a03ec30"  # Power Rangers franchise
POWER_RANGERS_TOYS_ID = "cf968bae-4353-4e54-95b1-87f41e5f9994"  # Power Rangers Toys collection


class ToyImporter:
    """Import Power Rangers toys to Supabase."""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.series_cache = {}  # Cache series entities to avoid repeated lookups
        self.toy_line_cache = {}  # Cache toy line entities
        self.image_localizer = ImageLocalizer(supabase)  # For image downloads
        self.embedding_generator = EmbeddingGenerator()  # For semantic search
        self.session = requests.Session()  # Reuse HTTP connections
        self.image_results = []  # Track image validation results (for dry run)

    def get_or_create_series(self, series_name: str, year: Optional[int] = None) -> str:
        """Get or create a series entity (TV show), return its ID."""
        if not series_name:
            return FRANCHISE_ID  # Default to franchise if no series specified

        # Check cache
        cache_key = f"{series_name}_{year}"
        if cache_key in self.series_cache:
            return self.series_cache[cache_key]

        # Check if series exists
        query = self.supabase.table("entities").select("id").eq("name", series_name).eq("type", "collection")

        if year:
            query = query.eq("year", year)

        result = query.execute()

        if result.data:
            series_id = result.data[0]["id"]
            self.series_cache[cache_key] = series_id
            return series_id

        # Create series as a collection
        series_data = {
            "name": series_name,
            "type": "collection",
            "year": year,
            "attributes": {}
        }

        result = self.supabase.table("entities").insert(series_data).execute()
        series_id = result.data[0]["id"]

        # Link series to Power Rangers Toys collection
        self.supabase.table("relationships").insert({
            "from_id": POWER_RANGERS_TOYS_ID,
            "to_id": series_id,
            "type": "contains"
        }).execute()

        self.series_cache[cache_key] = series_id
        print(f"  Created series: {series_name}")
        return series_id

    def get_or_create_toy_line(self, toy_line_data: Dict, series_id: str) -> str:
        """Get or create a toy line (assortment) entity, return its ID."""
        assortment_number = toy_line_data.get("assortment_number")
        name = toy_line_data.get("name")

        if not assortment_number:
            return series_id  # Fallback to series if no toy line

        # Check cache
        if assortment_number in self.toy_line_cache:
            return self.toy_line_cache[assortment_number]

        # Check if toy line exists
        result = self.supabase.table("entities").select("id").eq(
            "external_ids->>grnrngr_assortment", assortment_number
        ).execute()

        if result.data:
            toy_line_id = result.data[0]["id"]
            self.toy_line_cache[assortment_number] = toy_line_id
            return toy_line_id

        # Create toy line collection
        toy_line_entity = {
            "name": name,
            "type": "collection",
            "attributes": {
                "manufacturer": toy_line_data.get("manufacturer")
            },
            "external_ids": {
                "grnrngr_assortment": assortment_number
            },
            "source_url": toy_line_data.get("source_url")
        }

        # Remove None values
        toy_line_entity["attributes"] = {k: v for k, v in toy_line_entity["attributes"].items() if v is not None}

        result = self.supabase.table("entities").insert(toy_line_entity).execute()
        toy_line_id = result.data[0]["id"]

        # Link toy line to both Power Rangers Toys collection AND series
        # Link to Power Rangers Toys collection
        self.supabase.table("relationships").insert({
            "from_id": POWER_RANGERS_TOYS_ID,
            "to_id": toy_line_id,
            "type": "contains"
        }).execute()

        # Link to series (TV show)
        self.supabase.table("relationships").insert({
            "from_id": series_id,
            "to_id": toy_line_id,
            "type": "contains"
        }).execute()

        self.toy_line_cache[assortment_number] = toy_line_id
        print(f"    Created toy line: {name}")
        return toy_line_id

    def check_toy_exists(self, item_number: str) -> Optional[str]:
        """Check if toy already exists using item number (grnrngr external ID)."""
        if not item_number:
            return None

        # Query for entity with matching grnrngr item number
        result = self.supabase.table("entities").select("id").eq(
            "external_ids->>grnrngr", item_number
        ).execute()

        if result.data:
            return result.data[0]["id"]

        return None

    def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL. Returns image bytes or None on failure."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"    ⚠️  Failed to download image: {e}")
            return None

    def generate_thumbnail(self, image_bytes: bytes, size: int = 300) -> Optional[bytes]:
        """Generate WebP thumbnail from image bytes. Returns thumbnail bytes or None on failure."""
        try:
            # Open image
            img = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if necessary (handles PNG with transparency, etc.)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize maintaining aspect ratio
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            # Save as WebP
            output = io.BytesIO()
            img.save(output, format='WEBP', quality=85)
            return output.getvalue()
        except Exception as e:
            print(f"    ⚠️  Failed to generate thumbnail: {e}")
            return None

    def upload_to_storage(self, file_bytes: bytes, bucket_path: str, content_type: str = 'image/jpeg') -> bool:
        """Upload file to Supabase storage. Returns True on success."""
        try:
            self.supabase.storage.from_('images').upload(
                bucket_path,
                file_bytes,
                file_options={"content-type": content_type}
            )
            return True
        except Exception as e:
            # Check if file already exists (error code 409)
            if '409' in str(e) or 'already exists' in str(e).lower():
                print(f"    ℹ️  Image already exists: {bucket_path}")
                return True
            print(f"    ⚠️  Failed to upload to storage: {e}")
            return False

    def localize_image(self, external_url: str, entity_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Download external image, generate thumbnail, upload both to storage.
        Returns (image_url, thumbnail_url) or (None, None) on failure.
        """
        if not external_url:
            return None, None

        # Determine file extension from URL
        ext = external_url.split('.')[-1].lower()
        if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
            ext = 'jpg'

        # Download original
        print(f"    📥 Downloading image...")
        image_bytes = self.download_image(external_url)
        if not image_bytes:
            return None, None

        # Upload original
        original_path = f"originals/{entity_id}.{ext}"
        print(f"    📤 Uploading original...")
        if not self.upload_to_storage(image_bytes, original_path, f'image/{ext}'):
            return None, None

        # Generate thumbnail
        print(f"    🖼️  Generating thumbnail...")
        thumbnail_bytes = self.generate_thumbnail(image_bytes)
        if not thumbnail_bytes:
            # Even if thumbnail fails, we have the original
            image_url = f"/storage/v1/object/public/images/{original_path}"
            return image_url, None

        # Upload thumbnail
        thumbnail_path = f"thumbnails/{entity_id}.webp"
        print(f"    📤 Uploading thumbnail...")
        if not self.upload_to_storage(thumbnail_bytes, thumbnail_path, 'image/webp'):
            # Even if thumbnail upload fails, we have the original
            image_url = f"/storage/v1/object/public/images/{original_path}"
            return image_url, None

        # Success - return both URLs
        image_url = f"/storage/v1/object/public/images/{original_path}"
        thumbnail_url = f"/storage/v1/object/public/images/{thumbnail_path}"
        return image_url, thumbnail_url

    def update_toy_parent(self, toy_id: str, new_parent_id: str, toy_name: str) -> str:
        """
        Update toy's parent relationship from old series to new toy line.

        This is critical for maintaining collections when hierarchy changes.
        """
        # Find current parent relationships
        existing_rels = self.supabase.table("relationships").select("id,from_id").eq(
            "to_id", toy_id
        ).eq("type", "contains").execute()

        # Delete old parent relationships (from series collections)
        for rel in existing_rels.data:
            self.supabase.table("relationships").delete().eq("id", rel["id"]).execute()

        # Create new relationship to toy line
        try:
            self.supabase.table("relationships").insert({
                "from_id": new_parent_id,
                "to_id": toy_id,
                "type": "contains"
            }).execute()
            return f"Updated parent: {toy_name} → toy line"
        except Exception as e:
            # Relationship might already exist
            if '409' in str(e) or 'unique' in str(e).lower():
                return f"Re-linked: {toy_name} (relationship already exists)"
            raise

    def import_toy(self, toy_data: Dict, toy_line_id: str, manufacturer: Optional[str] = None) -> Tuple[bool, str]:
        """Import a single toy. Returns (success, message)."""
        name = toy_data["name"]
        year = toy_data.get("year")
        item_number = toy_data.get("item_number")
        external_image_url = toy_data.get("image_url")

        # Check if toy already exists
        existing_id = self.check_toy_exists(item_number)
        if existing_id:
            # MAINTAIN MODE: Update relationship if parent changed
            message = self.update_toy_parent(existing_id, toy_line_id, name)
            return True, message

        # CREATE MODE: Generate entity ID upfront (needed for image storage paths)
        entity_id = str(uuid.uuid4())

        # Localize image if present
        image_url = None
        thumbnail_url = None
        if external_image_url:
            print(f"      Processing images for: {name}")

            # Capture validation result if in dry run
            if hasattr(self.image_localizer, 'image_validator') and self.image_localizer.image_validator:
                result = self.image_localizer.image_validator.validate_image(external_image_url)
                self.image_results.append(result)

            image_url, thumbnail_url = self.image_localizer.localize_image(external_image_url, entity_id)
            if not image_url:
                print(f"        ⚠️  Image localization failed, using external URL")
                image_url = external_image_url

        # Generate embedding for semantic search
        name_embedding = self.embedding_generator.generate_embedding(name)

        # Prepare entity data with new metadata structure
        entity_data = {
            "id": entity_id,
            "name": name,
            "type": "toy",
            "year": year,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "name_embedding": name_embedding,
            "source_url": toy_data.get("source_url"),
            "external_ids": {
                "grnrngr": item_number
            },
            "attributes": {}
        }

        # Only add manufacturer to attributes if provided
        if manufacturer:
            entity_data["attributes"]["manufacturer"] = manufacturer

        try:
            # Create entity
            result = self.supabase.table("entities").insert(entity_data).execute()

            # Link to toy line
            self.supabase.table("relationships").insert({
                "from_id": toy_line_id,
                "to_id": entity_id,
                "type": "contains"
            }).execute()

            thumb_status = "with thumbnail" if thumbnail_url else "original only"
            return True, f"✓ Imported: {name} (#{item_number}) - {thumb_status}"

        except Exception as e:
            return False, f"Error importing {name}: {str(e)}"

    def import_all_toy_lines(self, toy_lines: list) -> Tuple[int, int, int, int]:
        """
        Import all toy lines and their toys.

        Returns (toy_lines_imported, toys_created, toys_updated, toys_skipped).
        """
        toy_lines_imported = 0
        toys_created = 0
        toys_updated = 0
        toys_skipped = 0

        for toy_line_data in toy_lines:
            series_name = toy_line_data.get("series")
            manufacturer = toy_line_data.get("manufacturer")

            print(f"\nProcessing: {toy_line_data.get('name')}")

            # Get or create series (TV show)
            series_id = self.get_or_create_series(series_name)

            # Get or create toy line (assortment)
            toy_line_id = self.get_or_create_toy_line(toy_line_data, series_id)
            toy_lines_imported += 1

            # Import all toys in this toy line
            for toy_data in toy_line_data.get("toys", []):
                success, message = self.import_toy(toy_data, toy_line_id, manufacturer)
                print(f"    {message}")

                if success:
                    # Distinguish between created and updated
                    if "Updated parent" in message or "Re-linked" in message:
                        toys_updated += 1
                    else:
                        toys_created += 1
                else:
                    toys_skipped += 1

        return toy_lines_imported, toys_created, toys_updated, toys_skipped


def load_config():
    """Load Supabase configuration from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        print("Either:")
        print("  1. Set environment variables")
        print("  2. Create secrets.env file in curator directory")
        sys.exit(1)

    return supabase_url, supabase_key


def load_fetched_data() -> list:
    """Load data from fetch script."""
    data_file = Path(__file__).parent.parent / FETCHED_FILE

    if not data_file.exists():
        print(f"Error: {FETCHED_FILE} not found")
        print("Run fetch_data.py first")
        sys.exit(1)

    with open(data_file) as f:
        return json.load(f)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Import Power Rangers toys to Supabase database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate import without writing to database'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Power Rangers Toy Importer")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be written to database")
    print("=" * 60)
    print()

    # Load configuration
    supabase_url, supabase_key = load_config()

    # Use mock or real client
    if args.dry_run:
        from dry_run_utils import MockSupabaseClient, ImageValidator, DryRunOutput
        supabase = MockSupabaseClient()
        image_validator = ImageValidator()
    else:
        supabase = create_client(supabase_url, supabase_key)
        image_validator = None

    # Load fetched data
    print("Loading fetched data...")
    toy_lines = load_fetched_data()
    total_toys = sum(len(tl.get("toys", [])) for tl in toy_lines)
    print(f"Found {len(toy_lines)} toy lines with {total_toys} toys to import")
    print()

    # Import toy lines and toys
    if not args.dry_run:
        print("Loading embedding model: sentence-transformers/all-MiniLM-L6-v2")

    importer = ToyImporter(supabase)

    # Pass validator to image localizer if present
    if image_validator:
        importer.image_localizer = ImageLocalizer(supabase, image_validator=image_validator)

    if not args.dry_run:
        print("✓ Model loaded\n")

    toy_lines_imported, toys_created, toys_updated, toys_skipped = importer.import_all_toy_lines(toy_lines)

    print()
    print("=" * 60)

    # Generate dry run output
    if args.dry_run:
        output = DryRunOutput(supabase, importer.image_results)
        output.print_yaml(max_entities=3)
        output.save_json('dry_run_results.json')
        print(f"\n✓ Dry run complete. Full results saved to dry_run_results.json")
    else:
        print(f"✓ Complete:")
        print(f"  Toy lines: {toy_lines_imported}")
        print(f"  Toys created: {toys_created}")
        print(f"  Toys updated (re-linked): {toys_updated}")
        print(f"  Toys skipped: {toys_skipped}")
        print(f"  Total toys processed: {toys_created + toys_updated}")

    print("=" * 60)


if __name__ == "__main__":
    main()
