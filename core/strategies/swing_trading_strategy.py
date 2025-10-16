# core/strategies/swing_trading_strategy.py
"""
Swing Trading Strategy - Operações de Médio Prazo
Captura oscilações (swings) entre suporte e resistência
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class SwingTradingStrategy(BaseStrategy):
    """
    Estratégia de Swing Trading
    
    Características:
    - Operações de 2-10 dias
    - Identifica suporte e resistência
    - Múltiplos indicadores de confirmação
    - Risk/Reward mínimo de 1:2
    """
    
    strategy_name = "SwingTrading"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.08,  # 8% profit target
        "360": 0.05,  # 5% após 6h
        "720": 0.03  # 3% após 12h
    }
    
    stoploss = -0.04  # 4% stop loss
    timeframe = "15m"
    startup_candle_count = 100
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calcula indicadores para swing trading
        """
        # Médias móveis
        dataframe['sma_20'] = dataframe['close'].rolling(window=20).mean()
        dataframe['sma_50'] = dataframe['close'].rolling(window=50).mean()
        dataframe['sma_200'] = dataframe['close'].rolling(window=200).mean()
        
        # Bollinger Bands
        std = dataframe['close'].rolling(window=20).std()
        dataframe['bb_upper'] = dataframe['sma_20'] + (2 * std)
        dataframe['bb_middle'] = dataframe['sma_20']
        dataframe['bb_lower'] = dataframe['sma_20'] - (2 * std)
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        
        # RSI
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        dataframe['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = dataframe['close'].ewm(span=12, adjust=False).mean()
        exp2 = dataframe['close'].ewm(span=26, adjust=False).mean()
        dataframe['macd'] = exp1 - exp2
        dataframe['macd_signal'] = dataframe['macd'].ewm(span=9, adjust=False).mean()
        dataframe['macd_hist'] = dataframe['macd'] - dataframe['macd_signal']
        
        # Stochastic
        low_14 = dataframe['low'].rolling(window=14).min()
        high_14 = dataframe['high'].rolling(window=14).max()
        dataframe['stoch'] = 100 * (dataframe['close'] - low_14) / (high_14 - low_14)
        dataframe['stoch_signal'] = dataframe['stoch'].rolling(window=3).mean()
        
        # Support and Resistance (pivots)
        dataframe['pivot'] = (dataframe['high'].shift(1) + dataframe['low'].shift(1) + dataframe['close'].shift(1)) / 3
        dataframe['resistance1'] = 2 * dataframe['pivot'] - dataframe['low'].shift(1)
        dataframe['support1'] = 2 * dataframe['pivot'] - dataframe['high'].shift(1)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Sinais de entrada para swing trading
        """
        dataframe.loc[
            (
                # Preço está em tendência de alta
                (dataframe['sma_20'] > dataframe['sma_50']) &
                (dataframe['sma_50'] > dataframe['sma_200']) &
                # Preço próximo ao suporte (BB lower)
                (dataframe['close'] < dataframe['bb_middle']) &
                (dataframe['close'] > dataframe['bb_lower']) &
                # RSI oversold
                (dataframe['rsi'] < 40) &
                # MACD cruzamento bullish
                (dataframe['macd'] > dataframe['macd_signal']) &
                (dataframe['macd_hist'] > 0) &
                # Stochastic oversold e virando
                (dataframe['stoch'] < 30) &
                (dataframe['stoch'] > dataframe['stoch_signal'])
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Preço está em tendência de baixa
                (dataframe['sma_20'] < dataframe['sma_50']) &
                (dataframe['sma_50'] < dataframe['sma_200']) &
                # Preço próximo à resistência (BB upper)
                (dataframe['close'] > dataframe['bb_middle']) &
                (dataframe['close'] < dataframe['bb_upper']) &
                # RSI overbought
                (dataframe['rsi'] > 60) &
                # MACD cruzamento bearish
                (dataframe['macd'] < dataframe['macd_signal']) &
                (dataframe['macd_hist'] < 0) &
                # Stochastic overbought e virando
                (dataframe['stoch'] > 70) &
                (dataframe['stoch'] < dataframe['stoch_signal'])
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Sinais de saída
        """
        dataframe.loc[
            (
                # Preço atingiu resistência
                (dataframe['close'] >= dataframe['bb_upper']) |
                # RSI overbought
                (dataframe['rsi'] > 70) |
                # MACD bearish crossover
                ((dataframe['macd'] < dataframe['macd_signal']) & (dataframe['macd'].shift(1) >= dataframe['macd_signal'].shift(1)))
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # Preço atingiu suporte
                (dataframe['close'] <= dataframe['bb_lower']) |
                # RSI oversold
                (dataframe['rsi'] < 30) |
                # MACD bullish crossover
                ((dataframe['macd'] > dataframe['macd_signal']) & (dataframe['macd'].shift(1) <= dataframe['macd_signal'].shift(1)))
            ),
            'exit_short'] = 1
        
        return dataframe
