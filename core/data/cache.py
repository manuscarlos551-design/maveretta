# core/data/cache.py
"""
Cache System - Sistema de cache para dados OHLCV
Adaptado do Freqtrade DataProvider
"""
import logging
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import redis
import pandas as pd

logger = logging.getLogger(__name__)

class DataCache:
    """Cache Redis para dados OHLCV e métricas"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.default_ttl = 300  # 5 minutos
        
    def _get_redis_client(self):
        """Obtém cliente Redis"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            return redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Erro ao conectar Redis para cache: {e}")
            return None
    
    def _generate_key(self, symbol: str, timeframe: str, data_type: str = "ohlcv") -> str:
        """Gera chave Redis para os dados"""
        return f"cache:{data_type}:{symbol.replace('/', '_')}:{timeframe}"
    
    def get_ohlcv(self, symbol: str, timeframe: str) -> Optional[List[Dict]]:
        """Obtém dados OHLCV do cache"""
        if not self.redis_client:
            return None
            
        try:
            key = self._generate_key(symbol, timeframe)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Cache hit para {symbol} {timeframe}")
                return data.get('candles')
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao ler cache OHLCV: {e}")
            return None
    
    def set_ohlcv(self, symbol: str, timeframe: str, candles: List[Dict], ttl: Optional[int] = None) -> bool:
        """Armazena dados OHLCV no cache"""
        if not self.redis_client or not candles:
            return False
            
        try:
            key = self._generate_key(symbol, timeframe)
            cache_data = {
                'candles': candles,
                'cached_at': datetime.now().isoformat(),
                'symbol': symbol,
                'timeframe': timeframe,
                'count': len(candles)
            }
            
            ttl_seconds = ttl or self.default_ttl
            self.redis_client.setex(key, ttl_seconds, json.dumps(cache_data))
            
            logger.debug(f"Cache salvo para {symbol} {timeframe}: {len(candles)} candles")
            return True
            
        except Exception as e:
            logger.warning(f"Erro ao salvar cache OHLCV: {e}")
            return False
    
    def get_ticker(self, symbol: str, exchange: str = "binance") -> Optional[Dict]:
        """Obtém ticker do cache"""
        if not self.redis_client:
            return None
            
        try:
            key = f"cache:ticker:{exchange}:{symbol.replace('/', '_')}"
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao ler cache ticker: {e}")
            return None
    
    def set_ticker(self, symbol: str, ticker_data: Dict, exchange: str = "binance", ttl: int = 30) -> bool:
        """Armazena ticker no cache"""
        if not self.redis_client or not ticker_data:
            return False
            
        try:
            key = f"cache:ticker:{exchange}:{symbol.replace('/', '_')}"
            cache_data = {
                **ticker_data,
                'cached_at': datetime.now().isoformat(),
                'exchange': exchange
            }
            
            self.redis_client.setex(key, ttl, json.dumps(cache_data))
            return True
            
        except Exception as e:
            logger.warning(f"Erro ao salvar cache ticker: {e}")
            return False
    
    def invalidate_symbol(self, symbol: str, timeframe: Optional[str] = None) -> int:
        """Invalida cache para um símbolo"""
        if not self.redis_client:
            return 0
            
        try:
            if timeframe:
                # Invalidar timeframe específico
                key = self._generate_key(symbol, timeframe)
                return self.redis_client.delete(key)
            else:
                # Invalidar todos os timeframes do símbolo
                pattern = f"cache:*:{symbol.replace('/', '_')}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
                
        except Exception as e:
            logger.warning(f"Erro ao invalidar cache: {e}")
            return 0
    
    def clear_all(self) -> int:
        """Limpa todo o cache de dados"""
        if not self.redis_client:
            return 0
            
        try:
            keys = self.redis_client.keys("cache:*")
            if keys:
                return self.redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.warning(f"Erro ao limpar cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Estatísticas do cache"""
        if not self.redis_client:
            return {'status': 'disconnected'}
            
        try:
            # Contar chaves por tipo
            ohlcv_keys = len(self.redis_client.keys("cache:ohlcv:*"))
            ticker_keys = len(self.redis_client.keys("cache:ticker:*")) 
            other_keys = len(self.redis_client.keys("cache:*")) - ohlcv_keys - ticker_keys
            
            # Informações da conexão Redis
            info = self.redis_client.info()
            
            return {
                'status': 'connected',
                'keys': {
                    'ohlcv': ohlcv_keys,
                    'ticker': ticker_keys,
                    'other': other_keys,
                    'total': ohlcv_keys + ticker_keys + other_keys
                },
                'redis_info': {
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_human': info.get('used_memory_human', 'N/A'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                },
                'hit_rate': self._calculate_hit_rate(info),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do cache: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_hit_rate(self, redis_info: Dict) -> float:
        """Calcula taxa de hit do cache"""
        try:
            hits = redis_info.get('keyspace_hits', 0)
            misses = redis_info.get('keyspace_misses', 0)
            
            if hits + misses == 0:
                return 0.0
            
            return (hits / (hits + misses)) * 100
            
        except:
            return 0.0


# Instância global do cache
data_cache = DataCache()