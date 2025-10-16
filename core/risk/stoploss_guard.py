# core/risk/stoploss_guard.py
"""
Maveretta Stoploss Guard - Adaptação do Freqtrade para Maveretta
Proteção contra múltiplos stoplosses sequenciais integrada com sistema de slots
Origem: freqtrade/plugins/protections/stoploss_guard.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class StoplossEvent:
    """Evento de stoploss registrado"""
    slot_id: str
    pair: str
    timestamp: datetime
    loss_amount: float
    loss_percentage: float
    trade_id: str
    reason: str = "stoploss"

@dataclass
class ProtectionStatus:
    """Status de proteção para um slot"""
    is_protected: bool
    protection_start: Optional[datetime] = None
    protection_end: Optional[datetime] = None
    reason: str = ""
    events_count: int = 0
    total_loss: float = 0.0

class MaverettaStoplossGuard:
    """
    Proteção contra múltiplos stoplosses sequenciais
    Adaptado do StoplossGuard do Freqtrade para sistema de slots
    """
    
    def __init__(self, orchestrator: Optional[Any] = None):
        """
        Inicializa o guard de stoploss
        
        Args:
            orchestrator: Referência ao orquestrador Maveretta
        """
        self.orchestrator = orchestrator
        
        # Configurações padrão
        self.trade_limit = 4  # Máximo de stoplosses
        self.lookback_period_minutes = 60  # Período de observação
        self.protection_duration_minutes = 60  # Duração da proteção
        self.min_loss_threshold = 0.01  # 1% perda mínima para contar
        self.profit_limit = -0.005  # Só conta se perda > 0.5%
        
        # Estado interno
        self.stoploss_events: Dict[str, List[StoplossEvent]] = {}  # Por slot
        self.protection_status: Dict[str, ProtectionStatus] = {}
        
        logger.info("[STOPLOSS_GUARD] Initialized Maveretta Stoploss Guard")
    
    def register_stoploss_event(
        self,
        slot_id: str,
        pair: str,
        loss_amount: float,
        loss_percentage: float,
        trade_id: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Registra evento de stoploss
        
        Args:
            slot_id: ID do slot
            pair: Par de trading
            loss_amount: Valor absoluto da perda
            loss_percentage: Percentual da perda
            trade_id: ID do trade
            timestamp: Timestamp do evento (atual se None)
        """
        try:
            timestamp = timestamp or datetime.now()
            
            # Verificar se perda é significativa
            if abs(loss_percentage) < self.min_loss_threshold:
                return
            
            # Só contar perdas (não lucros acidentais)
            if loss_percentage > self.profit_limit:
                return
            
            event = StoplossEvent(
                slot_id=slot_id,
                pair=pair,
                timestamp=timestamp,
                loss_amount=abs(loss_amount),
                loss_percentage=abs(loss_percentage),
                trade_id=trade_id,
                reason="stoploss"
            )
            
            # Adicionar ao histórico do slot
            if slot_id not in self.stoploss_events:
                self.stoploss_events[slot_id] = []
            
            self.stoploss_events[slot_id].append(event)
            
            logger.warning(f"[STOPLOSS_GUARD] Stoploss registered for slot {slot_id}: "
                          f"{loss_percentage:.2%} loss on {pair}")
            
            # Verificar se deve ativar proteção
            self._check_protection_trigger(slot_id)
            
        except Exception as e:
            logger.error(f"[STOPLOSS_GUARD] Error registering stoploss event: {e}")
    
    def is_slot_protected(self, slot_id: str) -> bool:
        """
        Verifica se slot está protegido
        
        Args:
            slot_id: ID do slot
            
        Returns:
            True se slot está protegido
        """
        try:
            if slot_id not in self.protection_status:
                return False
            
            status = self.protection_status[slot_id]
            
            if not status.is_protected:
                return False
            
            # Verificar se proteção ainda é válida
            if status.protection_end and datetime.now() > status.protection_end:
                # Proteção expirou
                status.is_protected = False
                logger.info(f"[STOPLOSS_GUARD] Protection expired for slot {slot_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[STOPLOSS_GUARD] Error checking protection status: {e}")
            return False
    
    def get_slot_protection_info(self, slot_id: str) -> Dict[str, Any]:
        """
        Retorna informações de proteção do slot
        
        Args:
            slot_id: ID do slot
            
        Returns:
            Dict com informações de proteção
        """
        try:
            if slot_id not in self.protection_status:
                return {
                    'is_protected': False,
                    'reason': 'No protection active',
                    'events_count': 0,
                    'recent_events': []
                }
            
            status = self.protection_status[slot_id]
            recent_events = self._get_recent_events(slot_id)
            
            return {
                'is_protected': self.is_slot_protected(slot_id),
                'protection_start': status.protection_start.isoformat() if status.protection_start else None,
                'protection_end': status.protection_end.isoformat() if status.protection_end else None,
                'reason': status.reason,
                'events_count': len(recent_events),
                'total_recent_loss': sum(event.loss_amount for event in recent_events),
                'total_recent_loss_pct': sum(event.loss_percentage for event in recent_events),
                'recent_events': [
                    {
                        'pair': event.pair,
                        'timestamp': event.timestamp.isoformat(),
                        'loss_amount': event.loss_amount,
                        'loss_percentage': event.loss_percentage,
                        'trade_id': event.trade_id
                    }
                    for event in recent_events[-5:]  # Últimos 5 eventos
                ]
            }
            
        except Exception as e:
            logger.error(f"[STOPLOSS_GUARD] Error getting protection info: {e}")
            return {'is_protected': False, 'reason': 'Error getting info'}
    
    def force_protection(
        self,
        slot_id: str,
        duration_minutes: Optional[int] = None,
        reason: str = "Manual activation"
    ) -> bool:
        """
        Força ativação de proteção para um slot
        
        Args:
            slot_id: ID do slot
            duration_minutes: Duração em minutos (padrão se None)
            reason: Motivo da proteção
            
        Returns:
            True se ativou com sucesso
        """
        try:
            duration = duration_minutes or self.protection_duration_minutes
            
            protection_start = datetime.now()
            protection_end = protection_start + timedelta(minutes=duration)
            
            self.protection_status[slot_id] = ProtectionStatus(
                is_protected=True,
                protection_start=protection_start,
                protection_end=protection_end,
                reason=reason,
                events_count=len(self._get_recent_events(slot_id)),
                total_loss=sum(event.loss_amount for event in self._get_recent_events(slot_id))
            )
            
            logger.warning(f"[STOPLOSS_GUARD] Force protection activated for slot {slot_id} "
                          f"until {protection_end.strftime('%H:%M:%S')}")
            
            # Notificar orquestrador se disponível
            self._notify_orchestrator(slot_id, "protection_activated", reason)
            
            return True
            
        except Exception as e:
            logger.error(f"[STOPLOSS_GUARD] Error forcing protection: {e}")
            return False
    
    def remove_protection(self, slot_id: str) -> bool:
        """
        Remove proteção de um slot
        
        Args:
            slot_id: ID do slot
            
        Returns:
            True se removeu com sucesso
        """
        try:
            if slot_id in self.protection_status:
                self.protection_status[slot_id].is_protected = False
                self.protection_status[slot_id].protection_end = datetime.now()
                
                logger.info(f"[STOPLOSS_GUARD] Protection manually removed for slot {slot_id}")
                
                # Notificar orquestrador
                self._notify_orchestrator(slot_id, "protection_removed", "Manual removal")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[STOPLOSS_GUARD] Error removing protection: {e}")
            return False
    
    def get_global_protection_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo global das proteções
        
        Returns:
            Dict com resumo das proteções
        """
        try:
            protected_slots = [
                slot_id for slot_id in self.protection_status.keys()
                if self.is_slot_protected(slot_id)
            ]
            
            total_events_24h = 0
            total_loss_24h = 0.0
            
            # Contar eventos das últimas 24 horas
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for slot_events in self.stoploss_events.values():
                recent = [e for e in slot_events if e.timestamp > cutoff_time]
                total_events_24h += len(recent)
                total_loss_24h += sum(e.loss_amount for e in recent)
            
            return {
                'protected_slots_count': len(protected_slots),
                'protected_slots': protected_slots,
                'total_slots_monitored': len(self.stoploss_events),
                'total_stoploss_events_24h': total_events_24h,
                'total_loss_24h': total_loss_24h,
                'active_protections': {
                    slot_id: self.get_slot_protection_info(slot_id)
                    for slot_id in protected_slots
                },
                'configuration': {
                    'trade_limit': self.trade_limit,
                    'lookback_period_minutes': self.lookback_period_minutes,
                    'protection_duration_minutes': self.protection_duration_minutes,
                    'min_loss_threshold': self.min_loss_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"[STOPLOSS_GUARD] Error getting global summary: {e}")
            return {}
    
    def _check_protection_trigger(self, slot_id: str) -> None:
        """Verifica se deve ativar proteção baseado nos eventos recentes"""
        try:
            recent_events = self._get_recent_events(slot_id)
            
            if len(recent_events) >= self.trade_limit:
                # Ativar proteção
                protection_start = datetime.now()
                protection_end = protection_start + timedelta(minutes=self.protection_duration_minutes)
                
                total_loss = sum(event.loss_amount for event in recent_events)
                
                self.protection_status[slot_id] = ProtectionStatus(
                    is_protected=True,
                    protection_start=protection_start,
                    protection_end=protection_end,
                    reason=f"{len(recent_events)} stoplosses in {self.lookback_period_minutes} minutes",
                    events_count=len(recent_events),
                    total_loss=total_loss
                )
                
                logger.warning(f"[STOPLOSS_GUARD] Protection ACTIVATED for slot {slot_id}: "
                              f"{len(recent_events)} stoplosses, total loss: {total_loss:.2f}")
                
                # Notificar orquestrador
                self._notify_orchestrator(slot_id, "protection_triggered", 
                                        f"Too many stoplosses: {len(recent_events)}")
        
        except Exception as e:
            logger.error(f"[STOPLOSS_GUARD] Error checking protection trigger: {e}")
    
    def _get_recent_events(self, slot_id: str) -> List[StoplossEvent]:
        """Retorna eventos recentes para um slot"""
        if slot_id not in self.stoploss_events:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=self.lookback_period_minutes)
        
        return [
            event for event in self.stoploss_events[slot_id]
            if event.timestamp > cutoff_time
        ]
    
    def _notify_orchestrator(self, slot_id: str, event_type: str, details: str) -> None:
        """Notifica o orquestrador sobre eventos de proteção"""
        try:
            if self.orchestrator and hasattr(self.orchestrator, 'handle_protection_event'):
                self.orchestrator.handle_protection_event(
                    slot_id=slot_id,
                    protection_type='stoploss_guard',
                    event_type=event_type,
                    details=details,
                    timestamp=datetime.now()
                )
        except Exception as e:
            logger.warning(f"[STOPLOSS_GUARD] Error notifying orchestrator: {e}")
    
    def cleanup_old_events(self, older_than_hours: int = 24) -> int:
        """
        Remove eventos antigos para controlar memória
        
        Args:
            older_than_hours: Remove eventos mais antigos que X horas
            
        Returns:
            Número de eventos removidos
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            removed_count = 0
            
            for slot_id in list(self.stoploss_events.keys()):
                original_count = len(self.stoploss_events[slot_id])
                
                self.stoploss_events[slot_id] = [
                    event for event in self.stoploss_events[slot_id]
                    if event.timestamp > cutoff_time
                ]
                
                removed = original_count - len(self.stoploss_events[slot_id])
                removed_count += removed
                
                # Remove slot se não há mais eventos
                if not self.stoploss_events[slot_id]:
                    del self.stoploss_events[slot_id]
            
            if removed_count > 0:
                logger.info(f"[STOPLOSS_GUARD] Cleaned up {removed_count} old stoploss events")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"[STOPLOSS_GUARD] Error cleaning up events: {e}")
            return 0

# Função de conveniência
def create_stoploss_guard(orchestrator=None, **config) -> MaverettaStoplossGuard:
    """Função de conveniência para criar guard de stoploss"""
    guard = MaverettaStoplossGuard(orchestrator)
    
    # Aplicar configurações personalizadas
    if 'trade_limit' in config:
        guard.trade_limit = config['trade_limit']
    if 'lookback_period_minutes' in config:
        guard.lookback_period_minutes = config['lookback_period_minutes']
    if 'protection_duration_minutes' in config:
        guard.protection_duration_minutes = config['protection_duration_minutes']
    
    return guard