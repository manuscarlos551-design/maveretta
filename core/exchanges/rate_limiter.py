"""Rate limiter for exchange API calls - P1 Implementation"""

import asyncio
import time
from collections import deque
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make request"""
        async with self._lock:
            now = time.time()
            
            # Remove old requests
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # Check limit
            if len(self.requests) >= self.max_requests:
                sleep_time = self.window_seconds - (now - self.requests[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            self.requests.append(now)

# Global rate limiters by exchange
_limiters: Dict[str, RateLimiter] = {
    'binance': RateLimiter(max_requests=1200, window_seconds=60),
    'kucoin': RateLimiter(max_requests=100, window_seconds=10),
    'bybit': RateLimiter(max_requests=120, window_seconds=60),
    'coinbase': RateLimiter(max_requests=10, window_seconds=1),
    'okx': RateLimiter(max_requests=20, window_seconds=2),
}

async def rate_limit(exchange: str):
    """Apply rate limit for exchange"""
    limiter = _limiters.get(exchange.lower())
    if limiter:
        await limiter.acquire()
    else:
        logger.warning(f"No rate limiter configured for {exchange}")

# Usage example:
# await rate_limit('binance')
# response = await exchange.fetch_ticker('BTC/USDT')
