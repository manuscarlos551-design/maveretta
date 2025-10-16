# core/execution/order_executor.py
"""
Order Executor - Executes real orders on exchanges via CCXT
Critical component for live trading mode
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import ccxt
import time
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# === PROMETHEUS METRICS ===
orders_executed = Counter(
    'core_orders_executed_total',
    'Total orders executed by status',
    ['slot', 'symbol', 'side', 'status', 'exchange']
)

order_execution_latency = Histogram(
    'core_order_execution_latency_ms',
    'Order execution latency in milliseconds',
    ['exchange', 'order_type'],
    buckets=(10, 50, 100, 250, 500, 1000, 2000, 5000)
)

order_rejections = Counter(
    'core_order_rejection_total',
    'Total orders rejected by reason',
    ['reason', 'exchange', 'symbol']
)

order_slippage = Histogram(
    'core_order_slippage_pct',
    'Order slippage percentage',
    ['symbol', 'side'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)


class OrderExecutor:
    """
    Handles real order execution on cryptocurrency exchanges.
    Uses CCXT library for exchange integration.
    """
    
    def __init__(self, exchange_manager):
        """
        Initialize OrderExecutor with an exchange manager
        
        Args:
            exchange_manager: ExchangeManager instance with active exchange connection
        """
        self.exchange_manager = exchange_manager
        self.exchange = exchange_manager.get_primary_exchange()
        
        if not self.exchange:
            raise RuntimeError("No exchange connection available")
        
        logger.info(f"OrderExecutor initialized with {self.exchange_manager.get_exchange_name()}")
    
    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
        slot_id: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create an order on the exchange
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            order_type: 'market' or 'limit'
            side: 'buy' or 'sell'
            amount: Order amount in base currency
            price: Limit price (required for limit orders)
            params: Additional exchange-specific parameters
            slot_id: Slot ID for metrics tracking
        
        Returns:
            Tuple of (success, order_data, error_message)
        """
        start_time = time.time()
        exchange_name = self.exchange_manager.get_exchange_name()
        slot = slot_id or 'unknown'
        
        try:
            # Validate inputs
            if order_type not in ['market', 'limit']:
                order_rejections.labels(
                    reason='invalid_order_type',
                    exchange=exchange_name,
                    symbol=symbol
                ).inc()
                return False, None, f"Invalid order type: {order_type}"
            
            if side not in ['buy', 'sell']:
                order_rejections.labels(
                    reason='invalid_side',
                    exchange=exchange_name,
                    symbol=symbol
                ).inc()
                return False, None, f"Invalid side: {side}"
            
            if order_type == 'limit' and price is None:
                order_rejections.labels(
                    reason='missing_price',
                    exchange=exchange_name,
                    symbol=symbol
                ).inc()
                return False, None, "Price required for limit orders"
            
            if amount <= 0:
                order_rejections.labels(
                    reason='invalid_amount',
                    exchange=exchange_name,
                    symbol=symbol
                ).inc()
                return False, None, f"Invalid amount: {amount}"
            
            # Log order attempt
            logger.info(
                f"Creating {order_type} {side} order: {amount} {symbol}"
                f"{f' @ {price}' if price else ''}"
            )
            
            # Create order via CCXT
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )
            
            # Measure latency
            latency_ms = (time.time() - start_time) * 1000
            order_execution_latency.labels(
                exchange=exchange_name,
                order_type=order_type
            ).observe(latency_ms)
            
            # Count successful order
            orders_executed.labels(
                slot=slot,
                symbol=symbol,
                side=side,
                status='success',
                exchange=exchange_name
            ).inc()
            
            logger.info(
                f"Order created successfully: ID={order.get('id')} "
                f"Status={order.get('status')} Latency={latency_ms:.1f}ms"
            )
            
            return True, order, None
            
        except ccxt.InsufficientFunds as e:
            error_msg = f"Insufficient funds: {str(e)}"
            logger.error(error_msg)
            order_rejections.labels(
                reason='insufficient_funds',
                exchange=exchange_name,
                symbol=symbol
            ).inc()
            orders_executed.labels(
                slot=slot,
                symbol=symbol,
                side=side,
                status='rejected_insufficient_funds',
                exchange=exchange_name
            ).inc()
            return False, None, error_msg
            
        except ccxt.InvalidOrder as e:
            error_msg = f"Invalid order: {str(e)}"
            logger.error(error_msg)
            order_rejections.labels(
                reason='invalid_order',
                exchange=exchange_name,
                symbol=symbol
            ).inc()
            orders_executed.labels(
                slot=slot,
                symbol=symbol,
                side=side,
                status='rejected_invalid',
                exchange=exchange_name
            ).inc()
            return False, None, error_msg
            
        except ccxt.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            order_rejections.labels(
                reason='network_error',
                exchange=exchange_name,
                symbol=symbol
            ).inc()
            orders_executed.labels(
                slot=slot,
                symbol=symbol,
                side=side,
                status='error_network',
                exchange=exchange_name
            ).inc()
            return False, None, error_msg
            
        except ccxt.ExchangeError as e:
            error_msg = f"Exchange error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error creating order: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def cancel_order(
        self,
        order_id: str,
        symbol: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Cancel an existing order
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair
            params: Additional exchange-specific parameters
        
        Returns:
            Tuple of (success, order_data, error_message)
        """
        try:
            logger.info(f"Cancelling order: {order_id} for {symbol}")
            
            # Cancel order via CCXT
            result = self.exchange.cancel_order(
                id=order_id,
                symbol=symbol,
                params=params or {}
            )
            
            logger.info(f"Order {order_id} cancelled successfully")
            return True, result, None
            
        except ccxt.OrderNotFound as e:
            error_msg = f"Order not found: {str(e)}"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except ccxt.InvalidOrder as e:
            error_msg = f"Cannot cancel order (may be filled/cancelled): {str(e)}"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except ccxt.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error cancelling order: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def fetch_order_status(
        self,
        order_id: str,
        symbol: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Fetch the status of an order
        
        Args:
            order_id: Order ID to fetch
            symbol: Trading pair
            params: Additional exchange-specific parameters
        
        Returns:
            Tuple of (success, order_data, error_message)
        """
        try:
            order = self.exchange.fetch_order(
                id=order_id,
                symbol=symbol,
                params=params or {}
            )
            
            return True, order, None
            
        except ccxt.OrderNotFound as e:
            error_msg = f"Order not found: {str(e)}"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except ccxt.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error fetching order: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def fetch_open_orders(
        self,
        symbol: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetch all open orders
        
        Args:
            symbol: Trading pair (optional, None for all symbols)
            params: Additional exchange-specific parameters
        
        Returns:
            Tuple of (success, orders_list, error_message)
        """
        try:
            orders = self.exchange.fetch_open_orders(
                symbol=symbol,
                params=params or {}
            )
            
            logger.debug(f"Fetched {len(orders)} open orders")
            return True, orders, None
            
        except ccxt.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error fetching open orders: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def fetch_balance(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Fetch account balance
        
        Returns:
            Tuple of (success, balance_data, error_message)
        """
        try:
            balance = self.exchange.fetch_balance()
            return True, balance, None
            
        except ccxt.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error fetching balance: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def fetch_ticker(self, symbol: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Fetch current ticker (price) for a symbol
        
        Args:
            symbol: Trading pair
        
        Returns:
            Tuple of (success, ticker_data, error_message)
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return True, ticker, None
            
        except Exception as e:
            error_msg = f"Error fetching ticker for {symbol}: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def get_min_order_amount(self, symbol: str) -> Optional[float]:
        """
        Get minimum order amount for a symbol
        
        Args:
            symbol: Trading pair
        
        Returns:
            Minimum order amount or None if not available
        """
        try:
            markets = self.exchange.load_markets()
            if symbol in markets:
                market = markets[symbol]
                return market.get('limits', {}).get('amount', {}).get('min')
            return None
        except Exception as e:
            logger.error(f"Error getting min order amount: {e}")
            return None
    
    def validate_order_params(
        self,
        symbol: str,
        amount: float,
        price: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate order parameters against exchange limits
        
        Args:
            symbol: Trading pair
            amount: Order amount
            price: Order price (for limit orders)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            markets = self.exchange.load_markets()
            
            if symbol not in markets:
                return False, f"Symbol {symbol} not available on exchange"
            
            market = markets[symbol]
            limits = market.get('limits', {})
            
            # Check amount limits
            amount_limits = limits.get('amount', {})
            min_amount = amount_limits.get('min', 0)
            max_amount = amount_limits.get('max', float('inf'))
            
            if amount < min_amount:
                return False, f"Amount {amount} below minimum {min_amount}"
            
            if amount > max_amount:
                return False, f"Amount {amount} above maximum {max_amount}"
            
            # Check price limits if provided
            if price is not None:
                price_limits = limits.get('price', {})
                min_price = price_limits.get('min', 0)
                max_price = price_limits.get('max', float('inf'))
                
                if price < min_price:
                    return False, f"Price {price} below minimum {min_price}"
                
                if price > max_price:
                    return False, f"Price {price} above maximum {max_price}"
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error validating order params: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
