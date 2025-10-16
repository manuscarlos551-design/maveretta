# core/strategies/base_strategy.py
"""
Base Strategy - Abstract class for trading strategies
Follows Freqtrade pattern for consistency
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    All strategies must implement:
    - populate_indicators: Calculate technical indicators
    - populate_entry_trend: Define buy/entry signals
    - populate_exit_trend: Define sell/exit signals
    """
    
    # Strategy metadata
    strategy_name: str = "BaseStrategy"
    strategy_version: str = "1.0.0"
    
    # Default parameters
    minimal_roi: Dict[int, float] = {
        "0": 0.10,  # 10% profit target
    }
    
    stoploss: float = -0.05  # 5% stop loss
    
    timeframe: str = "5m"  # Default timeframe
    
    # Process only new candles
    process_only_new_candles: bool = True
    
    # Startup candle count
    startup_candle_count: int = 30
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy
        
        Args:
            config: Strategy configuration dictionary
        """
        self.config = config or {}
        logger.info(f"Strategy {self.strategy_name} v{self.strategy_version} initialized")
    
    @abstractmethod
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calculate technical indicators on the dataframe.
        
        Args:
            dataframe: Raw OHLCV data
            metadata: Additional metadata (symbol, timeframe, etc)
        
        Returns:
            Dataframe with calculated indicators
        """
        pass
    
    @abstractmethod
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define entry (buy) signals.
        
        Should add 'enter_long' and/or 'enter_short' columns.
        
        Args:
            dataframe: Dataframe with indicators
            metadata: Additional metadata
        
        Returns:
            Dataframe with entry signals
        """
        pass
    
    @abstractmethod
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define exit (sell) signals.
        
        Should add 'exit_long' and/or 'exit_short' columns.
        
        Args:
            dataframe: Dataframe with indicators
            metadata: Additional metadata
        
        Returns:
            Dataframe with exit signals
        """
        pass
    
    def analyze(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Full analysis pipeline: indicators → entry → exit
        
        Args:
            dataframe: Raw OHLCV data
            metadata: Additional metadata
        
        Returns:
            Fully analyzed dataframe with signals
        """
        try:
            # Step 1: Calculate indicators
            dataframe = self.populate_indicators(dataframe, metadata)
            
            # Step 2: Define entry signals
            dataframe = self.populate_entry_trend(dataframe, metadata)
            
            # Step 3: Define exit signals
            dataframe = self.populate_exit_trend(dataframe, metadata)
            
            return dataframe
            
        except Exception as e:
            logger.error(f"Error in strategy analysis: {e}")
            raise
    
    def get_latest_signal(self, dataframe: pd.DataFrame) -> Dict[str, Any]:
        """
        Get the latest trading signal from analyzed dataframe
        
        Args:
            dataframe: Analyzed dataframe with signals
        
        Returns:
            Dictionary with signal information
        """
        if dataframe.empty:
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reason': 'No data available'
            }
        
        # Get last row
        last_row = dataframe.iloc[-1]
        
        # Check for entry signals
        if last_row.get('enter_long', 0) == 1:
            return {
                'action': 'open_long',
                'confidence': 0.8,  # Default confidence
                'reason': f'{self.strategy_name}: Long entry signal',
                'price': last_row.get('close'),
                'stop_loss': last_row.get('close') * (1 + self.stoploss),
                'take_profit': last_row.get('close') * (1 + list(self.minimal_roi.values())[0])
            }
        
        if last_row.get('enter_short', 0) == 1:
            return {
                'action': 'open_short',
                'confidence': 0.8,
                'reason': f'{self.strategy_name}: Short entry signal',
                'price': last_row.get('close'),
                'stop_loss': last_row.get('close') * (1 - self.stoploss),
                'take_profit': last_row.get('close') * (1 - list(self.minimal_roi.values())[0])
            }
        
        # Check for exit signals
        if last_row.get('exit_long', 0) == 1:
            return {
                'action': 'close_long',
                'confidence': 0.9,
                'reason': f'{self.strategy_name}: Long exit signal',
                'price': last_row.get('close')
            }
        
        if last_row.get('exit_short', 0) == 1:
            return {
                'action': 'close_short',
                'confidence': 0.9,
                'reason': f'{self.strategy_name}: Short exit signal',
                'price': last_row.get('close')
            }
        
        # No signal
        return {
            'action': 'hold',
            'confidence': 0.5,
            'reason': f'{self.strategy_name}: No clear signal',
            'price': last_row.get('close')
        }
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                           rate: float, time_in_force: str, **kwargs) -> bool:
        """
        Optional: Confirm trade entry before execution
        
        Returns:
            True to proceed with trade, False to cancel
        """
        return True
    
    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float,
                          rate: float, time_in_force: str, exit_reason: str, **kwargs) -> bool:
        """
        Optional: Confirm trade exit before execution
        
        Returns:
            True to proceed with exit, False to cancel
        """
        return True
    
    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                       current_profit: float, **kwargs) -> float:
        """
        Optional: Custom stop loss logic
        
        Returns:
            Stop loss value (negative float)
        """
        return self.stoploss
