"""
CoinGecko adapter for crypto market data.
"""
import logging
from typing import Optional
from interfaces.api.services.ia.key_manager import key_manager

logger = logging.getLogger(__name__)

class CoinGeckoAdapter:
    """CoinGecko API adapter for market data."""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.pro_url = "https://pro-api.coingecko.com/api/v3"
        self.timeout = 15
        self.api_key = None
        self.is_pro = False
        self._validate_key()
    
    def _validate_key(self):
        """Validate CoinGecko API key."""
        self.api_key = key_manager.get_coingecko_key()
        
        if self.api_key:
            self.is_pro = True
            logger.info("CoinGecko adapter initialized with Pro API key")
        else:
            logger.info("CoinGecko adapter initialized with free tier (rate limited)")
    
    def get_headers(self) -> dict:
        """Get request headers for CoinGecko API."""
        headers = {
            'accept': 'application/json',
            'User-Agent': 'MaverettaBot/1.0'
        }
        
        if self.api_key and self.is_pro:
            headers['x-cg-pro-api-key'] = self.api_key
        
        return headers
    
    def get_base_url(self) -> str:
        """Get appropriate base URL (pro vs free)."""
        return self.pro_url if self.is_pro else self.base_url
    
    def is_available(self) -> bool:
        """Check if adapter is available."""
        return True  # CoinGecko has free tier, always available
    
    def get_rate_limits(self) -> dict:
        """Get rate limit info based on tier."""
        if self.is_pro:
            return {
                'requests_per_minute': 500,
                'monthly_calls': 10000,
                'tier': 'pro'
            }
        else:
            return {
                'requests_per_minute': 10,
                'monthly_calls': None,
                'tier': 'free'
            }
    
    def get_config(self) -> dict:
        """Get adapter configuration."""
        return {
            'provider': 'coingecko',
            'base_url': self.get_base_url(),
            'timeout': self.timeout,
            'key_type': 'direct',
            'available': self.is_available(),
            'is_pro': self.is_pro,
            'rate_limits': self.get_rate_limits()
        }

# Global instance
coingecko_adapter = CoinGeckoAdapter()