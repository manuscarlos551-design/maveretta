# core/slots/router.py
"""Slot Router - Executes trading decisions through slots"""

import logging
import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone

from .models import TradeDecision, TradeAction, SlotMode
from .manager import slot_manager

logger = logging.getLogger(__name__)


class SlotRouter:
    """Routes and executes trading decisions through appropriate slots"""
    
    def __init__(self):
        self.manager = slot_manager
        logger.info("Slot Router initialized")
    
    def execute_decision(self, decision: TradeDecision) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute a trading decision based on mode
        
        Args:
            decision: TradeDecision object
        
        Returns:
            Tuple of (success, message, execution_details)
        """
        start_time = time.time()
        
        try:
            # Get slot
            slot = self.manager.get_slot(decision.slot_id)
            if not slot:
                return False, f"Slot {decision.slot_id} not found", {}
            
            # Check slot status
            if slot["status"] != "active":
                return False, f"Slot {decision.slot_id} is not active", {}
            
            # Execute based on mode
            if decision.mode == SlotMode.SHADOW:
                success, msg, details = self._execute_shadow(decision)
            elif decision.mode == SlotMode.PAPER:
                success, msg, details = self._execute_paper(decision)
            elif decision.mode == SlotMode.LIVE:
                success, msg, details = self._execute_live(decision)
            else:
                return False, f"Unknown mode: {decision.mode}", {}
            
            # Record execution time
            execution_time_ms = (time.time() - start_time) * 1000
            decision.execution_time_ms = execution_time_ms
            details["execution_time_ms"] = execution_time_ms
            
            # Update metrics
            if success:
                metrics = self.manager.get_metrics(decision.slot_id)
                if metrics:
                    metrics.total_decisions += 1
                    metrics.avg_decision_latency_ms = (
                        (metrics.avg_decision_latency_ms * (metrics.total_decisions - 1) 
                         + execution_time_ms) / metrics.total_decisions
                    )
            
            return success, msg, details
            
        except Exception as e:
            logger.error(f"Error executing decision: {e}")
            return False, str(e), {}
    
    def _execute_shadow(self, decision: TradeDecision) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Shadow mode: Log decision without execution
        
        Args:
            decision: TradeDecision object
        
        Returns:
            Tuple of (success, message, details)
        """
        logger.info(
            f"[SHADOW] Agent {decision.agent_id} → Slot {decision.slot_id}: "
            f"{decision.action.value} {decision.symbol} "
            f"(confidence: {decision.confidence:.2f})"
        )
        
        details = {
            "mode": "shadow",
            "action": decision.action.value,
            "symbol": decision.symbol,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "executed": False,
            "logged_only": True
        }
        
        return True, "Decision logged (shadow mode)", details
    
    def _execute_paper(self, decision: TradeDecision) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Paper mode: Simulate execution with real data
        
        Args:
            decision: TradeDecision object
        
        Returns:
            Tuple of (success, message, details)
        """
        logger.info(
            f"[PAPER] Agent {decision.agent_id} → Slot {decision.slot_id}: "
            f"{decision.action.value} {decision.symbol} "
            f"(confidence: {decision.confidence:.2f})"
        )
        
        # Simulate realistic price if not provided
        if decision.price is None:
            # In real implementation, fetch from market data
            decision.price = 50000.0 if "BTC" in decision.symbol else 3000.0
        
        # Execute action
        success = False
        message = ""
        
        if decision.action == TradeAction.OPEN_LONG:
            success = self.manager.open_position(
                slot_id=decision.slot_id,
                symbol=decision.symbol,
                side="long",
                size=decision.size or 0.01,
                entry_price=decision.price,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit
            )
            message = f"Opened LONG position: {decision.symbol} @ {decision.price}"
        
        elif decision.action == TradeAction.OPEN_SHORT:
            success = self.manager.open_position(
                slot_id=decision.slot_id,
                symbol=decision.symbol,
                side="short",
                size=decision.size or 0.01,
                entry_price=decision.price,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit
            )
            message = f"Opened SHORT position: {decision.symbol} @ {decision.price}"
        
        elif decision.action in [TradeAction.CLOSE_LONG, TradeAction.CLOSE_SHORT]:
            success = self.manager.close_position(
                slot_id=decision.slot_id,
                symbol=decision.symbol,
                close_price=decision.price
            )
            message = f"Closed position: {decision.symbol} @ {decision.price}"
        
        elif decision.action == TradeAction.HOLD:
            success = True
            message = f"Hold decision: {decision.symbol}"
        
        else:
            message = f"Action {decision.action.value} not implemented in paper mode"
        
        details = {
            "mode": "paper",
            "action": decision.action.value,
            "symbol": decision.symbol,
            "price": decision.price,
            "size": decision.size,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "executed": success,
            "simulated": True
        }
        
        return success, message, details
    
    def _execute_live(self, decision: TradeDecision) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Live mode: Execute real orders on exchange
        
        Args:
            decision: TradeDecision object
        
        Returns:
            Tuple of (success, message, details)
        """
        logger.info(
            f"[LIVE] Agent {decision.agent_id} → Slot {decision.slot_id}: "
            f"{decision.action.value} {decision.symbol} "
            f"(confidence: {decision.confidence:.2f})"
        )
        
        try:
            # Import dependencies
            from core.execution import OrderExecutor
            from core.positions import PositionManager
            from core.exchanges.exchange_manager import get_exchange_manager
            
            # Get exchange manager
            exchange_manager = get_exchange_manager()
            
            # Create order executor
            order_executor = OrderExecutor(exchange_manager)
            
            # Create position manager (could be cached for performance)
            position_manager = PositionManager(order_executor=order_executor)
            
            # Get current price
            success, ticker, error = order_executor.fetch_ticker(decision.symbol)
            if not success:
                logger.error(f"Failed to fetch ticker: {error}")
                return False, f"Failed to fetch price: {error}", {
                    "mode": "live",
                    "executed": False,
                    "error": error
                }
            
            current_price = ticker['last']
            
            # Execute based on action
            if decision.action == TradeAction.OPEN_LONG:
                # Open long position
                notional_usdt = self.manager.get_slot(decision.slot_id).get('capital_base', 1000) * 0.1
                tp_pct = 2.0  # 2% take profit
                sl_pct = 1.0  # 1% stop loss
                
                success, message, trade = position_manager.open_live_trade(
                    consensus_id=f"slot_{decision.slot_id}_{int(time.time())}",
                    agent_ids=[decision.agent_id],
                    action='open_long',
                    symbol=decision.symbol,
                    notional_usdt=notional_usdt,
                    tp_pct=tp_pct,
                    sl_pct=sl_pct
                )
                
                details = {
                    "mode": "live",
                    "action": "open_long",
                    "symbol": decision.symbol,
                    "price": current_price,
                    "notional_usdt": notional_usdt,
                    "executed": success,
                    "message": message
                }
                
                if success:
                    # Update slot metrics
                    metrics = self.manager.get_metrics(decision.slot_id)
                    if metrics:
                        metrics.executed_trades += 1
                        metrics.positions_open += 1
                
                return success, message, details
            
            elif decision.action == TradeAction.OPEN_SHORT:
                # Open short position
                notional_usdt = self.manager.get_slot(decision.slot_id).get('capital_base', 1000) * 0.1
                tp_pct = 2.0
                sl_pct = 1.0
                
                success, message, trade = position_manager.open_live_trade(
                    consensus_id=f"slot_{decision.slot_id}_{int(time.time())}",
                    agent_ids=[decision.agent_id],
                    action='open_short',
                    symbol=decision.symbol,
                    notional_usdt=notional_usdt,
                    tp_pct=tp_pct,
                    sl_pct=sl_pct
                )
                
                details = {
                    "mode": "live",
                    "action": "open_short",
                    "symbol": decision.symbol,
                    "price": current_price,
                    "notional_usdt": notional_usdt,
                    "executed": success,
                    "message": message
                }
                
                if success and metrics:
                    metrics.executed_trades += 1
                    metrics.positions_open += 1
                
                return success, message, details
            
            elif decision.action in [TradeAction.CLOSE_LONG, TradeAction.CLOSE_SHORT]:
                # Close existing position
                # Find open trade for this symbol
                open_trades = position_manager.get_open_trades()
                
                for trade in open_trades:
                    if trade['symbol'] == decision.symbol:
                        trade_id = trade['trade_id']
                        
                        success, message, result = position_manager.close_live_trade(
                            trade_id=trade_id,
                            reason="agent_decision"
                        )
                        
                        details = {
                            "mode": "live",
                            "action": decision.action.value,
                            "symbol": decision.symbol,
                            "price": current_price,
                            "executed": success,
                            "message": message
                        }
                        
                        if success:
                            metrics = self.manager.get_metrics(decision.slot_id)
                            if metrics:
                                metrics.positions_open = max(0, metrics.positions_open - 1)
                                metrics.realized_pnl += result.get('realized_pnl', 0)
                        
                        return success, message, details
                
                # No position found to close
                message = f"No open position found for {decision.symbol}"
                logger.warning(message)
                return False, message, {
                    "mode": "live",
                    "executed": False,
                    "error": message
                }
            
            elif decision.action == TradeAction.HOLD:
                # Hold - no action needed
                return True, f"Hold decision for {decision.symbol}", {
                    "mode": "live",
                    "action": "hold",
                    "symbol": decision.symbol,
                    "executed": True
                }
            
            else:
                message = f"Action {decision.action.value} not implemented in live mode"
                logger.warning(message)
                return False, message, {
                    "mode": "live",
                    "executed": False,
                    "error": message
                }
        
        except Exception as e:
            error_msg = f"Error executing live order: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {
                "mode": "live",
                "executed": False,
                "error": error_msg
            }
    
    def get_slot_positions(self, slot_id: str) -> list:
        """Get all positions for a slot"""
        positions = self.manager.get_positions(slot_id)
        return [pos.to_dict() for pos in positions]
    
    def get_slot_metrics(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a slot"""
        metrics = self.manager.get_metrics(slot_id)
        return metrics.to_dict() if metrics else None


# Global instance
slot_router = SlotRouter()
