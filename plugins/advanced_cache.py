#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Cache Plugin - Bot AI Trading
Sistema de cache avançado com Redis, TTL e invalidação inteligente
"""

import json
import logging
import pickle
from typing import Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import redis
from functools import wraps
import hashlib
from .base.plugin_interface import IPlugin

logger = logging.getLogger(__name__)

class AdvancedCachePlugin(IPlugin):
    """
    Plugin de Cache Avançado com Redis
    """
    
    def __init__(self):
        """Inicializa o plugin de cache"""
        self.name = "AdvancedCachePlugin"
        self.version = "1.0.0"
        self.description = "Sistema de cache avançado com Redis e TTL inteligente"
        self.enabled = True
        self.redis_client = None
        self.memory_cache = {}  # Fallback em memória
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
        
        logger.info(f"🗄️ {self.name} v{self.version} initialized")
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informações do plugin"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "type": "performance",
            "dependencies": ["redis", "pickle"],
            "config": {
                "default_ttl": 300,
                "max_memory_cache_size": 1000,
                "compression_enabled": True
            }
        }
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Inicializa o sistema de cache"""
        
        try:
            # Configuração padrão
            default_config = {
                "redis_url": "redis://localhost:6379/0",
                "redis_password": None,
                "default_ttl": 300,  # 5 minutos
                "max_memory_cache_size": 1000,
                "compression_enabled": True,
                "key_prefix": "botai_cache:",
                "fallback_to_memory": True
            }
            
            if config:
                default_config.update(config)
            
            self.config = default_config
            
            # Configurar Redis
            try:
                redis_config = {
                    'url': default_config["redis_url"],
                    'decode_responses': False,  # Para suportar pickle
                    'socket_timeout': 5,
                    'socket_connect_timeout': 5,
                    'retry_on_timeout': True
                }
                
                if default_config.get("redis_password"):
                    redis_config['password'] = default_config["redis_password"]
                
                self.redis_client = redis.from_url(**redis_config)
                self.redis_client.ping()  # Teste de conexão
                logger.info("✅ Redis connection established for caching")
                
            except Exception as e:
                logger.warning(f"Redis not available, using memory cache: {e}")
                self.redis_client = None
                if not default_config.get("fallback_to_memory", True):
                    return False
            
            logger.info("✅ Advanced cache system initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing cache system: {e}")
            return False
    
    def _generate_key(self, key: str) -> str:
        """Gera chave de cache com prefix"""
        prefix = self.config.get("key_prefix", "botai_cache:")
        return f"{prefix}{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serializa valor para armazenamento"""
        
        try:
            if self.config.get("compression_enabled", True):
                return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                return json.dumps(value).encode('utf-8')
        except Exception as e:
            logger.error(f"Error serializing value: {e}")
            raise
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserializa valor do armazenamento"""
        
        try:
            # Tentar pickle primeiro (mais robusto)
            try:
                return pickle.loads(data)
            except:
                # Fallback para JSON
                return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error deserializing value: {e}")
            return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor do cache"""
        
        try:
            cache_key = self._generate_key(key)
            
            # Tentar Redis primeiro
            if self.redis_client:
                try:
                    data = self.redis_client.get(cache_key)
                    if data is not None:
                        value = self._deserialize_value(data)
                        self.cache_stats["hits"] += 1
                        return value
                except Exception as e:
                    logger.warning(f"Redis get error: {e}")
            
            # Fallback para cache em memória
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # Verificar TTL
                if entry["expires_at"] is None or entry["expires_at"] > datetime.now():
                    self.cache_stats["hits"] += 1
                    return entry["value"]
                else:
                    # Expirado, remover
                    del self.memory_cache[key]
            
            self.cache_stats["misses"] += 1
            return default
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.cache_stats["misses"] += 1
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Define valor no cache"""
        
        try:
            if ttl is None:
                ttl = self.config.get("default_ttl", 300)
            
            cache_key = self._generate_key(key)
            serialized_value = self._serialize_value(value)
            
            # Definir no Redis
            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, ttl, serialized_value)
                    self.cache_stats["sets"] += 1
                    return True
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")
            
            # Fallback para cache em memória
            expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
            
            # Verificar limite de tamanho
            max_size = self.config.get("max_memory_cache_size", 1000)
            if len(self.memory_cache) >= max_size:
                # Remover entrada mais antiga
                oldest_key = min(
                    self.memory_cache.keys(),
                    key=lambda k: self.memory_cache[k]["created_at"]
                )
                del self.memory_cache[oldest_key]
            
            self.memory_cache[key] = {
                "value": value,
                "created_at": datetime.now(),
                "expires_at": expires_at
            }
            
            self.cache_stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Remove valor do cache"""
        
        try:
            cache_key = self._generate_key(key)
            
            # Remover do Redis
            if self.redis_client:
                try:
                    self.redis_client.delete(cache_key)
                except Exception as e:
                    logger.warning(f"Redis delete error: {e}")
            
            # Remover da memória
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            self.cache_stats["deletes"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe no cache"""
        
        try:
            cache_key = self._generate_key(key)
            
            # Verificar Redis
            if self.redis_client:
                try:
                    return bool(self.redis_client.exists(cache_key))
                except Exception as e:
                    logger.warning(f"Redis exists error: {e}")
            
            # Verificar memória
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if entry["expires_at"] is None or entry["expires_at"] > datetime.now():
                    return True
                else:
                    del self.memory_cache[key]
            
            return False
            
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que correspondem ao padrão"""
        
        removed_count = 0
        
        try:
            # Redis
            if self.redis_client:
                try:
                    cache_pattern = self._generate_key(pattern)
                    keys = self.redis_client.keys(cache_pattern)
                    if keys:
                        removed_count += self.redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"Redis clear pattern error: {e}")
            
            # Memória
            keys_to_remove = [
                key for key in self.memory_cache.keys() 
                if pattern in key
            ]
            
            for key in keys_to_remove:
                del self.memory_cache[key]
                removed_count += 1
            
            self.cache_stats["deletes"] += removed_count
            return removed_count
            
        except Exception as e:
            logger.error(f"Clear pattern error: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Remove todos os valores do cache"""
        
        try:
            # Redis - apenas chaves com nosso prefix
            if self.redis_client:
                try:
                    prefix = self.config.get("key_prefix", "botai_cache:")
                    keys = self.redis_client.keys(f"{prefix}*")
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"Redis clear all error: {e}")
            
            # Memória
            self.memory_cache.clear()
            
            logger.info("✅ Cache cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Clear all error: {e}")
            return False
    
    def cache_decorator(self, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
        """Decorator para cache automático de funções"""
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Gerar chave de cache
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Chave baseada no nome da função e argumentos
                    args_str = json.dumps([str(arg) for arg in args], sort_keys=True)
                    kwargs_str = json.dumps(kwargs, sort_keys=True)
                    key_data = f"{func.__name__}:{args_str}:{kwargs_str}"
                    cache_key = hashlib.md5(key_data.encode()).hexdigest()
                
                # Verificar cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Executar função e cachear resultado
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        
        total_operations = sum(self.cache_stats.values())
        hit_rate = (self.cache_stats["hits"] / total_operations * 100) if total_operations > 0 else 0
        
        stats = {
            "operations": self.cache_stats,
            "hit_rate_percent": round(hit_rate, 2),
            "memory_cache_size": len(self.memory_cache),
            "redis_connected": self.redis_client is not None
        }
        
        # Estatísticas Redis
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_info"] = {
                    "used_memory": info.get("used_memory"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "connected_clients": info.get("connected_clients")
                }
            except Exception as e:
                stats["redis_info"] = {"error": str(e)}
        
        return stats
    
    def execute(self) -> Dict[str, Any]:
        """Executa verificações do sistema de cache"""
        
        try:
            status = {
                "plugin": self.name,
                "timestamp": datetime.now().isoformat(),
                "cache_enabled": self.enabled,
                "stats": self.get_stats()
            }
            
            # Teste de operação
            test_key = f"health_check_{datetime.now().timestamp()}"
            test_value = {"test": True, "timestamp": datetime.now().isoformat()}
            
            # Teste set/get
            if self.set(test_key, test_value, ttl=60):
                retrieved_value = self.get(test_key)
                if retrieved_value == test_value:
                    status["health_check"] = "passed"
                    self.delete(test_key)  # Limpar teste
                else:
                    status["health_check"] = "failed_retrieval"
            else:
                status["health_check"] = "failed_set"
            
            return status
            
        except Exception as e:
            logger.error(f"Error executing cache checks: {e}")
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
            
            self.memory_cache.clear()
            
            logger.info(f"🛑 {self.name} shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False

# Instância global do plugin
advanced_cache_plugin = AdvancedCachePlugin()

# Utilitários de conveniência
def setup_cache(config: Optional[Dict[str, Any]] = None):
    """Setup rápido de cache"""
    return advanced_cache_plugin.initialize(config)

def cache_get(key: str, default: Any = None):
    """Get do cache"""
    return advanced_cache_plugin.get(key, default)

def cache_set(key: str, value: Any, ttl: Optional[int] = None):
    """Set do cache"""
    return advanced_cache_plugin.set(key, value, ttl)

def cache_delete(key: str):
    """Delete do cache"""
    return advanced_cache_plugin.delete(key)

def cached(ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """Decorator de cache"""
    return advanced_cache_plugin.cache_decorator(ttl, key_func)