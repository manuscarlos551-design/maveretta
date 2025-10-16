# core/risk/drawdown_guard.py
"""
Maveretta Drawdown Guard - Adaptação do Freqtrade para Maveretta
Proteção por drawdown máximo integrada com sistema de slots
Origem: freqtrade/plugins/protections/max_drawdown_protection.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class DrawdownSnapshot:
    """Snapshot de drawdown em um momento específico"""
    timestamp: datetime
    capital: float
    peak_capital: float
    drawdown_abs: float
    drawdown_pct: float
    duration_minutes: int

class MaverettaDrawdownGuard:
    """
    Proteção por drawdown máximo
    Monitora drawdown por slot e global, ativando proteções quando necessário
    """
    
    def __init__(self, orchestrator: Optional[Any] = None):
        """
        Inicializa o guard de drawdown
        
        Args:
            orchestrator: Referência ao orquestrador Maveretta
        """
        self.orchestrator = orchestrator
        
        # Configurações padrão
        self.max_drawdown_pct = 0.20  # 20% drawdown máximo
        self.max_drawdown_abs = 2000.0  # $2000 perda máxima absoluta
        self.lookback_period_hours = 24  # Período de observação
        self.protection_duration_minutes = 240  # 4 horas de proteção
        self.min_trades_for_protection = 3  # Mínimo de trades para ativar proteção
        
        # Estado interno por slot
        self.capital_history: Dict[str, List[Tuple[datetime, float]]] = {}  # histórico de capital
        self.peak_capital: Dict[str, float] = {}  # pico de capital por slot
        self.current_drawdown: Dict[str, DrawdownSnapshot] = {}
        self.protection_status: Dict[str, Dict[str, Any]] = {}
        
        # Estado global
        self.global_capital_history: List[Tuple[datetime, float]] = []
        self.global_peak_capital = 0.0
        self.global_protection_active = False
        
        logger.info("[DRAWDOWN_GUARD] Initialized Maveretta Drawdown Guard")
    
    def update_slot_capital(
        self,
        slot_id: str,
        current_capital: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Atualiza capital atual do slot
        
        Args:
            slot_id: ID do slot
            current_capital: Capital atual
            timestamp: Timestamp da atualização
        """
        try:
            timestamp = timestamp or datetime.now()
            
            # Inicializar histórico se não existe
            if slot_id not in self.capital_history:
                self.capital_history[slot_id] = []
                self.peak_capital[slot_id] = current_capital
            
            # Adicionar ao histórico
            self.capital_history[slot_id].append((timestamp, current_capital))
            
            # Atualizar pico se necessário
            if current_capital > self.peak_capital[slot_id]:
                self.peak_capital[slot_id] = current_capital
            
            # Calcular drawdown atual
            current_dd_snapshot = self._calculate_current_drawdown(slot_id, current_capital, timestamp)
            self.current_drawdown[slot_id] = current_dd_snapshot
            
            # Verificar se deve ativar proteção
            self._check_drawdown_protection(slot_id, current_dd_snapshot)
            
            # Limpar histórico antigo
            self._cleanup_old_history(slot_id)
            
            logger.debug(f"[DRAWDOWN_GUARD] Updated capital for slot {slot_id}: {current_capital}, "
                        f"drawdown: {current_dd_snapshot.drawdown_pct:.2%}")
            
        except Exception as e:
            logger.error(f"[DRAWDOWN_GUARD] Error updating slot capital: {e}")
    
    def update_global_capital(
        self,
        total_capital: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Atualiza capital global do portfólio
        
        Args:
            total_capital: Capital total do portfólio
            timestamp: Timestamp da atualização
        """
        try:
            timestamp = timestamp or datetime.now()
            
            # Adicionar ao histórico global
            self.global_capital_history.append((timestamp, total_capital))
            
            # Atualizar pico global
            if total_capital > self.global_peak_capital:
                self.global_peak_capital = total_capital
            
            # Verificar proteção global
            global_dd_pct = self._calculate_global_drawdown_pct(total_capital)
            
            if global_dd_pct > self.max_drawdown_pct:
                self._activate_global_protection(global_dd_pct, total_capital)
            
            # Limpar histórico antigo
            self._cleanup_global_history()
            
        except Exception as e:
            logger.error(f"[DRAWDOWN_GUARD] Error updating global capital: {e}")
    
    def is_slot_protected(self, slot_id: str) -> bool:
        """
        Verifica se slot está protegido por drawdown
        
        Args:
            slot_id: ID do slot
            
        Returns:
            True se slot está protegido
        """
        try:
            if slot_id not in self.protection_status:
                return False
            
            protection = self.protection_status[slot_id]
            
            if not protection.get('is_active', False):
                return False
            
            # Verificar se proteção ainda é válida
            protection_end = protection.get('protection_end')
            if protection_end and datetime.now() > protection_end:
                protection['is_active'] = False
                logger.info(f"[DRAWDOWN_GUARD] Protection expired for slot {slot_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[DRAWDOWN_GUARD] Error checking protection status: {e}")
            return False
    
    def get_slot_drawdown_info(self, slot_id: str) -> Dict[str, Any]:
        """
        Retorna informações de drawdown do slot
        
        Args:
            slot_id: ID do slot
            
        Returns:
            Dict com informações de drawdown
        """
        try:
            if slot_id not in self.current_drawdown:
                return {
                    'current_drawdown_pct': 0.0,
                    'current_drawdown_abs': 0.0,
                    'peak_capital': 0.0,
                    'current_capital': 0.0,
                    'is_protected': False
                }
            
            snapshot = self.current_drawdown[slot_id]
            protection = self.protection_status.get(slot_id, {})
            
            # Calcular estatísticas do período
            max_dd_period = self._calculate_max_drawdown_period(slot_id)
            
            return {
                'current_drawdown_pct': snapshot.drawdown_pct,
                'current_drawdown_abs': snapshot.drawdown_abs,
                'peak_capital': snapshot.peak_capital,
                'current_capital': snapshot.capital,
                'drawdown_duration_minutes': snapshot.duration_minutes,
                'max_drawdown_period': max_dd_period,
                'is_protected': self.is_slot_protected(slot_id),
                'protection_info': {
                    'protection_start': protection.get('protection_start'),
                    'protection_end': protection.get('protection_end'),
                    'trigger_reason': protection.get('trigger_reason', ''),
                    'trigger_drawdown': protection.get('trigger_drawdown', 0.0)
                },
                'thresholds': {
                    'max_drawdown_pct': self.max_drawdown_pct,
                    'max_drawdown_abs': self.max_drawdown_abs
                }
            }
            
        except Exception as e:
            logger.error(f"[DRAWDOWN_GUARD] Error getting drawdown info: {e}")
            return {}
    
    def force_drawdown_protection(
        self,
        slot_id: str,
        duration_minutes: Optional[int] = None,
        reason: str = "Manual activation"
    ) -> bool:
        """
        Força ativação de proteção por drawdown
        
        Args:
            slot_id: ID do slot
            duration_minutes: Duração em minutos
            reason: Motivo da proteção
            
        Returns:
            True se ativou com sucesso
        """
        try:
            duration = duration_minutes or self.protection_duration_minutes
            
            protection_start = datetime.now()
            protection_end = protection_start + timedelta(minutes=duration)
            
            self.protection_status[slot_id] = {
                'is_active': True,
                'protection_start': protection_start,
                'protection_end': protection_end,
                'trigger_reason': reason,
                'trigger_drawdown': self.current_drawdown.get(slot_id, DrawdownSnapshot(
                    datetime.now(), 0, 0, 0, 0, 0)).drawdown_pct
            }
            
            logger.warning(f"[DRAWDOWN_GUARD] Force protection activated for slot {slot_id} "
                          f"until {protection_end.strftime('%H:%M:%S')}")
            
            # Notificar orquestrador
            self._notify_orchestrator(slot_id, "drawdown_protection_activated", reason)
            
            return True
            
        except Exception as e:
            logger.error(f"[DRAWDOWN_GUARD] Error forcing protection: {e}")
            return False
    
    def get_portfolio_drawdown_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo de drawdown do portfólio
        
        Returns:
            Dict com resumo do drawdown
        """
        try:
            # Calcular drawdown global atual
            current_global_capital = sum(
                self.capital_history[slot_id][-1][1] 
                for slot_id in self.capital_history.keys()
                if self.capital_history[slot_id]
            ) if self.capital_history else 0.0
            
            global_dd_pct = self._calculate_global_drawdown_pct(current_global_capital)
            
            # Slots protegidos
            protected_slots = [
                slot_id for slot_id in self.protection_status.keys()
                if self.is_slot_protected(slot_id)
            ]
            
            # Pior drawdown por slot
            worst_slots = []
            for slot_id in self.current_drawdown.keys():
                dd_info = self.get_slot_drawdown_info(slot_id)
                worst_slots.append({
                    'slot_id': slot_id,
                    'drawdown_pct': dd_info['current_drawdown_pct'],
                    'drawdown_abs': dd_info['current_drawdown_abs']
                })
            
            # Ordenar por pior drawdown
            worst_slots.sort(key=lambda x: x['drawdown_pct'], reverse=True)
            
            return {
                'global_drawdown_pct': global_dd_pct,
                'global_peak_capital': self.global_peak_capital,
                'current_global_capital': current_global_capital,
                'global_protection_active': self.global_protection_active,
                'protected_slots_count': len(protected_slots),
                'protected_slots': protected_slots,
                'worst_performing_slots': worst_slots[:5],  # Top 5 piores
                'total_slots_monitored': len(self.capital_history),
                'thresholds': {
                    'max_drawdown_pct': self.max_drawdown_pct,
                    'max_drawdown_abs': self.max_drawdown_abs,
                    'protection_duration_minutes': self.protection_duration_minutes
                }
            }
            
        except Exception as e:
            logger.error(f"[DRAWDOWN_GUARD] Error getting portfolio summary: {e}")
            return {}
    
    def _calculate_current_drawdown(
        self,
        slot_id: str,
        current_capital: float,
        timestamp: datetime
    ) -> DrawdownSnapshot:
        """Calcula drawdown atual do slot"""
        
        peak_capital = self.peak_capital.get(slot_id, current_capital)
        
        drawdown_abs = peak_capital - current_capital
        drawdown_pct = drawdown_abs / peak_capital if peak_capital > 0 else 0.0
        
        # Calcular duração do drawdown (tempo desde último pico)
        duration_minutes = 0
        if slot_id in self.capital_history:
            # Encontrar último pico
            for i in reversed(range(len(self.capital_history[slot_id]))):
                hist_time, hist_capital = self.capital_history[slot_id][i]
                if hist_capital >= peak_capital * 0.99:  # Próximo do pico (99%)
                    duration_minutes = int((timestamp - hist_time).total_seconds() / 60)
                    break
        
        return DrawdownSnapshot(
            timestamp=timestamp,
            capital=current_capital,
            peak_capital=peak_capital,
            drawdown_abs=drawdown_abs,
            drawdown_pct=drawdown_pct,
            duration_minutes=duration_minutes
        )
    
    def _calculate_max_drawdown_period(self, slot_id: str) -> Dict[str, Any]:
        """Calcula maior drawdown do período de observação"""
        
        if slot_id not in self.capital_history:
            return {'max_drawdown_pct': 0.0, 'max_drawdown_abs': 0.0}
        
        history = self.capital_history[slot_id]
        if len(history) < 2:
            return {'max_drawdown_pct': 0.0, 'max_drawdown_abs': 0.0}
        
        max_dd_pct = 0.0
        max_dd_abs = 0.0
        peak = history[0][1]
        
        for timestamp, capital in history:
            if capital > peak:
                peak = capital
            
            dd_abs = peak - capital
            dd_pct = dd_abs / peak if peak > 0 else 0.0
            
            max_dd_pct = max(max_dd_pct, dd_pct)
            max_dd_abs = max(max_dd_abs, dd_abs)
        
        return {
            'max_drawdown_pct': max_dd_pct,
            'max_drawdown_abs': max_dd_abs
        }
    
    def _calculate_global_drawdown_pct(self, current_global_capital: float) -> float:
        """Calcula drawdown percentual global"""
        if self.global_peak_capital == 0:
            return 0.0
        
        drawdown_abs = self.global_peak_capital - current_global_capital
        return drawdown_abs / self.global_peak_capital
    
    def _check_drawdown_protection(self, slot_id: str, snapshot: DrawdownSnapshot) -> None:
        """Verifica se deve ativar proteção por drawdown"""
        
        # Verificar se já está protegido
        if self.is_slot_protected(slot_id):
            return
        
        # Verificar limites
        trigger_pct = snapshot.drawdown_pct > self.max_drawdown_pct
        trigger_abs = snapshot.drawdown_abs > self.max_drawdown_abs
        
        if trigger_pct or trigger_abs:
            # Verificar mínimo de trades (via histórico de capital)
            if len(self.capital_history.get(slot_id, [])) >= self.min_trades_for_protection:
                
                protection_start = datetime.now()
                protection_end = protection_start + timedelta(minutes=self.protection_duration_minutes)
                
                trigger_reason = []
                if trigger_pct:
                    trigger_reason.append(f"Drawdown {snapshot.drawdown_pct:.1%} > {self.max_drawdown_pct:.1%}")
                if trigger_abs:
                    trigger_reason.append(f"Loss ${snapshot.drawdown_abs:.0f} > ${self.max_drawdown_abs:.0f}")
                
                reason = " | ".join(trigger_reason)
                
                self.protection_status[slot_id] = {
                    'is_active': True,
                    'protection_start': protection_start,
                    'protection_end': protection_end,
                    'trigger_reason': reason,
                    'trigger_drawdown': snapshot.drawdown_pct
                }
                
                logger.warning(f"[DRAWDOWN_GUARD] Protection ACTIVATED for slot {slot_id}: {reason}")
                
                # Notificar orquestrador
                self._notify_orchestrator(slot_id, "drawdown_protection_triggered", reason)
    
    def _activate_global_protection(self, drawdown_pct: float, current_capital: float) -> None:
        """Ativa proteção global"""
        if not self.global_protection_active:
            self.global_protection_active = True
            
            logger.critical(f"[DRAWDOWN_GUARD] GLOBAL PROTECTION ACTIVATED: "
                           f"Portfolio drawdown {drawdown_pct:.1%}")
            
            # Notificar orquestrador sobre proteção global
            self._notify_orchestrator("GLOBAL", "global_drawdown_protection", 
                                    f"Portfolio drawdown: {drawdown_pct:.1%}")
    
    def _cleanup_old_history(self, slot_id: str) -> None:
        """Remove histórico antigo do slot"""
        if slot_id not in self.capital_history:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=self.lookback_period_hours)
        
        self.capital_history[slot_id] = [
            (timestamp, capital) for timestamp, capital in self.capital_history[slot_id]
            if timestamp > cutoff_time
        ]
    
    def _cleanup_global_history(self) -> None:
        """Remove histórico global antigo"""
        cutoff_time = datetime.now() - timedelta(hours=self.lookback_period_hours)
        
        self.global_capital_history = [
            (timestamp, capital) for timestamp, capital in self.global_capital_history
            if timestamp > cutoff_time
        ]
    
    def _notify_orchestrator(self, slot_id: str, event_type: str, details: str) -> None:
        """Notifica orquestrador sobre eventos de drawdown"""
        try:
            if self.orchestrator and hasattr(self.orchestrator, 'handle_protection_event'):
                self.orchestrator.handle_protection_event(
                    slot_id=slot_id,
                    protection_type='drawdown_guard',
                    event_type=event_type,
                    details=details,
                    timestamp=datetime.now()
                )
        except Exception as e:
            logger.warning(f"[DRAWDOWN_GUARD] Error notifying orchestrator: {e}")

# Função de conveniência
def create_drawdown_guard(orchestrator=None, **config) -> MaverettaDrawdownGuard:
    """Função de conveniência para criar guard de drawdown"""
    guard = MaverettaDrawdownGuard(orchestrator)
    
    # Aplicar configurações personalizadas
    if 'max_drawdown_pct' in config:
        guard.max_drawdown_pct = config['max_drawdown_pct']
    if 'max_drawdown_abs' in config:
        guard.max_drawdown_abs = config['max_drawdown_abs']
    if 'protection_duration_minutes' in config:
        guard.protection_duration_minutes = config['protection_duration_minutes']
    
    return guard