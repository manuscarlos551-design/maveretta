"""HTTP connection pool manager - P1 Implementation"""

import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class HTTPPoolManager:
    """Manages HTTP connection pools for better performance"""
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
    
    async def initialize(self):
        """Initialize connection pool"""
        if self._session is None:
            # Create connector with connection pooling
            self._connector = aiohttp.TCPConnector(
                limit=100,  # Max total connections
                limit_per_host=20,  # Max connections per host
                ttl_dns_cache=300,  # DNS cache for 5 minutes
                keepalive_timeout=60,  # Keep connections alive for 60s
                force_close=False,  # Reuse connections
                enable_cleanup_closed=True
            )
            
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=self._timeout,
                headers={
                    'User-Agent': 'Maveretta-Bot/1.0'
                }
            )
            
            logger.info("HTTP connection pool initialized")
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """GET request using pool"""
        if self._session is None:
            await self.initialize()
        
        return await self._session.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """POST request using pool"""
        if self._session is None:
            await self.initialize()
        
        return await self._session.post(url, **kwargs)
    
    async def close(self):
        """Close connection pool"""
        if self._session:
            await self._session.close()
            self._session = None
        
        if self._connector:
            await self._connector.close()
            self._connector = None
        
        logger.info("HTTP connection pool closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        if self._session and not self._session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except Exception as e:
                logger.error(f"Error closing HTTP pool: {e}")

# Global pool instance
http_pool = HTTPPoolManager()

async def get_http_pool() -> HTTPPoolManager:
    """Get global HTTP pool instance"""
    if http_pool._session is None:
        await http_pool.initialize()
    return http_pool
