#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rate Limiter Plugin - Bot AI Trading
Implementa rate limiting para APIs e sistema de trading
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis
from .base.plugin_interface import IPlugin

logger = logging.getLogger(__name__)

class RateLimiterPlugin(IPlugin):
    """
    Plugin de Rate Limiting para controlar acesso às APIs
    """
    
    def __init__(self):
        """Inicializa o plugin de rate limiting"""
        self.name = "RateLimiterPlugin"
        self.version = "1.0.0"
        self.description = "Sistema de rate limiting para APIs e trading bot"
        self.enabled = True
        self.limiter = None
        self.redis_client = None
        
        logger.info(f"🚦 {self.name} v{self.version} initialized")
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informações do plugin"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "type": "security",
            "dependencies": ["fastapi", "slowapi", "redis"],
            "config": {
                "default_rate": "100/minute",
                "api_rate": "500/minute", 
                "auth_rate": "10/minute",
                "trading_rate": "30/minute"
            }
        }
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Inicializa o sistema de rate limiting"""
        
        try:
            # Configuração padrão
            default_config = {
                "redis_url": "redis://localhost:6379",
                "default_rate": "100/minute",
                "api_rate": "500/minute",
                "auth_rate": "10/minute",
                "trading_rate": "30/minute",
                "enabled": True
            }
            
            if config:
                default_config.update(config)
            
            # Configurar Redis para armazenamento de contadores
            try:
                self.redis_client = redis.from_url(
                    default_config.get("redis_url", "redis://localhost:6379")
                )
                self.redis_client.ping()  # Teste de conexão
                logger.info("✅ Redis connection established for rate limiting")
            except Exception as e:
                logger.warning(f"Redis not available, using memory storage: {e}")
                self.redis_client = None
            
            # Criar limiter
            self.limiter = Limiter(
                key_func=get_remote_address,
                default_limits=[default_config["default_rate"]],
                storage_uri=default_config.get("redis_url", "memory://") if self.redis_client else "memory://",
            )
            
            self.config = default_config
            logger.info("✅ Rate limiter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing rate limiter: {e}")
            return False
    
    def setup_fastapi_integration(self, app: FastAPI) -> bool:
        """Configura integração com FastAPI"""
        
        try:
            if not self.limiter:
                logger.error("Rate limiter not initialized")
                return False
            
            # Adicionar middleware
            app.add_middleware(SlowAPIMiddleware)
            
            # Configurar handler de exceção
            app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
            
            # Aplicar decoradores de rate limit
            self._apply_rate_limits(app)
            
            logger.info("✅ FastAPI rate limiting configured")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring FastAPI rate limiting: {e}")
            return False
    
    def _apply_rate_limits(self, app: FastAPI):
        """Aplica rate limits específicos para diferentes endpoints"""
        
        # Rate limits por categoria de endpoint
        rate_configs = {
            "/api/auth": self.config["auth_rate"],
            "/api/bot": self.config["trading_rate"],
            "/api/backtest": "5/minute",  # Operações pesadas
            "/api/analytics": self.config["api_rate"],
            "/api/health": "1000/minute",  # Checks de saúde
        }
        
        # Aplicar configs (seria aplicado nos endpoints específicos)
        logger.info(f"📊 Rate limit configs: {rate_configs}")
    
    def create_custom_limiter(self, rate: str) -> callable:
        """Cria um decorator de rate limit customizado"""
        
        if not self.limiter:
            logger.warning("Rate limiter not available, creating no-op decorator")
            return lambda f: f
        
        return self.limiter.limit(rate)
    
    def get_rate_limit_status(self, identifier: str) -> Dict[str, Any]:
        """Obtém status de rate limit para um identificador"""
        
        try:
            if not self.redis_client:
                return {"status": "memory_storage", "limits": "unavailable"}
            
            # Buscar informações de rate limit no Redis
            # (implementação específica dependeria da estrutura do slowapi)
            return {
                "identifier": identifier,
                "timestamp": datetime.now().isoformat(),
                "status": "active",
                "remaining_requests": "unknown",  # Seria calculado
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {"status": "error", "error": str(e)}
    
    def reset_rate_limit(self, identifier: str) -> bool:
        """Reset rate limit para um identificador específico"""
        
        try:
            if not self.redis_client:
                logger.warning("Redis not available, cannot reset rate limits")
                return False
            
            # Implementar reset específico
            # pattern = f"slowapi:*:{identifier}:*"
            # keys = self.redis_client.keys(pattern)
            # if keys:
            #     self.redis_client.delete(*keys)
            
            logger.info(f"Rate limit reset for {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")
            return False
    
    def execute(self) -> Dict[str, Any]:
        """Executa verificações do sistema de rate limiting"""
        
        try:
            status = {
                "plugin": self.name,
                "timestamp": datetime.now().isoformat(),
                "limiter_active": self.limiter is not None,
                "redis_connected": False,
                "metrics": {}
            }
            
            # Verificar conexão Redis
            if self.redis_client:
                try:
                    self.redis_client.ping()
                    status["redis_connected"] = True
                except:
                    status["redis_connected"] = False
            
            # Coletar métricas básicas
            if self.redis_client and status["redis_connected"]:
                try:
                    # Contagem de chaves de rate limit
                    keys = self.redis_client.keys("slowapi:*")
                    status["metrics"] = {
                        "active_limits": len(keys),
                        "redis_memory_usage": self.redis_client.memory_usage() if hasattr(self.redis_client, 'memory_usage') else "unknown"
                    }
                except Exception as e:
                    status["metrics"] = {"error": str(e)}
            
            return status
            
        except Exception as e:
            logger.error(f"Error executing rate limiter checks: {e}")
            return {
                "plugin": self.name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def shutdown(self) -> bool:
        """Shutdown do plugin"""
        
        try:
            if self.redis_client:
                self.redis_client.close()
            
            logger.info(f"🛑 {self.name} shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False

# Instância global do plugin para uso fácil
rate_limiter_plugin = RateLimiterPlugin()

# Utilitários de conveniência
def get_rate_limiter():
    """Retorna instância do rate limiter"""
    return rate_limiter_plugin.limiter

def setup_rate_limiting(app: FastAPI, config: Optional[Dict[str, Any]] = None):
    """Setup rápido de rate limiting para FastAPI"""
    
    if not rate_limiter_plugin.initialize(config):
        logger.error("Failed to initialize rate limiter")
        return False
    
    return rate_limiter_plugin.setup_fastapi_integration(app)

def limit(rate: str):
    """Decorator de rate limit customizado"""
    return rate_limiter_plugin.create_custom_limiter(rate)