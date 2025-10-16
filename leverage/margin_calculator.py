"""
Margin Calculator - Calculadora de Margem para Futuros

Features:
- Cálculo de margem inicial
- Cálculo de margem de manutenção
- Cálculo de margem disponível
- Margin ratio
- Validações de margem
"""

from typing import Dict
from decimal import Decimal


class MarginCalculator:
    """
    Calculadora de margem para futuros.
    """

    # Taxas de margem de manutenção por exchange (padrão)
    MAINTENANCE_MARGIN_RATES = {
        'binance': {
            'default': 0.004,  # 0.4%
            'tiers': {
                10000: 0.005,   # > $10k notional
                50000: 0.01,    # > $50k notional
                250000: 0.02,   # > $250k notional
            }
        },
        'bybit': {
            'default': 0.004,
            'tiers': {}
        },
        'okx': {
            'default': 0.004,
            'tiers': {}
        }
    }

    def __init__(self, exchange: str = 'binance'):
        """
        Inicializa calculadora de margem.

        Args:
            exchange: Nome da exchange (binance, bybit, okx)
        """
        self.exchange = exchange.lower()

    def calculate_initial_margin(
        self,
        position_size: float,
        leverage: int,
        price: float = 1.0
    ) -> float:
        """
        Calcula margem inicial necessária.

        Args:
            position_size: Tamanho da posição (em contratos/coins)
            leverage: Alavancagem
            price: Preço de entrada (padrão: 1.0)

        Returns:
            Margem inicial necessária
        """
        notional_value = position_size * price
        initial_margin = notional_value / leverage
        
        return initial_margin

    def calculate_maintenance_margin(
        self,
        position_size: float,
        leverage: int,
        exchange: str = None,
        price: float = 1.0
    ) -> float:
        """
        Calcula margem de manutenção.

        Args:
            position_size: Tamanho da posição
            leverage: Alavancagem
            exchange: Exchange (opcional, usa self.exchange se None)
            price: Preço atual

        Returns:
            Margem de manutenção necessária
        """
        if exchange is None:
            exchange = self.exchange

        notional_value = position_size * price
        
        # Obter taxa de manutenção baseada em tier
        maintenance_rate = self._get_maintenance_rate(exchange, notional_value)
        
        maintenance_margin = notional_value * maintenance_rate
        
        return maintenance_margin

    def calculate_available_margin(
        self,
        balance: float,
        used_margin: float
    ) -> float:
        """
        Calcula margem disponível.

        Args:
            balance: Saldo total
            used_margin: Margem já utilizada

        Returns:
            Margem disponível
        """
        available_margin = balance - used_margin
        
        return max(0, available_margin)

    def calculate_margin_ratio(
        self,
        equity: float,
        used_margin: float
    ) -> float:
        """
        Calcula ratio de margem.

        Margin Ratio = (Equity / Used Margin) * 100

        Args:
            equity: Equity atual (balance + unrealized PnL)
            used_margin: Margem utilizada

        Returns:
            Margin ratio em porcentagem
        """
        if used_margin == 0:
            return float('inf')
        
        margin_ratio = (equity / used_margin) * 100
        
        return margin_ratio

    def is_margin_sufficient(
        self,
        balance: float,
        position_size: float,
        leverage: int,
        price: float = 1.0
    ) -> Dict:
        """
        Verifica se a margem é suficiente.

        Args:
            balance: Saldo disponível
            position_size: Tamanho da posição desejada
            leverage: Alavancagem
            price: Preço de entrada

        Returns:
            Dict com resultado da validação
        """
        initial_margin = self.calculate_initial_margin(position_size, leverage, price)
        
        is_sufficient = balance >= initial_margin
        
        return {
            'is_sufficient': is_sufficient,
            'balance': balance,
            'initial_margin_required': initial_margin,
            'available_margin': balance - initial_margin if is_sufficient else 0,
            'deficit': initial_margin - balance if not is_sufficient else 0
        }

    def calculate_max_position_size(
        self,
        available_margin: float,
        leverage: int,
        price: float = 1.0,
        safety_factor: float = 0.95
    ) -> float:
        """
        Calcula tamanho máximo de posição baseado na margem disponível.

        Args:
            available_margin: Margem disponível
            leverage: Alavancagem
            price: Preço de entrada
            safety_factor: Fator de segurança (0.95 = usar 95% da margem)

        Returns:
            Tamanho máximo de posição
        """
        # Aplicar fator de segurança
        usable_margin = available_margin * safety_factor
        
        # Calcular tamanho máximo
        max_notional = usable_margin * leverage
        max_position_size = max_notional / price
        
        return max_position_size

    def calculate_pnl(
        self,
        entry_price: float,
        current_price: float,
        position_size: float,
        side: str = 'long'
    ) -> Dict:
        """
        Calcula PnL (Profit and Loss).

        Args:
            entry_price: Preço de entrada
            current_price: Preço atual
            position_size: Tamanho da posição
            side: 'long' ou 'short'

        Returns:
            Dict com PnL e ROE
        """
        if side.lower() in ['long', 'buy']:
            pnl = (current_price - entry_price) * position_size
        else:  # short
            pnl = (entry_price - current_price) * position_size
        
        # ROE (Return on Equity)
        notional = position_size * entry_price
        roe_pct = (pnl / notional) * 100 if notional > 0 else 0
        
        return {
            'pnl': pnl,
            'pnl_pct': roe_pct,
            'notional_value': notional,
            'entry_price': entry_price,
            'current_price': current_price,
            'position_size': position_size,
            'side': side
        }

    def calculate_liquidation_distance(
        self,
        current_price: float,
        liquidation_price: float,
        side: str = 'long'
    ) -> Dict:
        """
        Calcula distância até liquidação.

        Args:
            current_price: Preço atual
            liquidation_price: Preço de liquidação
            side: 'long' ou 'short'

        Returns:
            Dict com distância e risco
        """
        # Distância absoluta
        if side.lower() in ['long', 'buy']:
            distance_abs = current_price - liquidation_price
            distance_pct = (distance_abs / current_price) * 100
        else:  # short
            distance_abs = liquidation_price - current_price
            distance_pct = (distance_abs / current_price) * 100
        
        # Classificar risco
        if distance_pct < 5:
            risk_level = 'CRITICAL'
        elif distance_pct < 10:
            risk_level = 'HIGH'
        elif distance_pct < 20:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'distance_abs': distance_abs,
            'distance_pct': distance_pct,
            'risk_level': risk_level,
            'current_price': current_price,
            'liquidation_price': liquidation_price,
            'side': side
        }

    def _get_maintenance_rate(self, exchange: str, notional_value: float) -> float:
        """
        Obtém taxa de margem de manutenção baseada em tier.

        Args:
            exchange: Nome da exchange
            notional_value: Valor nocional da posição

        Returns:
            Taxa de margem de manutenção
        """
        if exchange not in self.MAINTENANCE_MARGIN_RATES:
            exchange = 'binance'  # padrão
        
        rates = self.MAINTENANCE_MARGIN_RATES[exchange]
        default_rate = rates['default']
        tiers = rates['tiers']
        
        # Verificar tiers (em ordem decrescente)
        for threshold in sorted(tiers.keys(), reverse=True):
            if notional_value >= threshold:
                return tiers[threshold]
        
        return default_rate

    def validate_leverage(
        self,
        leverage: int,
        max_leverage: int = 20
    ) -> Dict:
        """
        Valida se a alavancagem está dentro dos limites.

        Args:
            leverage: Alavancagem desejada
            max_leverage: Alavancagem máxima permitida

        Returns:
            Dict com resultado da validação
        """
        is_valid = 1 <= leverage <= max_leverage
        
        return {
            'is_valid': is_valid,
            'leverage': leverage,
            'max_leverage': max_leverage,
            'message': 'OK' if is_valid else f'Leverage deve estar entre 1x e {max_leverage}x'
        }
