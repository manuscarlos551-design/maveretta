"""LLM timeout wrapper - P1 Implementation"""

import asyncio
import logging
from typing import Callable, Any, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

DEFAULT_LLM_TIMEOUT = 30  # 30 seconds

def with_timeout(timeout: int = DEFAULT_LLM_TIMEOUT):
    """Decorator to add timeout to LLM calls"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Tuple[bool, Any, str]:
            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
                return result
            except asyncio.TimeoutError:
                logger.error(f"{func.__name__} timed out after {timeout}s")
                return False, None, f"LLM call timed out after {timeout}s"
            except Exception as e:
                logger.error(f"{func.__name__} failed: {e}")
                return False, None, str(e)
        
        return wrapper
    return decorator

async def call_with_timeout(coro, timeout: int = DEFAULT_LLM_TIMEOUT):
    """Call coroutine with timeout
    
    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
    
    Returns:
        Tuple of (success, result, error_message)
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return True, result, ""
    except asyncio.TimeoutError:
        logger.error(f"Coroutine timed out after {timeout}s")
        return False, None, f"Operation timed out after {timeout}s"
    except Exception as e:
        logger.error(f"Coroutine failed: {e}")
        return False, None, str(e)
