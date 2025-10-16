
# core/strategies/smart_dca.py
"""
Smart DCA+ - DCA inteligente que acelera em quedas e pausa em topos
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DCAConfig:
    """Configuração do DCA"""
    symbol: str
    base_amount_usdt: float
    interval_hours: int
    max_acceleration: float = 3.0  # Máximo 3x em quedas
    min_amount_usdt: float = 10.0
    max_amount_usdt: float = 500.0


class SmartDCA:
    """
    DCA+ Inteligente com aceleração/pausa baseada em condições de mercado
    """
    
    def __init__(self):
        self.active_plans: Dict[str, Dict[str, Any]] = {}
        
        logger.info("✅ Smart DCA+ initialized")
    
    def create_plan(self, config: DCAConfig) -> str:
        """
        Cria um plano de DCA
        
        Args:
            config: Configuração do DCA
        
        Returns:
            Plan ID
        """
        plan_id = f"dca_{config.symbol}_{int(datetime.now(timezone.utc).timestamp())}"
        
        self.active_plans[plan_id] = {
            'config': config,
            'total_invested': 0.0,
            'total_bought': 0.0,
            'avg_price': 0.0,
            'last_buy': None,
            'buys_count': 0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"DCA plan created: {plan_id} - {config.symbol} every {config.interval_hours}h")
        
        return plan_id
    
    def execute_cycle(
        self,
        plan_id: str,
        current_price: float,
        market_signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executa um ciclo de DCA
        
        Args:
            plan_id: ID do plano
            current_price: Preço atual
            market_signals: Sinais de mercado
        
        Returns:
            Resultado da execução
        """
        if plan_id not in self.active_plans:
            return {'success': False, 'error': 'Plan not found'}
        
        plan = self.active_plans[plan_id]
        config: DCAConfig = plan['config']
        
        # Verifica se está no intervalo
        if plan['last_buy']:
            last_buy_time = datetime.fromisoformat(plan['last_buy'])
            if datetime.now(timezone.utc) < last_buy_time + timedelta(hours=config.interval_hours):
                return {'success': False, 'reason': 'Not in interval yet'}
        
        # Calcula multiplicador baseado em sinais
        multiplier = self._calculate_multiplier(current_price, plan['avg_price'], market_signals)
        
        # Calcula quantidade a comprar
        amount_usdt = min(
            max(config.base_amount_usdt * multiplier, config.min_amount_usdt),
            config.max_amount_usdt
        )
        
        # Se multiplicador é 0, pula este ciclo
        if multiplier == 0:
            return {
                'success': False,
                'reason': 'Market too hot - pausing DCA',
                'signal': market_signals
            }
        
        # Executa compra (simulado)
        quantity = amount_usdt / current_price
        
        # Atualiza plano
        plan['total_invested'] += amount_usdt
        plan['total_bought'] += quantity
        plan['avg_price'] = plan['total_invested'] / plan['total_bought']
        plan['last_buy'] = datetime.now(timezone.utc).isoformat()
        plan['buys_count'] += 1
        
        logger.info(
            f"DCA executed: {config.symbol} ${amount_usdt:.2f} @ {current_price:.2f} "
            f"(multiplier: {multiplier:.2f}x)"
        )
        
        return {
            'success': True,
            'amount_usdt': amount_usdt,
            'quantity': quantity,
            'price': current_price,
            'multiplier': multiplier,
            'new_avg_price': plan['avg_price'],
            'total_invested': plan['total_invested']
        }
    
    def _calculate_multiplier(
        self,
        current_price: float,
        avg_price: Optional[float],
        signals: Dict[str, Any]
    ) -> float:
        """
        Calcula multiplicador de aceleração
        
        Returns:
            Multiplicador (0 = pausa, 1 = normal, >1 = acelera)
        """
        multiplier = 1.0
        
        # Se não tem preço médio ainda, compra normalmente
        if not avg_price or avg_price == 0:
            return multiplier
        
        # Aceleração baseada em queda
        price_drop = (avg_price - current_price) / avg_price
        
        if price_drop > 0.1:  # 10% abaixo da média
            multiplier = 2.0
        elif price_drop > 0.05:  # 5% abaixo
            multiplier = 1.5
        elif price_drop < -0.1:  # 10% acima (topo)
            multiplier = 0.0  # Pausa
        elif price_drop < -0.05:  # 5% acima
            multiplier = 0.5  # Reduz
        
        # Ajusta por volatilidade
        volatility = signals.get('volatility', 0.5)
        if volatility > 0.8:  # Alta volatilidade
            multiplier *= 1.3  # Aproveita quedas
        
        # Ajusta por tendência
        trend = signals.get('trend', 0)
        if trend < -0.3:  # Downtrend forte
            multiplier *= 1.2  # Acelera
        elif trend > 0.3:  # Uptrend forte
            multiplier *= 0.7  # Reduz
        
        return min(multiplier, 3.0)  # Cap em 3x
    
    def get_plan_stats(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retorna estatísticas do plano"""
        plan = self.active_plans.get(plan_id)
        
        if not plan:
            return None
        
        config: DCAConfig = plan['config']
        
        return {
            'plan_id': plan_id,
            'symbol': config.symbol,
            'total_invested': plan['total_invested'],
            'total_bought': plan['total_bought'],
            'avg_price': plan['avg_price'],
            'buys_count': plan['buys_count'],
            'last_buy': plan['last_buy']
        }


# Instância global
smart_dca = SmartDCA()
