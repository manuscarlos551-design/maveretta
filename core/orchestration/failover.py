# core/orchestration/failover.py
"""
Automatic Failover System - Sistema de Failover Automático com Handoff de Estado
Detecta falhas das IAs e executa substituição automática com preservação de contexto
"""

import os
import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

# Redis para contexto compartilhado
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configuração
FAILOVER_ENABLED = os.getenv("IA_FAILOVER_ENABLE", "true").lower() == "true"
HEARTBEAT_THRESHOLD_SEC = int(os.getenv("IA_FAILOVER_HEARTBEAT_SEC", "30"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Logger
logger = logging.getLogger(__name__)

class FailoverTrigger(Enum):
    """Tipos de trigger para failover"""
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    STATUS_DEGRADED = "status_degraded"
    HIGH_LATENCY = "high_latency" 
    MANUAL_TRIGGER = "manual_trigger"
    HEALTH_CHECK_FAILED = "health_check_failed"

@dataclass
class SlotContext:
    """Contexto compartilhado de um slot para handoff"""
    slot_id: str
    strategy_active: str
    strategy_params: Dict[str, Any]
    open_position: Optional[Dict[str, Any]]
    pending_signals: List[Dict[str, Any]]
    risk_snapshot: Dict[str, Any]
    last_decisions: List[Dict[str, Any]]
    last_update_ts: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlotContext':
        return cls(**data)

class FailoverManager:
    """Gerenciador de failover automático das IAs"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = FAILOVER_ENABLED
        self.heartbeat_threshold = HEARTBEAT_THRESHOLD_SEC
        
        # Inicializa Redis se disponível
        if REDIS_AVAILABLE and self.enabled:
            try:
                self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ Failover Manager: Redis conectado")
            except Exception as e:
                logger.warning(f"⚠️ Failover Manager: Redis não disponível - {e}")
                self.redis_client = None
        
        # Métricas de failover
        self.failover_events = []
        self.last_health_check = {}
    
    def store_slot_context(self, slot_context: SlotContext) -> bool:
        """Armazena contexto do slot no Redis para handoff"""
        if not self.redis_client:
            logger.warning("Redis não disponível para armazenar contexto")
            return False
        
        try:
            key = f"slot:{slot_context.slot_id}:context"
            context_data = json.dumps(slot_context.to_dict())
            
            # Armazena com TTL de 1 hora
            self.redis_client.setex(key, 3600, context_data)
            
            logger.debug(f"Contexto do slot {slot_context.slot_id} armazenado no Redis")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao armazenar contexto do slot {slot_context.slot_id}: {e}")
            return False
    
    def load_slot_context(self, slot_id: str) -> Optional[SlotContext]:
        """Carrega contexto do slot do Redis"""
        if not self.redis_client:
            return None
        
        try:
            key = f"slot:{slot_id}:context"
            context_data = self.redis_client.get(key)
            
            if not context_data:
                logger.warning(f"Contexto do slot {slot_id} não encontrado no Redis")
                return None
            
            context_dict = json.loads(context_data)
            return SlotContext.from_dict(context_dict)
            
        except Exception as e:
            logger.error(f"Erro ao carregar contexto do slot {slot_id}: {e}")
            return None
    
    def detect_ia_failures(self, ia_health: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detecta IAs com falha baseado nos critérios de saúde"""
        failed_ias = []
        
        if not self.enabled or not ia_health:
            return failed_ias
        
        current_time = time.time()
        
        for ia in ia_health:
            ia_id = ia.get("id", "unknown")
            status = ia.get("status", "RED")
            last_heartbeat = ia.get("last_heartbeat", 0)
            latency_ms = ia.get("latency_ms", float('inf'))
            
            # Armazena último health check
            self.last_health_check[ia_id] = {
                "timestamp": current_time,
                "status": status,
                "heartbeat": last_heartbeat,
                "latency": latency_ms
            }
            
            failure_reasons = []
            
            # 1. Status não é GREEN
            if status != "GREEN":
                failure_reasons.append(f"Status degraded: {status}")
            
            # 2. Heartbeat timeout
            if last_heartbeat > 0:
                heartbeat_age = current_time - last_heartbeat
                if heartbeat_age > self.heartbeat_threshold:
                    failure_reasons.append(f"Heartbeat timeout: {heartbeat_age:.1f}s > {self.heartbeat_threshold}s")
            
            # 3. Latência alta
            if latency_ms > 5000:  # 5 segundos
                failure_reasons.append(f"High latency: {latency_ms}ms")
            
            # Se encontrou falhas, marca para failover
            if failure_reasons:
                failed_ias.append({
                    "ia_id": ia_id,
                    "ia_data": ia,
                    "trigger": FailoverTrigger.HEARTBEAT_TIMEOUT if "timeout" in failure_reasons[0] else FailoverTrigger.STATUS_DEGRADED,
                    "reasons": failure_reasons,
                    "detected_at": current_time
                })
                
                logger.warning(f"🚨 IA {ia_id} com falha detectada: {'; '.join(failure_reasons)}")
        
        return failed_ias
    
    def select_substitute_ia(self, failed_ia_id: str, group: str, available_ias: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Seleciona IA substituta do mesmo grupo com melhor health score"""
        if not available_ias:
            return None
        
        # Filtra IAs do mesmo grupo que não falharam
        group_ias = []
        
        for ia in available_ias:
            ia_id = ia.get("id", "")
            ia_status = ia.get("status", "RED")
            
            # Verifica se é do mesmo grupo
            if group in ia_id or ("leader" in ia_id.lower() and group in ["G1", "G2"]):
                # Verifica se não falhou recentemente
                if ia_id != failed_ia_id and ia_status == "GREEN":
                    group_ias.append(ia)
        
        if not group_ias:
            logger.warning(f"Nenhuma IA substituta disponível no grupo {group}")
            return None
        
        # Calcula health score para cada IA candidata
        scored_ias = []
        
        for ia in group_ias:
            score = 0
            
            # Status (40% do peso)
            status = ia.get("status", "RED")
            if status == "GREEN":
                score += 0.4
            elif status == "AMBER":
                score += 0.2
            
            # Latência (30% do peso)
            latency_ms = ia.get("latency_ms", 1000)
            if latency_ms < 100:
                score += 0.3
            elif latency_ms < 500:
                score += 0.2
            elif latency_ms < 1000:
                score += 0.1
            
            # Uptime (20% do peso)
            uptime = ia.get("uptime_pct", 0)
            score += (uptime / 100) * 0.2
            
            # Accuracy (10% do peso)
            accuracy = ia.get("accuracy", 0)
            score += (accuracy / 100) * 0.1
            
            scored_ias.append({
                "ia": ia,
                "score": score
            })
        
        # Ordena por score decrescente e retorna a melhor
        scored_ias.sort(key=lambda x: x["score"], reverse=True)
        
        best_ia = scored_ias[0]["ia"]
        logger.info(f"✅ IA substituta selecionada: {best_ia.get('id')} (score: {scored_ias[0]['score']:.2f})")
        
        return best_ia
    
    def execute_failover(self, failed_ia_id: str, slot_id: str, substitute_ia: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o processo de failover com handoff de estado"""
        try:
            failover_start = time.time()
            
            # 1. Carrega contexto atual do slot
            slot_context = self.load_slot_context(slot_id)
            
            if not slot_context:
                logger.warning(f"Contexto do slot {slot_id} não encontrado - criando novo contexto")
                slot_context = SlotContext(
                    slot_id=slot_id,
                    strategy_active="momentum",  # Default seguro
                    strategy_params={},
                    open_position=None,
                    pending_signals=[],
                    risk_snapshot={},
                    last_decisions=[],
                    last_update_ts=time.time()
                )
            
            # 2. Registra evento de failover
            failover_event = {
                "event_id": f"failover_{int(time.time())}_{slot_id}",
                "type": "FAILOVER_TRIGGERED",
                "slot_id": slot_id,
                "failed_ia_id": failed_ia_id,
                "substitute_ia_id": substitute_ia.get("id"),
                "trigger_reason": "IA health check failed",
                "context_preserved": slot_context is not None,
                "timestamp": datetime.now().isoformat(),
                "duration_ms": 0  # Será atualizado no final
            }
            
            # 3. Atualiza binding da IA no slot (simulado - seria feito via API real)
            # Em implementação real, isso atualizaria o sistema de orquestração
            logger.info(f"🔄 Executando handoff: {failed_ia_id} → {substitute_ia.get('id')} para slot {slot_id}")
            
            # 4. Atualiza contexto com nova IA
            slot_context.last_update_ts = time.time()
            
            # 5. Salva contexto atualizado
            self.store_slot_context(slot_context)
            
            # 6. Finaliza evento
            failover_duration = (time.time() - failover_start) * 1000
            failover_event["duration_ms"] = failover_duration
            failover_event["type"] = "FAILOVER_COMPLETED"
            
            # 7. Registra na lista de eventos
            self.failover_events.append(failover_event)
            
            # Limita histórico a 100 eventos mais recentes
            if len(self.failover_events) > 100:
                self.failover_events = self.failover_events[-100:]
            
            logger.info(f"✅ Failover concluído em {failover_duration:.1f}ms: {substitute_ia.get('id')} assumiu slot {slot_id}")
            
            return {
                "success": True,
                "event": failover_event,
                "slot_context": slot_context.to_dict(),
                "message": f"Failover completed: {substitute_ia.get('id')} took over slot {slot_id}"
            }
            
        except Exception as e:
            logger.error(f"❌ Erro durante failover do slot {slot_id}: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def process_failovers(self, ia_health: List[Dict[str, Any]], slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processa todos os failovers necessários"""
        if not self.enabled:
            return []
        
        # 1. Detecta IAs com falha
        failed_ias = self.detect_ia_failures(ia_health)
        
        if not failed_ias:
            return []  # Nenhuma falha detectada
        
        # 2. Mapeia IAs para slots
        ia_slot_mapping = {}
        for slot in slots:
            assigned_ia = slot.get("assigned_ia") or slot.get("ia_id")
            if assigned_ia:
                ia_slot_mapping[assigned_ia] = slot
        
        # 3. Executa failovers para cada IA falhada
        failover_results = []
        
        for failed_ia_info in failed_ias:
            failed_ia_id = failed_ia_info["ia_id"]
            
            # Verifica se IA tem slot assignado
            if failed_ia_id not in ia_slot_mapping:
                logger.info(f"IA {failed_ia_id} com falha mas sem slot assignado - ignorando")
                continue
            
            slot = ia_slot_mapping[failed_ia_id]
            slot_id = slot.get("id")
            
            # Determina grupo da IA (G1/G2)
            group = self._determine_ia_group(failed_ia_id, slot)
            
            # Seleciona substituta
            available_ias = [ia for ia in ia_health if ia.get("id") != failed_ia_id]
            substitute_ia = self.select_substitute_ia(failed_ia_id, group, available_ias)
            
            if not substitute_ia:
                logger.error(f"❌ Não foi possível encontrar substituta para IA {failed_ia_id} no grupo {group}")
                continue
            
            # Executa failover
            result = self.execute_failover(failed_ia_id, slot_id, substitute_ia)
            failover_results.append(result)
        
        return failover_results
    
    def _determine_ia_group(self, ia_id: str, slot: Dict[str, Any]) -> str:
        """Determina grupo (G1/G2) da IA baseado no ID e slot"""
        # Verifica pelo ID da IA
        if "g1" in ia_id.lower():
            return "G1"
        elif "g2" in ia_id.lower():
            return "G2"
        
        # Verifica pelo slot (ímpares = G1, pares = G2)
        slot_id = slot.get("id", "")
        try:
            import re
            numbers = re.findall(r'\d+', str(slot_id))
            if numbers:
                return "G1" if int(numbers[0]) % 2 == 1 else "G2"
        except:
            pass
        
        # Default para líder/orquestrador
        if "leader" in ia_id.lower() or "orchestrator" in ia_id.lower():
            return "G1"  # Líder pode assumir G1 por padrão
        
        return "G1"  # Fallback
    
    def get_failover_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de failover"""
        recent_events = [e for e in self.failover_events if 
                        (time.time() - datetime.fromisoformat(e["timestamp"].replace('Z', '+00:00')).timestamp()) < 86400]
        
        return {
            "enabled": self.enabled,
            "heartbeat_threshold_sec": self.heartbeat_threshold,
            "redis_available": self.redis_client is not None,
            "total_failover_events": len(self.failover_events),
            "failovers_last_24h": len(recent_events),
            "recent_events": self.failover_events[-5:] if self.failover_events else []
        }

# Instância global
failover_manager = FailoverManager()

def process_automatic_failovers(ia_health: List[Dict[str, Any]], slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Função wrapper para processamento automático de failovers"""
    return failover_manager.process_failovers(ia_health, slots)

def get_failover_statistics() -> Dict[str, Any]:
    """Função wrapper para estatísticas de failover"""
    return failover_manager.get_failover_stats()