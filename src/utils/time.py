"""Time and retry utilities."""

import asyncio
import functools
from typing import Any, Callable, TypeVar

from src.app.config import config

T = TypeVar("T")


async def wait_seconds(seconds: float) -> None:
    """Wait for specified seconds."""
    await asyncio.sleep(seconds)


async def wait_with_timeout(
    coro: Any,
    timeout: float | None = None,
) -> Any:
    """Execute coroutine with timeout."""
    if timeout is None:
        timeout = config.BROWSER_TIMEOUT / 1000  # Convert ms to seconds
    return await asyncio.wait_for(coro, timeout=timeout)


class RetryError(Exception):
    """Raised when all retries are exhausted."""

    def __init__(self, message: str, last_error: Exception | None = None):
        super().__init__(message)
        self.last_error = last_error


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int | None = None,
    delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs: Any,
) -> Any:
    """Retry an async function with exponential backoff."""
    if max_retries is None:
        max_retries = config.MAX_RETRIES

    last_error: Exception | None = None
    current_delay = delay

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                raise RetryError(
                    f"Failed after {max_retries + 1} attempts: {e}",
                    last_error=last_error,
                )

    raise RetryError("Unexpected retry loop exit", last_error=last_error)


def with_retry(
    max_retries: int | None = None,
    delay: float = 1.0,
    backoff: float = 2.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for async retry logic."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_async(
                func,
                *args,
                max_retries=max_retries,
                delay=delay,
                backoff=backoff,
                **kwargs,
            )

        return wrapper

    return decorator
