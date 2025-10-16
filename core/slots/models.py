# core/slots/models.py
"""Slot data models for trading operations"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class SlotMode(str, Enum):
    """Slot execution modes"""
    SHADOW = "shadow"  # Log decisions, no execution
    PAPER = "paper"    # Simulate execution with real data
    LIVE = "live"      # Execute real orders (Phase 3+)


class TradeAction(str, Enum):
    """Available trading actions"""
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    HOLD = "hold"
    ADJUST_SL = "adjust_sl"
    ADJUST_TP = "adjust_tp"


class SlotStatus(str, Enum):
    """Slot operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    BLOCKED = "blocked"


class TradeDecision:
    """Represents a trading decision made by an agent"""
    
    def __init__(
        self,
        agent_id: str,
        slot_id: str,
        symbol: str,
        action: TradeAction,
        confidence: float,
        mode: SlotMode,
        reason: str = "",
        size: float = 0.0,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.slot_id = slot_id
        self.symbol = symbol
        self.action = action
        self.confidence = confidence
        self.mode = mode
        self.reason = reason
        self.size = size
        self.price = price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
        self.execution_time_ms = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            "agent_id": self.agent_id,
            "slot_id": self.slot_id,
            "symbol": self.symbol,
            "action": self.action.value,
            "confidence": self.confidence,
            "mode": self.mode.value,
            "reason": self.reason,
            "size": self.size,
            "price": self.price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms
        }


class SlotPosition:
    """Represents an open position in a slot"""
    
    def __init__(
        self,
        slot_id: str,
        symbol: str,
        side: str,  # "long" or "short"
        size: float,
        entry_price: float,
        current_price: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        unrealized_pnl: float = 0.0
    ):
        self.slot_id = slot_id
        self.symbol = symbol
        self.side = side
        self.size = size
        self.entry_price = entry_price
        self.current_price = current_price or entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.unrealized_pnl = unrealized_pnl
        self.opened_at = datetime.now(timezone.utc)
    
    def update_pnl(self, current_price: float):
        """Update unrealized PnL based on current price"""
        self.current_price = current_price
        
        if self.side == "long":
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:  # short
            self.unrealized_pnl = (self.entry_price - current_price) * self.size
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "slot_id": self.slot_id,
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "unrealized_pnl": self.unrealized_pnl,
            "opened_at": self.opened_at.isoformat()
        }


class SlotMetrics:
    """Metrics for a slot's performance"""
    
    def __init__(self, slot_id: str):
        self.slot_id = slot_id
        self.total_decisions = 0
        self.executed_trades = 0
        self.positions_open = 0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.drawdown_pct = 0.0
        self.win_rate = 0.0
        self.avg_decision_latency_ms = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "slot_id": self.slot_id,
            "total_decisions": self.total_decisions,
            "executed_trades": self.executed_trades,
            "positions_open": self.positions_open,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "drawdown_pct": self.drawdown_pct,
            "win_rate": self.win_rate,
            "avg_decision_latency_ms": self.avg_decision_latency_ms
        }


class PaperTrade:
    """Represents a paper trade from consensus - Phase 3"""
    
    def __init__(
        self,
        consensus_id: str,
        agent_ids: List[str],
        action: str,
        symbol: str,
        notional_usdt: float,
        tp_pct: float,
        sl_pct: float,
        entry_price: float = 0.0,
        mode: str = "paper"
    ):
        self.paper_id = consensus_id  # Use consensus_id as paper trade ID
        self.consensus_id = consensus_id
        self.agent_ids = agent_ids
        self.action = action
        self.symbol = symbol
        self.notional_usdt = notional_usdt
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.entry_price = entry_price
        self.current_price = entry_price
        self.mode = mode
        self.status = "open"  # open | closed
        self.opened_at = datetime.now(timezone.utc)
        self.closed_at = None
        self.close_reason = None
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
    
    def update_price(self, current_price: float):
        """Update current price and unrealized PnL"""
        self.current_price = current_price
        
        if self.entry_price > 0:
            price_change = (current_price - self.entry_price) / self.entry_price
            
            if self.action == "open_long":
                self.unrealized_pnl = self.notional_usdt * price_change
            elif self.action == "open_short":
                self.unrealized_pnl = self.notional_usdt * (-price_change)
    
    def close(self, close_price: float, reason: str = "manual"):
        """Close the paper trade"""
        self.status = "closed"
        self.closed_at = datetime.now(timezone.utc)
        self.close_reason = reason
        self.current_price = close_price
        self.update_price(close_price)
        self.realized_pnl = self.unrealized_pnl
    
    def check_sl_tp(self, current_price: float) -> Optional[str]:
        """Check if SL or TP is hit"""
        if self.entry_price <= 0:
            return None
        
        price_change_pct = abs((current_price - self.entry_price) / self.entry_price)
        
        # Check stop loss
        if price_change_pct >= (self.sl_pct / 100):
            if (self.action == "open_long" and current_price < self.entry_price) or \
               (self.action == "open_short" and current_price > self.entry_price):
                return "stop_loss"
        
        # Check take profit
        if price_change_pct >= (self.tp_pct / 100):
            if (self.action == "open_long" and current_price > self.entry_price) or \
               (self.action == "open_short" and current_price < self.entry_price):
                return "take_profit"
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "paper_id": self.paper_id,
            "consensus_id": self.consensus_id,
            "agent_ids": self.agent_ids,
            "action": self.action,
            "symbol": self.symbol,
            "notional_usdt": self.notional_usdt,
            "tp_pct": self.tp_pct,
            "sl_pct": self.sl_pct,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "mode": self.mode,
            "status": self.status,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "close_reason": self.close_reason,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl
        }
