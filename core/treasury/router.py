# core/treasury/router.py
"""
Treasury Router - Sistema de Roteamento de Lucros
Implementa a lógica de cascata com Valor Base (VB) fixo
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# === PROMETHEUS METRICS ===
treasury_capital_total = Gauge(
    'treasury_capital_total_usd',
    'Total capital under treasury management in USD'
)

treasury_allocation_by_slot = Gauge(
    'treasury_allocation_by_slot_usd',
    'Capital allocated to each slot in USD',
    ['slot', 'status']
)

treasury_profit_routing = Counter(
    'treasury_profit_routing_total',
    'Total profit routed by destination',
    ['destination', 'slot_origin']
)

treasury_expansion = Counter(
    'treasury_expansion_total_usd',
    'Capital expansion after S10 capitalization',
    ['slot_to']
)

treasury_balance_gauge = Gauge(
    'treasury_balance_usd',
    'Current treasury balance in USD'
)


@dataclass
class SlotState:
    """Estado de um slot na cascata"""
    slot_id: str
    valor_base: float  # VB - valor fixo que o slot opera
    capital_atual: float  # Capital atual do slot
    status: str = "BOOTSTRAP"  # BOOTSTRAP | OPERANDO
    total_lucro_recebido: float = 0.0
    total_lucro_enviado: float = 0.0
    trades_realizados: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def is_capitalized(self) -> bool:
        """Verifica se slot atingiu o VB"""
        return self.capital_atual >= self.valor_base
    
    def get_excess(self) -> float:
        """Retorna excesso acima do VB"""
        if self.capital_atual > self.valor_base:
            return self.capital_atual - self.valor_base
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dict"""
        return {
            "slot_id": self.slot_id,
            "valor_base": self.valor_base,
            "capital_atual": self.capital_atual,
            "status": self.status,
            "is_capitalized": self.is_capitalized(),
            "excess": self.get_excess(),
            "total_lucro_recebido": self.total_lucro_recebido,
            "total_lucro_enviado": self.total_lucro_enviado,
            "trades_realizados": self.trades_realizados,
            "created_at": self.created_at.isoformat()
        }


class TreasuryRouter:
    """
    Gerenciador de Roteamento de Lucros baseado em Cascata
    
    Conceitos:
    - VB (Valor Base): capital fixo que cada slot opera
    - Slots operam sempre em VB, nunca acima
    - Lucros são 100% roteados para próximo slot não capitalizado
    - Após todos capitalizados, vai para Tesouraria
    """
    
    def __init__(self, valor_base: float = 1000.0):
        self.valor_base = valor_base
        self.slots: List[SlotState] = []
        self.treasury_balance: float = 0.0
        self.settlement_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()  # FIX P0: Adicionar lock síncrono
        
        # Inicializa 10 slots
        self._initialize_slots()
        
        # Atualizar métricas iniciais
        self._update_prometheus_metrics()
        
        logger.info(f"Treasury Router inicializado | VB={valor_base} | 10 slots criados")
    
    def _initialize_slots(self):
        """Inicializa os 10 slots da cascata"""
        for i in range(1, 11):
            slot = SlotState(
                slot_id=f"slot_{i}",
                valor_base=self.valor_base,
                capital_atual=0.0 if i > 1 else self.valor_base  # Slot 1 começa com VB
            )
            
            # Slot 1 já está OPERANDO
            if i == 1:
                slot.status = "OPERANDO"
                slot.capital_atual = self.valor_base
            
            self.slots.append(slot)
        
        logger.info(f"✅ Slot 1 inicializado com VB=${self.valor_base} (OPERANDO)")
    
    def _update_prometheus_metrics(self):
        """Atualiza todas as métricas Prometheus do Treasury"""
        total_capital = sum(slot.capital_atual for slot in self.slots) + self.treasury_balance
        treasury_capital_total.set(total_capital)
        treasury_balance_gauge.set(self.treasury_balance)
        
        for slot in self.slots:
            treasury_allocation_by_slot.labels(
                slot=slot.slot_id,
                status=slot.status
            ).set(slot.capital_atual)
    
    def next_target_slot(self) -> Optional[SlotState]:
        """
        Retorna o próximo slot que precisa ser capitalizado
        
        Returns:
            SlotState do próximo slot < VB, ou None se todos capitalizados
        """
        for slot in self.slots:
            if not slot.is_capitalized():
                return slot
        return None
    
    def settle_trade(
        self,
        slot_id: str,
        net_pnl: float,
        settlement_id: str,
        trade_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Liquida um trade e roteia lucros conforme regras de cascata
        
        Args:
            slot_id: ID do slot que fechou o trade
            net_pnl: Lucro líquido (já descontadas taxas)
            settlement_id: ID único da liquidação (idempotência)
            trade_details: Detalhes opcionais do trade
        
        Returns:
            Resultado do settlement com roteamento
        """
        # FIX P0: Proteger com lock síncrono
        with self._lock:
            return self._settle_trade_locked(slot_id, net_pnl, settlement_id, trade_details)
    
    def _settle_trade_locked(
        self,
        slot_id: str,
        net_pnl: float,
        settlement_id: str,
        trade_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Versão interna com lock da settle_trade"""
        # Verifica idempotência
        if any(s['settlement_id'] == settlement_id for s in self.settlement_history):
            logger.warning(f"Settlement {settlement_id} já processado (idempotente)")
            return {
                "status": "already_processed",
                "settlement_id": settlement_id,
                "message": "Settlement já foi processado anteriormente"
            }
        
        # Busca o slot
        slot = self._get_slot(slot_id)
        if not slot:
            logger.error(f"Slot {slot_id} não encontrado")
            return {
                "status": "error",
                "message": f"Slot {slot_id} não encontrado"
            }
        
        # Atualiza capital do slot
        slot.capital_atual += net_pnl
        slot.trades_realizados += 1
        
        logger.info(
            f"💰 Settlement {settlement_id} | {slot_id} | "
            f"PnL=${net_pnl:.2f} | Capital: ${slot.capital_atual:.2f}"
        )
        
        # Roteia excesso
        routing_result = self._route_excess(slot)
        
        # Registra no histórico
        settlement_record = {
            "settlement_id": settlement_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "slot_id": slot_id,
            "net_pnl": net_pnl,
            "capital_after": slot.capital_atual,
            "routing": routing_result,
            "trade_details": trade_details or {}
        }
        self.settlement_history.append(settlement_record)
        
        # Limita histórico a 1000 registros
        if len(self.settlement_history) > 1000:
            self.settlement_history = self.settlement_history[-1000:]
        
        return {
            "status": "success",
            "settlement_id": settlement_id,
            "slot_id": slot_id,
            "net_pnl": net_pnl,
            "capital_after": slot.capital_atual,
            "routing": routing_result
        }
    
    def _route_excess(self, slot: SlotState) -> Dict[str, Any]:
        """
        Roteia excesso acima do VB para próximo slot
        
        Args:
            slot: Slot com potencial excesso
        
        Returns:
            Detalhes do roteamento
        """
        excess = slot.get_excess()
        
        if excess <= 0:
            return {
                "routed": False,
                "reason": "Sem excesso para rotear",
                "excess": 0.0
            }
        
        # Busca próximo slot alvo
        target_slot = self.next_target_slot()
        
        if target_slot is None:
            # Todos slots capitalizados → vai para Tesouraria
            slot.capital_atual -= excess
            slot.total_lucro_enviado += excess
            self.treasury_balance += excess
            
            # Prometheus metrics
            treasury_profit_routing.labels(
                destination='treasury',
                slot_origin=slot.slot_id
            ).inc(excess)
            
            self._update_prometheus_metrics()
            
            logger.info(
                f"🏦 TESOURARIA | ${excess:.2f} de {slot.slot_id} → Treasury | "
                f"Balance=${self.treasury_balance:.2f}"
            )
            
            return {
                "routed": True,
                "destination": "TREASURY",
                "amount": excess,
                "treasury_balance": self.treasury_balance
            }
        
        else:
            # Roteia para próximo slot
            slot.capital_atual -= excess
            slot.total_lucro_enviado += excess
            
            target_slot.capital_atual += excess
            target_slot.total_lucro_recebido += excess
            
            # Prometheus metrics
            treasury_profit_routing.labels(
                destination=target_slot.slot_id,
                slot_origin=slot.slot_id
            ).inc(excess)
            
            # Atualiza status se atingiu VB
            if target_slot.is_capitalized() and target_slot.status == "BOOTSTRAP":
                target_slot.status = "OPERANDO"
                logger.info(
                    f"🚀 {target_slot.slot_id} CAPITALIZADO! | "
                    f"VB=${self.valor_base} atingido | Status: OPERANDO"
                )
            
            self._update_prometheus_metrics()
            
            logger.info(
                f"💸 CASCATA | ${excess:.2f} | {slot.slot_id} → {target_slot.slot_id} | "
                f"Novo capital: ${target_slot.capital_atual:.2f}"
            )
            
            return {
                "routed": True,
                "destination": target_slot.slot_id,
                "amount": excess,
                "target_capital_after": target_slot.capital_atual,
                "target_capitalized": target_slot.is_capitalized()
            }
    
    def _get_slot(self, slot_id: str) -> Optional[SlotState]:
        """Retorna slot pelo ID"""
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot
        return None
    
    def get_slot_state(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Retorna estado de um slot"""
        slot = self._get_slot(slot_id)
        return slot.to_dict() if slot else None
    
    def get_all_slots_state(self) -> List[Dict[str, Any]]:
        """Retorna estado de todos os slots"""
        return [slot.to_dict() for slot in self.slots]
    
    def get_cascade_status(self) -> Dict[str, Any]:
        """Retorna status geral da cascata"""
        capitalized_slots = [s for s in self.slots if s.is_capitalized()]
        operating_slots = [s for s in self.slots if s.status == "OPERANDO"]
        bootstrap_slots = [s for s in self.slots if s.status == "BOOTSTRAP"]
        
        next_target = self.next_target_slot()
        
        total_capital = sum(s.capital_atual for s in self.slots)
        total_vb = len(self.slots) * self.valor_base
        
        return {
            "valor_base": self.valor_base,
            "total_slots": len(self.slots),
            "capitalized_count": len(capitalized_slots),
            "operating_count": len(operating_slots),
            "bootstrap_count": len(bootstrap_slots),
            "next_target_slot": next_target.slot_id if next_target else None,
            "treasury_balance": self.treasury_balance,
            "total_capital_deployed": total_capital,
            "total_valor_base": total_vb,
            "cascade_completion_pct": (len(capitalized_slots) / len(self.slots)) * 100,
            "slots": self.get_all_slots_state()
        }
    
    def get_settlement_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna histórico de settlements"""
        return self.settlement_history[-limit:]
    
    def force_sweep_all_slots(self) -> Dict[str, Any]:
        """
        Força varredura de todos os slots (útil para manutenção)
        
        Returns:
            Resultados da varredura
        """
        results = []
        
        for slot in self.slots:
            if slot.get_excess() > 0:
                result = self._route_excess(slot)
                results.append({
                    "slot_id": slot.slot_id,
                    "routing": result
                })
        
        logger.info(f"🧹 Varredura forçada | {len(results)} slots com excesso roteado")
        
        return {
            "swept_slots": len(results),
            "results": results
        }


# Instância global
treasury_router = TreasuryRouter(valor_base=1000.0)

# ===== ASYNC WRAPPER FOR ORCHESTRATOR =====
import asyncio

_settlement_lock = asyncio.Lock()


async def settle_and_route(
    slot_id: str,
    net_pnl: float,
    settlement_id: str,
    trade_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Async wrapper for settle_trade with idempotency and locking
    
    This function is called from the continuous orchestrator after trade execution.
    Ensures thread-safe settlement and cascade routing.
    
    Args:
        slot_id: Slot identifier
        net_pnl: Net profit/loss after fees
        settlement_id: Unique settlement ID (for idempotency)
        trade_details: Optional trade details
    
    Returns:
        Settlement result dictionary
    """
    async with _settlement_lock:
        # Call synchronous settle_trade
        result = treasury_router.settle_trade(
            slot_id=slot_id,
            net_pnl=net_pnl,
            settlement_id=settlement_id,
            trade_details=trade_details
        )
        
        return result
