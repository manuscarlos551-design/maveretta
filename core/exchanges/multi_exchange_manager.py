#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Exchange Manager - Gerenciamento Real de 5 Exchanges
Conecta com Binance, KuCoin, Bybit, Coinbase e OKX
Suporta operações reais de trading em live mode
"""

import os
import logging
import ccxt
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import time

logger = logging.getLogger(__name__)


class MultiExchangeManager:
    """Gerenciador unificado de múltiplas exchanges para live trading"""
    
    def __init__(self):
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.exchange_status: Dict[str, bool] = {}
        self.last_health_check: Dict[str, datetime] = {}
        
        # Configurações de exchanges suportadas
        self.supported_exchanges = {
            'binance': self._init_binance,
            'kucoin': self._init_kucoin,
            'bybit': self._init_bybit,
            'coinbase': self._init_coinbase,
            'okx': self._init_okx
        }
        
        self._initialize_all_exchanges()
        logger.info(f"✅ MultiExchangeManager inicializado com {len(self.exchanges)} exchanges")
    
    def _initialize_all_exchanges(self):
        """Inicializa todas as exchanges configuradas"""
        for exchange_name, init_func in self.supported_exchanges.items():
            try:
                exchange = init_func()
                if exchange:
                    self.exchanges[exchange_name] = exchange
                    self.exchange_status[exchange_name] = True
                    logger.info(f"✅ {exchange_name.upper()} inicializada com sucesso")
                else:
                    self.exchange_status[exchange_name] = False
                    logger.warning(f"⚠️ {exchange_name.upper()} - credenciais incompletas")
            except Exception as e:
                self.exchange_status[exchange_name] = False
                logger.error(f"❌ Erro ao inicializar {exchange_name.upper()}: {e}")
    
    def _init_binance(self) -> Optional[ccxt.Exchange]:
        """Inicializa Binance Spot"""
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        
        if not api_key or not api_secret:
            logger.warning("Binance: credenciais não encontradas")
            return None
        
        try:
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'timeout': 30000,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True,
                    'recvWindow': 10000
                }
            })
            
            # Validação de conexão
            exchange.load_markets()
            return exchange
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Binance: {e}")
            return None
    
    def _init_kucoin(self) -> Optional[ccxt.Exchange]:
        """Inicializa KuCoin"""
        api_key = os.getenv("KUCOIN_API_KEY")
        api_secret = os.getenv("KUCOIN_API_SECRET")
        passphrase = os.getenv("KUCOIN_API_PASSPHRASE")
        
        if not api_key or not api_secret:
            logger.warning("KuCoin: credenciais não encontradas")
            return None
        
        if not passphrase:
            logger.warning("KuCoin: PASSPHRASE obrigatória - exchange pronta mas inativa")
            return None
        
        try:
            exchange = ccxt.kucoin({
                'apiKey': api_key,
                'secret': api_secret,
                'password': passphrase,
                'enableRateLimit': True,
                'timeout': 30000
            })
            
            exchange.load_markets()
            return exchange
            
        except Exception as e:
            logger.error(f"Erro ao inicializar KuCoin: {e}")
            return None
    
    def _init_bybit(self) -> Optional[ccxt.Exchange]:
        """Inicializa Bybit"""
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")
        testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
        
        if not api_key or not api_secret:
            logger.warning("Bybit: credenciais não encontradas")
            return None
        
        try:
            exchange = ccxt.bybit({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'timeout': 30000,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            if testnet:
                exchange.set_sandbox_mode(True)
                logger.info("Bybit: Modo TESTNET ativado")
            
            exchange.load_markets()
            return exchange
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Bybit: {e}")
            return None
    
    def _init_coinbase(self) -> Optional[ccxt.Exchange]:
        """Inicializa Coinbase Advanced Trade"""
        api_key = os.getenv("COINBASE_API_KEY")
        private_key = os.getenv("COINBASE_PRIVATE_KEY_PEM")
        
        if not api_key or not private_key:
            logger.warning("Coinbase: credenciais não encontradas")
            return None
        
        try:
            exchange = ccxt.coinbase({
                'apiKey': api_key,
                'secret': private_key,
                'enableRateLimit': True,
                'timeout': 30000
            })
            
            exchange.load_markets()
            return exchange
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Coinbase: {e}")
            return None
    
    def _init_okx(self) -> Optional[ccxt.Exchange]:
        """Inicializa OKX"""
        api_key = os.getenv("OKX_API_KEY")
        api_secret = os.getenv("OKX_API_SECRET")
        passphrase = os.getenv("OKX_API_PASSPHRASE")
        
        if not api_key or not api_secret:
            logger.warning("OKX: credenciais não encontradas")
            return None
        
        if not passphrase:
            logger.warning("OKX: PASSPHRASE obrigatória - exchange pronta mas inativa")
            return None
        
        try:
            exchange = ccxt.okx({
                'apiKey': api_key,
                'secret': api_secret,
                'password': passphrase,
                'enableRateLimit': True,
                'timeout': 30000
            })
            
            exchange.load_markets()
            return exchange
            
        except Exception as e:
            logger.error(f"Erro ao inicializar OKX: {e}")
            return None
    
    def get_exchange(self, exchange_name: str) -> Optional[ccxt.Exchange]:
        """Retorna instância de uma exchange específica"""
        return self.exchanges.get(exchange_name.lower())
    
    def get_active_exchanges(self) -> List[str]:
        """Retorna lista de exchanges ativas"""
        return list(self.exchanges.keys())
    
    def get_all_balances(self) -> Dict[str, Any]:
        """Obtém saldo de todas as exchanges ativas"""
        balances = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                balance = exchange.fetch_balance()
                balances[exchange_name] = {
                    'total_usd': self._calculate_total_usd(balance),
                    'free': balance.get('free', {}),
                    'used': balance.get('used', {}),
                    'total': balance.get('total', {}),
                    'timestamp': datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Erro ao buscar saldo de {exchange_name}: {e}")
                balances[exchange_name] = {
                    'error': str(e),
                    'total_usd': 0.0
                }
        
        return balances
    
    def get_balance(self, exchange_name: str) -> Dict[str, Any]:
        """Obtém saldo de uma exchange específica"""
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            return {'error': f'Exchange {exchange_name} não disponível'}
        
        try:
            balance = exchange.fetch_balance()
            return {
                'exchange': exchange_name,
                'total_usd': self._calculate_total_usd(balance),
                'free': balance.get('free', {}),
                'used': balance.get('used', {}),
                'total': balance.get('total', {}),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Erro ao buscar saldo de {exchange_name}: {e}")
            return {'exchange': exchange_name, 'error': str(e)}
    
    def _calculate_total_usd(self, balance: Dict) -> float:
        """Calcula valor total em USD aproximado"""
        try:
            total = balance.get('total', {})
            # Prioriza USDT, USDC, USD
            stable_coins = ['USDT', 'USDC', 'USD', 'BUSD', 'DAI']
            total_usd = 0.0
            
            for coin in stable_coins:
                if coin in total:
                    total_usd += float(total[coin])
            
            # Se não tiver stablecoins, retorna 0 por enquanto
            # TODO: implementar conversão de outros ativos para USD
            return round(total_usd, 2)
        except Exception as e:
            logger.error(f"Erro ao calcular total USD: {e}")
            return 0.0
    
    def get_ticker(self, exchange_name: str, symbol: str) -> Dict[str, Any]:
        """Obtém ticker de um símbolo em uma exchange"""
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            return {'error': f'Exchange {exchange_name} não disponível'}
        
        try:
            ticker = exchange.fetch_ticker(symbol)
            return {
                'exchange': exchange_name,
                'symbol': symbol,
                'last': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'volume': ticker.get('volume'),
                'timestamp': ticker.get('timestamp'),
                'datetime': ticker.get('datetime')
            }
        except Exception as e:
            logger.error(f"Erro ao buscar ticker {symbol} de {exchange_name}: {e}")
            return {'exchange': exchange_name, 'symbol': symbol, 'error': str(e)}
    
    def get_open_orders(self, exchange_name: str, symbol: Optional[str] = None) -> List[Dict]:
        """Obtém ordens abertas de uma exchange"""
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            return []
        
        try:
            if symbol:
                orders = exchange.fetch_open_orders(symbol)
            else:
                orders = exchange.fetch_open_orders()
            return orders
        except Exception as e:
            logger.error(f"Erro ao buscar ordens de {exchange_name}: {e}")
            return []
    
    def create_order(
        self,
        exchange_name: str,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Cria uma ordem em uma exchange
        
        Args:
            exchange_name: Nome da exchange
            symbol: Par de trading (ex: BTC/USDT)
            order_type: 'market' ou 'limit'
            side: 'buy' ou 'sell'
            amount: Quantidade a negociar
            price: Preço (obrigatório para limit orders)
        """
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            return {'error': f'Exchange {exchange_name} não disponível'}
        
        try:
            if order_type == 'market':
                order = exchange.create_market_order(symbol, side, amount)
            elif order_type == 'limit':
                if price is None:
                    return {'error': 'Price is required for limit orders'}
                order = exchange.create_limit_order(symbol, side, amount, price)
            else:
                return {'error': f'Invalid order type: {order_type}'}
            
            logger.info(f"✅ Ordem criada: {exchange_name} {side} {amount} {symbol} @ {price or 'market'}")
            return order
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar ordem em {exchange_name}: {e}")
            return {'error': str(e)}
    
    def cancel_order(self, exchange_name: str, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancela uma ordem específica"""
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            return {'error': f'Exchange {exchange_name} não disponível'}
        
        try:
            result = exchange.cancel_order(order_id, symbol)
            logger.info(f"✅ Ordem {order_id} cancelada em {exchange_name}")
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao cancelar ordem em {exchange_name}: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica saúde de todas as exchanges"""
        health = {}
        
        for exchange_name in self.supported_exchanges.keys():
            try:
                if exchange_name in self.exchanges:
                    exchange = self.exchanges[exchange_name]
                    # Tenta buscar server time como health check
                    start = time.time()
                    exchange.fetch_time()
                    latency = (time.time() - start) * 1000
                    
                    health[exchange_name] = {
                        'status': 'online',
                        'latency_ms': round(latency, 2),
                        'markets_loaded': len(exchange.markets) if exchange.markets else 0,
                        'last_check': datetime.utcnow().isoformat()
                    }
                else:
                    health[exchange_name] = {
                        'status': 'offline',
                        'reason': 'Not initialized - check credentials',
                        'last_check': datetime.utcnow().isoformat()
                    }
            except Exception as e:
                health[exchange_name] = {
                    'status': 'error',
                    'error': str(e),
                    'last_check': datetime.utcnow().isoformat()
                }
        
        return health
    
    def get_markets(self, exchange_name: str) -> List[str]:
        """Retorna lista de mercados disponíveis em uma exchange"""
        exchange = self.get_exchange(exchange_name)
        if not exchange or not exchange.markets:
            return []
        
        return list(exchange.markets.keys())
    
    def close_all(self):
        """Fecha todas as conexões com exchanges"""
        for exchange_name, exchange in self.exchanges.items():
            try:
                if hasattr(exchange, 'close'):
                    exchange.close()
                logger.info(f"✅ Conexão fechada com {exchange_name}")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com {exchange_name}: {e}")
