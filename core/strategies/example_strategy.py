# core/strategies/example_strategy.py
"""
Example Strategy - Simple EMA Crossover Strategy
Demonstrates how to implement a concrete strategy
"""

import pandas as pd
import numpy as np
from typing import Dict
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


def ema(series: pd.Series, length: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return series.ewm(span=length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return series.rolling(window=length).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def bollinger_bands(series: pd.Series, length: int = 20, std: float = 2.0) -> tuple:
    """Calculate Bollinger Bands"""
    middle = series.rolling(window=length).mean()
    std_dev = series.rolling(window=length).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return upper, middle, lower


class ExampleStrategy(BaseStrategy):
    """
    Simple EMA (Exponential Moving Average) Crossover Strategy
    
    Entry Signal (Long):
    - Fast EMA crosses above Slow EMA
    - Volume is above average
    
    Exit Signal (Long):
    - Fast EMA crosses below Slow EMA
    - OR profit target reached
    - OR stop loss hit
    """
    
    # Strategy metadata
    strategy_name = "EMA_Crossover"
    strategy_version = "1.0.0"
    
    # Strategy parameters
    ema_short_period = 9
    ema_long_period = 21
    volume_ma_period = 20
    
    # Risk management
    minimal_roi = {
        "0": 0.02,   # 2% profit target
        "30": 0.01,  # After 30 minutes, 1% profit
        "60": 0.005  # After 1 hour, 0.5% profit
    }
    
    stoploss = -0.03  # 3% stop loss
    
    # Timeframe
    timeframe = "5m"
    
    # Startup candles needed
    startup_candle_count = 30
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calculate EMA indicators
        
        Args:
            dataframe: Raw OHLCV data
            metadata: Symbol and timeframe info
        
        Returns:
            Dataframe with EMA indicators
        """
        try:
            # Calculate EMAs
            dataframe['ema_short'] = ema(dataframe['close'], self.ema_short_period)
            dataframe['ema_long'] = ema(dataframe['close'], self.ema_long_period)
            
            # Calculate volume moving average
            dataframe['volume_ma'] = sma(dataframe['volume'], self.volume_ma_period)
            
            # Additional indicators for confirmation
            dataframe['rsi'] = rsi(dataframe['close'], 14)
            
            logger.debug(f"Indicators calculated for {metadata.get('pair', 'unknown')}")
            
            return dataframe
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            raise
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define entry signals
        
        Long Entry Conditions:
        1. Fast EMA crosses above Slow EMA
        2. Volume above average (confirmation)
        3. RSI not overbought (< 70)
        
        Args:
            dataframe: Dataframe with indicators
            metadata: Symbol and timeframe info
        
        Returns:
            Dataframe with entry signals
        """
        # Initialize signal columns
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        # Long entry conditions
        dataframe.loc[
            (
                # EMA crossover (fast crosses above slow)
                (dataframe['ema_short'] > dataframe['ema_long']) &
                (dataframe['ema_short'].shift(1) <= dataframe['ema_long'].shift(1)) &
                
                # Volume confirmation
                (dataframe['volume'] > dataframe['volume_ma']) &
                
                # RSI filter (not overbought)
                (dataframe['rsi'] < 70)
            ),
            'enter_long'
        ] = 1
        
        # Short entry conditions (inverse logic)
        dataframe.loc[
            (
                # EMA crossunder (fast crosses below slow)
                (dataframe['ema_short'] < dataframe['ema_long']) &
                (dataframe['ema_short'].shift(1) >= dataframe['ema_long'].shift(1)) &
                
                # Volume confirmation
                (dataframe['volume'] > dataframe['volume_ma']) &
                
                # RSI filter (not oversold)
                (dataframe['rsi'] > 30)
            ),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define exit signals
        
        Long Exit Conditions:
        - Fast EMA crosses below Slow EMA
        
        Short Exit Conditions:
        - Fast EMA crosses above Slow EMA
        
        Args:
            dataframe: Dataframe with indicators
            metadata: Symbol and timeframe info
        
        Returns:
            Dataframe with exit signals
        """
        # Initialize signal columns
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        # Long exit conditions
        dataframe.loc[
            (
                # EMA crossunder
                (dataframe['ema_short'] < dataframe['ema_long']) &
                (dataframe['ema_short'].shift(1) >= dataframe['ema_long'].shift(1))
            ),
            'exit_long'
        ] = 1
        
        # Short exit conditions
        dataframe.loc[
            (
                # EMA crossover
                (dataframe['ema_short'] > dataframe['ema_long']) &
                (dataframe['ema_short'].shift(1) <= dataframe['ema_long'].shift(1))
            ),
            'exit_short'
        ] = 1
        
        return dataframe


class ScalpingStrategy(BaseStrategy):
    """
    Aggressive scalping strategy for quick profits
    """
    
    strategy_name = "Scalping_RSI_BB"
    strategy_version = "1.0.0"
    
    # Faster timeframe
    timeframe = "1m"
    
    # Tight profit targets
    minimal_roi = {
        "0": 0.005,  # 0.5% profit target
    }
    
    stoploss = -0.02  # 2% stop loss
    
    startup_candle_count = 20
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Calculate RSI and Bollinger Bands"""
        # RSI
        dataframe['rsi'] = rsi(dataframe['close'], 14)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = bollinger_bands(dataframe['close'], 20, 2.0)
        dataframe['bb_upper'] = bb_upper
        dataframe['bb_middle'] = bb_middle
        dataframe['bb_lower'] = bb_lower
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Entry when oversold and bouncing from lower BB"""
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        # Long: RSI oversold + price at lower BB
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['close'] <= dataframe['bb_lower'])
            ),
            'enter_long'
        ] = 1
        
        # Short: RSI overbought + price at upper BB
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) &
                (dataframe['close'] >= dataframe['bb_upper'])
            ),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Exit when reaching middle BB or opposite extreme"""
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        # Exit long when price reaches middle BB or RSI overbought
        dataframe.loc[
            (
                (dataframe['close'] >= dataframe['bb_middle']) |
                (dataframe['rsi'] > 70)
            ),
            'exit_long'
        ] = 1
        
        # Exit short when price reaches middle BB or RSI oversold
        dataframe.loc[
            (
                (dataframe['close'] <= dataframe['bb_middle']) |
                (dataframe['rsi'] < 30)
            ),
            'exit_short'
        ] = 1
        
        return dataframe
