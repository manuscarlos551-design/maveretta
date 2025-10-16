"""
Claude adapter using Emergent LLM key system.
"""
import logging
from typing import Optional
from interfaces.api.services.ia.key_manager import key_manager

logger = logging.getLogger(__name__)

class ClaudeAdapter:
    """Claude API adapter using Emergent system."""
    
    def __init__(self):
        self.base_url = "https://api.anthropic.com/v1"
        self.timeout = 30
        self.api_key = None
        self._validate_key()
    
    def _validate_key(self):
        """Validate Emergent LLM key for Claude access."""
        self.api_key = key_manager.get_claude_key()
        if not self.api_key:
            logger.error("Claude adapter initialization failed - missing Emergent LLM key", 
                        extra={"source": "IA", "code": "apikey_missing"})
            raise ValueError("Claude adapter requires Emergent LLM key")
        
        # Validate format - Emergent keys start with sk-emergent-
        if not self.api_key.startswith('sk-emergent-'):
            logger.error("Invalid Emergent LLM key format for Claude", 
                        extra={"source": "IA", "code": "apikey_format_error"})
            raise ValueError("Invalid Emergent LLM key format")
        
        logger.info("Claude adapter initialized with Emergent LLM key")
    
    def get_headers(self) -> dict:
        """Get request headers for Claude API."""
        if not self.api_key:
            raise ValueError("API key not available")
        
        return {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01',
            'User-Agent': 'MaverettaBot/1.0'
        }
    
    def is_available(self) -> bool:
        """Check if adapter is available (has valid key)."""
        return self.api_key is not None
    
    def get_config(self) -> dict:
        """Get adapter configuration."""
        return {
            'provider': 'claude',
            'base_url': self.base_url,
            'timeout': self.timeout,
            'key_type': 'emergent_llm',
            'available': self.is_available()
        }

# Global instance
claude_adapter = ClaudeAdapter()