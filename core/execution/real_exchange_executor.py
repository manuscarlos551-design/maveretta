#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Exchange Executor - Execução real de ordens via CCXT
Suporta: Binance, Bybit, Kucoin, OKX, Coinbase
"""

import os
import ccxt
import logging
import asyncio
from typing import Dict, Optional, List, Any
from datetime import datetime
from enum import Enum

from core.exchanges.fee_manager import fee_manager, Exchange

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class RealExchangeExecutor:
    """
    Executor real de ordens em exchanges
    Usa CCXT para comunicação unificada
    """
    
    def __init__(self):
        self.exchanges = {}
        self.active_positions = {}
        self.order_history = []
        
        # Inicializa exchanges configuradas
        self._initialize_exchanges()
        
        logger.info(f"✅ Real Exchange Executor inicializado com {len(self.exchanges)} exchanges")
    
    def _initialize_exchanges(self):
        """Inicializa conexões com exchanges habilitadas"""
        
        # BINANCE
        if os.getenv('BINANCE_ENABLED', 'true').lower() == 'true':
            try:
                self.exchanges[Exchange.BINANCE] = ccxt.binance({
                    'apiKey': os.getenv('BINANCE_API_KEY'),
                    'secret': os.getenv('BINANCE_API_SECRET'),
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'
                    }
                })
                logger.info("✅ Binance conectada")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar Binance: {e}")
        
        # BYBIT
        if os.getenv('BYBIT_ENABLED', 'true').lower() == 'true':
            try:
                self.exchanges[Exchange.BYBIT] = ccxt.bybit({
                    'apiKey': os.getenv('BYBIT_API_KEY'),
                    'secret': os.getenv('BYBIT_API_SECRET'),
                    'enableRateLimit': True
                })
                logger.info("✅ Bybit conectada")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar Bybit: {e}")
        
        # KUCOIN
        if os.getenv('KUCOIN_ENABLED', 'true').lower() == 'true':
            try:
                passphrase = os.getenv('KUCOIN_API_PASSPHRASE', '')
                self.exchanges[Exchange.KUCOIN] = ccxt.kucoin({
                    'apiKey': os.getenv('KUCOIN_API_KEY'),
                    'secret': os.getenv('KUCOIN_API_SECRET'),
                    'password': passphrase if passphrase else None,
                    'enableRateLimit': True
                })
                logger.info("✅ Kucoin conectada")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar Kucoin: {e}")
        
        # OKX
        if os.getenv('OKX_ENABLED', 'true').lower() == 'true':
            try:
                passphrase = os.getenv('OKX_API_PASSPHRASE', '')
                self.exchanges[Exchange.OKX] = ccxt.okx({
                    'apiKey': os.getenv('OKX_API_KEY'),
                    'secret': os.getenv('OKX_API_SECRET'),
                    'password': passphrase if passphrase else None,
                    'enableRateLimit': True
                })
                logger.info("✅ OKX conectada")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar OKX: {e}")
        
        # COINBASE
        if os.getenv('COINBASE_ENABLED', 'true').lower() == 'true':
            try:
                self.exchanges[Exchange.COINBASE] = ccxt.coinbase({
                    'apiKey': os.getenv('COINBASE_API_KEY'),
                    'secret': os.getenv('COINBASE_PRIVATE_KEY_PEM'),
                    'enableRateLimit': True
                })
                logger.info("✅ Coinbase conectada")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar Coinbase: {e}")
    
    async def get_balance(self, exchange: Exchange) -> Dict[str, float]:
        """Obtém saldo da exchange"""
        try:
            if exchange not in self.exchanges:
                return {'error': f'Exchange {exchange} não configurada'}
            
            balance = await asyncio.to_thread(
                self.exchanges[exchange].fetch_balance
            )
            
            return {
                'total': balance.get('total', {}),
                'free': balance.get('free', {}),
                'used': balance.get('used', {})
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter saldo {exchange}: {e}")
            return {'error': str(e)}
    
    async def get_ticker(self, exchange: Exchange, symbol: str) -> Dict[str, Any]:
        """Obtém preço atual do símbolo"""
        try:
            if exchange not in self.exchanges:
                return {'error': f'Exchange {exchange} não configurada'}
            
            ticker = await asyncio.to_thread(
                self.exchanges[exchange].fetch_ticker,
                symbol
            )
            
            return ticker
        except Exception as e:
            logger.error(f"❌ Erro ao obter ticker {symbol} em {exchange}: {e}")
            return {'error': str(e)}
    
    async def create_market_order(
        self,
        exchange: Exchange,
        symbol: str,
        side: OrderSide,
        amount_usd: float
    ) -> Dict[str, Any]:
        """
        Cria ordem de mercado
        
        Args:
            exchange: Exchange a usar
            symbol: Par (ex: BTC/USDT)
            side: buy ou sell
            amount_usd: Valor em USD
        
        Returns:
            Resultado da ordem
        """
        try:
            if exchange not in self.exchanges:
                return {
                    'success': False,
                    'error': f'Exchange {exchange} não configurada'
                }
            
            # Obtém preço atual
            ticker = await self.get_ticker(exchange, symbol)
            if 'error' in ticker:
                return {'success': False, 'error': ticker['error']}
            
            current_price = ticker['last']
            
            # Calcula quantidade em moedas
            amount = amount_usd / current_price
            
            # Cria ordem
            logger.info(
                f"🚀 Criando ordem MARKET: {side.value} {amount:.6f} {symbol} "
                f"em {exchange.value} (~${amount_usd:.2f})"
            )
            
            order = await asyncio.to_thread(
                self.exchanges[exchange].create_order,
                symbol,
                'market',
                side.value,
                amount
            )
            
            # Registra no histórico
            order_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'exchange': exchange.value,
                'symbol': symbol,
                'side': side.value,
                'type': 'market',
                'amount': amount,
                'amount_usd': amount_usd,
                'price': current_price,
                'order_id': order.get('id'),
                'status': order.get('status'),
                'filled': order.get('filled'),
                'cost': order.get('cost')
            }
            
            self.order_history.append(order_record)
            
            logger.info(
                f"✅ Ordem executada: ID {order.get('id')} | "
                f"Filled: {order.get('filled')} | Cost: ${order.get('cost'):.2f}"
            )
            
            return {
                'success': True,
                'order': order,
                'order_record': order_record
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar ordem: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_limit_order_with_sltp(
        self,
        exchange: Exchange,
        symbol: str,
        side: OrderSide,
        amount_usd: float,
        entry_price: float = None
    ) -> Dict[str, Any]:
        """
        Cria ordem com Stop Loss e Take Profit automaticos
        
        Args:
            exchange: Exchange a usar
            symbol: Par de trading
            side: buy (long) ou sell (short)
            amount_usd: Valor em USD
            entry_price: Preço de entrada (None = mercado)
        
        Returns:
            Resultado com ordem principal + SL/TP
        """
        try:
            # Se não especificou preço, usa mercado
            if entry_price is None:
                ticker = await self.get_ticker(exchange, symbol)
                if 'error' in ticker:
                    return {'success': False, 'error': ticker['error']}
                entry_price = ticker['last']
            
            # Calcula SL e TP considerando taxas
            tp_price, tp_pct = fee_manager.calculate_take_profit(
                exchange, entry_price, 
                'long' if side == OrderSide.BUY else 'short'
            )
            
            sl_price = fee_manager.calculate_stop_loss(
                exchange, entry_price,
                'long' if side == OrderSide.BUY else 'short'
            )
            
            logger.info(
                f"🎯 Trade Setup: Entry ${entry_price:.2f} | "
                f"TP ${tp_price:.2f} ({tp_pct:.2%}) | "
                f"SL ${sl_price:.2f}"
            )
            
            # Cria ordem de entrada (market)
            entry_result = await self.create_market_order(
                exchange, symbol, side, amount_usd
            )
            
            if not entry_result['success']:
                return entry_result
            
            # Calcula quantidade preenchida
            filled_amount = entry_result['order'].get('filled', 0)
            
            # Registra posição ativa
            position_id = f"{exchange.value}_{symbol}_{datetime.utcnow().timestamp()}"
            
            self.active_positions[position_id] = {
                'exchange': exchange.value,
                'symbol': symbol,
                'side': 'long' if side == OrderSide.BUY else 'short',
                'entry_price': entry_price,
                'amount': filled_amount,
                'amount_usd': amount_usd,
                'tp_price': tp_price,
                'sl_price': sl_price,
                'tp_pct': tp_pct,
                'entry_order_id': entry_result['order'].get('id'),
                'opened_at': datetime.utcnow().isoformat(),
                'status': 'open'
            }
            
            logger.info(
                f"✅ Posição aberta: {position_id} | "
                f"Amount: {filled_amount:.6f} | "
                f"Value: ${amount_usd:.2f}"
            )
            
            return {
                'success': True,
                'position_id': position_id,
                'entry_order': entry_result['order'],
                'position': self.active_positions[position_id]
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar ordem com SL/TP: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def check_and_close_positions(self):
        """
        Verifica posições abertas e fecha quando atingir TP ou SL
        """
        positions_to_close = []
        
        for position_id, position in self.active_positions.items():
            if position['status'] != 'open':
                continue
            
            try:
                exchange = Exchange(position['exchange'])
                symbol = position['symbol']
                
                # Obtém preço atual
                ticker = await self.get_ticker(exchange, symbol)
                if 'error' in ticker:
                    continue
                
                current_price = ticker['last']
                entry_price = position['entry_price']
                side = position['side']
                
                # Verifica TP e SL
                should_close = False
                close_reason = None
                
                if side == 'long':
                    if current_price >= position['tp_price']:
                        should_close = True
                        close_reason = 'take_profit'
                    elif current_price <= position['sl_price']:
                        should_close = True
                        close_reason = 'stop_loss'
                else:  # short
                    if current_price <= position['tp_price']:
                        should_close = True
                        close_reason = 'take_profit'
                    elif current_price >= position['sl_price']:
                        should_close = True
                        close_reason = 'stop_loss'
                
                if should_close:
                    positions_to_close.append((position_id, close_reason, current_price))
            
            except Exception as e:
                logger.error(f"❌ Erro ao verificar posição {position_id}: {e}")
        
        # Fecha posições
        for position_id, reason, close_price in positions_to_close:
            await self.close_position(position_id, reason, close_price)
    
    async def close_position(
        self,
        position_id: str,
        reason: str,
        close_price: float = None
    ) -> Dict[str, Any]:
        """
        Fecha uma posição aberta
        
        Args:
            position_id: ID da posição
            reason: Motivo do fechamento (take_profit, stop_loss, manual)
            close_price: Preço de fechamento (None = mercado)
        
        Returns:
            Resultado do fechamento
        """
        try:
            if position_id not in self.active_positions:
                return {'success': False, 'error': 'Posição não encontrada'}
            
            position = self.active_positions[position_id]
            
            exchange = Exchange(position['exchange'])
            symbol = position['symbol']
            side = position['side']
            amount = position['amount']
            
            # Define lado da ordem de fechamento (inverso)
            close_side = OrderSide.SELL if side == 'long' else OrderSide.BUY
            
            # Se não especificou preço, usa mercado
            if close_price is None:
                ticker = await self.get_ticker(exchange, symbol)
                if 'error' in ticker:
                    return {'success': False, 'error': ticker['error']}
                close_price = ticker['last']
            
            # Calcula profit
            entry_price = position['entry_price']
            
            profit_calc = fee_manager.calculate_net_profit(
                exchange,
                entry_price,
                close_price,
                position['amount_usd'],
                side
            )
            
            # Cria ordem de fechamento
            close_amount_usd = amount * close_price
            
            close_result = await self.create_market_order(
                exchange, symbol, close_side, close_amount_usd
            )
            
            if not close_result['success']:
                return close_result
            
            # Atualiza posição
            position['status'] = 'closed'
            position['close_price'] = close_price
            position['close_reason'] = reason
            position['closed_at'] = datetime.utcnow().isoformat()
            position['profit'] = profit_calc
            position['close_order_id'] = close_result['order'].get('id')
            
            logger.info(
                f"✅ Posição fechada: {position_id} | "
                f"Reason: {reason} | "
                f"Entry: ${entry_price:.2f} | Close: ${close_price:.2f} | "
                f"Net P/L: ${profit_calc['net_profit_usd']:.2f} ({profit_calc['net_profit_pct']:.2%})"
            )
            
            return {
                'success': True,
                'position': position,
                'close_order': close_result['order']
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao fechar posição {position_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_active_positions(self) -> List[Dict[str, Any]]:
        """Retorna lista de posições abertas"""
        return [
            p for p in self.active_positions.values()
            if p['status'] == 'open'
        ]
    
    def get_closed_positions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna posições fechadas recentes"""
        closed = [
            p for p in self.active_positions.values()
            if p['status'] == 'closed'
        ]
        return sorted(
            closed,
            key=lambda x: x.get('closed_at', ''),
            reverse=True
        )[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do executor"""
        active = self.get_active_positions()
        closed = self.get_closed_positions()
        
        # Calcula win rate
        winning_trades = sum(1 for p in closed if p.get('profit', {}).get('is_profitable', False))
        total_closed = len(closed)
        win_rate = winning_trades / total_closed if total_closed > 0 else 0.0
        
        # Calcula profit total
        total_profit = sum(
            p.get('profit', {}).get('net_profit_usd', 0)
            for p in closed
        )
        
        return {
            'exchanges_connected': len(self.exchanges),
            'active_positions': len(active),
            'total_closed_positions': total_closed,
            'total_orders': len(self.order_history),
            'win_rate': win_rate,
            'total_profit_usd': total_profit,
            'winning_trades': winning_trades,
            'losing_trades': total_closed - winning_trades
        }


# Instância global
real_exchange_executor = RealExchangeExecutor()
