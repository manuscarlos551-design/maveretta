"""
Position Sizer - Calculador de Tamanho de Posição para Futures

Features:
- Cálculo de position size com leverage
- Ajuste baseado em liquidez
- Kelly Criterion
- Risk-based sizing
- Portfolio allocation
"""

from typing import Dict, Optional
from decimal import Decimal
import math


class PositionSizer:
    """
    Calculador de tamanho de posição para futures com leverage.
    """

    def __init__(self, config: Dict = None):
        """
        Inicializa position sizer.

        Args:
            config: Configurações opcionais
        """
        self.config = config or {}
        self.default_risk_per_trade = self.config.get('MAX_RISK_PER_TRADE_PCT', 2.0)
        self.max_exposure_pct = self.config.get('MAX_EXPOSURE_PCT', 50.0)

    def calculate_position_size(
        self,
        balance: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss_price: float,
        leverage: int = 1
    ) -> Dict:
        """
        Calcula tamanho de posição com leverage.

        Args:
            balance: Saldo disponível
            risk_per_trade: Risco por trade em % (ex: 2.0)
            entry_price: Preço de entrada
            stop_loss_price: Preço de stop loss
            leverage: Alavancagem (default: 1)

        Returns:
            Dict com cálculo de position size
        """
        # Validar inputs
        if entry_price <= 0 or stop_loss_price <= 0:
            raise ValueError("Preços devem ser positivos")
        
        if balance <= 0:
            raise ValueError("Balance deve ser positivo")

        # Calcular risco em valor absoluto
        risk_amount = balance * (risk_per_trade / 100)

        # Calcular distância de stop loss
        stop_distance_pct = abs((entry_price - stop_loss_price) / entry_price) * 100

        # Position size baseado em risco
        # Risk Amount = Position Size × Stop Distance × Entry Price
        # Position Size = Risk Amount / (Stop Distance × Entry Price)
        
        if stop_distance_pct == 0:
            raise ValueError("Stop loss não pode ser igual ao entry price")

        # Position size sem leverage
        position_size_base = risk_amount / (stop_distance_pct / 100)

        # Position size com leverage (em coins/contracts)
        position_size_coins = position_size_base / entry_price

        # Notional value (exposure total)
        notional_value = position_size_coins * entry_price * leverage

        # Margem necessária
        margin_required = notional_value / leverage

        # Validar margem disponível
        if margin_required > balance:
            # Ajustar position size para caber na margem
            max_notional = balance * leverage
            position_size_coins = max_notional / entry_price
            margin_required = balance
            notional_value = max_notional

        # Calcular percentuais
        exposure_pct = (notional_value / balance) * 100 if balance > 0 else 0
        margin_used_pct = (margin_required / balance) * 100 if balance > 0 else 0

        return {
            'position_size_coins': position_size_coins,
            'position_size_usd': position_size_coins * entry_price,
            'notional_value': notional_value,
            'margin_required': margin_required,
            'margin_available': balance - margin_required,
            'leverage': leverage,
            'risk_amount': risk_amount,
            'risk_per_trade_pct': risk_per_trade,
            'stop_distance_pct': stop_distance_pct,
            'exposure_pct': exposure_pct,
            'margin_used_pct': margin_used_pct,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'is_valid': margin_required <= balance and exposure_pct <= self.max_exposure_pct
        }

    def calculate_max_position_size(
        self,
        available_margin: float,
        leverage: int,
        price: float,
        safety_factor: float = 0.95
    ) -> Dict:
        """
        Calcula tamanho máximo de posição.

        Args:
            available_margin: Margem disponível
            leverage: Alavancagem
            price: Preço de entrada
            safety_factor: Fator de segurança (0.95 = usar 95%)

        Returns:
            Dict com cálculo
        """
        # Aplicar fator de segurança
        usable_margin = available_margin * safety_factor

        # Calcular tamanho máximo
        max_notional = usable_margin * leverage
        max_position_coins = max_notional / price

        return {
            'max_position_coins': max_position_coins,
            'max_position_usd': max_notional,
            'margin_required': usable_margin,
            'available_margin': available_margin,
            'leverage': leverage,
            'price': price,
            'safety_factor': safety_factor
        }

    def adjust_for_liquidity(
        self,
        desired_size: float,
        orderbook_liquidity: Dict
    ) -> Dict:
        """
        Ajusta tamanho baseado em liquidez.

        Args:
            desired_size: Tamanho desejado
            orderbook_liquidity: Dict com liquidez do orderbook
                {
                    'bid_volume': float,
                    'ask_volume': float,
                    'avg_bid_price': float,
                    'avg_ask_price': float
                }

        Returns:
            Dict com tamanho ajustado
        """
        bid_volume = orderbook_liquidity.get('bid_volume', 0)
        ask_volume = orderbook_liquidity.get('ask_volume', 0)

        # Usar menor volume (mais conservador)
        available_liquidity = min(bid_volume, ask_volume)

        # Limitar position size a % da liquidez disponível
        max_liquidity_size = available_liquidity * 0.1  # Máximo 10% da liquidez

        # Tamanho ajustado
        adjusted_size = min(desired_size, max_liquidity_size)

        # Impacto de liquidez
        liquidity_impact_pct = (adjusted_size / available_liquidity) * 100 if available_liquidity > 0 else 0

        return {
            'original_size': desired_size,
            'adjusted_size': adjusted_size,
            'available_liquidity': available_liquidity,
            'liquidity_impact_pct': liquidity_impact_pct,
            'was_adjusted': adjusted_size < desired_size,
            'adjustment_reason': 'Liquidez insuficiente' if adjusted_size < desired_size else 'OK'
        }

    def calculate_kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        balance: float,
        leverage: int = 1,
        kelly_fraction: float = 0.25
    ) -> Dict:
        """
        Calcula tamanho de posição usando Kelly Criterion.

        Formula: Kelly % = (Win Rate × Avg Win - (1 - Win Rate) × Avg Loss) / Avg Win

        Args:
            win_rate: Taxa de acerto (0-1, ex: 0.55)
            avg_win: Ganho médio por trade vencedor
            avg_loss: Perda média por trade perdedor
            balance: Saldo disponível
            leverage: Alavancagem
            kelly_fraction: Fração de Kelly a usar (0.25 = Quarter Kelly)

        Returns:
            Dict com cálculo de Kelly
        """
        if not (0 <= win_rate <= 1):
            raise ValueError("Win rate deve estar entre 0 e 1")

        if avg_win <= 0 or avg_loss <= 0:
            raise ValueError("Avg win e avg loss devem ser positivos")

        # Calcular Kelly %
        kelly_pct = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        # Aplicar fração de Kelly (mais conservador)
        adjusted_kelly_pct = kelly_pct * kelly_fraction

        # Limitar a valores razoáveis
        adjusted_kelly_pct = max(0, min(adjusted_kelly_pct, 0.25))  # Máximo 25%

        # Calcular tamanho de posição
        position_size_usd = balance * adjusted_kelly_pct * leverage

        return {
            'kelly_pct': kelly_pct * 100,
            'adjusted_kelly_pct': adjusted_kelly_pct * 100,
            'position_size_usd': position_size_usd,
            'leverage': leverage,
            'kelly_fraction_used': kelly_fraction,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'balance': balance,
            'recommendation': 'VALID' if 0 < adjusted_kelly_pct <= 0.25 else 'OUT_OF_RANGE'
        }

    def calculate_risk_based_size(
        self,
        balance: float,
        volatility: float,
        confidence: float,
        leverage: int,
        price: float
    ) -> Dict:
        """
        Calcula position size baseado em risco e volatilidade.

        Args:
            balance: Saldo disponível
            volatility: Volatilidade histórica (ex: 0.02 = 2%)
            confidence: Nível de confiança (0-1, ex: 0.7)
            leverage: Alavancagem
            price: Preço de entrada

        Returns:
            Dict com cálculo
        """
        # Risk-adjusted position size
        # Maior volatilidade = menor posição
        # Maior confiança = maior posição

        base_risk_pct = 0.02  # 2% base risk

        # Ajustar por volatilidade
        volatility_adj = 1 / (1 + volatility * 10)

        # Ajustar por confiança
        confidence_adj = confidence

        # Risk ajustado
        adjusted_risk_pct = base_risk_pct * volatility_adj * confidence_adj

        # Position size
        risk_amount = balance * adjusted_risk_pct
        position_size_usd = risk_amount * leverage
        position_size_coins = position_size_usd / price

        return {
            'position_size_coins': position_size_coins,
            'position_size_usd': position_size_usd,
            'risk_pct': adjusted_risk_pct * 100,
            'risk_amount': risk_amount,
            'leverage': leverage,
            'volatility': volatility,
            'confidence': confidence,
            'volatility_adjustment': volatility_adj,
            'confidence_adjustment': confidence_adj
        }

    def validate_position_size(
        self,
        position_size: float,
        balance: float,
        leverage: int,
        max_exposure_pct: float = None
    ) -> Dict:
        """
        Valida se position size está dentro dos limites.

        Args:
            position_size: Tamanho da posição (USD)
            balance: Saldo disponível
            leverage: Alavancagem
            max_exposure_pct: Exposição máxima (%)

        Returns:
            Dict com validação
        """
        if max_exposure_pct is None:
            max_exposure_pct = self.max_exposure_pct

        # Calcular margem necessária
        margin_required = position_size / leverage

        # Calcular exposure
        exposure_pct = (position_size / balance) * 100 if balance > 0 else 0

        # Validações
        is_valid = True
        errors = []

        if margin_required > balance:
            is_valid = False
            errors.append(f"Margem insuficiente: necessário ${margin_required:.2f}, disponível ${balance:.2f}")

        if exposure_pct > max_exposure_pct:
            is_valid = False
            errors.append(f"Exposição muito alta: {exposure_pct:.2f}% (máximo: {max_exposure_pct}%)")

        return {
            'is_valid': is_valid,
            'position_size': position_size,
            'margin_required': margin_required,
            'balance': balance,
            'exposure_pct': exposure_pct,
            'max_exposure_pct': max_exposure_pct,
            'errors': errors,
            'message': 'OK' if is_valid else '; '.join(errors)
        }

    def calculate_portfolio_allocation(
        self,
        total_balance: float,
        num_positions: int,
        leverage: int,
        allocation_method: str = 'equal'
    ) -> Dict:
        """
        Calcula alocação de portfolio para múltiplas posições.

        Args:
            total_balance: Saldo total
            num_positions: Número de posições
            leverage: Alavancagem
            allocation_method: 'equal' ou 'risk_parity'

        Returns:
            Dict com alocação
        """
        if num_positions <= 0:
            raise ValueError("Número de posições deve ser > 0")

        if allocation_method == 'equal':
            # Alocação igual
            margin_per_position = total_balance / num_positions
            size_per_position = margin_per_position * leverage
        else:
            # Risk parity (simplificado)
            margin_per_position = total_balance / num_positions
            size_per_position = margin_per_position * leverage

        # Validar que não ultrapassa max exposure
        total_exposure = size_per_position * num_positions
        exposure_pct = (total_exposure / total_balance) * 100 if total_balance > 0 else 0

        return {
            'total_balance': total_balance,
            'num_positions': num_positions,
            'margin_per_position': margin_per_position,
            'size_per_position': size_per_position,
            'total_exposure': total_exposure,
            'exposure_pct': exposure_pct,
            'leverage': leverage,
            'allocation_method': allocation_method,
            'is_valid': exposure_pct <= self.max_exposure_pct
        }
