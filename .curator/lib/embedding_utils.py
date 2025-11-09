#!/usr/bin/env python3
"""
Reusable embedding utilities for curator import scripts.

Provides functions to generate vector embeddings for semantic search
using sentence-transformers.

Usage:
    from ...lib.embedding_utils import EmbeddingGenerator

    generator = EmbeddingGenerator()
    embedding = generator.generate_embedding("Charizard")
"""

import sys
from typing import Optional, List

# Auto-install dependencies if missing
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Installing sentence-transformers (one-time download ~420MB)...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "--break-system-packages", "sentence-transformers"
    ])
    from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """
    Generates vector embeddings for semantic search.

    Uses sentence-transformers/all-MiniLM-L6-v2 model:
    - 384 dimensions
    - ~80MB model size
    - Fast inference (~5ms per text)
    - Good quality for short texts
    """

    # Model name (change if needed)
    MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

    def __init__(self):
        """
        Initialize embedding generator.

        Loads the sentence transformer model (downloads on first use).
        Model is cached in ~/.cache/torch/sentence_transformers/
        """
        print(f"Loading embedding model: {self.MODEL_NAME}")
        self.model = SentenceTransformer(self.MODEL_NAME)
        print("✓ Model loaded")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate vector embedding for a single text.

        Args:
            text: Text to embed (e.g., entity name)

        Returns:
            List of 384 floats, or None if text is empty
        """
        if not text or not text.strip():
            return None

        try:
            # Generate embedding
            embedding = self.model.encode(text.strip())
            # Convert to list for JSON serialization
            return embedding.tolist()
        except Exception as e:
            print(f"    ⚠️  Failed to generate embedding: {e}")
            return None

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in a batch (more efficient).

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (384-dim float lists) or None for empty texts
        """
        if not texts:
            return []

        # Filter out empty texts but keep track of indices
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_indices.append(i)
                valid_texts.append(text.strip())

        if not valid_texts:
            return [None] * len(texts)

        try:
            # Generate embeddings in batch
            embeddings = self.model.encode(valid_texts)

            # Map back to original indices
            result = [None] * len(texts)
            for i, embedding in zip(valid_indices, embeddings):
                result[i] = embedding.tolist()

            return result
        except Exception as e:
            print(f"    ⚠️  Failed to generate batch embeddings: {e}")
            return [None] * len(texts)


# Standalone convenience function
def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Convenience function for quick embedding generation.

    Note: Creates new model instance each time. For multiple calls,
    create an EmbeddingGenerator instance and reuse it.

    Args:
        text: Text to embed

    Returns:
        List of 384 floats
    """
    generator = EmbeddingGenerator()
    return generator.generate_embedding(text)
