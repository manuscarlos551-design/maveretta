"""
Binance adapter for exchange data and trading.
"""
import logging
from typing import Optional, Tuple
from interfaces.api.services.ia.key_manager import key_manager

logger = logging.getLogger(__name__)

class BinanceAdapter:
    """Binance API adapter for trading and market data."""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.ws_url = "wss://stream.binance.com:9443/ws"
        self.testnet_url = "https://testnet.binance.vision/api/v3"
        self.timeout = 10
        self.api_key = None
        self.api_secret = None
        self.is_testnet = False
        self._validate_keys()
    
    def _validate_keys(self):
        """Validate Binance API key and secret."""
        self.api_key, self.api_secret = key_manager.get_binance_key()
        
        if not self.api_key or not self.api_secret:
            logger.warning("Binance adapter initialization - missing API keys (read-only mode)", 
                          extra={"source": "IA", "code": "apikey_missing"})
            return
        
        logger.info("Binance adapter initialized with API credentials")
    
    def get_headers(self) -> dict:
        """Get request headers for Binance API."""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MaverettaBot/1.0'
        }
        
        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key
        
        return headers
    
    def get_base_url(self) -> str:
        """Get appropriate base URL (mainnet vs testnet)."""
        return self.testnet_url if self.is_testnet else self.base_url
    
    def is_available(self) -> bool:
        """Check if adapter is available."""
        return True  # Binance has public endpoints, always available for market data
    
    def can_trade(self) -> bool:
        """Check if trading operations are available."""
        return self.api_key is not None and self.api_secret is not None
    
    def set_testnet(self, testnet: bool = True):
        """Enable/disable testnet mode."""
        self.is_testnet = testnet
        logger.info(f"Binance adapter: testnet mode {'enabled' if testnet else 'disabled'}")
    
    def get_permissions(self) -> list:
        """Get available permissions based on key configuration."""
        permissions = ['MARKET_DATA']  # Always available
        
        if self.can_trade():
            permissions.extend(['SPOT_TRADING', 'ACCOUNT_INFO', 'WITHDRAWALS'])
        
        return permissions
    
    def get_config(self) -> dict:
        """Get adapter configuration."""
        return {
            'provider': 'binance',
            'base_url': self.get_base_url(),
            'ws_url': self.ws_url,
            'timeout': self.timeout,
            'key_type': 'direct',
            'available': self.is_available(),
            'can_trade': self.can_trade(),
            'is_testnet': self.is_testnet,
            'permissions': self.get_permissions()
        }

# Global instance
binance_adapter = BinanceAdapter()