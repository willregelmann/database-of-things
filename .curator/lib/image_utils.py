#!/usr/bin/env python3
"""
Reusable image utilities for curator import scripts.

Provides functions to download external images, generate thumbnails,
and upload to Supabase storage with proper paths.

Usage:
    from ...lib.image_utils import ImageLocalizer

    localizer = ImageLocalizer(supabase_client)
    image_url, thumbnail_url = localizer.localize_image(external_url, entity_id)
"""

import io
import sys
from typing import Optional, Tuple

# Auto-install dependencies if missing
try:
    import requests
    from PIL import Image
except ImportError:
    print("Installing image processing dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "requests", "pillow"])
    import requests
    from PIL import Image


class ImageLocalizer:
    """
    Handles downloading external images, generating thumbnails,
    and uploading to Supabase storage.
    """

    def __init__(self, supabase_client, image_validator=None):
        """
        Initialize image localizer.

        Args:
            supabase_client: Supabase client instance
            image_validator: Optional ImageValidator for dry run mode
        """
        self.supabase = supabase_client
        self.image_validator = image_validator
        self.session = requests.Session()  # Reuse HTTP connections

    def download_image(self, url: str, timeout: int = 10) -> Optional[bytes]:
        """
        Download image from URL, trying alternate patterns if needed.

        For grnrngr.com URLs, tries both with and without _1 suffix:
        - /bandai/12345.jpg
        - /bandai/12345_1.jpg

        Args:
            url: External image URL
            timeout: Request timeout in seconds

        Returns:
            Image bytes or None on failure
        """
        # Try original URL first
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.content
        except Exception as e:
            # If 404 and looks like a grnrngr.com URL, try alternate pattern
            if '404' in str(e) and 'grnrngr.com' in url and '/bandai/' in url:
                # Try toggling the _1 suffix
                if '_1.jpg' in url:
                    # Try without _1
                    alternate_url = url.replace('_1.jpg', '.jpg')
                elif '.jpg' in url and '_1.jpg' not in url:
                    # Try with _1
                    alternate_url = url.replace('.jpg', '_1.jpg')
                else:
                    return None

                print(f"    🔄 Trying alternate URL pattern...")
                try:
                    response = self.session.get(alternate_url, timeout=timeout)
                    response.raise_for_status()
                    return response.content
                except Exception as e2:
                    print(f"    ⚠️  Failed to download from both URL patterns")
                    return None
            else:
                print(f"    ⚠️  Failed to download image from {url}: {e}")
                return None

    def generate_thumbnail(self, image_bytes: bytes, size: int = 300, quality: int = 85) -> Optional[bytes]:
        """
        Generate WebP thumbnail from image bytes.

        Args:
            image_bytes: Original image data
            size: Thumbnail size (max width/height)
            quality: WebP quality (1-100)

        Returns:
            Thumbnail bytes or None on failure
        """
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
            img.save(output, format='WEBP', quality=quality)
            return output.getvalue()
        except Exception as e:
            print(f"    ⚠️  Failed to generate thumbnail: {e}")
            return None

    def upload_to_storage(
        self,
        file_bytes: bytes,
        bucket_path: str,
        content_type: str = 'image/jpeg',
        bucket: str = 'images'
    ) -> bool:
        """
        Upload file to Supabase storage.

        Args:
            file_bytes: File data to upload
            bucket_path: Path within bucket (e.g., "originals/uuid.jpg")
            content_type: MIME type
            bucket: Storage bucket name

        Returns:
            True on success, False on failure
        """
        try:
            self.supabase.storage.from_(bucket).upload(
                bucket_path,
                file_bytes,
                file_options={"content-type": content_type}
            )
            return True
        except Exception as e:
            # Check if file already exists (error code 409)
            error_str = str(e).lower()
            if '409' in error_str or 'already exists' in error_str:
                print(f"    ℹ️  Image already exists: {bucket_path}")
                return True
            print(f"    ⚠️  Failed to upload to storage: {e}")
            return False

    def localize_image(
        self,
        external_url: str,
        entity_id: str,
        thumbnail_size: int = 300
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Download external image, generate thumbnail, upload both to storage.

        If image_validator is set (dry run mode), validates URL instead of downloading.

        This is the main method curators should use. It handles the complete
        workflow of image localization.

        Args:
            external_url: External image URL to download
            entity_id: Entity UUID for storage paths
            thumbnail_size: Thumbnail max width/height in pixels

        Returns:
            Tuple of (image_url, thumbnail_url) or (None, None) on complete failure
            May return (image_url, None) if thumbnail generation fails
        """
        if not external_url:
            return None, None

        # DRY RUN MODE: Validate instead of download
        if self.image_validator:
            result = self.image_validator.validate_image(external_url)
            if result["accessible"]:
                return f"[would localize from {external_url}]", None
            else:
                return None, None

        # Determine file extension from URL
        ext = external_url.split('.')[-1].split('?')[0].lower()  # Handle query params
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
        thumbnail_bytes = self.generate_thumbnail(image_bytes, size=thumbnail_size)
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


# Standalone functions for simple usage
def localize_image(supabase_client, external_url: str, entity_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Convenience function for quick image localization.

    Args:
        supabase_client: Supabase client instance
        external_url: External image URL
        entity_id: Entity UUID

    Returns:
        Tuple of (image_url, thumbnail_url)
    """
    localizer = ImageLocalizer(supabase_client)
    return localizer.localize_image(external_url, entity_id)
