# core/slots/manager.py
"""Slot Manager - Manages trading slots and positions"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import threading

from .models import (
    SlotMode, TradeAction, SlotStatus, TradeDecision,
    SlotPosition, SlotMetrics, PaperTrade
)

logger = logging.getLogger(__name__)


class SlotManager:
    """Manages all trading slots and their state"""
    
    def __init__(self):
        self.slots: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, List[SlotPosition]] = {}  # slot_id -> positions
        self.metrics: Dict[str, SlotMetrics] = {}  # slot_id -> metrics
        self.paper_trades: Dict[str, PaperTrade] = {}  # paper_id -> PaperTrade (Phase 3)
        self._lock = threading.Lock()
        
        # Initialize demo slots for phase 2
        self._initialize_demo_slots()
        
        logger.info("Slot Manager initialized (Phase 3 with paper trades)")
    
    def _initialize_demo_slots(self):
        """Initialize demo slots for testing"""
        demo_slots = [
            {"slot_id": "slot_1", "exchange": "binance", "status": SlotStatus.ACTIVE, "capital_base": 1000.0},
            {"slot_id": "slot_2", "exchange": "binance", "status": SlotStatus.ACTIVE, "capital_base": 1500.0},
            {"slot_id": "slot_3", "exchange": "kucoin", "status": SlotStatus.INACTIVE, "capital_base": 2000.0},
            {"slot_id": "slot_4", "exchange": "bybit", "status": SlotStatus.ACTIVE, "capital_base": 1200.0},
        ]
        
        for slot_data in demo_slots:
            slot_id = slot_data["slot_id"]
            self.slots[slot_id] = {
                "slot_id": slot_id,
                "exchange": slot_data["exchange"],
                "status": slot_data["status"],
                "capital_base": slot_data["capital_base"],
                "capital_current": slot_data["capital_base"],
                "assigned_agent": None,
                "strategy": "default",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self.positions[slot_id] = []
            self.metrics[slot_id] = SlotMetrics(slot_id)
        
        logger.info(f"Initialized {len(self.slots)} demo slots")
    
    def register_slot(
        self,
        slot_id: str,
        exchange: str,
        capital_base: float,
        status: SlotStatus = SlotStatus.ACTIVE
    ) -> bool:
        """Register a new slot"""
        with self._lock:
            if slot_id in self.slots:
                logger.warning(f"Slot {slot_id} already registered")
                return False
            
            self.slots[slot_id] = {
                "slot_id": slot_id,
                "exchange": exchange,
                "status": status,
                "capital_base": capital_base,
                "capital_current": capital_base,
                "assigned_agent": None,
                "strategy": "default",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self.positions[slot_id] = []
            self.metrics[slot_id] = SlotMetrics(slot_id)
            
            logger.info(f"Registered slot {slot_id} on {exchange}")
            return True
    
    def assign_agent_to_slot(self, slot_id: str, agent_id: str) -> bool:
        """Assign an agent to a slot"""
        with self._lock:
            if slot_id not in self.slots:
                logger.error(f"Slot {slot_id} not found")
                return False
            
            self.slots[slot_id]["assigned_agent"] = agent_id
            logger.info(f"Assigned agent {agent_id} to slot {slot_id}")
            return True
    
    def get_slot(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Get slot information"""
        with self._lock:
            return self.slots.get(slot_id)
    
    def get_all_slots(self) -> Dict[str, Dict[str, Any]]:
        """Get all slots"""
        with self._lock:
            return dict(self.slots)
    
    def get_active_slots(self) -> List[str]:
        """Get list of active slot IDs"""
        with self._lock:
            return [
                slot_id for slot_id, slot in self.slots.items()
                if slot["status"] == SlotStatus.ACTIVE
            ]
    
    def get_positions(self, slot_id: str) -> List[SlotPosition]:
        """Get all positions for a slot"""
        with self._lock:
            return self.positions.get(slot_id, [])
    
    def open_position(
        self,
        slot_id: str,
        symbol: str,
        side: str,
        size: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        """Open a new position (paper mode)"""
        with self._lock:
            if slot_id not in self.slots:
                logger.error(f"Slot {slot_id} not found")
                return False
            
            # Create position
            position = SlotPosition(
                slot_id=slot_id,
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            self.positions[slot_id].append(position)
            self.metrics[slot_id].positions_open += 1
            
            logger.info(
                f"Opened {side} position in slot {slot_id}: "
                f"{size} {symbol} @ {entry_price}"
            )
            return True
    
    def close_position(
        self,
        slot_id: str,
        symbol: str,
        close_price: float
    ) -> bool:
        """Close a position (paper mode)"""
        with self._lock:
            if slot_id not in self.positions:
                logger.error(f"No positions for slot {slot_id}")
                return False
            
            # Find position to close
            positions = self.positions[slot_id]
            for i, pos in enumerate(positions):
                if pos.symbol == symbol:
                    # Calculate realized PnL
                    pos.update_pnl(close_price)
                    realized_pnl = pos.unrealized_pnl
                    
                    # Update slot capital
                    self.slots[slot_id]["capital_current"] += realized_pnl
                    
                    # Update metrics
                    self.metrics[slot_id].realized_pnl += realized_pnl
                    self.metrics[slot_id].positions_open -= 1
                    self.metrics[slot_id].executed_trades += 1
                    
                    # Remove position
                    positions.pop(i)
                    
                    logger.info(
                        f"Closed position in slot {slot_id}: "
                        f"{symbol} @ {close_price}, PnL: {realized_pnl:.2f}"
                    )
                    return True
            
            logger.warning(f"Position {symbol} not found in slot {slot_id}")
            return False
    
    def update_position_prices(self, slot_id: str, price_data: Dict[str, float]):
        """Update current prices for positions"""
        with self._lock:
            if slot_id not in self.positions:
                return
            
            for position in self.positions[slot_id]:
                if position.symbol in price_data:
                    position.update_pnl(price_data[position.symbol])
    
    def get_metrics(self, slot_id: str) -> Optional[SlotMetrics]:
        """Get metrics for a slot"""
        with self._lock:
            return self.metrics.get(slot_id)
    
    def get_all_metrics(self) -> Dict[str, SlotMetrics]:
        """Get metrics for all slots"""
        with self._lock:
            return dict(self.metrics)
    
    def update_slot_status(self, slot_id: str, status: SlotStatus) -> bool:
        """Update slot status"""
        with self._lock:
            if slot_id not in self.slots:
                return False
            
            self.slots[slot_id]["status"] = status
            logger.info(f"Slot {slot_id} status updated to {status}")
            return True
    
    # ========== PHASE 3: PAPER TRADING METHODS ==========
    
    def open_paper_trade(
        self,
        consensus_id: str,
        agent_ids: List[str],
        action: str,
        symbol: str,
        notional_usdt: float,
        tp_pct: float,
        sl_pct: float,
        entry_price: float
    ) -> tuple[bool, str]:
        """
        Open a paper trade from consensus - Phase 3
        
        Args:
            consensus_id: Consensus round ID
            agent_ids: Participating agent IDs
            action: Trade action (open_long/open_short)
            symbol: Trading symbol
            notional_usdt: Notional value in USDT
            tp_pct: Take profit percentage
            sl_pct: Stop loss percentage
            entry_price: Entry price
        
        Returns:
            (success, message)
        """
        with self._lock:
            if consensus_id in self.paper_trades:
                return False, f"Paper trade {consensus_id} already exists"
            
            # Create paper trade
            paper_trade = PaperTrade(
                consensus_id=consensus_id,
                agent_ids=agent_ids,
                action=action,
                symbol=symbol,
                notional_usdt=notional_usdt,
                tp_pct=tp_pct,
                sl_pct=sl_pct,
                entry_price=entry_price,
                mode="paper"
            )
            
            self.paper_trades[consensus_id] = paper_trade
            
            logger.info(
                f"Paper trade opened: {consensus_id} - {action} {symbol} @ {entry_price} "
                f"(notional: ${notional_usdt}, TP: {tp_pct}%, SL: {sl_pct}%)"
            )
            
            return True, f"Paper trade {consensus_id} opened"
    
    def close_paper_trade(
        self,
        paper_id: str,
        close_price: float,
        reason: str = "manual"
    ) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Close a paper trade - Phase 3
        
        Args:
            paper_id: Paper trade ID (consensus_id)
            close_price: Close price
            reason: Close reason
        
        Returns:
            (success, message, trade_data)
        """
        with self._lock:
            if paper_id not in self.paper_trades:
                return False, f"Paper trade {paper_id} not found", None
            
            paper_trade = self.paper_trades[paper_id]
            
            if paper_trade.status == "closed":
                return False, f"Paper trade {paper_id} already closed", None
            
            # Close the trade
            paper_trade.close(close_price, reason)
            
            logger.info(
                f"Paper trade closed: {paper_id} - {paper_trade.symbol} @ {close_price} "
                f"(PnL: ${paper_trade.realized_pnl:.2f}, reason: {reason})"
            )
            
            return True, f"Paper trade {paper_id} closed", paper_trade.to_dict()
    
    def get_open_paper_trades(self) -> List[Dict[str, Any]]:
        """Get all open paper trades - Phase 3"""
        with self._lock:
            return [
                trade.to_dict()
                for trade in self.paper_trades.values()
                if trade.status == "open"
            ]
    
    def get_paper_trade(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific paper trade - Phase 3"""
        with self._lock:
            trade = self.paper_trades.get(paper_id)
            return trade.to_dict() if trade else None
    
    def update_paper_trade_prices(self, price_data: Dict[str, float]):
        """
        Update prices for all open paper trades - Phase 3
        
        Args:
            price_data: Dict of symbol -> current_price
        """
        with self._lock:
            for trade in self.paper_trades.values():
                if trade.status == "open" and trade.symbol in price_data:
                    trade.update_price(price_data[trade.symbol])
                    
                    # Check if SL/TP hit
                    hit_reason = trade.check_sl_tp(price_data[trade.symbol])
                    if hit_reason:
                        trade.close(price_data[trade.symbol], hit_reason)
                        logger.info(
                            f"Paper trade {trade.paper_id} auto-closed: "
                            f"{hit_reason} hit at {price_data[trade.symbol]}"
                        )


# Global instance
slot_manager = SlotManager()
