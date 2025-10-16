"""
SentiaI adapter - placeholder for future integration.
"""
import logging
from typing import Optional
from interfaces.api.services.ia.key_manager import key_manager

logger = logging.getLogger(__name__)

class SentiaIAdapter:
    """SentiaI API adapter skeleton."""
    
    def __init__(self):
        self.base_url = "https://api.sentiai.com/v1"  # Placeholder URL
        self.timeout = 30
        self.api_key = None
        self._validate_key()
    
    def _validate_key(self):
        """Validate SentiaI API key."""
        self.api_key = key_manager.get_sentiai_key()
        if not self.api_key:
            logger.warning("SentiaI adapter initialization - no API key found", 
                          extra={"source": "IA", "code": "apikey_missing"})
            return
        
        logger.info("SentiaI adapter initialized")
    
    def get_headers(self) -> dict:
        """Get request headers for SentiaI API."""
        if not self.api_key:
            raise ValueError("SentiaI API key not available")
        
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'MaverettaBot/1.0'
        }
    
    def is_available(self) -> bool:
        """Check if adapter is available (has valid key)."""
        return self.api_key is not None
    
    def get_config(self) -> dict:
        """Get adapter configuration."""
        return {
            'provider': 'sentiai',
            'base_url': self.base_url,
            'timeout': self.timeout,
            'key_type': 'direct',
            'available': self.is_available()
        }

# Global instance  
sentiai_adapter = SentiaIAdapter()