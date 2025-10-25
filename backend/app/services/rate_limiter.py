"""
Rate Limiter Service for API calls
Protects against exceeding free tier limits for services like Groq
"""
import time
import asyncio
import logging
from typing import Dict, Optional
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_minute: int = 25  # Groq free tier: 30 RPM (we use 25 for safety)
    requests_per_day: int = 10000  # Groq free tier: 14,400 RPD (we use 10,000 for safety)
    retry_attempts: int = 3
    retry_delay: float = 2.0  # seconds
    enabled: bool = True


@dataclass
class RateLimitState:
    """State tracker for rate limiting"""
    minute_requests: deque = field(default_factory=deque)
    day_requests: deque = field(default_factory=deque)
    last_cleanup: datetime = field(default_factory=datetime.now)


class RateLimiter:
    """
    Rate limiter with sliding window algorithm
    Thread-safe implementation for concurrent requests
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.state = RateLimitState()
        self._lock = asyncio.Lock()

        logger.info(
            f"Rate limiter initialized: "
            f"{self.config.requests_per_minute} RPM, "
            f"{self.config.requests_per_day} RPD, "
            f"Enabled: {self.config.enabled}"
        )

    async def acquire(self, resource: str = "default") -> bool:
        """
        Acquire permission to make a request
        Blocks until rate limit allows the request

        Returns:
            bool: True if request is allowed, False if disabled
        """
        if not self.config.enabled:
            return True

        async with self._lock:
            now = datetime.now()

            # Clean up old requests
            self._cleanup_old_requests(now)

            # Check rate limits
            while True:
                minute_count = len(self.state.minute_requests)
                day_count = len(self.state.day_requests)

                # Check if we're within limits
                if (minute_count < self.config.requests_per_minute and
                    day_count < self.config.requests_per_day):
                    # Record this request
                    self.state.minute_requests.append(now)
                    self.state.day_requests.append(now)

                    logger.debug(
                        f"Rate limit OK - Minute: {minute_count + 1}/{self.config.requests_per_minute}, "
                        f"Day: {day_count + 1}/{self.config.requests_per_day}"
                    )
                    return True

                # Calculate wait time
                wait_time = self._calculate_wait_time(now)

                logger.warning(
                    f"Rate limit reached - Minute: {minute_count}/{self.config.requests_per_minute}, "
                    f"Day: {day_count}/{self.config.requests_per_day}. "
                    f"Waiting {wait_time:.2f}s..."
                )

                # Wait and retry
                await asyncio.sleep(wait_time)
                now = datetime.now()
                self._cleanup_old_requests(now)

    def _cleanup_old_requests(self, now: datetime):
        """Remove requests outside the sliding windows"""
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)

        # Clean minute window
        while self.state.minute_requests and self.state.minute_requests[0] < minute_ago:
            self.state.minute_requests.popleft()

        # Clean day window
        while self.state.day_requests and self.state.day_requests[0] < day_ago:
            self.state.day_requests.popleft()

    def _calculate_wait_time(self, now: datetime) -> float:
        """Calculate how long to wait before next request"""
        wait_times = []

        # Check minute limit
        if len(self.state.minute_requests) >= self.config.requests_per_minute:
            oldest_minute = self.state.minute_requests[0]
            minute_wait = 60 - (now - oldest_minute).total_seconds() + 1
            if minute_wait > 0:
                wait_times.append(minute_wait)

        # Check day limit
        if len(self.state.day_requests) >= self.config.requests_per_day:
            oldest_day = self.state.day_requests[0]
            day_wait = 86400 - (now - oldest_day).total_seconds() + 1
            if day_wait > 0:
                wait_times.append(day_wait)

        return max(wait_times) if wait_times else 1.0

    async def execute_with_retry(self, func, *args, **kwargs):
        """
        Execute a function with rate limiting and retry logic

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result from the function

        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None

        for attempt in range(self.config.retry_attempts):
            try:
                # Wait for rate limit permission
                await self.acquire()

                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                return result

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()

                # Check if it's a rate limit error
                if any(term in error_msg for term in ['rate limit', 'too many requests', '429']):
                    wait_time = self.config.retry_delay * (attempt + 1)
                    logger.warning(
                        f"Rate limit error (attempt {attempt + 1}/{self.config.retry_attempts}). "
                        f"Waiting {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    continue

                # For other errors, raise immediately
                logger.error(f"Function execution failed: {e}")
                raise

        # All retries exhausted
        logger.error(f"All {self.config.retry_attempts} retry attempts failed")
        raise last_error

    def get_stats(self) -> Dict[str, int]:
        """Get current rate limit statistics"""
        now = datetime.now()
        self._cleanup_old_requests(now)

        return {
            "requests_last_minute": len(self.state.minute_requests),
            "requests_last_day": len(self.state.day_requests),
            "minute_limit": self.config.requests_per_minute,
            "day_limit": self.config.requests_per_day,
            "minute_remaining": max(0, self.config.requests_per_minute - len(self.state.minute_requests)),
            "day_remaining": max(0, self.config.requests_per_day - len(self.state.day_requests)),
        }

    def reset(self):
        """Reset the rate limiter state"""
        self.state = RateLimitState()
        logger.info("Rate limiter state reset")


# Global rate limiter instances
_groq_rate_limiter: Optional[RateLimiter] = None


def get_groq_rate_limiter() -> RateLimiter:
    """Get or create the global Groq rate limiter"""
    global _groq_rate_limiter

    if _groq_rate_limiter is None:
        from ..config import settings

        config = RateLimitConfig(
            requests_per_minute=getattr(settings, 'GROQ_RATE_LIMIT_RPM', 25),
            requests_per_day=getattr(settings, 'GROQ_RATE_LIMIT_RPD', 10000),
            enabled=getattr(settings, 'GROQ_RATE_LIMIT_ENABLED', True),
            retry_attempts=3,
            retry_delay=2.0
        )

        _groq_rate_limiter = RateLimiter(config)
        logger.info("Global Groq rate limiter created")

    return _groq_rate_limiter


def reset_groq_rate_limiter():
    """Reset the global Groq rate limiter (useful for testing)"""
    global _groq_rate_limiter
    if _groq_rate_limiter:
        _groq_rate_limiter.reset()
