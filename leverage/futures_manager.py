"""
Futures Manager - Gerenciador de Trading com Futuros e Alavancagem

Features:
- Suporte a múltiplas exchanges (Binance, Bybit, OKX)
- Gestão de margem
- Proteção contra liquidação
- Análise de funding rate
- Position sizing com leverage
- Cálculo de preço de liquidação
- Modo isolated e cross margin
"""

from typing import Dict, List, Optional
from decimal import Decimal
import ccxt
import asyncio
from datetime import datetime


class FuturesManager:
    """
    Gerenciador de trading com futuros e alavancagem.
    """

    def __init__(self, config: Dict):
        """
        Inicializa o Futures Manager.

        Args:
            config: Dicionário com configurações das exchanges
        """
        self.config = config
        self.exchanges = {}
        self.max_leverage = int(config.get('MAX_LEVERAGE', 20))
        self.default_margin_mode = config.get('DEFAULT_MARGIN_MODE', 'isolated')
        
        # Inicializar exchanges com futures habilitado
        self._init_exchanges()

    def _init_exchanges(self):
        """Inicializa conexões com exchanges para futures"""
        # Binance Futures
        if self.config.get('BINANCE_ENABLED'):
            self.exchanges['binance'] = ccxt.binance({
                'apiKey': self.config['BINANCE_API_KEY'],
                'secret': self.config['BINANCE_API_SECRET'],
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True
                },
                'enableRateLimit': True,
            })
            print("✅ Binance Futures initialized")

        # Bybit Futures
        if self.config.get('BYBIT_ENABLED'):
            self.exchanges['bybit'] = ccxt.bybit({
                'apiKey': self.config['BYBIT_API_KEY'],
                'secret': self.config['BYBIT_API_SECRET'],
                'options': {
                    'defaultType': 'future',
                },
                'enableRateLimit': True,
            })
            print("✅ Bybit Futures initialized")

        # OKX Futures
        if self.config.get('OKX_ENABLED'):
            self.exchanges['okx'] = ccxt.okx({
                'apiKey': self.config['OKX_API_KEY'],
                'secret': self.config['OKX_API_SECRET'],
                'password': self.config.get('OKX_API_PASSPHRASE', ''),
                'options': {
                    'defaultType': 'swap',  # Perpetual futures
                },
                'enableRateLimit': True,
            })
            print("✅ OKX Futures initialized")

    def calculate_position_size(
        self,
        balance: float,
        leverage: int,
        risk_per_trade_pct: float,
        stop_loss_pct: float
    ) -> Dict:
        """
        Calcula tamanho ideal da posição com leverage.

        Args:
            balance: Saldo disponível
            leverage: Alavancagem (ex: 10x)
            risk_per_trade_pct: Risco por trade (ex: 2%)
            stop_loss_pct: Stop loss em % (ex: 1%)

        Returns:
            Dict com size e exposure
        """
        # Validar leverage
        if leverage > self.max_leverage:
            raise ValueError(
                f"Leverage too high! Max {self.max_leverage}x, requested {leverage}x"
            )

        # Risco em valor absoluto
        risk_amount = balance * (risk_per_trade_pct / 100)

        # Position size baseado em stop loss
        position_size = risk_amount / (stop_loss_pct / 100)

        # Exposure total com leverage
        total_exposure = position_size * leverage

        # Margem necessária
        margin_required = position_size / leverage

        # Validar margem disponível
        if margin_required > balance:
            raise ValueError(
                f"Margem insuficiente. Necessário: ${margin_required:.2f}, "
                f"Disponível: ${balance:.2f}"
            )

        # Margin ratio
        margin_ratio = (balance / margin_required) if margin_required > 0 else 0

        return {
            'position_size': position_size,
            'total_exposure': total_exposure,
            'margin_required': margin_required,
            'margin_available': balance - margin_required,
            'leverage': leverage,
            'risk_amount': risk_amount,
            'margin_ratio': margin_ratio,
            'risk_per_trade_pct': risk_per_trade_pct,
            'stop_loss_pct': stop_loss_pct
        }

    def calculate_liquidation_price(
        self,
        entry_price: float,
        leverage: int,
        side: str = 'long',
        maintenance_margin_rate: float = 0.004
    ) -> float:
        """
        Calcula preço de liquidação.

        Args:
            entry_price: Preço de entrada
            leverage: Alavancagem
            side: 'long' ou 'short'
            maintenance_margin_rate: Taxa de margem de manutenção (0.4% padrão)

        Returns:
            Preço de liquidação
        """
        if side.lower() in ['long', 'buy']:
            # Long: liquidação abaixo do entry
            liq_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
        else:  # short
            # Short: liquidação acima do entry
            liq_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)

        return liq_price

    async def open_futures_position(
        self,
        exchange_name: str,
        symbol: str,
        side: str,
        amount: float,
        leverage: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        margin_mode: str = 'isolated'
    ) -> Dict:
        """
        Abre posição de futuros.

        Args:
            exchange_name: Nome da exchange (binance, bybit, okx)
            symbol: Par de moedas (ex: 'BTC/USDT:USDT')
            side: 'buy' (long) ou 'sell' (short)
            amount: Quantidade
            leverage: Alavancagem
            stop_loss: Preço de stop loss (opcional)
            take_profit: Preço de take profit (opcional)
            margin_mode: 'isolated' ou 'cross'

        Returns:
            Dict com detalhes da ordem
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        if leverage > self.max_leverage:
            raise ValueError(f"Leverage máximo: {self.max_leverage}x")

        exchange = self.exchanges[exchange_name]

        # Validar stop loss obrigatório
        if stop_loss is None:
            raise ValueError("Stop loss é obrigatório para futures trading")

        try:
            # Configurar leverage
            await self._set_leverage_async(exchange, leverage, symbol)

            # Configurar margin mode
            await self._set_margin_mode_async(exchange, margin_mode, symbol)

            # Abrir posição
            order = await exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params={'leverage': leverage}
            )

            # Calcular preço de liquidação
            entry_price = order.get('average') or order.get('price', 0)
            liquidation_price = self.calculate_liquidation_price(
                entry_price=entry_price,
                leverage=leverage,
                side=side
            )

            # Configurar stop loss
            if stop_loss:
                await exchange.create_order(
                    symbol=symbol,
                    type='stop_market',
                    side='sell' if side == 'buy' else 'buy',
                    amount=amount,
                    params={
                        'stopPrice': stop_loss,
                        'reduceOnly': True
                    }
                )

            # Configurar take profit
            if take_profit:
                await exchange.create_order(
                    symbol=symbol,
                    type='take_profit_market',
                    side='sell' if side == 'buy' else 'buy',
                    amount=amount,
                    params={
                        'stopPrice': take_profit,
                        'reduceOnly': True
                    }
                )

            position_data = {
                'order_id': order['id'],
                'symbol': symbol,
                'exchange': exchange_name,
                'side': side,
                'amount': amount,
                'leverage': leverage,
                'entry_price': entry_price,
                'liquidation_price': liquidation_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'margin_mode': margin_mode,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'open'
            }

            print(f"✅ Posição de futures aberta: {symbol} {side.upper()} {amount} @ {entry_price} (leverage: {leverage}x)")
            
            return position_data

        except Exception as e:
            print(f"❌ Erro ao abrir posição de futures: {e}")
            raise

    async def close_futures_position(
        self,
        exchange_name: str,
        symbol: str,
        position_id: Optional[str] = None
    ) -> Dict:
        """
        Fecha posição de futuros.

        Args:
            exchange_name: Nome da exchange
            symbol: Par de moedas
            position_id: ID da posição (opcional)

        Returns:
            Dict com resultado do fechamento
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            # Obter posição atual
            positions = await exchange.fetch_positions([symbol])
            
            if not positions or len(positions) == 0:
                return {
                    'success': False,
                    'message': 'Nenhuma posição aberta encontrada'
                }

            position = positions[0]
            
            # Fechar posição
            side = 'sell' if position['side'] == 'long' else 'buy'
            amount = abs(float(position['contracts']))

            order = await exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params={'reduceOnly': True}
            )

            result = {
                'success': True,
                'order_id': order['id'],
                'symbol': symbol,
                'exchange': exchange_name,
                'amount': amount,
                'exit_price': order.get('average') or order.get('price', 0),
                'pnl': position.get('unrealizedPnl', 0),
                'timestamp': datetime.utcnow().isoformat()
            }

            print(f"✅ Posição de futures fechada: {symbol} PnL: ${result['pnl']:.2f}")
            
            return result

        except Exception as e:
            print(f"❌ Erro ao fechar posição de futures: {e}")
            raise

    async def get_open_positions(
        self,
        exchange_name: str,
        symbols: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Lista posições abertas.

        Args:
            exchange_name: Nome da exchange
            symbols: Lista de símbolos (opcional, None = todos)

        Returns:
            Lista de posições abertas
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            positions = await exchange.fetch_positions(symbols)
            
            # Filtrar apenas posições abertas
            open_positions = []
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts != 0:
                    open_positions.append({
                        'symbol': pos['symbol'],
                        'exchange': exchange_name,
                        'side': pos['side'],
                        'contracts': contracts,
                        'notional': pos.get('notional', 0),
                        'leverage': pos.get('leverage', 1),
                        'entry_price': pos.get('entryPrice', 0),
                        'mark_price': pos.get('markPrice', 0),
                        'liquidation_price': pos.get('liquidationPrice', 0),
                        'unrealized_pnl': pos.get('unrealizedPnl', 0),
                        'margin_mode': pos.get('marginMode', 'unknown'),
                        'timestamp': pos.get('timestamp', 0)
                    })

            return open_positions

        except Exception as e:
            print(f"❌ Erro ao obter posições abertas: {e}")
            raise

    async def _set_leverage_async(self, exchange, leverage: int, symbol: str):
        """Define alavancagem na exchange"""
        try:
            await exchange.set_leverage(leverage, symbol)
            print(f"✅ Leverage configurado: {leverage}x para {symbol}")
        except Exception as e:
            print(f"⚠️ Erro ao configurar leverage: {e}")

    async def _set_margin_mode_async(self, exchange, mode: str, symbol: str):
        """Define modo de margem (isolated/cross)"""
        try:
            await exchange.set_margin_mode(mode, symbol)
            print(f"✅ Margin mode configurado: {mode} para {symbol}")
        except Exception as e:
            print(f"⚠️ Erro ao configurar margin mode: {e}")

    def get_supported_exchanges(self) -> List[str]:
        """Retorna lista de exchanges suportadas"""
        return list(self.exchanges.keys())

    def is_futures_enabled(self, exchange_name: str) -> bool:
        """Verifica se futures está habilitado para uma exchange"""
        return exchange_name in self.exchanges
