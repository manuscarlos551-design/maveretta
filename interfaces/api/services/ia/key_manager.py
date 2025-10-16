"""
Central API key management using individual provider keys.
NO universal/emergent keys - only specific provider keys.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class KeyManager:
    """Central manager for all API keys using individual provider keys."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_openai_key(self) -> Optional[str]:
        """Get OpenAI key from environment."""
        key = os.environ.get('OPENAI_API_KEY')
        if not key:
            logger.error("OPENAI_API_KEY not found", extra={"source": "IA", "code": "apikey_missing"})
            return None
        if not self._validate_key_format(key, 'openai'):
            logger.error("Invalid OpenAI key format", extra={"source": "IA", "code": "apikey_format_error"})
            return None
        return key
    
    def get_claude_key(self) -> Optional[str]:
        """Get Claude key from environment."""
        key = os.environ.get('CLAUDE_API_KEY')
        if not key:
            logger.error("CLAUDE_API_KEY not found", extra={"source": "IA", "code": "apikey_missing"})
            return None
        if not self._validate_key_format(key, 'claude'):
            logger.error("Invalid Claude key format", extra={"source": "IA", "code": "apikey_format_error"})
            return None
        return key
    
    def get_sentiai_key(self) -> Optional[str]:
        """Get SentiaI key from environment."""
        key = os.environ.get('SENTIAI_API_KEY')
        if not key:
            logger.error("SENTIAI_API_KEY not found", extra={"source": "IA", "code": "apikey_missing"})
            return None
        if not self._validate_key_format(key, 'sentiai'):
            logger.error("Invalid SentiaI key format", extra={"source": "IA", "code": "apikey_format_error"})
            return None
        return key
    
    def get_coingecko_key(self) -> Optional[str]:
        """Get CoinGecko key from environment."""
        key = os.environ.get('COINGECKO_API_KEY')
        if not key:
            logger.warning("COINGECKO_API_KEY not found - using free tier", extra={"source": "IA", "code": "apikey_missing"})
            return None
        return key
    
    def get_binance_key(self) -> tuple[Optional[str], Optional[str]]:
        """Get Binance API key and secret."""
        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_API_SECRET')
        
        if not api_key:
            logger.error("BINANCE_API_KEY not found", extra={"source": "IA", "code": "apikey_missing"})
            return None, None
        
        if not api_secret:
            logger.error("BINANCE_API_SECRET not found", extra={"source": "IA", "code": "apikey_missing"})
            return None, None
            
        return api_key, api_secret
    
    def _validate_key_format(self, key: str, provider: str) -> bool:
        """Basic validation of API key formats."""
        if not key or len(key) < 10:
            return False
            
        # Basic format checks
        if provider == 'openai':
            return key.startswith('sk-')
        elif provider == 'claude':
            return key.startswith('sk-ant-')
        elif provider == 'sentiai':
            return key.startswith('sk-') or key.startswith('sia-')
        elif provider == 'coingecko':
            return len(key) >= 16  # CoinGecko keys are typically longer
        elif provider == 'binance':
            return len(key) >= 32  # Binance keys are typically 32+ chars
        
        return True
    
    def validate_all_keys(self) -> dict:
        """Validate all configured keys without external API calls."""
        validation_results = {
            'openai': bool(self.get_openai_key()),
            'claude': bool(self.get_claude_key()), 
            'sentiai': bool(self.get_sentiai_key()),
            'coingecko': bool(self.get_coingecko_key()),
            'binance': all(self.get_binance_key())
        }
        
        logger.info(f"Key validation results: {validation_results}")
        return validation_results
    
    def get_key_for_provider(self, provider: str) -> Optional[str]:
        """Get key for specific provider."""
        if provider == 'openai':
            return self.get_openai_key()
        elif provider == 'claude':
            return self.get_claude_key()
        elif provider == 'sentiai':
            return self.get_sentiai_key()
        elif provider == 'coingecko':
            return self.get_coingecko_key()
        elif provider == 'binance':
            api_key, _ = self.get_binance_key()
            return api_key
        else:
            logger.error(f"Unknown provider: {provider}", extra={"source": "IA", "code": "unknown_provider"})
            return None

# Global instance
key_manager = KeyManager()
