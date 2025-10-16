"""
Liquidation Protection - Proteção contra Liquidação

Features:
- Monitoramento de risco de liquidação
- Cálculo de alavancagem segura
- Redução automática de posição
- Trailing stop dinâmico
- Alertas de risco
"""

from typing import Dict, Optional
import asyncio
from datetime import datetime


class LiquidationProtection:
    """
    Proteção contra liquidação em futures trading.
    """

    def __init__(self, config: Dict = None):
        """
        Inicializa proteção contra liquidação.

        Args:
            config: Configurações opcionais
        """
        self.config = config or {}
        self.liquidation_threshold_pct = self.config.get('LIQUIDATION_THRESHOLD_PCT', 10.0)
        self.auto_reduce_enabled = self.config.get('AUTO_REDUCE_ENABLED', True)
        self.trailing_stop_enabled = self.config.get('TRAILING_STOP_ENABLED', True)

    def check_liquidation_risk(
        self,
        current_price: float,
        liquidation_price: float,
        side: str = 'long',
        threshold_pct: float = None
    ) -> Dict:
        """
        Verifica risco de liquidação.

        Args:
            current_price: Preço atual
            liquidation_price: Preço de liquidação
            side: 'long' ou 'short'
            threshold_pct: Threshold de risco (default: 10%)

        Returns:
            Dict com análise de risco
        """
        if threshold_pct is None:
            threshold_pct = self.liquidation_threshold_pct

        # Calcular distância até liquidação
        if side.lower() in ['long', 'buy']:
            distance_abs = current_price - liquidation_price
            distance_pct = (distance_abs / current_price) * 100
        else:  # short
            distance_abs = liquidation_price - current_price
            distance_pct = (distance_abs / current_price) * 100

        # Determinar nível de risco
        is_at_risk = distance_pct < threshold_pct
        
        if distance_pct < 5:
            risk_level = 'CRITICAL'
            action_required = 'IMMEDIATE_CLOSE'
        elif distance_pct < 10:
            risk_level = 'HIGH'
            action_required = 'REDUCE_POSITION'
        elif distance_pct < 20:
            risk_level = 'MEDIUM'
            action_required = 'MONITOR'
        else:
            risk_level = 'LOW'
            action_required = 'NONE'

        return {
            'is_at_risk': is_at_risk,
            'risk_level': risk_level,
            'action_required': action_required,
            'distance_abs': distance_abs,
            'distance_pct': distance_pct,
            'threshold_pct': threshold_pct,
            'current_price': current_price,
            'liquidation_price': liquidation_price,
            'side': side,
            'timestamp': datetime.utcnow().isoformat()
        }

    def calculate_safe_leverage(
        self,
        volatility: float,
        risk_tolerance: float = 0.5,
        min_leverage: int = 1,
        max_leverage: int = 20
    ) -> int:
        """
        Calcula alavancagem segura baseada em volatilidade.

        Args:
            volatility: Volatilidade histórica (ex: 0.02 = 2%)
            risk_tolerance: Tolerância ao risco (0-1, default: 0.5)
            min_leverage: Alavancagem mínima
            max_leverage: Alavancagem máxima

        Returns:
            Alavancagem segura recomendada
        """
        # Fórmula: Safe Leverage = (Risk Tolerance / Volatility)
        # Com limite entre min e max
        
        if volatility <= 0:
            return min_leverage

        safe_leverage = risk_tolerance / volatility
        
        # Aplicar limites
        safe_leverage = max(min_leverage, min(int(safe_leverage), max_leverage))
        
        return safe_leverage

    async def auto_reduce_position(
        self,
        position: Dict,
        futures_manager,
        reduction_pct: float = 50.0
    ) -> Dict:
        """
        Reduz posição automaticamente se próximo de liquidação.

        Args:
            position: Dados da posição
            futures_manager: Instância do FuturesManager
            reduction_pct: Percentual de redução (default: 50%)

        Returns:
            Resultado da redução
        """
        if not self.auto_reduce_enabled:
            return {
                'success': False,
                'message': 'Auto-reduce desabilitado'
            }

        try:
            symbol = position['symbol']
            exchange = position['exchange']
            current_amount = position['amount']
            
            # Calcular nova quantidade
            reduction_amount = current_amount * (reduction_pct / 100)
            
            # Fechar parcialmente a posição
            side = 'sell' if position['side'] == 'buy' else 'buy'
            
            # Executar redução (simulado aqui - integraria com exchange)
            result = {
                'success': True,
                'symbol': symbol,
                'exchange': exchange,
                'original_amount': current_amount,
                'reduced_amount': reduction_amount,
                'remaining_amount': current_amount - reduction_amount,
                'reduction_pct': reduction_pct,
                'timestamp': datetime.utcnow().isoformat(),
                'message': f'Posição reduzida em {reduction_pct}% por proteção de liquidação'
            }
            
            print(f"🛡️ Auto-reduce executado: {symbol} reduzido {reduction_pct}%")
            
            return result

        except Exception as e:
            print(f"❌ Erro no auto-reduce: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def set_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        side: str = 'long',
        trailing_pct: float = 2.0,
        activation_pct: float = 1.0
    ) -> Optional[float]:
        """
        Configura trailing stop dinâmico.

        Args:
            entry_price: Preço de entrada
            current_price: Preço atual
            side: 'long' ou 'short'
            trailing_pct: Distância do trailing stop (%)
            activation_pct: Lucro mínimo para ativar trailing (%)

        Returns:
            Preço do trailing stop ou None se não ativado
        """
        if not self.trailing_stop_enabled:
            return None

        # Calcular PnL atual
        if side.lower() in ['long', 'buy']:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Verificar se atingiu ativação
            if pnl_pct >= activation_pct:
                trailing_stop_price = current_price * (1 - trailing_pct / 100)
                return trailing_stop_price
        else:  # short
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            # Verificar se atingiu ativação
            if pnl_pct >= activation_pct:
                trailing_stop_price = current_price * (1 + trailing_pct / 100)
                return trailing_stop_price

        return None

    def calculate_safe_stop_loss(
        self,
        entry_price: float,
        leverage: int,
        side: str = 'long',
        max_loss_pct: float = 5.0
    ) -> float:
        """
        Calcula stop loss seguro considerando leverage.

        Args:
            entry_price: Preço de entrada
            leverage: Alavancagem
            side: 'long' ou 'short'
            max_loss_pct: Perda máxima aceitável do capital (%)

        Returns:
            Preço de stop loss recomendado
        """
        # Com leverage, o movimento de preço é amplificado
        # Se leverage = 10x, 1% de movimento = 10% de PnL
        
        # Calcular movimento de preço permitido
        price_move_pct = max_loss_pct / leverage
        
        if side.lower() in ['long', 'buy']:
            stop_loss = entry_price * (1 - price_move_pct / 100)
        else:  # short
            stop_loss = entry_price * (1 + price_move_pct / 100)
        
        return stop_loss

    def should_close_position(
        self,
        current_price: float,
        liquidation_price: float,
        side: str,
        emergency_threshold_pct: float = 5.0
    ) -> Dict:
        """
        Determina se deve fechar posição imediatamente.

        Args:
            current_price: Preço atual
            liquidation_price: Preço de liquidação
            side: 'long' ou 'short'
            emergency_threshold_pct: Threshold de emergência (%)

        Returns:
            Dict com decisão e justificativa
        """
        risk = self.check_liquidation_risk(
            current_price=current_price,
            liquidation_price=liquidation_price,
            side=side,
            threshold_pct=emergency_threshold_pct
        )
        
        should_close = risk['risk_level'] == 'CRITICAL'
        
        return {
            'should_close': should_close,
            'risk_level': risk['risk_level'],
            'distance_pct': risk['distance_pct'],
            'reason': f"Risco CRÍTICO - apenas {risk['distance_pct']:.2f}% até liquidação" if should_close else "Risco sob controle",
            'timestamp': datetime.utcnow().isoformat()
        }

    def calculate_add_margin_required(
        self,
        current_margin: float,
        current_price: float,
        liquidation_price: float,
        side: str,
        target_distance_pct: float = 15.0
    ) -> Dict:
        """
        Calcula margem adicional necessária para reduzir risco.

        Args:
            current_margin: Margem atual
            current_price: Preço atual
            liquidation_price: Preço de liquidação
            side: 'long' ou 'short'
            target_distance_pct: Distância alvo (%)

        Returns:
            Dict com margem adicional necessária
        """
        # Calcular distância atual
        if side.lower() in ['long', 'buy']:
            current_distance_pct = ((current_price - liquidation_price) / current_price) * 100
        else:  # short
            current_distance_pct = ((liquidation_price - current_price) / current_price) * 100

        # Se já está no alvo, não precisa adicionar
        if current_distance_pct >= target_distance_pct:
            return {
                'additional_margin_required': 0,
                'current_distance_pct': current_distance_pct,
                'target_distance_pct': target_distance_pct,
                'message': 'Margem suficiente'
            }

        # Calcular margem adicional (simplificado)
        # Em produção, usar fórmulas precisas da exchange
        distance_gap = target_distance_pct - current_distance_pct
        additional_margin = current_margin * (distance_gap / current_distance_pct)

        return {
            'additional_margin_required': additional_margin,
            'current_distance_pct': current_distance_pct,
            'target_distance_pct': target_distance_pct,
            'current_margin': current_margin,
            'recommended_action': 'ADD_MARGIN',
            'message': f'Adicionar ${additional_margin:.2f} de margem para atingir {target_distance_pct}% de distância'
        }

    def monitor_positions(
        self,
        positions: list,
        threshold_pct: float = 10.0
    ) -> Dict:
        """
        Monitora múltiplas posições e identifica riscos.

        Args:
            positions: Lista de posições
            threshold_pct: Threshold de risco

        Returns:
            Relatório de monitoramento
        """
        at_risk_positions = []
        safe_positions = []
        
        for position in positions:
            risk = self.check_liquidation_risk(
                current_price=position['current_price'],
                liquidation_price=position['liquidation_price'],
                side=position['side'],
                threshold_pct=threshold_pct
            )
            
            position_with_risk = {
                **position,
                'risk_analysis': risk
            }
            
            if risk['is_at_risk']:
                at_risk_positions.append(position_with_risk)
            else:
                safe_positions.append(position_with_risk)
        
        return {
            'total_positions': len(positions),
            'at_risk_count': len(at_risk_positions),
            'safe_count': len(safe_positions),
            'at_risk_positions': at_risk_positions,
            'safe_positions': safe_positions,
            'timestamp': datetime.utcnow().isoformat()
        }
