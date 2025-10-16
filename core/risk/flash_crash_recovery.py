
# core/risk/flash_crash_recovery.py
"""
Flash Crash Recovery - Detecta e capitaliza em flash crashes
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


class FlashCrashDetector:
    """
    Detecta flash crashes e executa ordens de recuperação
    """
    
    def __init__(self):
        self.price_history: Dict[str, deque] = {}
        self.crash_alerts: List[Dict[str, Any]] = []
        self.recovery_orders: List[Dict[str, Any]] = []
        
        # Parâmetros de detecção
        self.crash_threshold = -0.15  # -15% em curto período
        self.recovery_window = 300  # 5 minutos
        self.max_history = 100
        
        logger.info("✅ Flash Crash Detector initialized")
    
    def update_price(self, symbol: str, price: float, volume: float = 0):
        """
        Atualiza preço e detecta anomalias
        
        Args:
            symbol: Símbolo
            price: Preço atual
            volume: Volume
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.max_history)
        
        self.price_history[symbol].append({
            'price': price,
            'volume': volume,
            'timestamp': datetime.now(timezone.utc).timestamp()
        })
        
        # Verifica flash crash
        self._check_flash_crash(symbol)
    
    def _check_flash_crash(self, symbol: str):
        """Verifica se há flash crash"""
        history = list(self.price_history[symbol])
        
        if len(history) < 10:
            return
        
        current_price = history[-1]['price']
        
        # Verifica queda rápida nos últimos 5 minutos
        recent_history = [
            h for h in history
            if h['timestamp'] > datetime.now(timezone.utc).timestamp() - 300
        ]
        
        if len(recent_history) < 5:
            return
        
        max_recent = max(h['price'] for h in recent_history)
        drop_pct = (current_price - max_recent) / max_recent
        
        if drop_pct <= self.crash_threshold:
            # Flash crash detectado!
            self._handle_flash_crash(symbol, current_price, max_recent, drop_pct)
    
    def _handle_flash_crash(
        self,
        symbol: str,
        current_price: float,
        pre_crash_price: float,
        drop_pct: float
    ):
        """Trata flash crash detectado"""
        crash_id = f"crash_{symbol}_{int(datetime.now(timezone.utc).timestamp())}"
        
        alert = {
            'crash_id': crash_id,
            'symbol': symbol,
            'current_price': current_price,
            'pre_crash_price': pre_crash_price,
            'drop_pct': drop_pct,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.crash_alerts.append(alert)
        
        logger.warning(
            f"🚨 FLASH CRASH DETECTED: {symbol} "
            f"dropped {drop_pct:.1%} to ${current_price:.2f}"
        )
        
        # Coloca ordens de recuperação
        self._place_recovery_orders(symbol, current_price, pre_crash_price)
    
    def _place_recovery_orders(
        self,
        symbol: str,
        crash_price: float,
        target_price: float
    ):
        """Coloca ordens limite em níveis de suporte"""
        # Calcula níveis de suporte
        support_levels = [
            crash_price * 1.02,  # +2%
            crash_price * 1.05,  # +5%
            crash_price * 1.08,  # +8%
        ]
        
        for level in support_levels:
            if level < target_price:
                order = {
                    'symbol': symbol,
                    'type': 'limit',
                    'side': 'buy',
                    'price': level,
                    'amount': 100 / level,  # $100 por ordem
                    'placed_at': datetime.now(timezone.utc).isoformat()
                }
                
                self.recovery_orders.append(order)
                
                logger.info(f"Recovery order placed: {symbol} @ ${level:.2f}")
    
    def check_recovery(self, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
        """
        Verifica se houve recuperação
        
        Returns:
            Dados da recuperação se houver
        """
        # Busca ordens de recuperação para este símbolo
        symbol_orders = [o for o in self.recovery_orders if o['symbol'] == symbol]
        
        for order in symbol_orders:
            if current_price >= order['price']:
                # Ordem foi executada!
                profit_pct = (current_price - order['price']) / order['price']
                
                # Remove ordem
                self.recovery_orders.remove(order)
                
                logger.info(
                    f"✅ Recovery order filled: {symbol} @ ${order['price']:.2f} "
                    f"(profit: {profit_pct:.2%})"
                )
                
                return {
                    'symbol': symbol,
                    'entry_price': order['price'],
                    'exit_price': current_price,
                    'profit_pct': profit_pct,
                    'amount': order['amount']
                }
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas"""
        return {
            'total_crashes_detected': len(self.crash_alerts),
            'active_recovery_orders': len(self.recovery_orders),
            'symbols_monitored': len(self.price_history)
        }


# Instância global
flash_crash_detector = FlashCrashDetector()
