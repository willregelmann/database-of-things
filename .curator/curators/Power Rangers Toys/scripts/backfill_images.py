#!/usr/bin/env python3
"""
Backfill existing Power Rangers toys with localized images and thumbnails.

This script:
1. Finds all toys with external image URLs but no localized images
2. Downloads each external image
3. Uploads to Supabase storage (originals/ and thumbnails/)
4. Updates entities with new image_url and thumbnail_url
"""

import json
import os
import sys
import io
from pathlib import Path
from typing import Optional, Tuple

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


class ImageBackfiller:
    """Backfill images for existing entities."""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.session = requests.Session()

    def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"    ⚠️  Download failed: {e}")
            return None

    def generate_thumbnail(self, image_bytes: bytes, size: int = 300) -> Optional[bytes]:
        """Generate WebP thumbnail."""
        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            output = io.BytesIO()
            img.save(output, format='WEBP', quality=85)
            return output.getvalue()
        except Exception as e:
            print(f"    ⚠️  Thumbnail generation failed: {e}")
            return None

    def upload_to_storage(self, file_bytes: bytes, bucket_path: str, content_type: str) -> bool:
        """Upload file to Supabase storage."""
        try:
            self.supabase.storage.from_('images').upload(
                bucket_path,
                file_bytes,
                file_options={"content-type": content_type}
            )
            return True
        except Exception as e:
            error_str = str(e).lower()
            if '409' in error_str or 'already exists' in error_str:
                return True
            print(f"    ⚠️  Upload failed: {e}")
            return False

    def process_entity(self, entity) -> Tuple[bool, str]:
        """Process a single entity's images."""
        entity_id = entity['id']
        name = entity['name']
        external_url = entity['image_url']

        if not external_url:
            return False, f"Skip {name}: no image URL"

        # Skip if already localized (starts with /storage/)
        if external_url.startswith('/storage/'):
            return False, f"Skip {name}: already localized"

        print(f"\nProcessing: {name}")
        print(f"  External URL: {external_url}")

        # Determine extension
        ext = external_url.split('.')[-1].split('?')[0].lower()
        if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
            ext = 'jpg'

        # Map extension to proper MIME type
        mime_type = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }.get(ext, 'image/jpeg')

        # Download
        print(f"  📥 Downloading...")
        image_bytes = self.download_image(external_url)
        if not image_bytes:
            return False, f"Failed {name}: download error"

        # Upload original
        original_path = f"originals/{entity_id}.{ext}"
        print(f"  📤 Uploading original...")
        if not self.upload_to_storage(image_bytes, original_path, mime_type):
            return False, f"Failed {name}: original upload error"

        # Generate and upload thumbnail
        print(f"  🖼️  Generating thumbnail...")
        thumbnail_bytes = self.generate_thumbnail(image_bytes)
        thumbnail_path = f"thumbnails/{entity_id}.webp"
        thumbnail_uploaded = False

        if thumbnail_bytes:
            print(f"  📤 Uploading thumbnail...")
            thumbnail_uploaded = self.upload_to_storage(thumbnail_bytes, thumbnail_path, 'image/webp')

        # Update entity
        new_image_url = f"/storage/v1/object/public/images/{original_path}"
        new_thumbnail_url = f"/storage/v1/object/public/images/{thumbnail_path}" if thumbnail_uploaded else None

        update_data = {
            "image_url": new_image_url,
            "thumbnail_url": new_thumbnail_url
        }

        try:
            self.supabase.table("entities").update(update_data).eq("id", entity_id).execute()
            status = "with thumbnail" if thumbnail_uploaded else "original only"
            print(f"  ✅ Updated entity - {status}")
            return True, f"Success {name}"
        except Exception as e:
            return False, f"Failed {name}: database update error - {e}"


def load_config():
    """Load Supabase configuration from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        print("Run from curator directory or set environment variables")
        sys.exit(1)

    return supabase_url, supabase_key


def main():
    print("=" * 70)
    print("Power Rangers Image Backfiller")
    print("=" * 70)
    print()

    # Load configuration
    supabase_url, supabase_key = load_config()
    supabase = create_client(supabase_url, supabase_key)

    # Find entities needing backfill
    print("🔍 Finding entities with external images...")
    result = supabase.table("entities").select("id, name, image_url, thumbnail_url").filter(
        "external_ids->>grnrngr", "not.is", "null"
    ).filter(
        "thumbnail_url", "is", "null"
    ).execute()

    entities = result.data
    print(f"Found {len(entities)} entities to process")
    print()

    if not entities:
        print("✅ All entities already have localized images!")
        return

    # Ask for confirmation
    response = input(f"Process {len(entities)} images? This may take a while. (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return

    # Process entities
    backfiller = ImageBackfiller(supabase)
    success_count = 0
    fail_count = 0

    for i, entity in enumerate(entities, 1):
        print(f"\n[{i}/{len(entities)}]", end=" ")
        success, message = backfiller.process_entity(entity)

        if success:
            success_count += 1
        else:
            fail_count += 1
            print(f"  ⚠️  {message}")

    print()
    print("=" * 70)
    print(f"✅ Complete: {success_count} processed, {fail_count} failed")
    print("=" * 70)


if __name__ == "__main__":
    main()
