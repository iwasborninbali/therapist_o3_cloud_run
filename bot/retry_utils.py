import asyncio
import logging
import time
import functools
from typing import Callable, TypeVar, cast
from config import config

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_async(max_attempts: int = None, base_delay: float = None):
    """
    Decorator for asynchronous functions to retry with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff in seconds

    Returns:
        Decorated function
    """
    # Use config values if parameters not provided
    max_attempts = max_attempts or config.RETRY_ATTEMPTS
    base_delay = base_delay or config.RETRY_BASE_DELAY

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)

                    # If we're retrying and succeed, log the success
                    if attempt > 1:
                        logger.info(
                            f"Successfully executed {func.__name__} "
                            f"on attempt {attempt}")

                    return result

                except Exception as e:
                    last_exception = e

                    # Don't sleep if this is the last attempt
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        log_message = (
                            f"Attempt {attempt}/{max_attempts} for {func.__name__} "
                            f"failed with error: {str(e)}. Retrying in {delay:.2f}s"
                        )
                        logger.warning(log_message)
                        await asyncio.sleep(delay)
                    else:
                        log_message = (
                            f"All {max_attempts} attempts for {func.__name__} "
                            f"failed. Last error: {str(e)}"
                        )
                        logger.error(log_message)

            # All attempts failed
            raise last_exception

        return wrapper
    return decorator


def retry_sync(max_attempts: int = None, base_delay: float = None):
    """
    Decorator for synchronous functions to retry with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff in seconds

    Returns:
        Decorated function
    """
    # Use config values if parameters not provided
    max_attempts = max_attempts or config.RETRY_ATTEMPTS
    base_delay = base_delay or config.RETRY_BASE_DELAY

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)

                    # If we're retrying and succeed, log the success
                    if attempt > 1:
                        logger.info(
                            f"Successfully executed {func.__name__} "
                            f"on attempt {attempt}")

                    return result

                except Exception as e:
                    last_exception = e

                    # Don't sleep if this is the last attempt
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        log_message = (
                            f"Attempt {attempt}/{max_attempts} for {func.__name__} "
                            f"failed with error: {str(e)}. Retrying in {delay:.2f}s"
                        )
                        logger.warning(log_message)
                        time.sleep(delay)
                    else:
                        log_message = (
                            f"All {max_attempts} attempts for {func.__name__} "
                            f"failed. Last error: {str(e)}"
                        )
                        logger.error(log_message)

            # All attempts failed
            if last_exception:
                raise last_exception
            # This should never happen but makes type checker happy
            return cast(T, None)

        return wrapper
    return decorator
