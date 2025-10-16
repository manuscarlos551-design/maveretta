
# core/testing/realtime_backtest.py
"""
Real-time Backtesting - Simula estratégia em paralelo com live trading
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import copy

logger = logging.getLogger(__name__)


@dataclass
class ShadowTrade:
    """Trade simulado em paralelo"""
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float] = None
    pnl: float = 0.0
    status: str = 'open'
    opened_at: datetime = None
    closed_at: Optional[datetime] = None


class RealtimeBacktest:
    """
    Executa backtest em paralelo com trading real
    """
    
    def __init__(self):
        self.shadow_trades: Dict[str, ShadowTrade] = {}
        self.deviations: List[Dict[str, Any]] = []
        
        logger.info("✅ Realtime Backtest initialized")
    
    def shadow_execute(
        self,
        decision: Dict[str, Any],
        current_price: float
    ) -> str:
        """
        Executa decisão em modo shadow
        
        Args:
            decision: Decisão do agente
            current_price: Preço atual
        
        Returns:
            Shadow trade ID
        """
        trade_id = f"shadow_{decision['symbol']}_{int(datetime.now(timezone.utc).timestamp())}"
        
        shadow_trade = ShadowTrade(
            trade_id=trade_id,
            symbol=decision['symbol'],
            side=decision['action'],
            entry_price=current_price,
            opened_at=datetime.now(timezone.utc)
        )
        
        self.shadow_trades[trade_id] = shadow_trade
        
        logger.debug(f"Shadow trade opened: {trade_id} - {decision['action']} {decision['symbol']}")
        
        return trade_id
    
    def shadow_close(
        self,
        trade_id: str,
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Fecha trade shadow
        
        Args:
            trade_id: ID do trade
            current_price: Preço de fechamento
        
        Returns:
            Resultado do trade
        """
        if trade_id not in self.shadow_trades:
            return None
        
        trade = self.shadow_trades[trade_id]
        
        if trade.status == 'closed':
            return None
        
        trade.exit_price = current_price
        trade.closed_at = datetime.now(timezone.utc)
        trade.status = 'closed'
        
        # Calcula PnL
        if trade.side == 'buy':
            trade.pnl = (current_price - trade.entry_price) / trade.entry_price
        else:  # sell/short
            trade.pnl = (trade.entry_price - current_price) / trade.entry_price
        
        logger.debug(
            f"Shadow trade closed: {trade_id} - "
            f"PnL: {trade.pnl:.2%}"
        )
        
        return {
            'trade_id': trade_id,
            'pnl': trade.pnl,
            'entry': trade.entry_price,
            'exit': current_price
        }
    
    def compare_with_real(
        self,
        shadow_trade_id: str,
        real_trade: Dict[str, Any]
    ):
        """
        Compara resultado shadow vs real
        
        Args:
            shadow_trade_id: ID do shadow trade
            real_trade: Dados do trade real
        """
        if shadow_trade_id not in self.shadow_trades:
            return
        
        shadow = self.shadow_trades[shadow_trade_id]
        
        deviation = {
            'symbol': shadow.symbol,
            'shadow_pnl': shadow.pnl,
            'real_pnl': real_trade.get('pnl', 0),
            'shadow_entry': shadow.entry_price,
            'real_entry': real_trade.get('entry_price', 0),
            'slippage': abs(shadow.entry_price - real_trade.get('entry_price', 0)),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.deviations.append(deviation)
        
        # Log se desvio for significativo
        pnl_diff = abs(shadow.pnl - real_trade.get('pnl', 0))
        if pnl_diff > 0.02:  # >2%
            logger.warning(
                f"⚠️ Significant deviation detected: shadow vs real PnL diff = {pnl_diff:.2%}"
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas comparativas"""
        if not self.deviations:
            return {'total_comparisons': 0}
        
        avg_slippage = sum(d['slippage'] for d in self.deviations) / len(self.deviations)
        avg_pnl_deviation = sum(
            abs(d['shadow_pnl'] - d['real_pnl']) for d in self.deviations
        ) / len(self.deviations)
        
        return {
            'total_comparisons': len(self.deviations),
            'avg_slippage': avg_slippage,
            'avg_pnl_deviation': avg_pnl_deviation,
            'total_shadow_trades': len(self.shadow_trades),
            'open_shadow_trades': sum(1 for t in self.shadow_trades.values() if t.status == 'open')
        }


# Instância global
realtime_backtest = RealtimeBacktest()
