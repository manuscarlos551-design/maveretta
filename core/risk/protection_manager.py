# core/risk/protection_manager.py
"""
Maveretta Protection Manager - Adaptação do Freqtrade para Maveretta
Gerenciador centralizado de proteções integrado com sistema de slots
Origem: freqtrade/plugins/protectionmanager.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from .stoploss_guard import MaverettaStoplossGuard
from .drawdown_guard import MaverettaDrawdownGuard
from .cooldown_manager import MaverettaCooldownManager, CooldownReason

logger = logging.getLogger(__name__)

class ProtectionType(Enum):
    """Tipos de proteção disponíveis"""
    STOPLOSS_GUARD = "stoploss_guard"
    DRAWDOWN_GUARD = "drawdown_guard"
    COOLDOWN_MANAGER = "cooldown_manager"

class ProtectionLevel(Enum):
    """Níveis de proteção"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ProtectionEvent:
    """Evento de proteção registrado"""
    timestamp: datetime
    slot_id: str
    protection_type: ProtectionType
    event_type: str
    level: ProtectionLevel
    details: str
    auto_generated: bool = True

@dataclass
class ProtectionConfig:
    """Configuração de proteção"""
    stoploss_guard_enabled: bool = True
    drawdown_guard_enabled: bool = True
    cooldown_manager_enabled: bool = True
    
    # Configurações específicas
    stoploss_config: Dict[str, Any] = field(default_factory=dict)
    drawdown_config: Dict[str, Any] = field(default_factory=dict)
    cooldown_config: Dict[str, Any] = field(default_factory=dict)
    
    # Configurações globais
    max_concurrent_protections: int = 5
    global_protection_threshold: float = 0.3  # 30% dos slots protegidos
    emergency_stop_enabled: bool = True

class MaverettaProtectionManager:
    """
    Gerenciador centralizado de todas as proteções do sistema Maveretta
    Coordena stoploss guard, drawdown guard e cooldown manager
    """
    
    def __init__(self, orchestrator: Optional[Any] = None, config: Optional[ProtectionConfig] = None):
        """
        Inicializa o manager de proteções
        
        Args:
            orchestrator: Referência ao orquestrador Maveretta
            config: Configuração de proteções
        """
        self.orchestrator = orchestrator
        self.config = config or ProtectionConfig()
        
        # Inicializar componentes de proteção
        self.stoploss_guard = MaverettaStoplossGuard(orchestrator) if self.config.stoploss_guard_enabled else None
        self.drawdown_guard = MaverettaDrawdownGuard(orchestrator) if self.config.drawdown_guard_enabled else None
        self.cooldown_manager = MaverettaCooldownManager(orchestrator) if self.config.cooldown_manager_enabled else None
        
        # Estado interno
        self.protection_events: List[ProtectionEvent] = []
        self.emergency_stop_active = False
        self.emergency_stop_reason = ""
        self.last_protection_check = datetime.now()
        
        # Configurações aplicadas
        self._apply_component_configurations()
        
        logger.info("[PROTECTION_MANAGER] Initialized Maveretta Protection Manager")
        logger.info(f"[PROTECTION_MANAGER] Enabled protections: "
                   f"StoplossGuard={self.config.stoploss_guard_enabled}, "
                   f"DrawdownGuard={self.config.drawdown_guard_enabled}, "
                   f"CooldownManager={self.config.cooldown_manager_enabled}")
    
    def evaluate_slot_protection(
        self,
        slot_id: str,
        recent_trades: Optional[List[Dict[str, Any]]] = None,
        current_capital: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Avalia proteções para um slot específico
        
        Args:
            slot_id: ID do slot
            recent_trades: Lista de trades recentes (opcional)
            current_capital: Capital atual do slot (opcional)
            
        Returns:
            Dict com status de todas as proteções
        """
        try:
            logger.debug(f"[PROTECTION_MANAGER] Evaluating protections for slot {slot_id}")
            
            protection_status = {
                'slot_id': slot_id,
                'timestamp': datetime.now().isoformat(),
                'any_protection_active': False,
                'can_trade': True,
                'protection_summary': {
                    'stoploss_guard': {'active': False, 'reason': ''},
                    'drawdown_guard': {'active': False, 'reason': ''},
                    'cooldown_manager': {'active': False, 'reason': ''}
                }
            }
            
            # Avaliar cada tipo de proteção
            
            # 1. Stoploss Guard
            if self.stoploss_guard:
                stoploss_protected = self.stoploss_guard.is_slot_protected(slot_id)
                if stoploss_protected:
                    info = self.stoploss_guard.get_slot_protection_info(slot_id)
                    protection_status['protection_summary']['stoploss_guard'] = {
                        'active': True,
                        'reason': info.get('reason', 'Stoploss protection'),
                        'events_count': info.get('events_count', 0)
                    }
                    protection_status['any_protection_active'] = True
                    protection_status['can_trade'] = False
            
            # 2. Drawdown Guard
            if self.drawdown_guard and current_capital is not None:
                # Atualizar capital atual
                self.drawdown_guard.update_slot_capital(slot_id, current_capital)
                
                drawdown_protected = self.drawdown_guard.is_slot_protected(slot_id)
                if drawdown_protected:
                    info = self.drawdown_guard.get_slot_drawdown_info(slot_id)
                    protection_status['protection_summary']['drawdown_guard'] = {
                        'active': True,
                        'reason': info.get('protection_info', {}).get('trigger_reason', 'Drawdown protection'),
                        'drawdown_pct': info.get('current_drawdown_pct', 0)
                    }
                    protection_status['any_protection_active'] = True
                    protection_status['can_trade'] = False
            
            # 3. Cooldown Manager
            if self.cooldown_manager:
                cooldown_active = self.cooldown_manager.is_slot_in_cooldown(slot_id)
                if cooldown_active:
                    info = self.cooldown_manager.get_slot_cooldown_info(slot_id)
                    protection_status['protection_summary']['cooldown_manager'] = {
                        'active': True,
                        'reason': info.get('description', info.get('reason', 'Cooldown active')),
                        'remaining_minutes': info.get('remaining_minutes', 0)
                    }
                    protection_status['any_protection_active'] = True
                    protection_status['can_trade'] = False
            
            # Verificar emergency stop global
            if self.emergency_stop_active:
                protection_status['can_trade'] = False
                protection_status['emergency_stop'] = {
                    'active': True,
                    'reason': self.emergency_stop_reason
                }
            
            return protection_status
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error evaluating slot protection: {e}")
            return {
                'slot_id': slot_id,
                'any_protection_active': True,
                'can_trade': False,
                'error': str(e)
            }
    
    def register_trade_event(
        self,
        slot_id: str,
        trade_data: Dict[str, Any]
    ) -> None:
        """
        Registra evento de trade para análise de proteções
        
        Args:
            slot_id: ID do slot
            trade_data: Dados do trade
        """
        try:
            # Extrair informações relevantes do trade
            exit_reason = trade_data.get('exit_reason', '')
            profit_abs = trade_data.get('profit_abs', 0)
            profit_pct = trade_data.get('profit_pct', 0)
            
            # Registrar em Stoploss Guard se for stoploss
            if (self.stoploss_guard and 
                exit_reason in ['stoploss', 'stop_loss', 'trailing_stop_loss'] and 
                profit_pct < 0):
                
                self.stoploss_guard.register_stoploss_event(
                    slot_id=slot_id,
                    pair=trade_data.get('pair', 'UNKNOWN'),
                    loss_amount=abs(profit_abs),
                    loss_percentage=abs(profit_pct),
                    trade_id=trade_data.get('id', str(datetime.now().timestamp()))
                )
                
                # Registrar evento
                self._register_protection_event(
                    slot_id=slot_id,
                    protection_type=ProtectionType.STOPLOSS_GUARD,
                    event_type="stoploss_registered",
                    level=ProtectionLevel.MEDIUM,
                    details=f"Stoploss trade: {profit_pct:.2%} loss"
                )
            
            logger.debug(f"[PROTECTION_MANAGER] Trade event registered for slot {slot_id}")
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error registering trade event: {e}")
    
    def update_slot_capital(
        self,
        slot_id: str,
        current_capital: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Atualiza capital do slot para análise de drawdown
        
        Args:
            slot_id: ID do slot
            current_capital: Capital atual
            timestamp: Timestamp da atualização
        """
        try:
            if self.drawdown_guard:
                self.drawdown_guard.update_slot_capital(slot_id, current_capital, timestamp)
                
                # Verificar se nova proteção foi ativada
                if self.drawdown_guard.is_slot_protected(slot_id):
                    info = self.drawdown_guard.get_slot_drawdown_info(slot_id)
                    
                    self._register_protection_event(
                        slot_id=slot_id,
                        protection_type=ProtectionType.DRAWDOWN_GUARD,
                        event_type="drawdown_protection_check",
                        level=ProtectionLevel.HIGH,
                        details=f"Drawdown: {info.get('current_drawdown_pct', 0):.2%}"
                    )
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error updating slot capital: {e}")
    
    def apply_manual_protection(
        self,
        slot_id: str,
        protection_type: str,
        duration_minutes: int,
        reason: str = "Manual protection"
    ) -> bool:
        """
        Aplica proteção manual a um slot
        
        Args:
            slot_id: ID do slot
            protection_type: Tipo de proteção ('cooldown', 'stoploss', 'drawdown')
            duration_minutes: Duração em minutos
            reason: Motivo da proteção
            
        Returns:
            True se aplicou com sucesso
        """
        try:
            success = False
            
            if protection_type == 'cooldown' and self.cooldown_manager:
                success = self.cooldown_manager.apply_cooldown(
                    slot_id=slot_id,
                    reason=CooldownReason.MANUAL,
                    duration_minutes=duration_minutes,
                    description=reason,
                    priority=2  # Prioridade média para manual
                )
                
            elif protection_type == 'stoploss' and self.stoploss_guard:
                success = self.stoploss_guard.force_protection(
                    slot_id=slot_id,
                    duration_minutes=duration_minutes,
                    reason=reason
                )
                
            elif protection_type == 'drawdown' and self.drawdown_guard:
                success = self.drawdown_guard.force_drawdown_protection(
                    slot_id=slot_id,
                    duration_minutes=duration_minutes,
                    reason=reason
                )
            
            if success:
                self._register_protection_event(
                    slot_id=slot_id,
                    protection_type=ProtectionType(protection_type + "_guard" if protection_type != "cooldown" else "cooldown_manager"),
                    event_type="manual_protection_applied",
                    level=ProtectionLevel.MEDIUM,
                    details=reason,
                    auto_generated=False
                )
                
                logger.info(f"[PROTECTION_MANAGER] Manual {protection_type} protection applied to slot {slot_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error applying manual protection: {e}")
            return False
    
    def remove_slot_protection(
        self,
        slot_id: str,
        protection_types: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Remove proteções de um slot
        
        Args:
            slot_id: ID do slot
            protection_types: Tipos específicos a remover (None = todos)
            
        Returns:
            Dict com resultado da remoção por tipo
        """
        results = {}
        
        try:
            types_to_remove = protection_types or ['stoploss', 'drawdown', 'cooldown']
            
            for ptype in types_to_remove:
                if ptype == 'stoploss' and self.stoploss_guard:
                    results['stoploss'] = self.stoploss_guard.remove_protection(slot_id)
                    
                elif ptype == 'drawdown' and self.drawdown_guard:
                    # Drawdown guard não tem remoção específica, mas podemos resetar capital peak
                    results['drawdown'] = True  # Simplificado
                    
                elif ptype == 'cooldown' and self.cooldown_manager:
                    results['cooldown'] = self.cooldown_manager.remove_cooldown(slot_id)
            
            # Registrar evento se alguma proteção foi removida
            removed_any = any(results.values())
            if removed_any:
                self._register_protection_event(
                    slot_id=slot_id,
                    protection_type=ProtectionType.COOLDOWN_MANAGER,  # Genérico
                    event_type="protections_removed",
                    level=ProtectionLevel.LOW,
                    details=f"Removed: {', '.join([k for k, v in results.items() if v])}",
                    auto_generated=False
                )
            
            return results
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error removing protections: {e}")
            return {}
    
    def get_global_protection_status(self) -> Dict[str, Any]:
        """
        Retorna status global de todas as proteções
        
        Returns:
            Dict com status global das proteções
        """
        try:
            # Obter resumos de cada componente
            stoploss_summary = self.stoploss_guard.get_global_protection_summary() if self.stoploss_guard else {}
            drawdown_summary = self.drawdown_guard.get_portfolio_drawdown_summary() if self.drawdown_guard else {}
            cooldown_summary = self.cooldown_manager.get_cooldown_summary() if self.cooldown_manager else {}
            
            # Calcular estatísticas gerais
            total_protected_slots = set()
            
            if stoploss_summary:
                total_protected_slots.update(stoploss_summary.get('protected_slots', []))
            if drawdown_summary:
                total_protected_slots.update(drawdown_summary.get('protected_slots', []))
            if cooldown_summary:
                total_protected_slots.update([cd['slot_id'] for cd in cooldown_summary.get('active_slots', [])])
            
            # Verificar se deve ativar emergency stop
            self._check_emergency_stop_conditions(len(total_protected_slots))
            
            # Eventos recentes
            recent_events = [
                {
                    'timestamp': event.timestamp.isoformat(),
                    'slot_id': event.slot_id,
                    'protection_type': event.protection_type.value,
                    'event_type': event.event_type,
                    'level': event.level.value,
                    'details': event.details[:100] + '...' if len(event.details) > 100 else event.details
                }
                for event in self.protection_events[-20:]  # Últimos 20 eventos
            ]
            
            return {
                'timestamp': datetime.now().isoformat(),
                'emergency_stop': {
                    'active': self.emergency_stop_active,
                    'reason': self.emergency_stop_reason
                },
                'total_protected_slots': len(total_protected_slots),
                'protected_slot_ids': list(total_protected_slots),
                'protection_components': {
                    'stoploss_guard': {
                        'enabled': self.config.stoploss_guard_enabled,
                        'summary': stoploss_summary
                    },
                    'drawdown_guard': {
                        'enabled': self.config.drawdown_guard_enabled,
                        'summary': drawdown_summary
                    },
                    'cooldown_manager': {
                        'enabled': self.config.cooldown_manager_enabled,
                        'summary': cooldown_summary
                    }
                },
                'recent_events': recent_events,
                'configuration': {
                    'max_concurrent_protections': self.config.max_concurrent_protections,
                    'global_protection_threshold': self.config.global_protection_threshold,
                    'emergency_stop_enabled': self.config.emergency_stop_enabled
                }
            }
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error getting global status: {e}")
            return {'error': str(e)}
    
    def handle_protection_event(
        self,
        slot_id: str,
        protection_type: str,
        event_type: str,
        details: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Manipula evento de proteção vindo de componentes
        
        Args:
            slot_id: ID do slot
            protection_type: Tipo de proteção
            event_type: Tipo do evento
            details: Detalhes do evento
            timestamp: Timestamp do evento
        """
        try:
            # Determinar nível baseado no tipo de evento
            level = ProtectionLevel.MEDIUM
            
            if 'triggered' in event_type or 'activated' in event_type:
                level = ProtectionLevel.HIGH
            elif 'critical' in event_type or 'emergency' in event_type:
                level = ProtectionLevel.CRITICAL
            elif 'removed' in event_type or 'expired' in event_type:
                level = ProtectionLevel.LOW
            
            # Registrar evento
            self._register_protection_event(
                slot_id=slot_id,
                protection_type=ProtectionType(protection_type),
                event_type=event_type,
                level=level,
                details=details,
                timestamp=timestamp
            )
            
            # Notificar orquestrador se disponível
            if self.orchestrator and hasattr(self.orchestrator, 'handle_protection_notification'):
                self.orchestrator.handle_protection_notification(
                    slot_id=slot_id,
                    protection_type=protection_type,
                    event_type=event_type,
                    level=level.value,
                    details=details
                )
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error handling protection event: {e}")
    
    def activate_emergency_stop(self, reason: str = "Emergency conditions detected") -> bool:
        """
        Ativa emergency stop global
        
        Args:
            reason: Motivo do emergency stop
            
        Returns:
            True se ativou com sucesso
        """
        try:
            self.emergency_stop_active = True
            self.emergency_stop_reason = reason
            
            logger.critical(f"[PROTECTION_MANAGER] EMERGENCY STOP ACTIVATED: {reason}")
            
            # Aplicar cooldown global se cooldown manager disponível
            if self.cooldown_manager:
                self.cooldown_manager.apply_global_cooldown(
                    duration_minutes=60,  # 1 hora de cooldown
                    reason=f"Emergency stop: {reason}"
                )
            
            # Registrar evento crítico
            self._register_protection_event(
                slot_id="GLOBAL",
                protection_type=ProtectionType.COOLDOWN_MANAGER,
                event_type="emergency_stop_activated",
                level=ProtectionLevel.CRITICAL,
                details=reason,
                auto_generated=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error activating emergency stop: {e}")
            return False
    
    def deactivate_emergency_stop(self) -> bool:
        """Desativa emergency stop global"""
        try:
            if self.emergency_stop_active:
                self.emergency_stop_active = False
                old_reason = self.emergency_stop_reason
                self.emergency_stop_reason = ""
                
                logger.warning(f"[PROTECTION_MANAGER] Emergency stop deactivated. Previous reason: {old_reason}")
                
                self._register_protection_event(
                    slot_id="GLOBAL",
                    protection_type=ProtectionType.COOLDOWN_MANAGER,
                    event_type="emergency_stop_deactivated",
                    level=ProtectionLevel.MEDIUM,
                    details=f"Deactivated. Previous: {old_reason}",
                    auto_generated=False
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error deactivating emergency stop: {e}")
            return False
    
    def _apply_component_configurations(self) -> None:
        """Aplica configurações específicas aos componentes"""
        try:
            # Aplicar configurações específicas do stoploss guard
            if self.stoploss_guard and self.config.stoploss_config:
                for key, value in self.config.stoploss_config.items():
                    if hasattr(self.stoploss_guard, key):
                        setattr(self.stoploss_guard, key, value)
            
            # Aplicar configurações específicas do drawdown guard
            if self.drawdown_guard and self.config.drawdown_config:
                for key, value in self.config.drawdown_config.items():
                    if hasattr(self.drawdown_guard, key):
                        setattr(self.drawdown_guard, key, value)
            
            # Aplicar configurações específicas do cooldown manager
            if self.cooldown_manager and self.config.cooldown_config:
                for key, value in self.config.cooldown_config.items():
                    if hasattr(self.cooldown_manager, key):
                        setattr(self.cooldown_manager, key, value)
            
        except Exception as e:
            logger.warning(f"[PROTECTION_MANAGER] Error applying component configurations: {e}")
    
    def _register_protection_event(
        self,
        slot_id: str,
        protection_type: ProtectionType,
        event_type: str,
        level: ProtectionLevel,
        details: str,
        auto_generated: bool = True,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Registra evento de proteção interno"""
        
        event = ProtectionEvent(
            timestamp=timestamp or datetime.now(),
            slot_id=slot_id,
            protection_type=protection_type,
            event_type=event_type,
            level=level,
            details=details,
            auto_generated=auto_generated
        )
        
        self.protection_events.append(event)
        
        # Manter apenas últimos 1000 eventos
        if len(self.protection_events) > 1000:
            self.protection_events = self.protection_events[-1000:]
        
        # Log baseado no nível
        if level == ProtectionLevel.CRITICAL:
            logger.critical(f"[PROTECTION_MANAGER] {protection_type.value}: {event_type} - {details}")
        elif level == ProtectionLevel.HIGH:
            logger.warning(f"[PROTECTION_MANAGER] {protection_type.value}: {event_type} - {details}")
        else:
            logger.info(f"[PROTECTION_MANAGER] {protection_type.value}: {event_type} - {details}")
    
    def _check_emergency_stop_conditions(self, protected_slots_count: int) -> None:
        """Verifica condições para ativar emergency stop automático"""
        
        if not self.config.emergency_stop_enabled or self.emergency_stop_active:
            return
        
        try:
            # Obter número total de slots ativos (simplificado)
            total_active_slots = len(set(
                list(self.stoploss_guard.protection_status.keys() if self.stoploss_guard else []) +
                list(self.drawdown_guard.protection_status.keys() if self.drawdown_guard else []) +
                list(self.cooldown_manager.active_cooldowns.keys() if self.cooldown_manager else [])
            )) or 1  # Evitar divisão por zero
            
            protection_ratio = protected_slots_count / total_active_slots
            
            # Ativar emergency stop se muitos slots protegidos
            if protection_ratio >= self.config.global_protection_threshold:
                self.activate_emergency_stop(
                    f"Too many protected slots: {protected_slots_count}/{total_active_slots} "
                    f"({protection_ratio:.1%} >= {self.config.global_protection_threshold:.1%})"
                )
        
        except Exception as e:
            logger.error(f"[PROTECTION_MANAGER] Error checking emergency stop conditions: {e}")

# Funções de conveniência
def create_protection_manager(orchestrator=None, **config_kwargs) -> MaverettaProtectionManager:
    """Função de conveniência para criar manager de proteções"""
    
    config = ProtectionConfig(**config_kwargs)
    return MaverettaProtectionManager(orchestrator, config)