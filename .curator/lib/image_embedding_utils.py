#!/usr/bin/env python3
"""
Image embedding utilities for CLIP-based reverse image search.

Provides functions to generate 512-dimensional vector embeddings from images
using OpenAI's CLIP model for semantic visual similarity search.

Usage:
    from ...lib.image_embedding_utils import ImageEmbeddingGenerator

    generator = ImageEmbeddingGenerator()
    embedding = generator.generate_embedding_from_url("https://example.com/image.jpg")
"""

import sys
import io
from typing import Optional, List
from PIL import Image

# Auto-install dependencies if missing
try:
    from sentence_transformers import SentenceTransformer
    import requests
except ImportError:
    print("Installing required packages (one-time setup)...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "sentence-transformers", "requests", "pillow"
    ])
    from sentence_transformers import SentenceTransformer
    import requests


class ImageEmbeddingGenerator:
    """
    Generates vector embeddings for images using CLIP.

    Uses sentence-transformers/clip-ViT-B-32 model:
    - 512 dimensions
    - ~350MB model size
    - Trained on image-text pairs (multimodal)
    - Good for visual similarity search
    """

    # Model name (CLIP variant)
    MODEL_NAME = 'sentence-transformers/clip-ViT-B-32'

    def __init__(self):
        """
        Initialize image embedding generator.

        Loads the CLIP model (downloads on first use ~350MB).
        Model is cached in ~/.cache/torch/sentence_transformers/
        """
        print(f"Loading CLIP model: {self.MODEL_NAME}")
        self.model = SentenceTransformer(self.MODEL_NAME)
        print("✓ CLIP model loaded")

    def generate_embedding_from_url(self, image_url: str, base_url: str = None) -> Optional[List[float]]:
        """
        Generate vector embedding from an image URL.

        Args:
            image_url: Image URL (can be relative path like /storage/v1/object/public/images/...)
            base_url: Base URL to prepend if image_url is a relative path (e.g., http://127.0.0.1:54321)

        Returns:
            List of 512 floats, or None if image cannot be loaded
        """
        if not image_url or not image_url.strip():
            return None

        try:
            # Handle relative paths (Supabase storage)
            full_url = image_url
            if not image_url.startswith(('http://', 'https://')):
                if not base_url:
                    print(f"    ⚠️  Relative URL requires base_url: {image_url}")
                    return None
                full_url = base_url.rstrip('/') + '/' + image_url.lstrip('/')

            # Download image
            response = requests.get(full_url, timeout=10)
            response.raise_for_status()

            # Load image
            image = Image.open(io.BytesIO(response.content))

            # Convert to RGB if needed (CLIP requires RGB)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Generate embedding
            embedding = self.model.encode(image)

            # Convert to list for JSON serialization
            return embedding.tolist()

        except requests.exceptions.RequestException as e:
            print(f"    ⚠️  Failed to download image: {e}")
            return None
        except Exception as e:
            print(f"    ⚠️  Failed to generate image embedding: {e}")
            return None

    def generate_embedding_from_image(self, image: Image.Image) -> Optional[List[float]]:
        """
        Generate vector embedding from a PIL Image object.

        Args:
            image: PIL Image object

        Returns:
            List of 512 floats, or None on failure
        """
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Generate embedding
            embedding = self.model.encode(image)

            # Convert to list for JSON serialization
            return embedding.tolist()

        except Exception as e:
            print(f"    ⚠️  Failed to generate image embedding: {e}")
            return None

    def generate_embeddings_batch(self, image_urls: List[str], base_url: str = None) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple images in a batch (more efficient).

        Args:
            image_urls: List of image URLs
            base_url: Base URL for relative paths

        Returns:
            List of embeddings (512-dim float lists) or None for failed images
        """
        if not image_urls:
            return []

        result = []
        for url in image_urls:
            embedding = self.generate_embedding_from_url(url, base_url)
            result.append(embedding)

        return result


# Standalone convenience function
def generate_image_embedding(image_url: str, base_url: str = None) -> Optional[List[float]]:
    """
    Convenience function for quick image embedding generation.

    Note: Creates new model instance each time. For multiple calls,
    create an ImageEmbeddingGenerator instance and reuse it.

    Args:
        image_url: Image URL or path
        base_url: Base URL for relative paths

    Returns:
        List of 512 floats
    """
    generator = ImageEmbeddingGenerator()
    return generator.generate_embedding_from_url(image_url, base_url)
