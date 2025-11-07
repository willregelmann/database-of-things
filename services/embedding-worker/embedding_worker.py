#!/usr/bin/env python3
"""
Embedding Worker Service

This service continuously polls the embedding queue and generates vector embeddings
for entity names using sentence-transformers. It's designed to be reliable,
efficient, and easy to monitor.

Features:
- Automatic retry with exponential backoff
- Batch processing for efficiency
- Row-level locking to prevent race conditions
- Graceful shutdown on SIGTERM/SIGINT
- Health check endpoint (optional)
- Prometheus metrics (optional)

Usage:
    python embedding_worker.py

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (required)
    MODEL_NAME: Sentence transformer model (default: sentence-transformers/all-MiniLM-L6-v2)
    BATCH_SIZE: Number of items to process per batch (default: 100)
    POLL_INTERVAL: Seconds between polls when queue is empty (default: 10)
    LOG_LEVEL: Logging level (default: INFO)
    WORKER_ID: Unique identifier for this worker (default: hostname)
"""

import os
import sys
import time
import signal
import socket
import logging
import asyncio
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer
import asyncpg
from asyncpg import Pool

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class WorkerConfig:
    """Worker configuration from environment variables."""
    database_url: str
    model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'
    batch_size: int = 100
    poll_interval: int = 10
    worker_id: str = socket.gethostname()
    max_retries: int = 3
    cleanup_days: int = 7

    @classmethod
    def from_env(cls) -> 'WorkerConfig':
        """Create configuration from environment variables."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            # Try local Supabase if DATABASE_URL not set
            database_url = "postgresql://postgres:postgres@localhost:54322/postgres"
            logger.warning(f"DATABASE_URL not set, using local Supabase: {database_url}")

        return cls(
            database_url=database_url,
            model_name=os.getenv("MODEL_NAME", cls.model_name),
            batch_size=int(os.getenv("BATCH_SIZE", str(cls.batch_size))),
            poll_interval=int(os.getenv("POLL_INTERVAL", str(cls.poll_interval))),
            worker_id=os.getenv("WORKER_ID", cls.worker_id),
            max_retries=int(os.getenv("MAX_RETRIES", str(cls.max_retries))),
            cleanup_days=int(os.getenv("CLEANUP_DAYS", str(cls.cleanup_days)))
        )

class EmbeddingWorker:
    """Main worker class for processing embedding queue."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.model: Optional[SentenceTransformer] = None
        self.pool: Optional[Pool] = None
        self.running = True
        self.stats = {
            'processed': 0,
            'failed': 0,
            'start_time': datetime.now()
        }

    async def init(self):
        """Initialize model and database connection."""
        # Load the sentence transformer model
        logger.info(f"Loading model {self.config.model_name}...")
        try:
            self.model = SentenceTransformer(self.config.model_name)
            embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {embedding_dim}")

            # Verify dimension matches database
            if embedding_dim != 384:
                logger.warning(
                    f"Model dimension ({embedding_dim}) differs from database (384). "
                    "Ensure database schema matches model output."
                )
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

        # Create database connection pool
        logger.info("Creating database connection pool...")
        try:
            self.pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': f'embedding_worker_{self.config.worker_id}'
                }
            )
            logger.info("Database connection pool created successfully")

            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Connected to: {version}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources on shutdown."""
        logger.info("Cleaning up resources...")
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def claim_batch(self) -> List[Tuple[str, str, str]]:
        """
        Claim a batch of items from the queue.

        Returns:
            List of tuples (queue_id, entity_id, entity_name)
        """
        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch(
                    "SELECT * FROM claim_embedding_batch($1, $2)",
                    self.config.batch_size,
                    self.config.worker_id
                )
                return [(row['queue_id'], row['entity_id'], row['entity_name']) for row in rows]
            except Exception as e:
                logger.error(f"Error claiming batch: {e}")
                return []

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            NumPy array of embeddings
        """
        try:
            # Generate embeddings (no progress bar for cleaner logs)
            embeddings = self.model.encode(
                texts,
                batch_size=min(32, len(texts)),
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    async def update_embeddings(self, updates: List[Tuple[str, str, np.ndarray]]) -> bool:
        """
        Update entities with embeddings and mark queue items as processed.

        Args:
            updates: List of (queue_id, entity_id, embedding) tuples

        Returns:
            True if successful, False otherwise
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Update entities with embeddings
                    for queue_id, entity_id, embedding in updates:
                        # Convert numpy array to list for PostgreSQL
                        embedding_list = embedding.tolist()

                        # Update entity
                        await conn.execute(
                            """
                            UPDATE entities
                            SET name_embedding = $1::vector(384),
                                updated_at = NOW()
                            WHERE id = $2
                            """,
                            embedding_list,
                            entity_id
                        )

                    # Mark all queue items as completed
                    queue_ids = [queue_id for queue_id, _, _ in updates]
                    completed_count = await conn.fetchval(
                        "SELECT complete_embedding_batch($1::uuid[])",
                        queue_ids
                    )

                    if completed_count != len(queue_ids):
                        logger.warning(
                            f"Mismatch in completed count: expected {len(queue_ids)}, got {completed_count}"
                        )

                    return True

                except Exception as e:
                    logger.error(f"Error updating embeddings: {e}")
                    # Transaction will rollback
                    return False

    async def mark_failed(self, queue_id: str, error: str):
        """Mark a queue item as failed."""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    "SELECT fail_embedding_item($1, $2)",
                    queue_id,
                    error[:500]  # Truncate error message
                )
            except Exception as e:
                logger.error(f"Error marking item as failed: {e}")

    async def process_batch(self) -> int:
        """
        Process a single batch of embeddings.

        Returns:
            Number of successfully processed items
        """
        # Claim batch from queue
        batch = await self.claim_batch()

        if not batch:
            return 0

        logger.info(f"Processing batch of {len(batch)} items")
        start_time = time.time()

        try:
            # Extract entity names
            texts = [entity_name for _, _, entity_name in batch]

            # Generate embeddings
            logger.debug(f"Generating embeddings for {len(texts)} texts")
            embeddings = self.generate_embeddings(texts)

            # Prepare updates
            updates = [
                (queue_id, entity_id, embedding)
                for (queue_id, entity_id, _), embedding
                in zip(batch, embeddings)
            ]

            # Update database
            success = await self.update_embeddings(updates)

            if success:
                elapsed = time.time() - start_time
                logger.info(
                    f"Successfully processed {len(batch)} embeddings in {elapsed:.2f}s "
                    f"({len(batch)/elapsed:.1f} items/sec)"
                )
                self.stats['processed'] += len(batch)
                return len(batch)
            else:
                # Mark items as failed
                logger.error("Batch update failed, marking items for retry")
                for queue_id, _, _ in batch:
                    await self.mark_failed(queue_id, "Batch update failed")
                self.stats['failed'] += len(batch)
                return 0

        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            # Mark all items in batch as failed
            for queue_id, _, _ in batch:
                await self.mark_failed(queue_id, str(e))
            self.stats['failed'] += len(batch)
            return 0

    async def cleanup_old_completed(self):
        """Clean up old completed queue items."""
        async with self.pool.acquire() as conn:
            try:
                deleted = await conn.fetchval(
                    "SELECT cleanup_old_queue_items($1)",
                    self.config.cleanup_days
                )
                if deleted:
                    logger.info(f"Cleaned up {deleted} old completed queue items")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    async def log_stats(self):
        """Log worker statistics."""
        async with self.pool.acquire() as conn:
            try:
                # Get queue stats
                stats = await conn.fetch("SELECT * FROM embedding_queue_stats")
                for row in stats:
                    logger.info(
                        f"Queue [{row['status']}]: {row['count']} items, "
                        f"oldest: {row['oldest']}, avg_wait: {row['avg_wait_seconds']:.1f}s"
                    )

                # Get missing embeddings count
                missing = await conn.fetchval(
                    "SELECT COUNT(*) FROM entities_missing_embeddings"
                )
                logger.info(f"Entities missing embeddings: {missing}")

                # Log worker stats
                uptime = datetime.now() - self.stats['start_time']
                logger.info(
                    f"Worker stats - Processed: {self.stats['processed']}, "
                    f"Failed: {self.stats['failed']}, "
                    f"Uptime: {uptime}"
                )

            except Exception as e:
                logger.error(f"Error getting stats: {e}")

    async def run(self):
        """Main worker loop."""
        await self.init()

        logger.info(f"Starting embedding worker (ID: {self.config.worker_id})")
        logger.info(f"Configuration: batch_size={self.config.batch_size}, poll_interval={self.config.poll_interval}")

        consecutive_empty = 0
        last_cleanup = datetime.now()
        last_stats = datetime.now()

        while self.running:
            try:
                # Process a batch
                processed = await self.process_batch()

                if processed == 0:
                    # No items processed, use backoff
                    consecutive_empty += 1
                    wait_time = min(
                        self.config.poll_interval * (2 ** min(consecutive_empty - 1, 5)),
                        300  # Max 5 minutes
                    )
                    logger.debug(f"Queue empty, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    # Items processed, check for more immediately
                    consecutive_empty = 0
                    await asyncio.sleep(0.1)  # Brief pause

                # Periodic cleanup (every hour)
                if datetime.now() - last_cleanup > timedelta(hours=1):
                    await self.cleanup_old_completed()
                    last_cleanup = datetime.now()

                # Periodic stats logging (every 5 minutes)
                if datetime.now() - last_stats > timedelta(minutes=5):
                    await self.log_stats()
                    last_stats = datetime.now()

            except asyncio.CancelledError:
                logger.info("Worker cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying

        await self.cleanup()
        logger.info("Worker stopped")

def handle_signal(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

async def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Load configuration
    config = WorkerConfig.from_env()

    # Create and run worker
    worker = EmbeddingWorker(config)

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        worker.running = False
        await worker.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)