# core/slots/cascade_manager.py
"""
Sistema de Alocação em Cascata
Gerencia a alocação progressiva de capital em slots
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
from prometheus_client import Counter, Histogram, Gauge
import time

logger = logging.getLogger(__name__)

# === PROMETHEUS METRICS ===
cascade_transfers = Counter(
    'core_cascade_transfers_usd_total',
    'Total USD transferred between slots in cascade',
    ['from_slot', 'to_slot']
)

cascade_triggers = Counter(
    'core_cascade_trigger_total',
    'Cascade stage upgrade triggers by reason',
    ['slot', 'reason', 'stage']
)

cascade_latency = Histogram(
    'core_cascade_latency_ms',
    'Cascade decision and execution latency in milliseconds',
    ['slot', 'operation'],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2000)
)

slot_vb_status = Gauge(
    'core_slot_vb_status',
    'Slot VB capitalization status (0=bootstrap, 1=ready)',
    ['slot', 'exchange']
)

slot_capital_allocated = Gauge(
    'core_slot_capital_allocated_usd',
    'Currently allocated capital per slot in USD',
    ['slot', 'exchange', 'stage']
)

slot_profit_loss = Gauge(
    'core_slot_profit_loss_usd',
    'Cumulative profit/loss per slot in USD',
    ['slot', 'exchange']
)


class CascadeStage(str, Enum):
    """Estágios de uma cascata"""
    INITIAL = "initial"         # 10% do capital
    STAGE_1 = "stage_1"         # 20% do capital
    STAGE_2 = "stage_2"         # 30% do capital
    STAGE_3 = "stage_3"         # 40% do capital
    FULL = "full"               # 100% do capital


class CascadeSlot:
    """Representa um slot em cascata"""
    
    def __init__(
        self,
        slot_id: str,
        exchange: str,
        total_capital: float,
        strategy: str = "default"
    ):
        self.slot_id = slot_id
        self.exchange = exchange
        self.total_capital = total_capital
        self.strategy = strategy
        
        # Estado da cascata
        self.current_stage = CascadeStage.INITIAL
        self.allocated_capital = total_capital * 0.10  # Começa com 10%
        self.used_capital = 0.0
        self.profit_loss = 0.0
        
        # Histórico
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
        self.created_at = datetime.now(timezone.utc)
        
        # Thresholds para upgrade de estágio
        self.stage_thresholds = {
            CascadeStage.INITIAL: {"min_trades": 3, "min_win_rate": 0.6, "min_profit_pct": 5.0},
            CascadeStage.STAGE_1: {"min_trades": 5, "min_win_rate": 0.65, "min_profit_pct": 8.0},
            CascadeStage.STAGE_2: {"min_trades": 8, "min_win_rate": 0.7, "min_profit_pct": 12.0},
            CascadeStage.STAGE_3: {"min_trades": 12, "min_win_rate": 0.7, "min_profit_pct": 15.0},
        }
        
        logger.info(f"Cascade slot {slot_id} criado: ${total_capital:.2f} total, ${self.allocated_capital:.2f} inicial")
        
        # Atualizar métricas Prometheus
        slot_vb_status.labels(slot=slot_id, exchange=exchange).set(0)  # Bootstrap
        slot_capital_allocated.labels(
            slot=slot_id, 
            exchange=exchange, 
            stage=self.current_stage.value
        ).set(self.allocated_capital)
        slot_profit_loss.labels(slot=slot_id, exchange=exchange).set(0.0)
    
    def get_available_capital(self) -> float:
        """Retorna capital disponível para trading"""
        return self.allocated_capital - self.used_capital
    
    def record_trade(self, profit_loss: float):
        """Registra resultado de um trade"""
        start_time = time.time()
        
        self.trades_count += 1
        self.profit_loss += profit_loss
        
        if profit_loss > 0:
            self.wins += 1
        else:
            self.losses += 1
        
        # Atualizar métricas Prometheus
        slot_profit_loss.labels(slot=self.slot_id, exchange=self.exchange).set(self.profit_loss)
        
        latency_ms = (time.time() - start_time) * 1000
        cascade_latency.labels(slot=self.slot_id, operation='record_trade').observe(latency_ms)
        
        logger.debug(
            f"Trade registrado no slot {self.slot_id}: "
            f"P&L=${profit_loss:.2f}, Total=${self.profit_loss:.2f}"
        )
    
    def get_win_rate(self) -> float:
        """Calcula taxa de acerto"""
        if self.trades_count == 0:
            return 0.0
        return self.wins / self.trades_count
    
    def get_profit_pct(self) -> float:
        """Calcula percentual de lucro sobre capital alocado"""
        if self.allocated_capital == 0:
            return 0.0
        return (self.profit_loss / self.allocated_capital) * 100
    
    def can_upgrade_stage(self) -> bool:
        """Verifica se pode avançar de estágio"""
        if self.current_stage == CascadeStage.FULL:
            return False
        
        threshold = self.stage_thresholds.get(self.current_stage)
        if not threshold:
            return False
        
        win_rate = self.get_win_rate()
        profit_pct = self.get_profit_pct()
        
        meets_trades = self.trades_count >= threshold["min_trades"]
        meets_win_rate = win_rate >= threshold["min_win_rate"]
        meets_profit = profit_pct >= threshold["min_profit_pct"]
        
        return meets_trades and meets_win_rate and meets_profit
    
    def upgrade_stage(self) -> bool:
        """Avança para próximo estágio de alocação"""
        start_time = time.time()
        
        if not self.can_upgrade_stage():
            logger.warning(f"Slot {self.slot_id} não cumpre requisitos para upgrade")
            return False
        
        # Mapeamento de stages
        stage_progression = {
            CascadeStage.INITIAL: (CascadeStage.STAGE_1, 0.20),
            CascadeStage.STAGE_1: (CascadeStage.STAGE_2, 0.30),
            CascadeStage.STAGE_2: (CascadeStage.STAGE_3, 0.40),
            CascadeStage.STAGE_3: (CascadeStage.FULL, 1.00),
        }
        
        next_stage, allocation_pct = stage_progression[self.current_stage]
        old_stage = self.current_stage
        old_capital = self.allocated_capital
        
        self.current_stage = next_stage
        self.allocated_capital = self.total_capital * allocation_pct
        capital_added = self.allocated_capital - old_capital
        
        # Métricas Prometheus
        cascade_triggers.labels(
            slot=self.slot_id,
            reason='performance_upgrade',
            stage=next_stage.value
        ).inc()
        
        cascade_transfers.labels(
            from_slot='treasury',
            to_slot=self.slot_id
        ).inc(capital_added)
        
        slot_capital_allocated.labels(
            slot=self.slot_id,
            exchange=self.exchange,
            stage=next_stage.value
        ).set(self.allocated_capital)
        
        # VB status: se chegou em FULL, marca como ready
        if next_stage == CascadeStage.FULL:
            slot_vb_status.labels(slot=self.slot_id, exchange=self.exchange).set(1)
        
        latency_ms = (time.time() - start_time) * 1000
        cascade_latency.labels(slot=self.slot_id, operation='upgrade_stage').observe(latency_ms)
        
        logger.info(
            f"🚀 UPGRADE no slot {self.slot_id}: "
            f"{old_stage.value} → {next_stage.value} | "
            f"Capital: ${old_capital:.2f} → ${self.allocated_capital:.2f} "
            f"(Win rate: {self.get_win_rate():.1%}, Profit: {self.get_profit_pct():.1f}%)"
        )
        
        return True
    
    def should_downgrade(self) -> bool:
        """Verifica se deve rebaixar de estágio (performance ruim)"""
        if self.current_stage == CascadeStage.INITIAL:
            return False
        
        # Critérios de rebaixamento
        if self.trades_count < 5:
            return False
        
        win_rate = self.get_win_rate()
        profit_pct = self.get_profit_pct()
        
        # Rebaixar se win rate < 40% OU perda > 15%
        return win_rate < 0.40 or profit_pct < -15.0
    
    def downgrade_stage(self) -> bool:
        """Rebaixa para estágio anterior"""
        start_time = time.time()
        
        if self.current_stage == CascadeStage.INITIAL:
            logger.warning(f"Slot {self.slot_id} já está no estágio inicial")
            return False
        
        # Mapeamento de rebaixamento
        stage_regression = {
            CascadeStage.STAGE_1: (CascadeStage.INITIAL, 0.10),
            CascadeStage.STAGE_2: (CascadeStage.STAGE_1, 0.20),
            CascadeStage.STAGE_3: (CascadeStage.STAGE_2, 0.30),
            CascadeStage.FULL: (CascadeStage.STAGE_3, 0.40),
        }
        
        prev_stage, allocation_pct = stage_regression[self.current_stage]
        old_stage = self.current_stage
        old_capital = self.allocated_capital
        
        self.current_stage = prev_stage
        self.allocated_capital = self.total_capital * allocation_pct
        
        logger.warning(
            f"⚠️ DOWNGRADE no slot {self.slot_id}: "
            f"{old_stage.value} → {prev_stage.value} | "
            f"Capital: ${old_capital:.2f} → ${self.allocated_capital:.2f} "
            f"(Win rate: {self.get_win_rate():.1%}, Profit: {self.get_profit_pct():.1f}%)"
        )
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dict"""
        return {
            "slot_id": self.slot_id,
            "exchange": self.exchange,
            "strategy": self.strategy,
            "current_stage": self.current_stage.value,
            "total_capital": self.total_capital,
            "allocated_capital": self.allocated_capital,
            "used_capital": self.used_capital,
            "available_capital": self.get_available_capital(),
            "profit_loss": self.profit_loss,
            "profit_pct": self.get_profit_pct(),
            "trades_count": self.trades_count,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.get_win_rate(),
            "can_upgrade": self.can_upgrade_stage(),
            "should_downgrade": self.should_downgrade(),
            "created_at": self.created_at.isoformat()
        }


class CascadeManager:
    """Gerenciador global de cascatas de slots"""
    
    def __init__(self):
        self.slots: Dict[str, CascadeSlot] = {}
        logger.info("Cascade Manager inicializado")
    
    def create_slot(
        self,
        slot_id: str,
        exchange: str,
        total_capital: float,
        strategy: str = "default"
    ) -> bool:
        """Cria um novo slot em cascata"""
        if slot_id in self.slots:
            logger.warning(f"Slot {slot_id} já existe")
            return False
        
        self.slots[slot_id] = CascadeSlot(slot_id, exchange, total_capital, strategy)
        logger.info(f"Slot em cascata criado: {slot_id}")
        return True
    
    def get_slot(self, slot_id: str) -> Optional[CascadeSlot]:
        """Retorna um slot"""
        return self.slots.get(slot_id)
    
    def record_trade_result(
        self,
        slot_id: str,
        profit_loss: float
    ) -> bool:
        """Registra resultado de trade e avalia upgrades/downgrades"""
        slot = self.get_slot(slot_id)
        if not slot:
            logger.error(f"Slot {slot_id} não encontrado")
            return False
        
        # Registrar trade
        slot.record_trade(profit_loss)
        
        # Avaliar upgrade
        if slot.can_upgrade_stage():
            slot.upgrade_stage()
        
        # Avaliar downgrade
        elif slot.should_downgrade():
            slot.downgrade_stage()
        
        return True
    
    def get_all_slots(self) -> List[Dict[str, Any]]:
        """Retorna todos os slots serializados"""
        return [slot.to_dict() for slot in self.slots.values()]
    
    def get_total_allocated_capital(self) -> float:
        """Retorna capital total alocado em todos os slots"""
        return sum(slot.allocated_capital for slot in self.slots.values())
    
    def get_total_profit_loss(self) -> float:
        """Retorna P&L total de todos os slots"""
        return sum(slot.profit_loss for slot in self.slots.values())
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas globais"""
        total_trades = sum(slot.trades_count for slot in self.slots.values())
        total_wins = sum(slot.wins for slot in self.slots.values())
        
        return {
            "total_slots": len(self.slots),
            "active_slots": len([s for s in self.slots.values() if s.get_available_capital() > 0]),
            "total_capital": sum(slot.total_capital for slot in self.slots.values()),
            "allocated_capital": self.get_total_allocated_capital(),
            "total_profit_loss": self.get_total_profit_loss(),
            "total_trades": total_trades,
            "global_win_rate": total_wins / total_trades if total_trades > 0 else 0.0,
            "slots_by_stage": self._count_slots_by_stage()
        }
    
    def _count_slots_by_stage(self) -> Dict[str, int]:
        """Conta slots por estágio"""
        counts = {stage.value: 0 for stage in CascadeStage}
        for slot in self.slots.values():
            counts[slot.current_stage.value] += 1
        return counts


# Instância global
cascade_manager = CascadeManager()
