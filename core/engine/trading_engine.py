# core/engine/trading_engine.py
"""
Trading Engine - Real trading loop for live mode
Executes strategies, places orders, manages positions
"""

import logging
import time
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import threading

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Main trading engine for executing live trades
    Manages the complete trading cycle: data → strategy → execution
    """
    
    def __init__(
        self,
        exchange_manager,
        order_executor,
        position_manager,
        strategy,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Trading Engine
        
        Args:
            exchange_manager: ExchangeManager instance
            order_executor: OrderExecutor instance
            position_manager: PositionManager instance
            strategy: Trading strategy instance
            config: Configuration dictionary
        """
        self.exchange_manager = exchange_manager
        self.order_executor = order_executor
        self.position_manager = position_manager
        self.strategy = strategy
        self.config = config or {}
        
        self.running = False
        self._thread = None
        self._stop_flag = threading.Event()
        
        # Configuration
        self.pairs = self.config.get('pairs', ['BTC/USDT'])
        self.timeframe = self.config.get('timeframe', '5m')
        self.loop_interval = self.config.get('loop_interval', 60)  # seconds
        self.max_open_positions = self.config.get('max_open_positions', 3)
        
        logger.info(
            f"TradingEngine initialized with {self.strategy.strategy_name} strategy "
            f"on {len(self.pairs)} pairs"
        )
    
    def start(self):
        """Start the trading engine in a background thread"""
        if self.running:
            logger.warning("Trading engine is already running")
            return
        
        self.running = True
        self._stop_flag.clear()
        
        self._thread = threading.Thread(
            target=self._trading_loop,
            daemon=True
        )
        self._thread.start()
        
        logger.info("Trading engine started")
    
    def stop(self):
        """Stop the trading engine"""
        if not self.running:
            return
        
        logger.info("Stopping trading engine...")
        self.running = False
        self._stop_flag.set()
        
        if self._thread:
            self._thread.join(timeout=10)
        
        logger.info("Trading engine stopped")
    
    def _trading_loop(self):
        """Main trading loop - runs continuously"""
        logger.info("Trading loop started")
        
        while not self._stop_flag.is_set():
            try:
                cycle_start = time.time()
                
                # Update prices for open positions
                self._update_position_prices()
                
                # Check each trading pair
                for pair in self.pairs:
                    try:
                        self._process_pair(pair)
                    except Exception as e:
                        logger.error(f"Error processing pair {pair}: {e}")
                
                # Calculate sleep time to maintain interval
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, self.loop_interval - cycle_duration)
                
                logger.debug(
                    f"Trading cycle completed in {cycle_duration:.2f}s, "
                    f"sleeping {sleep_time:.2f}s"
                )
                
                # Sleep with interrupt capability
                self._stop_flag.wait(timeout=sleep_time)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(5)
        
        logger.info("Trading loop stopped")
    
    def _process_pair(self, pair: str):
        """
        Process a single trading pair
        
        Args:
            pair: Trading pair (e.g., 'BTC/USDT')
        """
        try:
            # Check if we can open new positions
            open_positions = len(self.position_manager.get_open_trades())
            can_open_new = open_positions < self.max_open_positions
            
            # Check if we already have a position for this pair
            has_position = any(
                trade['symbol'] == pair
                for trade in self.position_manager.get_open_trades()
            )
            
            # Fetch OHLCV data
            success, dataframe = self._fetch_ohlcv(pair)
            if not success or dataframe.empty:
                logger.warning(f"No data available for {pair}")
                return
            
            # Analyze with strategy
            metadata = {
                'pair': pair,
                'timeframe': self.timeframe
            }
            
            analyzed_df = self.strategy.analyze(dataframe, metadata)
            
            # Get latest signal
            signal = self.strategy.get_latest_signal(analyzed_df)
            
            logger.debug(
                f"{pair}: Signal={signal['action']}, "
                f"Confidence={signal['confidence']:.2f}, "
                f"Price={signal.get('price', 0):.2f}"
            )
            
            # Process signal
            if signal['action'] in ['open_long', 'open_short']:
                if can_open_new and not has_position:
                    self._execute_entry_signal(pair, signal)
                else:
                    reason = "max positions reached" if not can_open_new else "already has position"
                    logger.debug(f"Skipping {pair} entry signal: {reason}")
            
            elif signal['action'] in ['close_long', 'close_short']:
                if has_position:
                    self._execute_exit_signal(pair, signal)
            
        except Exception as e:
            logger.error(f"Error processing pair {pair}: {e}")
    
    def _fetch_ohlcv(self, pair: str) -> Tuple[bool, pd.DataFrame]:
        """
        Fetch OHLCV data for a pair
        
        Args:
            pair: Trading pair
        
        Returns:
            Tuple of (success, dataframe)
        """
        try:
            exchange = self.exchange_manager.get_primary_exchange()
            if not exchange:
                return False, pd.DataFrame()
            
            # Fetch enough candles for strategy
            limit = self.strategy.startup_candle_count + 10
            
            ohlcv = exchange.fetch_ohlcv(
                symbol=pair,
                timeframe=self.timeframe,
                limit=limit
            )
            
            if not ohlcv:
                return False, pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return True, df
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {pair}: {e}")
            return False, pd.DataFrame()
    
    def _execute_entry_signal(self, pair: str, signal: Dict[str, Any]):
        """
        Execute an entry signal by opening a position
        
        Args:
            pair: Trading pair
            signal: Signal dictionary from strategy
        """
        try:
            action = signal['action']
            confidence = signal['confidence']
            
            # Get default position size from config
            notional_usdt = self.config.get('position_size_usdt', 300.0)
            tp_pct = self.config.get('take_profit_pct', 2.0)
            sl_pct = self.config.get('stop_loss_pct', 1.0)
            
            # Override with signal values if available
            if 'take_profit' in signal and 'price' in signal:
                tp_pct = abs((signal['take_profit'] - signal['price']) / signal['price']) * 100
            
            if 'stop_loss' in signal and 'price' in signal:
                sl_pct = abs((signal['price'] - signal['stop_loss']) / signal['price']) * 100
            
            logger.info(
                f"Executing {action} for {pair}: "
                f"${notional_usdt} USDT, TP={tp_pct:.1f}%, SL={sl_pct:.1f}%"
            )
            
            # Open live trade
            success, message, trade = self.position_manager.open_live_trade(
                consensus_id=f"strategy_{int(time.time())}",
                agent_ids=[self.strategy.strategy_name],
                action=action,
                symbol=pair,
                notional_usdt=notional_usdt,
                tp_pct=tp_pct,
                sl_pct=sl_pct,
                exchange=self.exchange_manager.get_exchange_name()
            )
            
            if success:
                logger.info(f"✅ Position opened: {message}")
            else:
                logger.error(f"❌ Failed to open position: {message}")
            
        except Exception as e:
            logger.error(f"Error executing entry signal for {pair}: {e}")
    
    def _execute_exit_signal(self, pair: str, signal: Dict[str, Any]):
        """
        Execute an exit signal by closing a position
        
        Args:
            pair: Trading pair
            signal: Signal dictionary from strategy
        """
        try:
            # Find open trade for this pair
            open_trades = self.position_manager.get_open_trades()
            
            for trade in open_trades:
                if trade['symbol'] == pair:
                    trade_id = trade['trade_id']
                    
                    logger.info(f"Executing exit for {pair}, trade {trade_id}")
                    
                    # Close the trade
                    success, message, result = self.position_manager.close_live_trade(
                        trade_id=trade_id,
                        reason="strategy_signal"
                    )
                    
                    if success:
                        pnl = result.get('realized_pnl', 0)
                        logger.info(f"✅ Position closed: {message}, PnL: ${pnl:.2f}")
                    else:
                        logger.error(f"❌ Failed to close position: {message}")
                    
                    break
            
        except Exception as e:
            logger.error(f"Error executing exit signal for {pair}: {e}")
    
    def _update_position_prices(self):
        """Update current prices for all open positions"""
        try:
            open_trades = self.position_manager.get_open_trades()
            if not open_trades:
                return
            
            # Get unique symbols
            symbols = list(set(trade['symbol'] for trade in open_trades))
            
            # Fetch current prices
            price_data = {}
            for symbol in symbols:
                success, ticker, error = self.order_executor.fetch_ticker(symbol)
                if success:
                    price_data[symbol] = ticker['last']
            
            # Update positions
            if price_data:
                self.position_manager.update_trade_prices(price_data)
            
        except Exception as e:
            logger.error(f"Error updating position prices: {e}")
    
    def force_close_all_positions(self, reason: str = "force_close"):
        """
        Force close all open positions
        Useful for emergency stops
        
        Args:
            reason: Reason for closing
        """
        logger.warning(f"Force closing all positions: {reason}")
        
        open_trades = self.position_manager.get_open_trades()
        
        for trade in open_trades:
            try:
                trade_id = trade['trade_id']
                success, message, _ = self.position_manager.close_live_trade(
                    trade_id=trade_id,
                    reason=reason
                )
                
                if success:
                    logger.info(f"Closed trade {trade_id}: {message}")
                else:
                    logger.error(f"Failed to close trade {trade_id}: {message}")
                    
            except Exception as e:
                logger.error(f"Error force closing trade: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get trading engine status"""
        stats = self.position_manager.get_statistics()
        
        return {
            'running': self.running,
            'strategy': self.strategy.strategy_name,
            'pairs': self.pairs,
            'timeframe': self.timeframe,
            'max_open_positions': self.max_open_positions,
            'statistics': stats
        }


def create_trading_engine(
    exchange_manager,
    strategy_name: str = 'example',
    config: Optional[Dict[str, Any]] = None
) -> Optional[TradingEngine]:
    """
    Factory function to create a fully configured TradingEngine
    
    Args:
        exchange_manager: ExchangeManager instance
        strategy_name: Name of strategy to use ('example' or 'scalping')
        config: Configuration dictionary
    
    Returns:
        Configured TradingEngine instance or None if setup fails
    """
    try:
        from core.execution import OrderExecutor
        from core.positions import PositionManager
        from core.strategies.example_strategy import ExampleStrategy, ScalpingStrategy
        
        # Create OrderExecutor
        order_executor = OrderExecutor(exchange_manager)
        
        # Create PositionManager
        position_manager = PositionManager(order_executor=order_executor)
        
        # Select strategy
        if strategy_name == 'scalping':
            strategy = ScalpingStrategy(config)
        else:
            strategy = ExampleStrategy(config)
        
        # Create TradingEngine
        engine = TradingEngine(
            exchange_manager=exchange_manager,
            order_executor=order_executor,
            position_manager=position_manager,
            strategy=strategy,
            config=config
        )
        
        logger.info(f"Trading engine created with {strategy_name} strategy")
        return engine
        
    except Exception as e:
        logger.error(f"Failed to create trading engine: {e}")
        return None
