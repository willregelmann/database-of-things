"""
Rate limiting and exponential backoff utilities for API calls.
"""

import asyncio
import time
from typing import Callable, Any, Optional
from functools import wraps

import redis.asyncio as redis
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from core.config import settings


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    pass


class RateLimiter:
    """
    Token bucket rate limiter using Redis for distributed rate limiting.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Optional Redis client (creates one if not provided)
        """
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                decode_responses=True,
            )

        self.rate_per_second = settings.api_rate_limit_per_second

    async def check_rate_limit(self, key: str) -> bool:
        """
        Check if operation is within rate limit using token bucket algorithm.

        Args:
            key: Rate limit key (e.g., "curator:{id}:api_calls")

        Returns:
            True if within limit, False otherwise
        """
        now = time.time()
        bucket_key = f"rate_limit:{key}"

        # Get current bucket state
        pipe = self.redis.pipeline()
        pipe.get(f"{bucket_key}:tokens")
        pipe.get(f"{bucket_key}:last_refill")
        tokens, last_refill = await pipe.execute()

        # Initialize bucket if needed
        if tokens is None:
            tokens = self.rate_per_second
            last_refill = now
        else:
            tokens = float(tokens)
            last_refill = float(last_refill)

        # Refill tokens based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = time_elapsed * self.rate_per_second
        tokens = min(tokens + tokens_to_add, self.rate_per_second)

        # Check if we have tokens
        if tokens < 1.0:
            return False

        # Consume token
        tokens -= 1.0

        # Update bucket
        pipe = self.redis.pipeline()
        pipe.set(f"{bucket_key}:tokens", tokens)
        pipe.set(f"{bucket_key}:last_refill", now)
        pipe.expire(f"{bucket_key}:tokens", 60)  # Expire after 1 minute
        pipe.expire(f"{bucket_key}:last_refill", 60)
        await pipe.execute()

        return True

    async def wait_for_rate_limit(self, key: str) -> None:
        """
        Wait until rate limit allows operation.

        Args:
            key: Rate limit key
        """
        while not await self.check_rate_limit(key):
            await asyncio.sleep(1.0 / self.rate_per_second)

    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.aclose()


def rate_limited(key_prefix: str):
    """
    Decorator for rate-limited async functions.

    Args:
        key_prefix: Prefix for rate limit key

    Example:
        @rate_limited("pokemontcg_api")
        async def fetch_cards():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            limiter = RateLimiter()
            try:
                # Extract curator_id if available
                curator_id = kwargs.get("curator_id", "default")
                key = f"{key_prefix}:{curator_id}"

                # Wait for rate limit
                await limiter.wait_for_rate_limit(key)

                # Execute function
                return await func(*args, **kwargs)
            finally:
                await limiter.close()

        return wrapper

    return decorator


def with_exponential_backoff(
    max_attempts: Optional[int] = None,
    exception_types: tuple = (Exception,),
):
    """
    Decorator for exponential backoff retry logic.

    Args:
        max_attempts: Max retry attempts (default from settings)
        exception_types: Exception types to retry on

    Example:
        @with_exponential_backoff(exception_types=(httpx.HTTPError,))
        async def fetch_data():
            ...
    """
    max_attempts = max_attempts or settings.max_retry_attempts

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=60,
            exp_base=settings.exponential_backoff_base,
        ),
        retry=retry_if_exception_type(exception_types),
        reraise=True,
    )


# Combined decorator for rate limiting + exponential backoff
def api_call(key_prefix: str, exception_types: tuple = (Exception,)):
    """
    Combined decorator for rate-limited API calls with exponential backoff.

    Args:
        key_prefix: Prefix for rate limit key
        exception_types: Exception types to retry on

    Example:
        @api_call("pokemontcg_api", exception_types=(httpx.HTTPError,))
        async def fetch_cards():
            ...
    """

    def decorator(func: Callable) -> Callable:
        # Apply both decorators
        func = rate_limited(key_prefix)(func)
        func = with_exponential_backoff(exception_types=exception_types)(func)
        return func

    return decorator
