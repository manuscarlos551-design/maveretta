# core/risk/protections.py
"""
Protection System - Sistema de proteções adaptado do Freqtrade
"""
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, NamedTuple
from enum import Enum
import redis

logger = logging.getLogger(__name__)

class ProtectionType(Enum):
    COOLDOWN = "cooldown"
    STOPLOSS_GUARD = "stoploss_guard" 
    DRAWDOWN_GUARD = "drawdown_guard"
    MANUAL = "manual"

class ProtectionReturn(NamedTuple):
    lock: bool
    until: datetime
    reason: str
    pair: Optional[str] = None

class CooldownReason(Enum):
    MANUAL = "manual"
    STOPLOSS = "stoploss"
    DRAWDOWN = "drawdown"
    PERFORMANCE = "performance"
    MARKET_CONDITIONS = "market_conditions"
    ERROR_RECOVERY = "error_recovery"

class ProtectionManager:
    """Gerenciador centralizado de proteções"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.protections = {}
        
        # Configurações padrão
        self.config = {
            'cooldown_period_minutes': 30,
            'stoploss_guard_limit': 3,
            'stoploss_guard_lookback_minutes': 60,
            'drawdown_guard_max_pct': 10.0,
            'drawdown_guard_lookback_hours': 24
        }
        
        # Inicializar proteções
        self._init_protections()
    
    def _get_redis_client(self):
        """Obtém cliente Redis"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            return redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Erro ao conectar Redis para proteções: {e}")
            return None
    
    def _init_protections(self):
        """Inicializa as proteções disponíveis"""
        # Cooldown Period
        self.protections[ProtectionType.COOLDOWN] = CooldownPeriod(self)
        
        # Stoploss Guard
        self.protections[ProtectionType.STOPLOSS_GUARD] = StoplossGuard(self)
        
        # Drawdown Guard
        self.protections[ProtectionType.DRAWDOWN_GUARD] = DrawdownGuard(self)
    
    def should_block_slot(self, slot_id: str) -> tuple[bool, str]:
        """
        Verifica se um slot deve ser bloqueado por qualquer proteção
        
        Returns:
            tuple: (blocked, reason)
        """
        try:
            current_time = datetime.now()
            
            for protection_type, protection in self.protections.items():
                result = protection.check_protection(slot_id, current_time)
                if result and result.lock:
                    return True, result.reason
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Erro ao verificar proteções para slot {slot_id}: {e}")
            return False, str(e)
    
    def apply_protection(
        self, 
        slot_id: str, 
        protection_type: ProtectionType, 
        duration_minutes: int,
        reason: str,
        data: Optional[Dict] = None
    ) -> bool:
        """
        Aplica uma proteção a um slot
        """
        try:
            if protection_type not in self.protections:
                logger.error(f"Tipo de proteção {protection_type} não existe")
                return False
            
            protection = self.protections[protection_type]
            return protection.apply_protection(slot_id, duration_minutes, reason, data or {})
            
        except Exception as e:
            logger.error(f"Erro ao aplicar proteção {protection_type} ao slot {slot_id}: {e}")
            return False
    
    def remove_protection(self, slot_id: str, protection_type: Optional[ProtectionType] = None) -> bool:
        """
        Remove proteção(ões) de um slot
        """
        try:
            if protection_type:
                # Remover proteção específica
                if protection_type in self.protections:
                    return self.protections[protection_type].remove_protection(slot_id)
                return False
            else:
                # Remover todas as proteções
                results = []
                for protection in self.protections.values():
                    results.append(protection.remove_protection(slot_id))
                return any(results)
                
        except Exception as e:
            logger.error(f"Erro ao remover proteções do slot {slot_id}: {e}")
            return False
    
    def get_slot_protections(self, slot_id: str) -> Dict[str, Any]:
        """
        Obtém status de todas as proteções para um slot
        """
        try:
            protections_status = {}
            
            for protection_type, protection in self.protections.items():
                status = protection.get_protection_status(slot_id)
                protections_status[protection_type.value] = status
            
            return protections_status
            
        except Exception as e:
            logger.error(f"Erro ao obter proteções do slot {slot_id}: {e}")
            return {}
    
    def register_trade_event(self, slot_id: str, trade_data: Dict[str, Any]):
        """
        Registra evento de trade para análise das proteções
        """
        try:
            # Registrar em todas as proteções que precisam de dados de trade
            for protection in self.protections.values():
                if hasattr(protection, 'register_trade_event'):
                    protection.register_trade_event(slot_id, trade_data)
                    
        except Exception as e:
            logger.error(f"Erro ao registrar evento de trade: {e}")

class BaseProtection:
    """Classe base para proteções"""
    
    def __init__(self, manager: ProtectionManager):
        self.manager = manager
        self.redis_client = manager.redis_client
    
    def _get_key(self, slot_id: str, suffix: str = "") -> str:
        """Gera chave Redis para a proteção"""
        protection_name = self.__class__.__name__.lower()
        return f"protection:{protection_name}:{slot_id}{':' + suffix if suffix else ''}"
    
    def check_protection(self, slot_id: str, current_time: datetime) -> Optional[ProtectionReturn]:
        """Implementar nas classes filhas"""
        raise NotImplementedError
    
    def apply_protection(self, slot_id: str, duration_minutes: int, reason: str, data: Dict) -> bool:
        """Implementar nas classes filhas"""
        raise NotImplementedError
    
    def remove_protection(self, slot_id: str) -> bool:
        """Remove proteção do slot"""
        if not self.redis_client:
            return False
        
        try:
            key = self._get_key(slot_id)
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.warning(f"Erro ao remover proteção: {e}")
            return False
    
    def get_protection_status(self, slot_id: str) -> Dict[str, Any]:
        """Obtém status da proteção para o slot"""
        if not self.redis_client:
            return {'active': False, 'error': 'Redis não disponível'}
        
        try:
            key = self._get_key(slot_id)
            data = self.redis_client.get(key)
            
            if data:
                protection_data = json.loads(data)
                until = datetime.fromisoformat(protection_data['until'])
                active = datetime.now() < until
                
                return {
                    'active': active,
                    'until': protection_data['until'],
                    'reason': protection_data['reason'],
                    'applied_at': protection_data.get('applied_at')
                }
            
            return {'active': False}
            
        except Exception as e:
            logger.warning(f"Erro ao obter status da proteção: {e}")
            return {'active': False, 'error': str(e)}

class CooldownPeriod(BaseProtection):
    """Proteção de cooldown - período de pausa após evento"""
    
    def check_protection(self, slot_id: str, current_time: datetime) -> Optional[ProtectionReturn]:
        """Verifica se slot está em cooldown"""
        if not self.redis_client:
            return None
        
        try:
            key = self._get_key(slot_id)
            data = self.redis_client.get(key)
            
            if data:
                cooldown_data = json.loads(data)
                until = datetime.fromisoformat(cooldown_data['until'])
                
                if current_time < until:
                    return ProtectionReturn(
                        lock=True,
                        until=until,
                        reason=cooldown_data['reason'],
                        pair=slot_id
                    )
                else:
                    # Cooldown expirado, remover
                    self.redis_client.delete(key)
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao verificar cooldown: {e}")
            return None
    
    def apply_protection(self, slot_id: str, duration_minutes: int, reason: str, data: Dict) -> bool:
        """Aplica cooldown ao slot"""
        if not self.redis_client:
            return False
        
        try:
            current_time = datetime.now()
            until = current_time + timedelta(minutes=duration_minutes)
            
            cooldown_data = {
                'until': until.isoformat(),
                'reason': reason,
                'applied_at': current_time.isoformat(),
                'duration_minutes': duration_minutes,
                **data
            }
            
            key = self._get_key(slot_id)
            ttl_seconds = duration_minutes * 60 + 60  # TTL com margem
            
            self.redis_client.setex(key, ttl_seconds, json.dumps(cooldown_data))
            
            logger.info(f"Cooldown aplicado ao slot {slot_id}: {duration_minutes}min - {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao aplicar cooldown: {e}")
            return False

class StoplossGuard(BaseProtection):
    """Proteção contra múltiplos stoplosses"""
    
    def __init__(self, manager: ProtectionManager):
        super().__init__(manager)
        self.lookback_minutes = manager.config['stoploss_guard_lookback_minutes']
        self.limit = manager.config['stoploss_guard_limit']
    
    def check_protection(self, slot_id: str, current_time: datetime) -> Optional[ProtectionReturn]:
        """Verifica proteção por stoploss"""
        # Verifica se já está protegido por cooldown
        cooldown_result = self.manager.protections[ProtectionType.COOLDOWN].check_protection(slot_id, current_time)
        if cooldown_result and cooldown_result.lock:
            return cooldown_result
        
        # Verifica múltiplos stoplosses
        if self._has_multiple_stoplosses(slot_id, current_time):
            # Aplicar cooldown automático
            self.apply_protection(
                slot_id, 
                duration_minutes=30, 
                reason=f"Múltiplos stoplosses ({self.limit} em {self.lookback_minutes}min)",
                data={'type': 'auto_stoploss_guard'}
            )
            
            return ProtectionReturn(
                lock=True,
                until=current_time + timedelta(minutes=30),
                reason=f"Stoploss guard ativado",
                pair=slot_id
            )
        
        return None
    
    def _has_multiple_stoplosses(self, slot_id: str, current_time: datetime) -> bool:
        """Verifica se houve múltiplos stoplosses no período"""
        if not self.redis_client:
            return False
        
        try:
            events_key = self._get_key(slot_id, "events")
            events_data = self.redis_client.lrange(events_key, 0, -1)
            
            cutoff_time = current_time - timedelta(minutes=self.lookback_minutes)
            stoploss_count = 0
            
            for event_str in events_data:
                try:
                    event = json.loads(event_str)
                    event_time = datetime.fromisoformat(event['timestamp'])
                    
                    if event_time >= cutoff_time and event.get('type') == 'stoploss':
                        stoploss_count += 1
                except:
                    continue
            
            return stoploss_count >= self.limit
            
        except Exception as e:
            logger.warning(f"Erro ao verificar stoplosses: {e}")
            return False
    
    def register_trade_event(self, slot_id: str, trade_data: Dict[str, Any]):
        """Registra evento de trade"""
        if not self.redis_client or trade_data.get('exit_reason') != 'stop_loss':
            return
        
        try:
            event = {
                'type': 'stoploss',
                'timestamp': datetime.now().isoformat(),
                'trade_data': trade_data
            }
            
            events_key = self._get_key(slot_id, "events")
            
            # Adicionar evento
            self.redis_client.lpush(events_key, json.dumps(event))
            
            # Manter apenas eventos dos últimos dias
            self.redis_client.ltrim(events_key, 0, 99)
            
            # TTL
            self.redis_client.expire(events_key, 86400 * 2)  # 2 dias
            
        except Exception as e:
            logger.warning(f"Erro ao registrar evento de stoploss: {e}")
    
    def apply_protection(self, slot_id: str, duration_minutes: int, reason: str, data: Dict) -> bool:
        """Aplica proteção via cooldown"""
        return self.manager.protections[ProtectionType.COOLDOWN].apply_protection(
            slot_id, duration_minutes, reason, data
        )

class DrawdownGuard(BaseProtection):
    """Proteção contra drawdown excessivo"""
    
    def __init__(self, manager: ProtectionManager):
        super().__init__(manager)
        self.max_drawdown_pct = manager.config['drawdown_guard_max_pct']
        self.lookback_hours = manager.config['drawdown_guard_lookback_hours']
    
    def check_protection(self, slot_id: str, current_time: datetime) -> Optional[ProtectionReturn]:
        """Verifica proteção por drawdown"""
        # Verifica cooldown primeiro
        cooldown_result = self.manager.protections[ProtectionType.COOLDOWN].check_protection(slot_id, current_time)
        if cooldown_result and cooldown_result.lock:
            return cooldown_result
        
        # Verifica drawdown
        drawdown_pct = self._calculate_recent_drawdown(slot_id, current_time)
        
        if drawdown_pct > self.max_drawdown_pct:
            # Aplicar cooldown automático
            duration = min(60, int(drawdown_pct * 2))  # Cooldown proporcional, max 60min
            
            self.apply_protection(
                slot_id,
                duration_minutes=duration,
                reason=f"Drawdown de {drawdown_pct:.1f}% (max {self.max_drawdown_pct}%)",
                data={'type': 'auto_drawdown_guard', 'drawdown_pct': drawdown_pct}
            )
            
            return ProtectionReturn(
                lock=True,
                until=current_time + timedelta(minutes=duration),
                reason="Drawdown guard ativado",
                pair=slot_id
            )
        
        return None
    
    def _calculate_recent_drawdown(self, slot_id: str, current_time: datetime) -> float:
        """Calcula drawdown recente do slot"""
        if not self.redis_client:
            return 0.0
        
        try:
            # Buscar dados de P&L do slot
            pnl_key = f"slot:{slot_id}:pnl_history"
            pnl_data = self.redis_client.lrange(pnl_key, 0, -1)
            
            if len(pnl_data) < 2:
                return 0.0
            
            cutoff_time = current_time - timedelta(hours=self.lookback_hours)
            pnl_values = []
            
            for pnl_str in pnl_data:
                try:
                    pnl_entry = json.loads(pnl_str)
                    entry_time = datetime.fromisoformat(pnl_entry['timestamp'])
                    
                    if entry_time >= cutoff_time:
                        pnl_values.append(pnl_entry['pnl'])
                except:
                    continue
            
            if len(pnl_values) < 2:
                return 0.0
            
            # Calcular drawdown máximo
            peak = max(pnl_values)
            trough = min(pnl_values[pnl_values.index(peak):]) if peak in pnl_values else min(pnl_values)
            
            if peak > 0:
                drawdown_pct = abs((trough - peak) / peak) * 100
            else:
                drawdown_pct = abs(trough - peak)  # Drawdown absoluto se não há lucro
            
            return drawdown_pct
            
        except Exception as e:
            logger.warning(f"Erro ao calcular drawdown: {e}")
            return 0.0
    
    def apply_protection(self, slot_id: str, duration_minutes: int, reason: str, data: Dict) -> bool:
        """Aplica proteção via cooldown"""
        return self.manager.protections[ProtectionType.COOLDOWN].apply_protection(
            slot_id, duration_minutes, reason, data
        )


# Instância global do gerenciador
protection_manager = ProtectionManager()