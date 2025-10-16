# core/risk/cooldown_manager.py
"""
Maveretta Cooldown Manager - Adaptação do Freqtrade para Maveretta
Gestão de períodos de cooldown integrada com sistema de slots
Origem: freqtrade/plugins/protections/cooldown_period.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CooldownReason(Enum):
    """Motivos de cooldown"""
    MANUAL = "manual"
    STOPLOSS = "stoploss"
    DRAWDOWN = "drawdown"
    PERFORMANCE = "performance"
    MARKET_CONDITIONS = "market_conditions"
    ERROR_RECOVERY = "error_recovery"

@dataclass
class CooldownStatus:
    """Status de cooldown para um slot"""
    slot_id: str
    is_active: bool
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    reason: CooldownReason
    description: str = ""
    auto_created: bool = True
    priority: int = 1  # 1=baixa, 2=média, 3=alta

class MaverettaCooldownManager:
    """
    Gerenciador de períodos de cooldown para slots
    Controla quando slots devem pausar operações temporariamente
    """
    
    def __init__(self, orchestrator: Optional[Any] = None):
        """
        Inicializa o manager de cooldown
        
        Args:
            orchestrator: Referência ao orquestrador Maveretta
        """
        self.orchestrator = orchestrator
        
        # Configurações padrão por tipo de cooldown
        self.default_durations = {
            CooldownReason.MANUAL: 30,  # 30 minutos
            CooldownReason.STOPLOSS: 60,  # 1 hora
            CooldownReason.DRAWDOWN: 240,  # 4 horas
            CooldownReason.PERFORMANCE: 120,  # 2 horas
            CooldownReason.MARKET_CONDITIONS: 180,  # 3 horas
            CooldownReason.ERROR_RECOVERY: 15  # 15 minutos
        }
        
        # Estado interno
        self.active_cooldowns: Dict[str, CooldownStatus] = {}  # Por slot_id
        self.cooldown_history: List[CooldownStatus] = []
        self.global_cooldown_active = False
        self.global_cooldown_end = None
        
        # Configurações
        self.max_cooldown_duration_hours = 24  # Máximo 24 horas
        self.auto_extend_on_repeated_issues = True
        self.max_concurrent_cooldowns = 10  # Máximo de slots em cooldown simultâneo
        
        logger.info("[COOLDOWN_MANAGER] Initialized Maveretta Cooldown Manager")
    
    def apply_cooldown(
        self,
        slot_id: str,
        reason: CooldownReason,
        duration_minutes: Optional[int] = None,
        description: str = "",
        priority: int = 1
    ) -> bool:
        """
        Aplica cooldown a um slot
        
        Args:
            slot_id: ID do slot
            reason: Motivo do cooldown
            duration_minutes: Duração em minutos (usa padrão se None)
            description: Descrição adicional
            priority: Prioridade (1=baixa, 2=média, 3=alta)
            
        Returns:
            True se aplicou cooldown com sucesso
        """
        try:
            # Verificar se já está em cooldown
            if self.is_slot_in_cooldown(slot_id):
                existing = self.active_cooldowns[slot_id]
                
                # Se nova prioridade é maior, substitui
                if priority > existing.priority:
                    logger.info(f"[COOLDOWN_MANAGER] Replacing cooldown for slot {slot_id} "
                              f"(priority {existing.priority} -> {priority})")
                    self.remove_cooldown(slot_id)
                else:
                    logger.warning(f"[COOLDOWN_MANAGER] Slot {slot_id} already in cooldown "
                                  f"with higher/equal priority")
                    return False
            
            # Verificar limite de cooldowns simultâneos
            if len(self.active_cooldowns) >= self.max_concurrent_cooldowns:
                logger.warning(f"[COOLDOWN_MANAGER] Max concurrent cooldowns reached "
                              f"({self.max_concurrent_cooldowns})")
                # Remover cooldown de menor prioridade se possível
                self._cleanup_lowest_priority_cooldown()
            
            # Determinar duração
            duration = duration_minutes or self.default_durations.get(reason, 30)
            
            # Verificar duração máxima
            max_duration = self.max_cooldown_duration_hours * 60
            duration = min(duration, max_duration)
            
            # Verificar extensão automática por problemas repetidos
            if self.auto_extend_on_repeated_issues:
                duration = self._calculate_extended_duration(slot_id, reason, duration)
            
            # Criar cooldown
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration)
            
            cooldown_status = CooldownStatus(
                slot_id=slot_id,
                is_active=True,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                reason=reason,
                description=description,
                auto_created=True,
                priority=priority
            )
            
            # Aplicar cooldown
            self.active_cooldowns[slot_id] = cooldown_status
            self.cooldown_history.append(cooldown_status)
            
            logger.warning(f"[COOLDOWN_MANAGER] Cooldown applied to slot {slot_id}: "
                          f"{reason.value} for {duration} minutes until {end_time.strftime('%H:%M:%S')}")
            
            # Notificar orquestrador
            self._notify_orchestrator(slot_id, "cooldown_applied", 
                                    f"{reason.value}: {description}")
            
            return True
            
        except Exception as e:
            logger.error(f"[COOLDOWN_MANAGER] Error applying cooldown: {e}")
            return False
    
    def remove_cooldown(self, slot_id: str, reason: str = "Manual removal") -> bool:
        """
        Remove cooldown de um slot
        
        Args:
            slot_id: ID do slot
            reason: Motivo da remoção
            
        Returns:
            True se removeu com sucesso
        """
        try:
            if slot_id not in self.active_cooldowns:
                logger.warning(f"[COOLDOWN_MANAGER] No active cooldown for slot {slot_id}")
                return False
            
            cooldown = self.active_cooldowns[slot_id]
            cooldown.is_active = False
            
            # Remover da lista ativa
            del self.active_cooldowns[slot_id]
            
            logger.info(f"[COOLDOWN_MANAGER] Cooldown removed for slot {slot_id}: {reason}")
            
            # Notificar orquestrador
            self._notify_orchestrator(slot_id, "cooldown_removed", reason)
            
            return True
            
        except Exception as e:
            logger.error(f"[COOLDOWN_MANAGER] Error removing cooldown: {e}")
            return False
    
    def is_slot_in_cooldown(self, slot_id: str) -> bool:
        """
        Verifica se slot está em cooldown
        
        Args:
            slot_id: ID do slot
            
        Returns:
            True se slot está em cooldown
        """
        try:
            if slot_id not in self.active_cooldowns:
                return False
            
            cooldown = self.active_cooldowns[slot_id]
            
            # Verificar se cooldown expirou
            if datetime.now() > cooldown.end_time:
                cooldown.is_active = False
                del self.active_cooldowns[slot_id]
                
                logger.info(f"[COOLDOWN_MANAGER] Cooldown expired for slot {slot_id}")
                
                # Notificar orquestrador
                self._notify_orchestrator(slot_id, "cooldown_expired", "Natural expiration")
                
                return False
            
            return cooldown.is_active
            
        except Exception as e:
            logger.error(f"[COOLDOWN_MANAGER] Error checking cooldown status: {e}")
            return False
    
    def get_slot_cooldown_info(self, slot_id: str) -> Dict[str, Any]:
        """
        Retorna informações de cooldown do slot
        
        Args:
            slot_id: ID do slot
            
        Returns:
            Dict com informações de cooldown
        """
        try:
            if not self.is_slot_in_cooldown(slot_id):
                return {
                    'active': False,
                    'reason': None,
                    'remaining_minutes': 0,
                    'unlock_time': None
                }
            
            cooldown = self.active_cooldowns[slot_id]
            remaining = cooldown.end_time - datetime.now()
            remaining_minutes = max(0, int(remaining.total_seconds() / 60))
            
            # Histórico recente do slot
            recent_cooldowns = [
                cd for cd in self.cooldown_history[-20:]  # Últimos 20
                if cd.slot_id == slot_id and cd.start_time > datetime.now() - timedelta(hours=24)
            ]
            
            return {
                'active': True,
                'reason': cooldown.reason.value,
                'description': cooldown.description,
                'priority': cooldown.priority,
                'start_time': cooldown.start_time.isoformat(),
                'end_time': cooldown.end_time.isoformat(),
                'unlock_time': cooldown.end_time.isoformat(),
                'duration_minutes': cooldown.duration_minutes,
                'remaining_minutes': remaining_minutes,
                'progress_pct': ((cooldown.duration_minutes - remaining_minutes) / cooldown.duration_minutes) * 100,
                'recent_cooldowns_24h': len(recent_cooldowns),
                'auto_created': cooldown.auto_created
            }
            
        except Exception as e:
            logger.error(f"[COOLDOWN_MANAGER] Error getting cooldown info: {e}")
            return {'active': False, 'reason': 'Error getting info'}
    
    def extend_cooldown(
        self,
        slot_id: str,
        additional_minutes: int,
        reason: str = "Extended due to conditions"
    ) -> bool:
        """
        Estende cooldown existente
        
        Args:
            slot_id: ID do slot
            additional_minutes: Minutos adicionais
            reason: Motivo da extensão
            
        Returns:
            True se estendeu com sucesso
        """
        try:
            if not self.is_slot_in_cooldown(slot_id):
                logger.warning(f"[COOLDOWN_MANAGER] Cannot extend: no active cooldown for slot {slot_id}")
                return False
            
            cooldown = self.active_cooldowns[slot_id]
            
            # Calcular nova duração
            new_end_time = cooldown.end_time + timedelta(minutes=additional_minutes)
            max_end_time = cooldown.start_time + timedelta(hours=self.max_cooldown_duration_hours)
            
            # Limitar duração máxima
            new_end_time = min(new_end_time, max_end_time)
            
            # Atualizar cooldown
            cooldown.end_time = new_end_time
            cooldown.duration_minutes += additional_minutes
            cooldown.description += f" | Extended: {reason}"
            
            logger.warning(f"[COOLDOWN_MANAGER] Extended cooldown for slot {slot_id} "
                          f"by {additional_minutes} min until {new_end_time.strftime('%H:%M:%S')}")
            
            # Notificar orquestrador
            self._notify_orchestrator(slot_id, "cooldown_extended", 
                                    f"+{additional_minutes}min: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"[COOLDOWN_MANAGER] Error extending cooldown: {e}")
            return False
    
    def apply_global_cooldown(
        self,
        duration_minutes: int,
        reason: str = "Global market conditions"
    ) -> bool:
        """
        Aplica cooldown global a todos os slots
        
        Args:
            duration_minutes: Duração em minutos
            reason: Motivo do cooldown global
            
        Returns:
            True se aplicou com sucesso
        """
        try:
            end_time = datetime.now() + timedelta(minutes=duration_minutes)
            
            self.global_cooldown_active = True
            self.global_cooldown_end = end_time
            
            logger.critical(f"[COOLDOWN_MANAGER] GLOBAL COOLDOWN activated for {duration_minutes} "
                           f"minutes until {end_time.strftime('%H:%M:%S')}: {reason}")
            
            # Notificar orquestrador
            self._notify_orchestrator("GLOBAL", "global_cooldown_applied", reason)
            
            return True
            
        except Exception as e:
            logger.error(f"[COOLDOWN_MANAGER] Error applying global cooldown: {e}")
            return False
    
    def is_global_cooldown_active(self) -> bool:
        """Verifica se cooldown global está ativo"""
        if not self.global_cooldown_active or not self.global_cooldown_end:
            return False
        
        if datetime.now() > self.global_cooldown_end:
            self.global_cooldown_active = False
            self.global_cooldown_end = None
            
            logger.info("[COOLDOWN_MANAGER] Global cooldown expired")
            self._notify_orchestrator("GLOBAL", "global_cooldown_expired", "Natural expiration")
            
            return False
        
        return True
    
    def get_cooldown_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo geral dos cooldowns
        
        Returns:
            Dict com resumo dos cooldowns
        """
        try:
            # Limpar cooldowns expirados primeiro
            self._cleanup_expired_cooldowns()
            
            # Estatísticas por motivo
            reason_stats = {}
            for reason in CooldownReason:
                recent_count = len([
                    cd for cd in self.cooldown_history[-50:]  # Últimos 50
                    if cd.reason == reason and cd.start_time > datetime.now() - timedelta(hours=24)
                ])
                reason_stats[reason.value] = recent_count
            
            # Cooldowns ativos ordenados por prioridade
            active_by_priority = sorted(
                self.active_cooldowns.values(),
                key=lambda cd: (-cd.priority, cd.end_time)
            )
            
            return {
                'active_cooldowns': len(self.active_cooldowns),
                'global_cooldown_active': self.is_global_cooldown_active(),
                'global_cooldown_end': self.global_cooldown_end.isoformat() if self.global_cooldown_end else None,
                'max_concurrent': self.max_concurrent_cooldowns,
                'cooldowns_24h_by_reason': reason_stats,
                'active_slots': [
                    {
                        'slot_id': cd.slot_id,
                        'reason': cd.reason.value,
                        'priority': cd.priority,
                        'remaining_minutes': max(0, int((cd.end_time - datetime.now()).total_seconds() / 60)),
                        'description': cd.description[:50] + '...' if len(cd.description) > 50 else cd.description
                    }
                    for cd in active_by_priority
                ],
                'configuration': {
                    'default_durations': {k.value: v for k, v in self.default_durations.items()},
                    'max_duration_hours': self.max_cooldown_duration_hours,
                    'auto_extend_enabled': self.auto_extend_on_repeated_issues
                }
            }
            
        except Exception as e:
            logger.error(f"[COOLDOWN_MANAGER] Error getting summary: {e}")
            return {}
    
    def _calculate_extended_duration(
        self,
        slot_id: str,
        reason: CooldownReason,
        base_duration: int
    ) -> int:
        """Calcula duração estendida baseada no histórico de problemas"""
        
        # Contar cooldowns recentes pelo mesmo motivo
        recent_same_reason = len([
            cd for cd in self.cooldown_history[-10:]  # Últimos 10
            if (cd.slot_id == slot_id and 
                cd.reason == reason and 
                cd.start_time > datetime.now() - timedelta(hours=6))
        ])
        
        # Aumentar duração progressivamente
        if recent_same_reason >= 3:
            multiplier = min(3.0, 1.0 + (recent_same_reason - 1) * 0.5)
            extended_duration = int(base_duration * multiplier)
            
            logger.info(f"[COOLDOWN_MANAGER] Extended duration for slot {slot_id} "
                       f"due to {recent_same_reason} recent issues: {base_duration} -> {extended_duration} min")
            
            return extended_duration
        
        return base_duration
    
    def _cleanup_expired_cooldowns(self) -> None:
        """Remove cooldowns expirados"""
        expired_slots = []
        
        for slot_id, cooldown in list(self.active_cooldowns.items()):
            if datetime.now() > cooldown.end_time:
                expired_slots.append(slot_id)
        
        for slot_id in expired_slots:
            self.remove_cooldown(slot_id, "Natural expiration")
    
    def _cleanup_lowest_priority_cooldown(self) -> bool:
        """Remove cooldown de menor prioridade para liberar espaço"""
        if not self.active_cooldowns:
            return False
        
        # Encontrar cooldown de menor prioridade
        lowest_priority_slot = min(
            self.active_cooldowns.keys(),
            key=lambda slot: self.active_cooldowns[slot].priority
        )
        
        lowest_priority = self.active_cooldowns[lowest_priority_slot].priority
        
        # Só remover se prioridade é baixa (1)
        if lowest_priority == 1:
            self.remove_cooldown(lowest_priority_slot, "Removed to make space for higher priority cooldown")
            return True
        
        return False
    
    def _notify_orchestrator(self, slot_id: str, event_type: str, details: str) -> None:
        """Notifica orquestrador sobre eventos de cooldown"""
        try:
            if self.orchestrator and hasattr(self.orchestrator, 'handle_protection_event'):
                self.orchestrator.handle_protection_event(
                    slot_id=slot_id,
                    protection_type='cooldown_manager',
                    event_type=event_type,
                    details=details,
                    timestamp=datetime.now()
                )
        except Exception as e:
            logger.warning(f"[COOLDOWN_MANAGER] Error notifying orchestrator: {e}")

# Funções de conveniência
def apply_slot_cooldown(slot_id: str, reason: CooldownReason, duration_minutes: int = None, **kwargs) -> bool:
    """Função de conveniência para aplicar cooldown"""
    manager = MaverettaCooldownManager()
    return manager.apply_cooldown(slot_id, reason, duration_minutes, **kwargs)

def check_slot_cooldown(slot_id: str) -> Dict[str, Any]:
    """Função de conveniência para verificar cooldown"""
    manager = MaverettaCooldownManager()
    return manager.get_slot_cooldown_info(slot_id)