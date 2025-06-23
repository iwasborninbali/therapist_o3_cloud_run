import asyncio
import logging
import time
import functools
from typing import Callable, TypeVar, cast
from config import config
import ssl
import requests
from google.auth.exceptions import TransportError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Define retryable exceptions that commonly occur with SSL/network issues
RETRYABLE_EXCEPTIONS = (
    ssl.SSLError,
    ssl.SSLEOFError,
    requests.exceptions.SSLError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    TransportError,
    ConnectionResetError,
    ConnectionAbortedError,
)

def is_retryable_error(exception: Exception) -> bool:
    """Check if an exception is retryable"""
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True
    
    # Check for specific SSL error messages
    error_str = str(exception).lower()
    ssl_keywords = [
        'ssl',
        'certificate',
        'handshake',
        'connection reset',
        'connection aborted',
        'eof occurred in violation',
        'oauth2.googleapis.com',
        'unexpected_eof_while_reading'
    ]
    
    return any(keyword in error_str for keyword in ssl_keywords)


def get_retry_delay(attempt: int, base_delay: float, exception: Exception) -> float:
    """Calculate retry delay with exponential backoff"""
    if is_retryable_error(exception):
        # Shorter delays for retryable errors
        return min(base_delay * (1.5 ** (attempt - 1)), 30.0)
    else:
        # Standard exponential backoff for other errors
        return base_delay * (2 ** (attempt - 1))


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
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # If we're retrying and succeed, log the success
                    if attempt > 1:
                        logger.info(
                            f"Successfully executed {func.__name__} "
                            f"on attempt {attempt}"
                        )
                    
                    return result
                
                except Exception as e:
                    last_exception = e
                    
                    # Don't sleep if this is the last attempt
                    if attempt < max_attempts:
                        delay = get_retry_delay(attempt, base_delay, e)
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
            raise last_exception
        
        return wrapper
    
    return decorator


def retry_async(
    max_attempts: int = 2,  # Reduced from 3 to 2 for faster failures
    base_delay: float = 1.0,
    max_delay: float = 60.0,  # Reduced from default to prevent long delays
    exponential_base: float = 2.0,
    exceptions: tuple = None,
):
    """
    Async retry decorator with exponential backoff and jitter.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 2, reduced for Cloud Run)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0, reduced for Cloud Run)
        exponential_base: Base for exponential backoff (default: 2.0)
        exceptions: Tuple of exception types to retry on (default: retryable exceptions)
    """
    if exceptions is None:
        # Only retry on specific exceptions, not all exceptions
        exceptions = RETRYABLE_EXCEPTIONS + (
            # Add OpenAI specific exceptions that might be retryable
            TimeoutError,
            ConnectionError,
        )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts. "
                            f"Final error: {e}"
                        )
                        raise
                    
                    # Only log retryable errors, not all exceptions
                    if is_retryable_error(e):
                        logger.warning(
                            f"Retryable error in {func.__name__} (attempt {attempt + 1}/{max_attempts}): {e}"
                        )
                    else:
                        logger.warning(
                            f"Error in {func.__name__} (attempt {attempt + 1}/{max_attempts}): {e}"
                        )
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    jittered_delay = delay * (0.5 + 0.5 * (hash(str(args) + str(kwargs)) % 100) / 100)
                    
                    logger.info(f"Retrying {func.__name__} in {jittered_delay:.2f} seconds...")
                    await asyncio.sleep(jittered_delay)
                except Exception as e:
                    # For non-retryable exceptions, fail immediately
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            # This should never be reached due to the raise in the loop
            if last_exception:
                raise last_exception
            
        return cast(Callable[..., T], wrapper)
    return decorator
