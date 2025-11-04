"""
Image downloading and processing utilities for curator agents.
"""

import hashlib
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple
from uuid import uuid4

import httpx
from PIL import Image

from core.config import settings


class ImageProcessor:
    """
    Handles image downloading, validation, and thumbnail generation.
    """

    def __init__(self):
        """Initialize image processor."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.max_size_bytes = settings.image_max_size_mb * 1024 * 1024

    async def download_image(self, url: str) -> bytes:
        """
        Download image from URL with size validation.

        Args:
            url: Image URL

        Returns:
            Image bytes

        Raises:
            ValueError: If image is too large or download fails
        """
        response = await self.http_client.get(url)
        response.raise_for_status()

        image_bytes = response.content

        if len(image_bytes) > self.max_size_bytes:
            raise ValueError(
                f"Image too large: {len(image_bytes) / 1024 / 1024:.1f}MB "
                f"(max: {settings.image_max_size_mb}MB)"
            )

        return image_bytes

    def validate_image(self, image_bytes: bytes) -> Tuple[str, int, int]:
        """
        Validate image and get metadata.

        Args:
            image_bytes: Image data

        Returns:
            Tuple of (format, width, height)

        Raises:
            ValueError: If image is invalid
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            return image.format.lower(), image.width, image.height
        except Exception as e:
            raise ValueError(f"Invalid image: {e}")

    def generate_thumbnail(
        self,
        image_bytes: bytes,
        size: Optional[int] = None,
        quality: Optional[int] = None,
    ) -> bytes:
        """
        Generate WebP thumbnail from image.

        Args:
            image_bytes: Original image data
            size: Thumbnail size in pixels (default from settings)
            quality: WebP quality 1-100 (default from settings)

        Returns:
            Thumbnail bytes (WebP format)
        """
        size = size or settings.thumbnail_size
        quality = quality or settings.thumbnail_quality

        # Open and resize
        image = Image.open(BytesIO(image_bytes))

        # Convert RGBA to RGB if necessary
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Resize with high-quality resampling
        image.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Save as WebP
        output = BytesIO()
        image.save(output, format="WEBP", quality=quality, method=6)
        return output.getvalue()

    def compute_hash(self, image_bytes: bytes) -> str:
        """
        Compute SHA256 hash of image (for deduplication).

        Args:
            image_bytes: Image data

        Returns:
            Hex digest of hash
        """
        return hashlib.sha256(image_bytes).hexdigest()

    async def upload_to_supabase(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
        folder: str = "originals",
    ) -> str:
        """
        Upload image to Supabase Storage.

        Args:
            image_bytes: Image data
            filename: Optional filename (generates UUID if not provided)
            folder: Folder within images bucket (default: "originals")

        Returns:
            Storage path (e.g., "/storage/v1/object/public/images/originals/{uuid}.jpg")
        """
        from supabase import create_client

        client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )

        # Determine format
        image_format, _, _ = self.validate_image(image_bytes)

        # Generate filename if not provided
        if not filename:
            filename = f"{uuid4()}.{image_format}"

        # Upload path
        path = f"{folder}/{filename}"

        # Upload
        result = client.storage.from_("images").upload(
            path=path,
            file=image_bytes,
            file_options={
                "content-type": f"image/{image_format}",
                "upsert": "false",
            },
        )

        # Return public URL path
        return f"/storage/v1/object/public/images/{path}"

    async def download_and_upload(
        self,
        url: str,
        generate_thumbnail: bool = True,
    ) -> Tuple[str, Optional[str]]:
        """
        Download image from URL and upload to Supabase with optional thumbnail.

        Args:
            url: Source image URL
            generate_thumbnail: Whether to generate thumbnail

        Returns:
            Tuple of (image_url, thumbnail_url)
        """
        # Download
        image_bytes = await self.download_image(url)

        # Validate
        self.validate_image(image_bytes)

        # Upload original
        image_url = await self.upload_to_supabase(image_bytes, folder="originals")

        # Generate and upload thumbnail if requested
        thumbnail_url = None
        if generate_thumbnail:
            thumbnail_bytes = self.generate_thumbnail(image_bytes)
            # Use same UUID for thumbnail
            image_id = image_url.split("/")[-1].split(".")[0]
            thumbnail_url = await self.upload_to_supabase(
                thumbnail_bytes,
                filename=f"{image_id}.webp",
                folder="thumbnails",
            )

        return image_url, thumbnail_url

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()
