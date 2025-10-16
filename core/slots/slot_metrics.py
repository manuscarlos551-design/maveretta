# core/slots/slot_metrics.py
"""
Sistema de métricas Prometheus para slots de trading
Métricas de cascata, alocação e performance
"""

from prometheus_client import Counter, Gauge, Histogram
from typing import Optional
import time

# ===== MÉTRICAS DOS SLOTS =====

# Status do slot
bot_slot_status = Gauge(
    'bot_slot_status',
    'Slot status (1=active, 0.5=paused, 0=stopped)',
    ['slot_id', 'exchange', 'strategy', 'cascade_level']
)

# Alocação em USD
bot_slot_allocation_usd = Gauge(
    'bot_slot_allocation_usd',
    'Capital allocated to slot in USD',
    ['slot_id', 'exchange', 'strategy']
)

# P&L do slot
bot_slot_pnl_usd = Gauge(
    'bot_slot_pnl_usd',
    'Slot profit/loss in USD',
    ['slot_id', 'exchange', 'strategy']
)

bot_slot_pnl_pct = Gauge(
    'bot_slot_pnl_pct',
    'Slot profit/loss in percentage',
    ['slot_id', 'exchange', 'strategy']
)

# Total de trades do slot
bot_slot_trades_total = Counter(
    'bot_slot_trades_total',
    'Total number of trades executed by slot',
    ['slot_id', 'exchange', 'strategy', 'side']
)

# Win rate do slot
bot_slot_win_rate = Gauge(
    'bot_slot_win_rate',
    'Slot win rate (0-1)',
    ['slot_id', 'exchange', 'strategy']
)

# Nível de cascata
bot_cascade_level = Gauge(
    'bot_cascade_level',
    'Current cascade level of slot (0=base, 1=first, etc)',
    ['slot_id']
)

# Transferências de cascata
bot_cascade_transfers_total = Counter(
    'bot_cascade_transfers_total',
    'Total cascade transfers',
    ['from_slot', 'to_slot', 'reason']
)

# Valor transferido em cascata
bot_cascade_transfer_amount_usd = Histogram(
    'bot_cascade_transfer_amount_usd',
    'Amount transferred in cascade (USD)',
    ['from_slot', 'to_slot'],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
)

# Equity total nos slots
bot_slots_equity_total_usd = Gauge(
    'bot_slots_equity_total_usd',
    'Total equity across all slots in USD'
)

# Número de slots ativos
bot_slots_active_count = Gauge(
    'bot_slots_active_count',
    'Number of active slots'
)

# Drawdown do slot
bot_slot_drawdown_pct = Gauge(
    'bot_slot_drawdown_pct',
    'Current drawdown of slot in percentage',
    ['slot_id', 'exchange']
)

# Sharpe ratio do slot
bot_slot_sharpe_ratio = Gauge(
    'bot_slot_sharpe_ratio',
    'Sharpe ratio of slot',
    ['slot_id', 'exchange', 'strategy']
)

# Duração média dos trades
bot_slot_trade_duration_seconds = Histogram(
    'bot_slot_trade_duration_seconds',
    'Average trade duration',
    ['slot_id', 'exchange'],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400, 28800]  # 1min to 8h
)


class SlotMetrics:
    """
    Wrapper de métricas para um slot específico
    """
    
    def __init__(self, slot_id: str, exchange: str, strategy: str, cascade_level: int = 0):
        self.slot_id = slot_id
        self.exchange = exchange
        self.strategy = strategy
        self.cascade_level = cascade_level
        
        # Define status inicial
        self.set_active()
        
        # Define nível de cascata
        bot_cascade_level.labels(slot_id=slot_id).set(cascade_level)
    
    def set_active(self):
        """Marca slot como ativo"""
        bot_slot_status.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy,
            cascade_level=str(self.cascade_level)
        ).set(1)
    
    def set_paused(self):
        """Marca slot como pausado"""
        bot_slot_status.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy,
            cascade_level=str(self.cascade_level)
        ).set(0.5)
    
    def set_stopped(self):
        """Marca slot como parado"""
        bot_slot_status.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy,
            cascade_level=str(self.cascade_level)
        ).set(0)
    
    def update_allocation(self, amount_usd: float):
        """Atualiza alocação do slot"""
        bot_slot_allocation_usd.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy
        ).set(amount_usd)
    
    def update_pnl(self, pnl_usd: float, pnl_pct: float):
        """Atualiza P&L do slot"""
        bot_slot_pnl_usd.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy
        ).set(pnl_usd)
        
        bot_slot_pnl_pct.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy
        ).set(pnl_pct)
    
    def record_trade(self, side: str):
        """
        Registra um trade executado
        
        Args:
            side: 'buy' ou 'sell'
        """
        bot_slot_trades_total.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy,
            side=side.lower()
        ).inc()
    
    def update_win_rate(self, win_rate: float):
        """Atualiza win rate (0-1)"""
        bot_slot_win_rate.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy
        ).set(win_rate)
    
    def update_drawdown(self, drawdown_pct: float):
        """Atualiza drawdown em percentual"""
        bot_slot_drawdown_pct.labels(
            slot_id=self.slot_id,
            exchange=self.exchange
        ).set(drawdown_pct)
    
    def update_sharpe_ratio(self, sharpe: float):
        """Atualiza Sharpe ratio"""
        bot_slot_sharpe_ratio.labels(
            slot_id=self.slot_id,
            exchange=self.exchange,
            strategy=self.strategy
        ).set(sharpe)
    
    def record_trade_duration(self, duration_seconds: float):
        """Registra duração de um trade"""
        bot_slot_trade_duration_seconds.labels(
            slot_id=self.slot_id,
            exchange=self.exchange
        ).observe(duration_seconds)
    
    def update_cascade_level(self, level: int):
        """Atualiza nível de cascata"""
        self.cascade_level = level
        bot_cascade_level.labels(slot_id=self.slot_id).set(level)


def record_cascade_transfer(from_slot: str, to_slot: str, amount_usd: float, reason: str):
    """
    Registra uma transferência de cascata entre slots
    
    Args:
        from_slot: ID do slot de origem
        to_slot: ID do slot de destino
        amount_usd: Valor transferido em USD
        reason: Motivo da transferência ('profit', 'loss', 'rebalance', etc)
    """
    bot_cascade_transfers_total.labels(
        from_slot=from_slot,
        to_slot=to_slot,
        reason=reason
    ).inc()
    
    bot_cascade_transfer_amount_usd.labels(
        from_slot=from_slot,
        to_slot=to_slot
    ).observe(amount_usd)


def update_global_slot_metrics(total_equity_usd: float, active_count: int):
    """
    Atualiza métricas globais dos slots
    
    Args:
        total_equity_usd: Equity total de todos os slots
        active_count: Número de slots ativos
    """
    bot_slots_equity_total_usd.set(total_equity_usd)
    bot_slots_active_count.set(active_count)


# ===== EXEMPLO DE USO =====
"""
# No gerenciador de slots:

from core.slots.slot_metrics import SlotMetrics, record_cascade_transfer, update_global_slot_metrics

class SlotManager:
    def __init__(self):
        self.slots = {}
    
    def create_slot(self, slot_id, exchange, strategy, cascade_level=0):
        # Criar slot com métricas
        slot_metrics = SlotMetrics(
            slot_id=slot_id,
            exchange=exchange,
            strategy=strategy,
            cascade_level=cascade_level
        )
        
        self.slots[slot_id] = {
            'metrics': slot_metrics,
            'data': {...}
        }
        
        return slot_metrics
    
    def execute_trade(self, slot_id, side, amount):
        slot = self.slots[slot_id]
        
        # Executar trade
        result = self._do_trade(side, amount)
        
        # Registrar nas métricas
        slot['metrics'].record_trade(side)
        
        # Atualizar P&L
        new_pnl_usd = self._calculate_pnl_usd(slot_id)
        new_pnl_pct = self._calculate_pnl_pct(slot_id)
        slot['metrics'].update_pnl(new_pnl_usd, new_pnl_pct)
        
        return result
    
    def trigger_cascade(self, from_slot_id, to_slot_id, amount, reason):
        # Transferir capital
        self._transfer_capital(from_slot_id, to_slot_id, amount)
        
        # Registrar nas métricas
        record_cascade_transfer(
            from_slot=from_slot_id,
            to_slot=to_slot_id,
            amount_usd=amount,
            reason=reason
        )
        
        # Atualizar níveis de cascata
        self.slots[to_slot_id]['metrics'].update_cascade_level(
            self.slots[from_slot_id]['metrics'].cascade_level + 1
        )
    
    def update_global_metrics(self):
        total_equity = sum(slot['equity'] for slot in self.slots.values())
        active_count = sum(1 for slot in self.slots.values() if slot['status'] == 'active')
        
        update_global_slot_metrics(total_equity, active_count)
"""
