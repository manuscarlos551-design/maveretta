# core/orchestrator/metrics.py
"""Prometheus Metrics for Agent Orchestration - Phase 4"""

import logging
from prometheus_client import Gauge, Counter, Histogram

logger = logging.getLogger(__name__)

# ========== PHASE 1 METRICS (PRESERVED) ==========

# Agent mode (one-hot encoding)
agent_mode_metric = Gauge(
    'agent_mode',
    'Current execution mode of agent (1=active, 0=inactive)',
    ['agent_id', 'mode']
)

# Agent heartbeat
agent_heartbeat_metric = Gauge(
    'agent_heartbeat_ts',
    'Timestamp of last heartbeat from agent',
    ['agent_id']
)

# Agent running status
agent_running_metric = Gauge(
    'agent_running',
    'Whether agent is running (1) or stopped (0)',
    ['agent_id']
)


# ========== PHASE 2 METRICS (PRESERVED) ==========

# Decision counters
agent_decisions_total = Counter(
    'agent_decisions_total',
    'Total number of decisions made by agent',
    ['agent_id', 'action', 'symbol', 'mode']
)

# Decision latency
agent_decision_latency_ms = Histogram(
    'agent_decision_latency_ms',
    'Decision processing latency in milliseconds',
    ['agent_id'],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
)

# Risk blocked counter
agent_risk_blocked_total = Counter(
    'agent_risk_blocked_total',
    'Total number of decisions blocked by risk management',
    ['agent_id', 'reason']
)

# Open positions
agent_positions_open = Gauge(
    'agent_positions_open',
    'Number of currently open positions',
    ['agent_id']
)

# Realized PnL
agent_pnl_realized = Gauge(
    'agent_pnl_realized',
    'Realized profit and loss in quote currency',
    ['agent_id', 'quote']
)

# Drawdown percentage
agent_drawdown_pct = Gauge(
    'agent_drawdown_pct',
    'Current drawdown percentage',
    ['agent_id']
)

# Dialog counter
agent_dialogs_total = Counter(
    'agent_dialogs_total',
    'Total number of dialogs between agents',
    ['from_agent', 'to_agent']
)


# ========== PHASE 3 METRICS (PRESERVED) ==========

# Consensus rounds counter
agent_consensus_rounds_total = Counter(
    'agent_consensus_rounds_total',
    'Total number of consensus rounds',
    ['symbol']
)

# Alias for backward compatibility
consensus_rounds_total = agent_consensus_rounds_total

# Consensus approved counter
agent_consensus_approved_total = Counter(
    'agent_consensus_approved_total',
    'Total number of approved consensus decisions',
    ['symbol', 'action']
)

# Consensus average confidence
agent_consensus_confidence_avg = Gauge(
    'agent_consensus_confidence_avg',
    'Average confidence of consensus decisions',
    ['symbol']
)

# Paper trades opened
paper_trades_opened_total = Counter(
    'paper_trades_opened_total',
    'Total number of paper trades opened',
    ['symbol', 'action']
)

# Paper trades closed
paper_trades_closed_total = Counter(
    'paper_trades_closed_total',
    'Total number of paper trades closed',
    ['symbol', 'reason']
)

# Paper trades unrealized PnL
paper_trades_pnl_unrealized = Gauge(
    'paper_trades_pnl_unrealized',
    'Unrealized PnL of open paper trades',
    ['symbol']
)


# ========== PHASE 4 METRICS (NEW) ==========

# Dialog messages counter
agent_dialog_messages_total = Counter(
    'agent_dialog_messages_total',
    'Total number of dialog messages sent by agent in each phase',
    ['agent_id', 'phase']
)

# Consensus rationale length (average)
agent_consensus_rationale_length_avg = Gauge(
    'agent_consensus_rationale_length_avg',
    'Average length of consensus rationale in characters',
    ['symbol']
)

# Consensus confidence histogram
agent_consensus_confidence_histogram = Histogram(
    'agent_consensus_confidence_histogram',
    'Distribution of consensus confidence values',
    ['symbol'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Dynamic risk blocked counter
agent_risk_dynamic_blocked_total = Counter(
    'agent_risk_dynamic_blocked_total',
    'Total number of consensus decisions blocked by dynamic risk management',
    ['agent_id', 'reason']
)

# Dynamic risk adjusted notional
agent_risk_adjusted_notional = Gauge(
    'agent_risk_adjusted_notional',
    'Adjusted notional position size after dynamic risk evaluation',
    ['agent_id', 'symbol']
)


# ========== METRIC UPDATE FUNCTIONS ==========

def register_agent_metrics():
    """Register agent metrics with Prometheus"""
    logger.info("Agent orchestration metrics registered with Prometheus (Phase 4)")


# Phase 1 functions (preserved)
def update_agent_mode(agent_id: str, mode: str):
    """Update agent mode metric"""
    for m in ['shadow', 'paper', 'live']:
        value = 1 if m == mode else 0
        agent_mode_metric.labels(agent_id=agent_id, mode=m).set(value)


def update_agent_heartbeat(agent_id: str, timestamp: float):
    """Update agent heartbeat timestamp"""
    agent_heartbeat_metric.labels(agent_id=agent_id).set(timestamp)


def update_agent_running(agent_id: str, is_running: bool):
    """Update agent running status"""
    agent_running_metric.labels(agent_id=agent_id).set(1 if is_running else 0)


# Phase 2 functions (preserved)
def increment_agent_decision(agent_id: str, action: str, symbol: str, mode: str):
    """Increment decision counter"""
    agent_decisions_total.labels(
        agent_id=agent_id,
        action=action,
        symbol=symbol,
        mode=mode
    ).inc()


def observe_decision_latency(agent_id: str, latency_ms: float):
    """Record decision latency"""
    agent_decision_latency_ms.labels(agent_id=agent_id).observe(latency_ms)


def increment_risk_blocked(agent_id: str, reason: str):
    """Increment risk blocked counter"""
    agent_risk_blocked_total.labels(agent_id=agent_id, reason=reason).inc()


def update_positions_open(agent_id: str, count: int):
    """Update open positions count"""
    agent_positions_open.labels(agent_id=agent_id).set(count)


def update_realized_pnl(agent_id: str, pnl: float, quote: str = "USDT"):
    """Update realized PnL"""
    agent_pnl_realized.labels(agent_id=agent_id, quote=quote).set(pnl)


def update_drawdown(agent_id: str, drawdown_pct: float):
    """Update drawdown percentage"""
    agent_drawdown_pct.labels(agent_id=agent_id).set(drawdown_pct)


def increment_dialog(from_agent: str, to_agent: str):
    """Increment dialog counter"""
    agent_dialogs_total.labels(from_agent=from_agent, to_agent=to_agent).inc()


# Phase 3 functions (preserved)
def increment_consensus_round(symbol: str):
    """Increment consensus round counter"""
    agent_consensus_rounds_total.labels(symbol=symbol).inc()


def increment_consensus_approved(symbol: str, action: str):
    """Increment approved consensus counter"""
    agent_consensus_approved_total.labels(symbol=symbol, action=action).inc()


def update_consensus_confidence(symbol: str, confidence: float):
    """Update consensus confidence gauge"""
    agent_consensus_confidence_avg.labels(symbol=symbol).set(confidence)


def increment_paper_trade_opened(symbol: str, action: str):
    """Increment paper trade opened counter"""
    paper_trades_opened_total.labels(symbol=symbol, action=action).inc()


def increment_paper_trade_closed(symbol: str, reason: str):
    """Increment paper trade closed counter"""
    paper_trades_closed_total.labels(symbol=symbol, reason=reason).inc()


def update_paper_pnl_unrealized(symbol: str, pnl: float):
    """Update paper trade unrealized PnL"""
    paper_trades_pnl_unrealized.labels(symbol=symbol).set(pnl)


# ========== CONTINUOUS ORCHESTRATION METRICS (NEW) ==========

# Agent tick counter
agent_ticks_total = Counter(
    'agent_ticks_total',
    'Total ticks processed by agent',
    ['agent']
)

# Agent errors
agent_errors_total = Counter(
    'agent_errors_total',
    'Total errors encountered by agent',
    ['agent', 'error_type']
)

# Core trades executed
core_trades_executed_total = Counter(
    'core_trades_executed_total',
    'Total trades executed by slot and exchange',
    ['slot', 'exchange', 'action']
)

# Treasury cascade events
treasury_cascade_events_total = Counter(
    'core_cascade_transfers_usd_total',
    'USD transferred in cascade between slots',
    ['from_slot', 'to_slot']
)


# Phase 4 functions (new)
def increment_dialog_message(agent_id: str, phase: str):
    """Increment dialog message counter
    
    Args:
        agent_id: Agent identifier
        phase: Dialog phase (propose, challenge, decide)
    """
    agent_dialog_messages_total.labels(agent_id=agent_id, phase=phase).inc()


def update_rationale_length(symbol: str, length: int):
    """Update average rationale length
    
    Args:
        symbol: Trading symbol
        length: Length of rationale in characters
    """
    agent_consensus_rationale_length_avg.labels(symbol=symbol).set(length)


def observe_consensus_confidence(symbol: str, confidence: float):
    """Record consensus confidence in histogram
    
    Args:
        symbol: Trading symbol
        confidence: Confidence value (0.0-1.0)
    """
    agent_consensus_confidence_histogram.labels(symbol=symbol).observe(confidence)


def increment_risk_dynamic_blocked(agent_id: str, reason: str):
    """Increment dynamic risk blocked counter
    
    Args:
        agent_id: Agent identifier
        reason: Reason for blocking (high_volatility, high_drawdown, etc.)
    """
    agent_risk_dynamic_blocked_total.labels(agent_id=agent_id, reason=reason).inc()


def update_adjusted_notional(agent_id: str, symbol: str, notional: float):
    """Update adjusted notional position size
    
    Args:
        agent_id: Agent identifier
        symbol: Trading symbol
        notional: Adjusted notional in USDT
    """
    agent_risk_adjusted_notional.labels(agent_id=agent_id, symbol=symbol).set(notional)
