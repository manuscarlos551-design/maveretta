# core/positions/position_manager.py
"""
Position Manager - Manages live trading positions
Tracks real orders and positions, syncs with exchange
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class LiveTrade:
    """
    Represents a live trade with real exchange orders
    """
    trade_id: str
    consensus_id: Optional[str]
    agent_ids: List[str]
    symbol: str
    action: str  # 'open_long' or 'open_short'
    notional_usdt: float
    tp_pct: float
    sl_pct: float
    
    # Order information
    entry_order_id: Optional[str] = None
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    
    exit_order_id: Optional[str] = None
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    
    # Position state
    status: str = 'pending'  # pending, open, closing, closed, error
    current_price: float = 0.0
    
    # P&L tracking
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    fees_paid: float = 0.0
    
    # Risk management
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    # Metadata
    exchange: str = 'binance'
    mode: str = 'live'
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    
    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def update_price(self, current_price: float):
        """Update current price and calculate unrealized PnL"""
        self.current_price = current_price
        
        if self.entry_price > 0 and self.status == 'open':
            price_change = (current_price - self.entry_price) / self.entry_price
            
            if self.action == 'open_long':
                self.unrealized_pnl = self.notional_usdt * price_change
            elif self.action == 'open_short':
                self.unrealized_pnl = self.notional_usdt * (-price_change)
    
    def close(self, close_price: float, reason: str = "manual"):
        """Close the trade"""
        self.status = 'closed'
        self.exit_price = close_price
        self.closed_at = datetime.now(timezone.utc)
        self.close_reason = reason
        self.update_price(close_price)
        self.realized_pnl = self.unrealized_pnl
    
    def check_sl_tp(self, current_price: float) -> Optional[str]:
        """
        Check if stop loss or take profit should trigger
        
        Returns:
            'stop_loss', 'take_profit', or None
        """
        if self.stop_loss_price and self.take_profit_price:
            if self.action == 'open_long':
                if current_price <= self.stop_loss_price:
                    return 'stop_loss'
                if current_price >= self.take_profit_price:
                    return 'take_profit'
            elif self.action == 'open_short':
                if current_price >= self.stop_loss_price:
                    return 'stop_loss'
                if current_price <= self.take_profit_price:
                    return 'take_profit'
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key in ['opened_at', 'closed_at', 'entry_time', 'exit_time']:
            if data.get(key):
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data


class PositionManager:
    """
    Manages all live trading positions
    Handles position lifecycle and synchronization with exchange
    """
    
    def __init__(self, order_executor=None, db_client=None):
        """
        Initialize Position Manager
        
        Args:
            order_executor: OrderExecutor instance for order management
            db_client: MongoDB client for persistence
        """
        self.order_executor = order_executor
        self.db_client = db_client
        self.positions: Dict[str, LiveTrade] = {}
        self._lock = threading.Lock()
        
        logger.info("PositionManager initialized")
    
    def open_live_trade(
        self,
        consensus_id: str,
        agent_ids: List[str],
        action: str,
        symbol: str,
        notional_usdt: float,
        tp_pct: float,
        sl_pct: float,
        exchange: str = 'binance'
    ) -> Tuple[bool, Optional[str], Optional[LiveTrade]]:
        """
        Open a live trade by placing a real order
        
        Args:
            consensus_id: Consensus round ID
            agent_ids: Participating agent IDs
            action: 'open_long' or 'open_short'
            symbol: Trading pair
            notional_usdt: Position size in USDT
            tp_pct: Take profit percentage
            sl_pct: Stop loss percentage
            exchange: Exchange name
        
        Returns:
            Tuple of (success, message, trade_object)
        """
        with self._lock:
            try:
                import uuid
                trade_id = str(uuid.uuid4())
                
                # Create LiveTrade object
                trade = LiveTrade(
                    trade_id=trade_id,
                    consensus_id=consensus_id,
                    agent_ids=agent_ids,
                    symbol=symbol,
                    action=action,
                    notional_usdt=notional_usdt,
                    tp_pct=tp_pct,
                    sl_pct=sl_pct,
                    exchange=exchange
                )
                
                # Get current price
                if self.order_executor:
                    success, ticker, error = self.order_executor.fetch_ticker(symbol)
                    if not success:
                        logger.error(f"Failed to fetch ticker for {symbol}: {error}")
                        trade.status = 'error'
                        trade.error_message = f"Failed to fetch price: {error}"
                        return False, error, trade
                    
                    current_price = ticker['last']
                    trade.current_price = current_price
                    
                    # Calculate position size in base currency
                    amount = notional_usdt / current_price
                    
                    # Determine order side
                    side = 'buy' if action == 'open_long' else 'sell'
                    
                    # Place market order
                    success, order, error = self.order_executor.create_order(
                        symbol=symbol,
                        order_type='market',
                        side=side,
                        amount=amount
                    )
                    
                    if not success:
                        logger.error(f"Failed to create order: {error}")
                        trade.status = 'error'
                        trade.error_message = error
                        return False, error, trade
                    
                    # Update trade with order information
                    trade.entry_order_id = order['id']
                    trade.entry_price = order.get('average') or order.get('price') or current_price
                    trade.entry_time = datetime.now(timezone.utc)
                    trade.status = 'open'
                    
                    # Calculate SL/TP prices
                    if action == 'open_long':
                        trade.stop_loss_price = trade.entry_price * (1 - sl_pct / 100)
                        trade.take_profit_price = trade.entry_price * (1 + tp_pct / 100)
                    else:  # open_short
                        trade.stop_loss_price = trade.entry_price * (1 + sl_pct / 100)
                        trade.take_profit_price = trade.entry_price * (1 - tp_pct / 100)
                    
                    # Store position
                    self.positions[trade_id] = trade
                    
                    # Persist to database if available
                    if self.db_client:
                        self._save_trade_to_db(trade)
                    
                    logger.info(
                        f"Live trade opened: {trade_id} - {action} {symbol} @ {trade.entry_price} "
                        f"(notional: ${notional_usdt}, SL: {trade.stop_loss_price:.2f}, "
                        f"TP: {trade.take_profit_price:.2f})"
                    )
                    
                    return True, f"Trade {trade_id} opened successfully", trade
                
                else:
                    # No order executor - simulation mode
                    trade.status = 'error'
                    trade.error_message = "No order executor available"
                    return False, "No order executor available", trade
                    
            except Exception as e:
                error_msg = f"Error opening live trade: {str(e)}"
                logger.error(error_msg)
                return False, error_msg, None
    
    def close_live_trade(
        self,
        trade_id: str,
        reason: str = "manual"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Close a live trade by placing a closing order
        
        Args:
            trade_id: Trade ID to close
            reason: Close reason
        
        Returns:
            Tuple of (success, message, trade_data)
        """
        with self._lock:
            try:
                if trade_id not in self.positions:
                    return False, f"Trade {trade_id} not found", None
                
                trade = self.positions[trade_id]
                
                if trade.status != 'open':
                    return False, f"Trade {trade_id} is not open (status: {trade.status})", None
                
                trade.status = 'closing'
                
                if self.order_executor:
                    # Get current price
                    success, ticker, error = self.order_executor.fetch_ticker(trade.symbol)
                    if not success:
                        logger.error(f"Failed to fetch ticker: {error}")
                        return False, error, trade.to_dict()
                    
                    close_price = ticker['last']
                    
                    # Determine closing order side (opposite of entry)
                    side = 'sell' if trade.action == 'open_long' else 'buy'
                    
                    # Calculate amount (same as entry)
                    amount = trade.notional_usdt / trade.entry_price
                    
                    # Place market order to close
                    success, order, error = self.order_executor.create_order(
                        symbol=trade.symbol,
                        order_type='market',
                        side=side,
                        amount=amount
                    )
                    
                    if not success:
                        logger.error(f"Failed to close trade: {error}")
                        trade.status = 'error'
                        trade.error_message = error
                        return False, error, trade.to_dict()
                    
                    # Update trade
                    trade.exit_order_id = order['id']
                    trade.exit_price = order.get('average') or order.get('price') or close_price
                    trade.exit_time = datetime.now(timezone.utc)
                    trade.close(trade.exit_price, reason)
                    
                    # Update in database
                    if self.db_client:
                        self._save_trade_to_db(trade)
                    
                    logger.info(
                        f"Live trade closed: {trade_id} - {trade.symbol} @ {trade.exit_price} "
                        f"(PnL: ${trade.realized_pnl:.2f}, reason: {reason})"
                    )
                    
                    return True, f"Trade {trade_id} closed successfully", trade.to_dict()
                
                else:
                    return False, "No order executor available", None
                    
            except Exception as e:
                error_msg = f"Error closing live trade: {str(e)}"
                logger.error(error_msg)
                return False, error_msg, None
    
    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open live trades"""
        with self._lock:
            return [
                trade.to_dict()
                for trade in self.positions.values()
                if trade.status == 'open'
            ]
    
    def get_trade(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trade"""
        with self._lock:
            trade = self.positions.get(trade_id)
            return trade.to_dict() if trade else None
    
    def update_trade_prices(self, price_data: Dict[str, float]):
        """
        Update prices for all open trades and check SL/TP
        
        Args:
            price_data: Dict of symbol -> current_price
        """
        with self._lock:
            for trade in self.positions.values():
                if trade.status == 'open' and trade.symbol in price_data:
                    current_price = price_data[trade.symbol]
                    trade.update_price(current_price)
                    
                    # Check if SL or TP hit
                    trigger = trade.check_sl_tp(current_price)
                    if trigger:
                        logger.info(f"Trade {trade.trade_id}: {trigger} triggered at {current_price}")
                        # Close the trade
                        self.close_live_trade(trade.trade_id, trigger)
    
    def sync_positions_from_exchange(self) -> Tuple[bool, str]:
        """
        Synchronize positions with exchange state
        Useful for recovery after restarts
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.order_executor:
                return False, "No order executor available"
            
            # Fetch open orders from exchange
            success, open_orders, error = self.order_executor.fetch_open_orders()
            if not success:
                return False, f"Failed to fetch open orders: {error}"
            
            # Fetch balance to check positions
            success, balance, error = self.order_executor.fetch_balance()
            if not success:
                return False, f"Failed to fetch balance: {error}"
            
            logger.info(
                f"Sync complete: {len(open_orders)} open orders, "
                f"balance fetched"
            )
            
            # TODO: Reconcile local positions with exchange state
            # This is a placeholder for more sophisticated sync logic
            
            return True, "Positions synchronized"
            
        except Exception as e:
            error_msg = f"Error syncing positions: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _save_trade_to_db(self, trade: LiveTrade):
        """Save trade to MongoDB"""
        try:
            if self.db_client:
                collection = self.db_client['botai_trading']['live_trades']
                trade_dict = trade.to_dict()
                collection.replace_one(
                    {'trade_id': trade.trade_id},
                    trade_dict,
                    upsert=True
                )
                logger.debug(f"Trade {trade.trade_id} saved to database")
        except Exception as e:
            logger.error(f"Error saving trade to database: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get trading statistics"""
        with self._lock:
            total_trades = len(self.positions)
            open_trades = sum(1 for t in self.positions.values() if t.status == 'open')
            closed_trades = sum(1 for t in self.positions.values() if t.status == 'closed')
            
            total_pnl = sum(t.realized_pnl for t in self.positions.values() if t.status == 'closed')
            total_fees = sum(t.fees_paid for t in self.positions.values())
            
            return {
                'total_trades': total_trades,
                'open_trades': open_trades,
                'closed_trades': closed_trades,
                'total_realized_pnl': total_pnl,
                'total_fees_paid': total_fees,
                'net_pnl': total_pnl - total_fees
            }


# Global instance placeholder (will be initialized with proper dependencies)
position_manager = None
