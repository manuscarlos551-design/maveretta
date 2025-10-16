# core/market/streams.py
"""Market Event Streams - Asynchronous event queue for market data

Provides async queue for market events (price moves, volume spikes, etc.)
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MarketEventStream:
    """Manages async queue for market events"""
    
    def __init__(self, maxsize: int = 1000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.running = False
        
        logger.info(f"MarketEventStream initialized (maxsize={maxsize})")
    
    async def publish(self, event: Dict[str, Any]):
        """Publish event to queue
        
        Args:
            event: Event dictionary with 'type', 'symbol', and other fields
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in event:
                event['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            await self.queue.put(event)
            
            logger.debug(f"Event published: {event.get('type')}")
            
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event")
    
    async def consume(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Consume event from queue
        
        Args:
            timeout: Timeout in seconds
        
        Returns:
            Event dictionary or None if timeout
        """
        try:
            event = await asyncio.wait_for(
                self.queue.get(),
                timeout=timeout
            )
            return event
            
        except asyncio.TimeoutError:
            return None
    
    def qsize(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()


# Global stream instance
market_stream = MarketEventStream()
