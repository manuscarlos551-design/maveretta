# core/execution/exchange_executor.py
"""
Exchange Executor - Executor de ordens nas exchanges usando CCXT
"""

import ccxt
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ExchangeExecutor:
    """
    Executor de ordens nas exchanges usando CCXT
    Suporta: Binance, KuCoin, Bybit, Coinbase, OKX
    """
    
    def __init__(self):
        self.exchanges = {}
        self._initialize_exchanges()
        logger.info("✅ Exchange Executor inicializado")
    
    def _initialize_exchanges(self):
        """Inicializa conexões com exchanges"""
        
        # Binance
        binance_api_key = os.getenv("BINANCE_API_KEY")
        binance_secret = os.getenv("BINANCE_SECRET")
        if binance_api_key and binance_secret:
            try:
                self.exchanges["binance"] = ccxt.binance({
                    'apiKey': binance_api_key,
                    'secret': binance_secret,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                })
                logger.info("✅ Binance exchange inicializada")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Binance: {e}")
        
        # KuCoin
        kucoin_api_key = os.getenv("KUCOIN_API_KEY")
        kucoin_secret = os.getenv("KUCOIN_SECRET")
        kucoin_password = os.getenv("KUCOIN_PASSWORD")
        if kucoin_api_key and kucoin_secret and kucoin_password:
            try:
                self.exchanges["kucoin"] = ccxt.kucoin({
                    'apiKey': kucoin_api_key,
                    'secret': kucoin_secret,
                    'password': kucoin_password,
                    'enableRateLimit': True
                })
                logger.info("✅ KuCoin exchange inicializada")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar KuCoin: {e}")
        
        # Bybit
        bybit_api_key = os.getenv("BYBIT_API_KEY")
        bybit_secret = os.getenv("BYBIT_SECRET")
        if bybit_api_key and bybit_secret:
            try:
                self.exchanges["bybit"] = ccxt.bybit({
                    'apiKey': bybit_api_key,
                    'secret': bybit_secret,
                    'enableRateLimit': True
                })
                logger.info("✅ Bybit exchange inicializada")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Bybit: {e}")
        
        # Coinbase
        coinbase_api_key = os.getenv("COINBASE_API_KEY")
        coinbase_secret = os.getenv("COINBASE_SECRET")
        if coinbase_api_key and coinbase_secret:
            try:
                self.exchanges["coinbase"] = ccxt.coinbase({
                    'apiKey': coinbase_api_key,
                    'secret': coinbase_secret,
                    'enableRateLimit': True
                })
                logger.info("✅ Coinbase exchange inicializada")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Coinbase: {e}")
        
        # OKX
        okx_api_key = os.getenv("OKX_API_KEY")
        okx_secret = os.getenv("OKX_SECRET")
        okx_password = os.getenv("OKX_PASSWORD")
        if okx_api_key and okx_secret and okx_password:
            try:
                self.exchanges["okx"] = ccxt.okx({
                    'apiKey': okx_api_key,
                    'secret': okx_secret,
                    'password': okx_password,
                    'enableRateLimit': True
                })
                logger.info("✅ OKX exchange inicializada")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar OKX: {e}")
        
        if not self.exchanges:
            logger.warning("⚠️ Nenhuma exchange inicializada - verifique as credenciais no .env")
    
    def execute_market_order(self, exchange: str, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        """
        Executa ordem a mercado
        
        Args:
            exchange: Nome da exchange (binance, kucoin, etc)
            symbol: Par de negociação (BTC/USDT)
            side: 'buy' ou 'sell'
            amount: Quantidade a negociar
        
        Returns:
            Dict com resultado da ordem (order_id, price, filled, etc) ou erro
        """
        try:
            if exchange not in self.exchanges:
                return {"success": False, "error": f"Exchange {exchange} não configurada"}
            
            exchange_obj = self.exchanges[exchange]
            
            # Executa ordem a mercado
            order = exchange_obj.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount
            )
            
            logger.info(f"✅ Ordem a mercado executada: {exchange} {side} {amount} {symbol}")
            
            return {
                "success": True,
                "order_id": order['id'],
                "symbol": symbol,
                "side": side,
                "type": "market",
                "amount": amount,
                "filled": order.get('filled', amount),
                "price": order.get('average', order.get('price')),
                "cost": order.get('cost'),
                "fee": order.get('fee'),
                "timestamp": order.get('timestamp'),
                "datetime": order.get('datetime'),
                "status": order.get('status'),
                "raw_order": order
            }
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"❌ Saldo insuficiente: {e}")
            return {"success": False, "error": "Saldo insuficiente", "details": str(e)}
        
        except ccxt.InvalidOrder as e:
            logger.error(f"❌ Ordem inválida: {e}")
            return {"success": False, "error": "Ordem inválida", "details": str(e)}
        
        except ccxt.NetworkError as e:
            logger.error(f"❌ Erro de rede: {e}")
            return {"success": False, "error": "Erro de rede", "details": str(e)}
        
        except Exception as e:
            logger.error(f"❌ Erro ao executar ordem: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_limit_order(
        self, 
        exchange: str, 
        symbol: str, 
        side: str, 
        amount: float, 
        price: float
    ) -> Dict[str, Any]:
        """
        Executa ordem limitada
        
        Args:
            exchange: Nome da exchange
            symbol: Par de negociação
            side: 'buy' ou 'sell'
            amount: Quantidade
            price: Preço limite
        
        Returns:
            Dict com resultado da ordem ou erro
        """
        try:
            if exchange not in self.exchanges:
                return {"success": False, "error": f"Exchange {exchange} não configurada"}
            
            exchange_obj = self.exchanges[exchange]
            
            # Executa ordem limitada
            order = exchange_obj.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price
            )
            
            logger.info(f"✅ Ordem limitada criada: {exchange} {side} {amount} {symbol} @ {price}")
            
            return {
                "success": True,
                "order_id": order['id'],
                "symbol": symbol,
                "side": side,
                "type": "limit",
                "amount": amount,
                "price": price,
                "filled": order.get('filled', 0),
                "remaining": order.get('remaining', amount),
                "cost": order.get('cost'),
                "fee": order.get('fee'),
                "timestamp": order.get('timestamp'),
                "datetime": order.get('datetime'),
                "status": order.get('status'),
                "raw_order": order
            }
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"❌ Saldo insuficiente: {e}")
            return {"success": False, "error": "Saldo insuficiente", "details": str(e)}
        
        except ccxt.InvalidOrder as e:
            logger.error(f"❌ Ordem inválida: {e}")
            return {"success": False, "error": "Ordem inválida", "details": str(e)}
        
        except Exception as e:
            logger.error(f"❌ Erro ao executar ordem: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_order(self, exchange: str, order_id: str, symbol: str) -> bool:
        """
        Cancela uma ordem
        
        Args:
            exchange: Nome da exchange
            order_id: ID da ordem
            symbol: Par de negociação
        
        Returns:
            True se cancelada com sucesso, False caso contrário
        """
        try:
            if exchange not in self.exchanges:
                logger.error(f"Exchange {exchange} não configurada")
                return False
            
            exchange_obj = self.exchanges[exchange]
            exchange_obj.cancel_order(order_id, symbol)
            
            logger.info(f"✅ Ordem cancelada: {order_id} em {exchange}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao cancelar ordem {order_id}: {e}")
            return False
    
    def get_balance(self, exchange: str, currency: str = 'USDT') -> float:
        """
        Retorna saldo disponível
        
        Args:
            exchange: Nome da exchange
            currency: Moeda (default: USDT)
        
        Returns:
            Saldo disponível ou 0 em caso de erro
        """
        try:
            if exchange not in self.exchanges:
                logger.error(f"Exchange {exchange} não configurada")
                return 0.0
            
            exchange_obj = self.exchanges[exchange]
            balance = exchange_obj.fetch_balance()
            
            free_balance = balance.get('free', {}).get(currency, 0)
            
            logger.info(f"💰 Saldo {currency} em {exchange}: {free_balance}")
            return float(free_balance)
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar saldo em {exchange}: {e}")
            return 0.0
    
    def close_all_positions(self, exchange: str) -> list:
        """
        Fecha todas as posições abertas (para STOP e EMERGENCY)
        
        Args:
            exchange: Nome da exchange
        
        Returns:
            Lista de ordens fechadas
        """
        try:
            if exchange not in self.exchanges:
                logger.error(f"Exchange {exchange} não configurada")
                return []
            
            exchange_obj = self.exchanges[exchange]
            
            # Buscar ordens abertas
            open_orders = exchange_obj.fetch_open_orders()
            
            closed_orders = []
            for order in open_orders:
                try:
                    # Cancela ordem
                    exchange_obj.cancel_order(order['id'], order['symbol'])
                    closed_orders.append(order)
                    logger.info(f"✅ Ordem {order['id']} cancelada")
                except Exception as e:
                    logger.error(f"❌ Erro ao cancelar ordem {order['id']}: {e}")
            
            logger.info(f"✅ {len(closed_orders)} ordens fechadas em {exchange}")
            return closed_orders
            
        except Exception as e:
            logger.error(f"❌ Erro ao fechar posições em {exchange}: {e}")
            return []
    
    def get_ticker(self, exchange: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtém ticker (preço atual) de um símbolo
        
        Args:
            exchange: Nome da exchange
            symbol: Par de negociação
        
        Returns:
            Dict com dados do ticker ou None em caso de erro
        """
        try:
            if exchange not in self.exchanges:
                logger.error(f"Exchange {exchange} não configurada")
                return None
            
            exchange_obj = self.exchanges[exchange]
            ticker = exchange_obj.fetch_ticker(symbol)
            
            return {
                "symbol": symbol,
                "last": ticker.get('last'),
                "bid": ticker.get('bid'),
                "ask": ticker.get('ask'),
                "high": ticker.get('high'),
                "low": ticker.get('low'),
                "volume": ticker.get('volume'),
                "timestamp": ticker.get('timestamp'),
                "datetime": ticker.get('datetime')
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar ticker {symbol} em {exchange}: {e}")
            return None
