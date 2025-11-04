"""
Token budget management for curator agents.

Tracks daily token usage and enforces limits to prevent runaway costs.
"""

from datetime import datetime, timedelta
from typing import Optional
import redis.asyncio as redis

from core.config import settings


class TokenBudgetExceeded(Exception):
    """Raised when token budget is exceeded."""

    pass


class TokenBudgetManager:
    """
    Manages daily token budgets for curator agents using Redis.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize token budget manager.

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

        self.daily_limit = settings.daily_token_limit
        self.buffer_percentage = settings.token_buffer_percentage
        self.usable_limit = int(self.daily_limit * (1 - self.buffer_percentage))

    def _get_key(self, curator_id: str, date: Optional[datetime] = None) -> str:
        """
        Get Redis key for token usage.

        Args:
            curator_id: Curator identifier
            date: Date (defaults to today)

        Returns:
            Redis key
        """
        date = date or datetime.utcnow()
        date_str = date.strftime("%Y-%m-%d")
        return f"token_budget:{curator_id}:{date_str}"

    async def get_usage(self, curator_id: str) -> int:
        """
        Get current token usage for today.

        Args:
            curator_id: Curator identifier

        Returns:
            Token count used today
        """
        key = self._get_key(curator_id)
        usage = await self.redis.get(key)
        return int(usage) if usage else 0

    async def check_budget(
        self, curator_id: str, estimated_tokens: int, critical: bool = False
    ) -> bool:
        """
        Check if operation is within budget.

        Args:
            curator_id: Curator identifier
            estimated_tokens: Estimated tokens for operation
            critical: If True, use full budget including buffer

        Returns:
            True if within budget, False otherwise
        """
        current_usage = await self.get_usage(curator_id)
        limit = self.daily_limit if critical else self.usable_limit

        return current_usage + estimated_tokens <= limit

    async def record_usage(self, curator_id: str, tokens_used: int) -> int:
        """
        Record token usage.

        Args:
            curator_id: Curator identifier
            tokens_used: Number of tokens used

        Returns:
            Total usage after recording

        Raises:
            TokenBudgetExceeded: If recording would exceed budget
        """
        key = self._get_key(curator_id)

        # Increment usage
        new_usage = await self.redis.incrby(key, tokens_used)

        # Set expiry to end of day (UTC)
        now = datetime.utcnow()
        end_of_day = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        seconds_until_midnight = int((end_of_day - now).total_seconds())
        await self.redis.expire(key, seconds_until_midnight)

        # Check if exceeded
        if new_usage > self.daily_limit:
            raise TokenBudgetExceeded(
                f"Daily token budget exceeded: {new_usage}/{self.daily_limit}"
            )

        return new_usage

    async def get_remaining(self, curator_id: str, critical: bool = False) -> int:
        """
        Get remaining tokens for today.

        Args:
            curator_id: Curator identifier
            critical: If True, include buffer in calculation

        Returns:
            Remaining token count
        """
        usage = await self.get_usage(curator_id)
        limit = self.daily_limit if critical else self.usable_limit
        return max(0, limit - usage)

    async def get_stats(self, curator_id: str) -> dict:
        """
        Get detailed budget statistics.

        Args:
            curator_id: Curator identifier

        Returns:
            Dict with usage, remaining, limit, percentage
        """
        usage = await self.get_usage(curator_id)
        remaining = await self.get_remaining(curator_id)
        remaining_critical = await self.get_remaining(curator_id, critical=True)

        return {
            "curator_id": curator_id,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "usage": usage,
            "remaining": remaining,
            "remaining_critical": remaining_critical,
            "limit": self.usable_limit,
            "total_limit": self.daily_limit,
            "buffer": self.daily_limit - self.usable_limit,
            "percentage_used": (usage / self.daily_limit * 100) if self.daily_limit > 0 else 0,
        }

    async def reset_budget(self, curator_id: str) -> None:
        """
        Manually reset budget (for testing/admin).

        Args:
            curator_id: Curator identifier
        """
        key = self._get_key(curator_id)
        await self.redis.delete(key)

    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.aclose()


async def check_and_record_tokens(
    curator_id: str,
    estimated_tokens: int,
    actual_tokens: Optional[int] = None,
    critical: bool = False,
) -> None:
    """
    Helper function to check budget before operation and record after.

    Args:
        curator_id: Curator identifier
        estimated_tokens: Estimated tokens (for pre-check)
        actual_tokens: Actual tokens used (for recording, defaults to estimated)
        critical: If True, allow use of buffer

    Raises:
        TokenBudgetExceeded: If budget exceeded
    """
    manager = TokenBudgetManager()
    try:
        # Pre-check
        if not await manager.check_budget(curator_id, estimated_tokens, critical):
            raise TokenBudgetExceeded(
                f"Insufficient token budget for operation requiring {estimated_tokens} tokens"
            )

        # Record actual usage
        tokens_to_record = actual_tokens if actual_tokens is not None else estimated_tokens
        await manager.record_usage(curator_id, tokens_to_record)

    finally:
        await manager.close()
