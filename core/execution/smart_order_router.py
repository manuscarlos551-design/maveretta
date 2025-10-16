
# core/execution/smart_order_router.py
"""
Smart Order Routing (SOR) - Agregação de liquidez cross-exchange
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ExchangeQuote:
    """Quote de uma exchange"""
    exchange: str
    symbol: str
    side: str  # 'buy' or 'sell'
    price: float
    size: float
    fee_pct: float
    latency_ms: float
    depth_score: float  # 0-1


class SmartOrderRouter:
    """
    Roteia ordens para melhor execução cross-exchange
    """
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.routing_history: List[Dict[str, Any]] = []
        
        logger.info("✅ Smart Order Router initialized")
    
    async def get_best_execution(
        self,
        symbol: str,
        side: str,
        amount: float,
        max_slippage_pct: float = 0.5
    ) -> Tuple[List[Dict[str, Any]], float, float]:
        """
        Encontra melhor execução agregando múltiplas exchanges
        
        Args:
            symbol: Par de trading
            side: 'buy' ou 'sell'
            amount: Quantidade desejada
            max_slippage_pct: Slippage máximo aceitável
        
        Returns:
            (orders, avg_price, total_fee)
        """
        try:
            # Busca quotes de todas exchanges
            quotes = await self._fetch_all_quotes(symbol, side)
            
            if not quotes:
                return [], 0.0, 0.0
            
            # Ordena por melhor preço (considerando fees)
            quotes.sort(
                key=lambda q: q.price * (1 + q.fee_pct / 100) 
                if side == 'buy' 
                else q.price * (1 - q.fee_pct / 100),
                reverse=(side == 'sell')
            )
            
            # Aloca ordens para atingir amount total
            orders = []
            remaining = amount
            total_cost = 0.0
            total_fee = 0.0
            
            for quote in quotes:
                if remaining <= 0:
                    break
                
                # Quantidade a alocar nesta exchange
                alloc_amount = min(remaining, quote.size)
                
                # Calcula custo com fee
                cost = alloc_amount * quote.price
                fee = cost * (quote.fee_pct / 100)
                
                orders.append({
                    'exchange': quote.exchange,
                    'symbol': symbol,
                    'side': side,
                    'amount': alloc_amount,
                    'price': quote.price,
                    'fee': fee
                })
                
                total_cost += cost
                total_fee += fee
                remaining -= alloc_amount
            
            # Calcula preço médio
            avg_price = total_cost / amount if amount > 0 else 0
            
            # Verifica slippage
            best_quote = quotes[0]
            slippage = abs(avg_price - best_quote.price) / best_quote.price * 100
            
            if slippage > max_slippage_pct:
                logger.warning(
                    f"Slippage {slippage:.2%} exceeds max {max_slippage_pct:.2%}"
                )
            
            # Registra roteamento
            self.routing_history.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'orders': orders,
                'avg_price': avg_price,
                'total_fee': total_fee,
                'slippage_pct': slippage
            })
            
            logger.info(
                f"SOR: {len(orders)} orders across {len(set(o['exchange'] for o in orders))} exchanges, "
                f"avg price: {avg_price:.2f}, slippage: {slippage:.2%}"
            )
            
            return orders, avg_price, total_fee
            
        except Exception as e:
            logger.error(f"Error in smart order routing: {e}")
            return [], 0.0, 0.0
    
    async def _fetch_all_quotes(
        self,
        symbol: str,
        side: str
    ) -> List[ExchangeQuote]:
        """
        Busca quotes de todas exchanges configuradas
        
        Args:
            symbol: Par de trading
            side: 'buy' ou 'sell'
        
        Returns:
            Lista de quotes
        """
        quotes = []
        
        try:
            # Lista de exchanges (mock - integrar com exchange_manager real)
            exchanges = ['binance', 'coinbase', 'kraken', 'bybit']
            
            tasks = []
            for exchange in exchanges:
                tasks.append(self._fetch_quote(exchange, symbol, side))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, ExchangeQuote):
                    quotes.append(result)
            
            return quotes
            
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return []
    
    async def _fetch_quote(
        self,
        exchange: str,
        symbol: str,
        side: str
    ) -> Optional[ExchangeQuote]:
        """
        Busca quote de uma exchange específica
        
        Args:
            exchange: Nome da exchange
            symbol: Par de trading
            side: 'buy' ou 'sell'
        
        Returns:
            Quote da exchange
        """
        try:
            # Simula latência de rede
            await asyncio.sleep(0.05)
            
            # Mock data - integrar com exchange_manager real
            import random
            base_price = 50000 if 'BTC' in symbol else 3000
            
            quote = ExchangeQuote(
                exchange=exchange,
                symbol=symbol,
                side=side,
                price=base_price * random.uniform(0.998, 1.002),
                size=random.uniform(0.1, 5.0),
                fee_pct=random.uniform(0.05, 0.2),
                latency_ms=random.uniform(20, 100),
                depth_score=random.uniform(0.5, 1.0)
            )
            
            return quote
            
        except Exception as e:
            logger.error(f"Error fetching quote from {exchange}: {e}")
            return None
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de roteamento"""
        if not self.routing_history:
            return {}
        
        import pandas as pd
        df = pd.DataFrame(self.routing_history)
        
        # Estatísticas por exchange
        all_orders = []
        for routing in self.routing_history:
            all_orders.extend(routing['orders'])
        
        if all_orders:
            orders_df = pd.DataFrame(all_orders)
            by_exchange = orders_df.groupby('exchange').agg({
                'amount': 'sum',
                'fee': 'sum'
            }).to_dict()
        else:
            by_exchange = {}
        
        return {
            'total_routings': len(self.routing_history),
            'avg_slippage_pct': df['slippage_pct'].mean(),
            'total_fees': df['total_fee'].sum(),
            'by_exchange': by_exchange
        }


# Instância global (será inicializada com exchange_manager)
smart_order_router = None
