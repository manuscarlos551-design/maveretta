# core/orchestrator/llm_clients.py
"""LLM Client Manager - Real clients for Phase 4"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
import json

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'env_var': 'OPENAI_API_KEY',
        'models': ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4o']
    },
    'anthropic': {
        'name': 'Anthropic',
        'env_var': 'CLAUDE_API_KEY',
        'models': ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku']
    },
    'together': {
        'name': 'Together AI',
        'env_var': 'TOGETHER_API_KEY',
        'models': ['meta-llama/Llama-3-70b', 'mistralai/Mixtral-8x7B']
    }
}


class LLMClientManager:
    """Manager for LLM client connections - Phase 4: Real implementations"""
    
    def __init__(self):
        self.providers = SUPPORTED_PROVIDERS
        self._validated_providers = {}
        self._clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize real LLM clients based on available API keys"""
        for provider, config in self.providers.items():
            api_key = os.getenv(config['env_var'])
            if api_key and len(api_key) > 10:
                try:
                    if provider == 'openai':
                        self._init_openai_client(api_key)
                    elif provider == 'anthropic':
                        self._init_anthropic_client(api_key)
                    elif provider == 'together':
                        self._init_together_client(api_key)
                    
                    self._validated_providers[provider] = {
                        'env_var': config['env_var'],
                        'status': 'active'
                    }
                    logger.info(f"✅ {config['name']} client initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize {provider} client: {e}")
                    self._validated_providers[provider] = {
                        'env_var': config['env_var'],
                        'status': 'inactive',
                        'error': str(e)
                    }
            else:
                logger.info(f"ℹ️ {config['name']} API key not configured - agent will be inactive")
                self._validated_providers[provider] = {
                    'env_var': config['env_var'],
                    'status': 'inactive',
                    'error': 'API key not configured'
                }
    
    def _init_openai_client(self, api_key: str):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            self._clients['openai'] = OpenAI(api_key=api_key)
        except ImportError:
            logger.warning("openai package not installed")
            raise
    
    def _init_anthropic_client(self, api_key: str):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic
            self._clients['anthropic'] = Anthropic(api_key=api_key)
        except ImportError:
            logger.warning("anthropic package not installed")
            raise
    
    def _init_together_client(self, api_key: str):
        """Initialize Together AI client"""
        try:
            import requests
            # Together uses OpenAI-compatible API
            self._clients['together'] = {
                'api_key': api_key,
                'base_url': 'https://api.together.xyz/v1'
            }
        except Exception as e:
            logger.warning(f"Failed to setup together client: {e}")
            raise
    
    def validate_provider(self, provider: str, api_key_env: str) -> Tuple[bool, Optional[str]]:
        """Validate that a provider is supported and has valid credentials"""
        if provider not in self.providers:
            return False, f"Unsupported provider: {provider}"
        
        if provider in self._validated_providers:
            status = self._validated_providers[provider]['status']
            if status == 'active':
                return True, None
            else:
                error = self._validated_providers[provider].get('error', 'Unknown error')
                return False, f"Provider {provider} inactive: {error}"
        
        api_key = os.getenv(api_key_env)
        if not api_key or len(api_key) < 10:
            return False, f"API key {api_key_env} not configured or invalid"
        
        return True, None
    
    def call_llm(
        self,
        provider: str,
        model: str,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Call LLM and return response
        
        Args:
            provider: Provider name (openai, anthropic, together)
            model: Model name
            prompt: Prompt text
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
        
        Returns:
            Tuple of (success, response_text, error_message)
        """
        if provider not in self._clients:
            return False, None, f"Provider {provider} not initialized"
        
        try:
            if provider == 'openai':
                return self._call_openai(model, prompt, max_tokens, temperature)
            elif provider == 'anthropic':
                return self._call_anthropic(model, prompt, max_tokens, temperature)
            elif provider == 'together':
                return self._call_together(model, prompt, max_tokens, temperature)
            else:
                return False, None, f"Provider {provider} not implemented"
        except Exception as e:
            logger.error(f"Error calling {provider}: {e}")
            return False, None, str(e)
    
    def _call_openai(self, model: str, prompt: str, max_tokens: int, temperature: float) -> Tuple[bool, Optional[str], Optional[str]]:
        """Call OpenAI API"""
        try:
            client = self._clients['openai']
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a professional trading AI assistant. Always respond in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            return True, content, None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return False, None, str(e)
    
    def _call_anthropic(self, model: str, prompt: str, max_tokens: int, temperature: float) -> Tuple[bool, Optional[str], Optional[str]]:
        """Call Anthropic API"""
        try:
            client = self._clients['anthropic']
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = message.content[0].text
            return True, content, None
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return False, None, str(e)
    
    def _call_together(self, model: str, prompt: str, max_tokens: int, temperature: float) -> Tuple[bool, Optional[str], Optional[str]]:
        """Call Together AI API"""
        try:
            import requests
            
            config = self._clients['together']
            url = f"{config['base_url']}/chat/completions"
            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a professional trading AI assistant. Always respond in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            return True, content, None
        except Exception as e:
            logger.error(f"Together AI API error: {e}")
            return False, None, str(e)
    
    def parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response to extract JSON
        
        Args:
            response_text: Raw text response from LLM
        
        Returns:
            Parsed dictionary or None if parsing fails
        """
        if not response_text:
            return None
        
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                json_text = response_text[start:end].strip()
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    pass
            
            # Try to extract JSON from anywhere in the text
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Failed to parse LLM response as JSON: {response_text[:200]}...")
            return None
    
    def list_supported_providers(self) -> Dict[str, Any]:
        """List all supported providers"""
        return self.providers
    
    def get_validated_providers(self) -> Dict[str, Any]:
        """Get list of validated providers with status"""
        return self._validated_providers


# Global instance
llm_client_manager = LLMClientManager()
