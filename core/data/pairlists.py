# core/data/pairlists.py
"""
Pairlists - Sistema de seleção de pares para trading
Adaptado do Freqtrade PairListManager
"""
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import ccxt
import redis
import json

logger = logging.getLogger(__name__)

class PairListManager:
    """Gerenciador de listas de pares para trading"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.exchange_instances = {}
        
        # Configuração padrão
        self.config = {
            'top_volume_pairs': 20,
            'min_volume_usdt': 100000,  # Volume mínimo 24h em USDT
            'blacklisted_pairs': ['USDT/USD', 'BUSD/USDT'],
            'whitelisted_pairs': [],
            'quote_currencies': ['USDT', 'BTC', 'ETH'],
            'cache_ttl_minutes': 60
        }
    
    def _get_redis_client(self):
        """Obtém cliente Redis"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            return redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Erro ao conectar Redis para pairlists: {e}")
            return None
    
    def _get_exchange(self, exchange_id: str = "binance") -> ccxt.Exchange:
        """Obtém instância da exchange (com cache)"""
        if exchange_id not in self.exchange_instances:
            if exchange_id == "binance":
                self.exchange_instances[exchange_id] = ccxt.binance({
                    'sandbox': False,
                    'enableRateLimit': True,
                    'timeout': 10000
                })
            elif exchange_id == "kucoin":
                self.exchange_instances[exchange_id] = ccxt.kucoin({
                    'sandbox': False,
                    'enableRateLimit': True,
                    'timeout': 10000
                })
            elif exchange_id == "bybit":
                self.exchange_instances[exchange_id] = ccxt.bybit({
                    'sandbox': False,
                    'enableRateLimit': True,
                    'timeout': 10000
                })
            else:
                # Default para Binance
                self.exchange_instances[exchange_id] = ccxt.binance({
                    'sandbox': False,
                    'enableRateLimit': True,
                    'timeout': 10000
                })
        
        return self.exchange_instances[exchange_id]
    
    async def get_top_volume_pairs(
        self,
        exchange: str = "binance",
        quote_currency: str = "USDT",
        limit: int = 20
    ) -> List[str]:
        """
        Obtém pares com maior volume de negociação
        
        Args:
            exchange: Exchange para buscar dados
            quote_currency: Moeda quote (USDT, BTC, etc)
            limit: Número máximo de pares
            
        Returns:
            Lista de pares ordenados por volume
        """
        try:
            # Verificar cache primeiro
            cache_key = f"pairlist:volume:{exchange}:{quote_currency}:{limit}"
            
            if self.redis_client:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    cached_pairs = json.loads(cached_data)
                    logger.debug(f"Usando pairlist do cache: {len(cached_pairs)} pares")
                    return cached_pairs
            
            # Buscar da exchange
            exchange_instance = self._get_exchange(exchange)
            
            # Carregar mercados
            markets = await exchange_instance.load_markets()
            
            # Buscar tickers para volume
            tickers = await exchange_instance.fetch_tickers()
            
            # Filtrar e ordenar por volume
            volume_pairs = []
            
            for symbol, market in markets.items():
                # Filtros básicos
                if not market.get('active', True):
                    continue
                
                if market['quote'] != quote_currency:
                    continue
                
                if symbol in self.config['blacklisted_pairs']:
                    continue
                
                # Verificar ticker
                ticker = tickers.get(symbol)
                if not ticker:
                    continue
                
                volume_quote = ticker.get('quoteVolume', 0)
                if volume_quote and volume_quote > self.config['min_volume_usdt']:
                    volume_pairs.append({
                        'symbol': symbol,
                        'volume': volume_quote,
                        'price': ticker.get('last', 0)
                    })
            
            # Ordenar por volume decrescente
            volume_pairs.sort(key=lambda x: x['volume'], reverse=True)
            
            # Extrair apenas símbolos
            top_pairs = [pair['symbol'] for pair in volume_pairs[:limit]]
            
            # Salvar no cache
            if self.redis_client and top_pairs:
                ttl_seconds = self.config['cache_ttl_minutes'] * 60
                self.redis_client.setex(cache_key, ttl_seconds, json.dumps(top_pairs))
            
            logger.info(f"Obtidos {len(top_pairs)} pares por volume da {exchange}")
            return top_pairs
            
        except Exception as e:
            logger.error(f"Erro ao obter pares por volume: {e}")
            return self._get_fallback_pairs(quote_currency)
    
    async def get_trending_pairs(
        self,
        exchange: str = "binance",
        quote_currency: str = "USDT",
        limit: int = 15
    ) -> List[str]:
        """
        Obtém pares em tendência (maior variação de preço 24h)
        
        Args:
            exchange: Exchange
            quote_currency: Moeda quote
            limit: Número de pares
            
        Returns:
            Lista de pares em tendência
        """
        try:
            # Verificar cache
            cache_key = f"pairlist:trending:{exchange}:{quote_currency}:{limit}"
            
            if self.redis_client:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            
            # Buscar da exchange
            exchange_instance = self._get_exchange(exchange)
            
            markets = await exchange_instance.load_markets()
            tickers = await exchange_instance.fetch_tickers()
            
            # Filtrar e ordenar por variação percentual
            trending_pairs = []
            
            for symbol, market in markets.items():
                if not market.get('active', True):
                    continue
                
                if market['quote'] != quote_currency:
                    continue
                
                if symbol in self.config['blacklisted_pairs']:
                    continue
                
                ticker = tickers.get(symbol)
                if not ticker:
                    continue
                
                percentage_change = ticker.get('percentage')
                volume_quote = ticker.get('quoteVolume', 0)
                
                # Filtrar por volume mínimo e variação significativa
                if (volume_quote and volume_quote > self.config['min_volume_usdt'] * 0.5 and
                    percentage_change is not None and abs(percentage_change) > 2):
                    
                    trending_pairs.append({
                        'symbol': symbol,
                        'change': abs(percentage_change),
                        'volume': volume_quote,
                        'direction': 'up' if percentage_change > 0 else 'down'
                    })
            
            # Ordenar por variação decrescente
            trending_pairs.sort(key=lambda x: x['change'], reverse=True)
            
            # Extrair símbolos
            trending_symbols = [pair['symbol'] for pair in trending_pairs[:limit]]
            
            # Cache
            if self.redis_client and trending_symbols:
                ttl_seconds = 30 * 60  # Cache menor para trending (30min)
                self.redis_client.setex(cache_key, ttl_seconds, json.dumps(trending_symbols))
            
            logger.info(f"Obtidos {len(trending_symbols)} pares em tendência da {exchange}")
            return trending_symbols
            
        except Exception as e:
            logger.error(f"Erro ao obter pares trending: {e}")
            return self._get_fallback_pairs(quote_currency)[:limit]
    
    def get_static_pairlist(self, strategy: str = "balanced") -> List[str]:
        """
        Obtém lista estática de pares baseada na estratégia
        
        Args:
            strategy: Tipo de estratégia (balanced, conservative, aggressive)
            
        Returns:
            Lista de pares estáticos
        """
        try:
            # Listas pré-definidas por estratégia
            static_lists = {
                'conservative': [
                    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 
                    'XRP/USDT', 'SOL/USDT', 'DOT/USDT', 'LINK/USDT'
                ],
                'balanced': [
                    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT',
                    'SOL/USDT', 'DOT/USDT', 'DOGE/USDT', 'AVAX/USDT', 'MATIC/USDT',
                    'LINK/USDT', 'UNI/USDT', 'LTC/USDT', 'ATOM/USDT', 'FTM/USDT'
                ],
                'aggressive': [
                    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT',
                    'XRP/USDT', 'DOGE/USDT', 'AVAX/USDT', 'MATIC/USDT', 'SAND/USDT',
                    'MANA/USDT', 'GALA/USDT', 'ENJ/USDT', 'CHZ/USDT', 'ALICE/USDT',
                    'TLM/USDT', 'SLP/USDT', 'AXS/USDT', 'ICP/USDT', 'NEAR/USDT'
                ]
            }
            
            pairlist = static_lists.get(strategy, static_lists['balanced'])
            
            # Filtrar pares da blacklist
            filtered_pairlist = [
                pair for pair in pairlist 
                if pair not in self.config['blacklisted_pairs']
            ]
            
            return filtered_pairlist
            
        except Exception as e:
            logger.error(f"Erro ao obter pairlist estática: {e}")
            return self._get_fallback_pairs()
    
    async def get_adaptive_pairlist(
        self,
        exchange: str = "binance",
        strategy_type: str = "momentum",
        limit: int = 20
    ) -> List[str]:
        """
        Obtém pairlist adaptativa baseada na estratégia
        
        Args:
            exchange: Exchange
            strategy_type: Tipo de estratégia (momentum, mean_reversion, etc)
            limit: Número máximo de pares
            
        Returns:
            Lista adaptativa de pares
        """
        try:
            if strategy_type == "momentum":
                # Para momentum: combinar volume alto + trending
                volume_pairs = await self.get_top_volume_pairs(exchange, limit=limit//2)
                trending_pairs = await self.get_trending_pairs(exchange, limit=limit//2)
                
                # Combinar sem duplicatas
                adaptive_pairs = list(dict.fromkeys(volume_pairs + trending_pairs))[:limit]
                
            elif strategy_type == "mean_reversion":
                # Para mean reversion: focar em pares estáveis com volume
                volume_pairs = await self.get_top_volume_pairs(exchange, limit=limit)
                # Filtrar pares muito voláteis (seria implementado com lógica adicional)
                adaptive_pairs = volume_pairs
                
            elif strategy_type == "arbitrage":
                # Para arbitragem: pares com alta liquidez
                volume_pairs = await self.get_top_volume_pairs(exchange, limit=limit)
                adaptive_pairs = volume_pairs
                
            else:
                # Default: balanceado
                adaptive_pairs = self.get_static_pairlist("balanced")[:limit]
            
            logger.info(f"Pairlist adaptativa ({strategy_type}): {len(adaptive_pairs)} pares")
            return adaptive_pairs
            
        except Exception as e:
            logger.error(f"Erro ao gerar pairlist adaptativa: {e}")
            return self._get_fallback_pairs()[:limit]
    
    def _get_fallback_pairs(self, quote_currency: str = "USDT") -> List[str]:
        """Pares de fallback em caso de erro"""
        fallback_pairs = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT',
            'SOL/USDT', 'DOT/USDT', 'DOGE/USDT', 'AVAX/USDT', 'MATIC/USDT'
        ]
        
        # Filtrar por quote currency se diferente de USDT
        if quote_currency != "USDT":
            fallback_pairs = [pair.replace("/USDT", f"/{quote_currency}") for pair in fallback_pairs]
        
        return fallback_pairs
    
    def get_pairlist_info(self, pairlist: List[str]) -> Dict[str, Any]:
        """
        Obtém informações sobre uma pairlist
        
        Args:
            pairlist: Lista de pares
            
        Returns:
            Informações da pairlist
        """
        try:
            # Analisar quote currencies
            quote_currencies = {}
            for pair in pairlist:
                if '/' in pair:
                    quote = pair.split('/')[1]
                    quote_currencies[quote] = quote_currencies.get(quote, 0) + 1
            
            return {
                'total_pairs': len(pairlist),
                'quote_currencies': quote_currencies,
                'pairs': pairlist,
                'blacklisted_count': len([p for p in pairlist if p in self.config['blacklisted_pairs']]),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao analisar pairlist: {e}")
            return {'total_pairs': 0, 'pairs': [], 'error': str(e)}


# Instância global
pairlist_manager = PairListManager()