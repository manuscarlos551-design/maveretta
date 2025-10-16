"""
Futures Executor - Executor de Ordens de Futuros

Features:
- Execução de ordens market
- Execução de ordens limit
- Configuração de SL/TP
- Reduce-only orders
- Post-only orders
"""

from typing import Dict, Optional
import asyncio
from datetime import datetime


class FuturesExecutor:
    """
    Executor de ordens de futuros.
    """

    def __init__(self, exchanges: Dict):
        """
        Inicializa executor de futuros.

        Args:
            exchanges: Dicionário com conexões CCXT
        """
        self.exchanges = exchanges

    async def execute_market_order(
        self,
        exchange_name: str,
        symbol: str,
        side: str,
        amount: float,
        leverage: int,
        reduce_only: bool = False
    ) -> Dict:
        """
        Executa ordem a mercado.

        Args:
            exchange_name: Nome da exchange
            symbol: Símbolo (ex: 'BTC/USDT:USDT')
            side: 'buy' ou 'sell'
            amount: Quantidade
            leverage: Alavancagem
            reduce_only: Se True, apenas reduz posição existente

        Returns:
            Dict com resultado da ordem
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            # Configurar leverage
            await exchange.set_leverage(leverage, symbol)

            # Parâmetros da ordem
            params = {
                'leverage': leverage
            }

            if reduce_only:
                params['reduceOnly'] = True

            # Executar ordem
            order = await exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params=params
            )

            result = {
                'success': True,
                'order_id': order['id'],
                'symbol': symbol,
                'exchange': exchange_name,
                'type': 'market',
                'side': side,
                'amount': amount,
                'filled': order.get('filled', 0),
                'average_price': order.get('average') or order.get('price', 0),
                'leverage': leverage,
                'reduce_only': reduce_only,
                'timestamp': datetime.utcnow().isoformat(),
                'order_data': order
            }

            print(f"✅ Market order executada: {symbol} {side.upper()} {amount}")

            return result

        except Exception as e:
            print(f"❌ Erro ao executar market order: {e}")
            return {
                'success': False,
                'error': str(e),
                'exchange': exchange_name,
                'symbol': symbol,
                'timestamp': datetime.utcnow().isoformat()
            }

    async def execute_limit_order(
        self,
        exchange_name: str,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        leverage: int,
        post_only: bool = False,
        reduce_only: bool = False
    ) -> Dict:
        """
        Executa ordem limitada.

        Args:
            exchange_name: Nome da exchange
            symbol: Símbolo
            side: 'buy' ou 'sell'
            amount: Quantidade
            price: Preço limite
            leverage: Alavancagem
            post_only: Se True, ordem só entra como maker
            reduce_only: Se True, apenas reduz posição

        Returns:
            Dict com resultado
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            # Configurar leverage
            await exchange.set_leverage(leverage, symbol)

            # Parâmetros da ordem
            params = {
                'leverage': leverage
            }

            if post_only:
                params['postOnly'] = True

            if reduce_only:
                params['reduceOnly'] = True

            # Executar ordem
            order = await exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=amount,
                price=price,
                params=params
            )

            result = {
                'success': True,
                'order_id': order['id'],
                'symbol': symbol,
                'exchange': exchange_name,
                'type': 'limit',
                'side': side,
                'amount': amount,
                'price': price,
                'filled': order.get('filled', 0),
                'leverage': leverage,
                'post_only': post_only,
                'reduce_only': reduce_only,
                'status': order.get('status', 'open'),
                'timestamp': datetime.utcnow().isoformat(),
                'order_data': order
            }

            print(f"✅ Limit order criada: {symbol} {side.upper()} {amount} @ {price}")

            return result

        except Exception as e:
            print(f"❌ Erro ao executar limit order: {e}")
            return {
                'success': False,
                'error': str(e),
                'exchange': exchange_name,
                'symbol': symbol,
                'timestamp': datetime.utcnow().isoformat()
            }

    async def set_stop_loss_take_profit(
        self,
        exchange_name: str,
        symbol: str,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        position_size: float,
        side: str
    ) -> Dict:
        """
        Configura SL/TP para posição.

        Args:
            exchange_name: Nome da exchange
            symbol: Símbolo
            stop_loss: Preço de stop loss
            take_profit: Preço de take profit
            position_size: Tamanho da posição
            side: 'buy' ou 'sell' (da posição original)

        Returns:
            Dict com resultado
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]
        results = {
            'symbol': symbol,
            'exchange': exchange_name,
            'stop_loss_order': None,
            'take_profit_order': None,
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            # Determinar lado oposto para fechar
            close_side = 'sell' if side == 'buy' else 'buy'

            # Criar stop loss
            if stop_loss:
                sl_order = await exchange.create_order(
                    symbol=symbol,
                    type='stop_market',
                    side=close_side,
                    amount=position_size,
                    params={
                        'stopPrice': stop_loss,
                        'reduceOnly': True
                    }
                )

                results['stop_loss_order'] = {
                    'order_id': sl_order['id'],
                    'stop_price': stop_loss,
                    'amount': position_size
                }

                print(f"✅ Stop Loss configurado: {symbol} @ {stop_loss}")

            # Criar take profit
            if take_profit:
                tp_order = await exchange.create_order(
                    symbol=symbol,
                    type='take_profit_market',
                    side=close_side,
                    amount=position_size,
                    params={
                        'stopPrice': take_profit,
                        'reduceOnly': True
                    }
                )

                results['take_profit_order'] = {
                    'order_id': tp_order['id'],
                    'stop_price': take_profit,
                    'amount': position_size
                }

                print(f"✅ Take Profit configurado: {symbol} @ {take_profit}")

            return results

        except Exception as e:
            print(f"❌ Erro ao configurar SL/TP: {e}")
            results['success'] = False
            results['error'] = str(e)
            return results

    async def cancel_order(
        self,
        exchange_name: str,
        order_id: str,
        symbol: str
    ) -> Dict:
        """
        Cancela ordem.

        Args:
            exchange_name: Nome da exchange
            order_id: ID da ordem
            symbol: Símbolo

        Returns:
            Dict com resultado
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            result = await exchange.cancel_order(order_id, symbol)

            return {
                'success': True,
                'order_id': order_id,
                'symbol': symbol,
                'exchange': exchange_name,
                'timestamp': datetime.utcnow().isoformat(),
                'result': result
            }

        except Exception as e:
            print(f"❌ Erro ao cancelar ordem: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id,
                'symbol': symbol,
                'exchange': exchange_name,
                'timestamp': datetime.utcnow().isoformat()
            }

    async def modify_order(
        self,
        exchange_name: str,
        order_id: str,
        symbol: str,
        amount: Optional[float] = None,
        price: Optional[float] = None
    ) -> Dict:
        """
        Modifica ordem existente.

        Args:
            exchange_name: Nome da exchange
            order_id: ID da ordem
            symbol: Símbolo
            amount: Nova quantidade (opcional)
            price: Novo preço (opcional)

        Returns:
            Dict com resultado
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            params = {}
            if amount is not None:
                params['amount'] = amount
            if price is not None:
                params['price'] = price

            result = await exchange.edit_order(order_id, symbol, **params)

            return {
                'success': True,
                'order_id': order_id,
                'symbol': symbol,
                'exchange': exchange_name,
                'modifications': params,
                'timestamp': datetime.utcnow().isoformat(),
                'result': result
            }

        except Exception as e:
            print(f"❌ Erro ao modificar ordem: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id,
                'symbol': symbol,
                'exchange': exchange_name,
                'timestamp': datetime.utcnow().isoformat()
            }

    async def get_order_status(
        self,
        exchange_name: str,
        order_id: str,
        symbol: str
    ) -> Dict:
        """
        Obtém status de ordem.

        Args:
            exchange_name: Nome da exchange
            order_id: ID da ordem
            symbol: Símbolo

        Returns:
            Dict com status
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            order = await exchange.fetch_order(order_id, symbol)

            return {
                'success': True,
                'order_id': order_id,
                'symbol': symbol,
                'exchange': exchange_name,
                'status': order.get('status', 'unknown'),
                'filled': order.get('filled', 0),
                'remaining': order.get('remaining', 0),
                'average_price': order.get('average') or order.get('price', 0),
                'timestamp': datetime.utcnow().isoformat(),
                'order': order
            }

        except Exception as e:
            print(f"❌ Erro ao obter status da ordem: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id,
                'symbol': symbol,
                'exchange': exchange_name,
                'timestamp': datetime.utcnow().isoformat()
            }

    async def close_all_positions(
        self,
        exchange_name: str
    ) -> Dict:
        """
        Fecha todas as posições abertas (EMERGÊNCIA).

        Args:
            exchange_name: Nome da exchange

        Returns:
            Dict com resultado
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            # Obter todas as posições
            positions = await exchange.fetch_positions()

            closed_positions = []
            errors = []

            for position in positions:
                contracts = float(position.get('contracts', 0))
                
                if contracts != 0:
                    symbol = position['symbol']
                    side = 'sell' if position['side'] == 'long' else 'buy'
                    amount = abs(contracts)

                    try:
                        order = await exchange.create_order(
                            symbol=symbol,
                            type='market',
                            side=side,
                            amount=amount,
                            params={'reduceOnly': True}
                        )

                        closed_positions.append({
                            'symbol': symbol,
                            'amount': amount,
                            'order_id': order['id']
                        })

                        print(f"✅ Posição fechada: {symbol}")

                    except Exception as e:
                        errors.append({
                            'symbol': symbol,
                            'error': str(e)
                        })
                        print(f"❌ Erro ao fechar {symbol}: {e}")

            return {
                'success': len(errors) == 0,
                'exchange': exchange_name,
                'closed_count': len(closed_positions),
                'closed_positions': closed_positions,
                'errors': errors,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ Erro ao fechar todas as posições: {e}")
            return {
                'success': False,
                'error': str(e),
                'exchange': exchange_name,
                'timestamp': datetime.utcnow().isoformat()
            }
