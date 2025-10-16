# core/strategies/scalping_strategy.py
"""
Scalping Strategy - Operações de Altíssima Frequência
Lucros pequenos e rápidos com muitas operações
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class ScalpingStrategy(BaseStrategy):
    """
    Estratégia de Scalping
    
    Características:
    - Operações de 1-5 minutos
    - Take profit pequeno (0.5-1%)
    - Stop loss apertado (0.3-0.5%)
    - Alta frequência de operações
    """
    
    strategy_name = "Scalping"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.01,  # 1% profit target
        "5": 0.007,  # 0.7% após 5 min
        "10": 0.005  # 0.5% após 10 min
    }
    
    stoploss = -0.005  # 0.5% stop loss
    timeframe = "1m"
    startup_candle_count = 30
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para scalping rápido
        """
        # EMAs rápidas
        dataframe['ema_3'] = dataframe['close'].ewm(span=3, adjust=False).mean()
        dataframe['ema_5'] = dataframe['close'].ewm(span=5, adjust=False).mean()
        dataframe['ema_8'] = dataframe['close'].ewm(span=8, adjust=False).mean()
        
        # Spread bid-ask simulado via high-low
        dataframe['spread'] = dataframe['high'] - dataframe['low']
        dataframe['spread_pct'] = (dataframe['spread'] / dataframe['close']) * 100
        
        # Microtrend (mudança de preço em 3 candles)
        dataframe['price_change_3'] = dataframe['close'].pct_change(3) * 100
        
        # Volume instantâneo
        dataframe['volume_ma_5'] = dataframe['volume'].rolling(window=5).mean()
        dataframe['volume_spike'] = dataframe['volume'] / dataframe['volume_ma_5']
        
        # Momentum rápido
        dataframe['momentum'] = dataframe['close'] - dataframe['close'].shift(3)
        
        # Order flow proxy (usando volume e price action)
        dataframe['buy_pressure'] = dataframe['close'] - dataframe['low']
        dataframe['sell_pressure'] = dataframe['high'] - dataframe['close']
        dataframe['pressure_ratio'] = dataframe['buy_pressure'] / (dataframe['sell_pressure'] + 0.0001)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entradas rápidas baseadas em microtrends
        """
        dataframe.loc[
            (
                # EMA rápida acima da lenta
                (dataframe['ema_3'] > dataframe['ema_5']) &
                (dataframe['ema_5'] > dataframe['ema_8']) &
                # Momentum positivo
                (dataframe['momentum'] > 0) &
                # Volume spike
                (dataframe['volume_spike'] > 1.2) &
                # Buy pressure > sell pressure
                (dataframe['pressure_ratio'] > 1.3) &
                # Spread não muito largo
                (dataframe['spread_pct'] < 0.5) &
                # Preço subindo recentemente
                (dataframe['price_change_3'] > 0)
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # EMA rápida abaixo da lenta
                (dataframe['ema_3'] < dataframe['ema_5']) &
                (dataframe['ema_5'] < dataframe['ema_8']) &
                # Momentum negativo
                (dataframe['momentum'] < 0) &
                # Volume spike
                (dataframe['volume_spike'] > 1.2) &
                # Sell pressure > buy pressure
                (dataframe['pressure_ratio'] < 0.7) &
                # Spread não muito largo
                (dataframe['spread_pct'] < 0.5) &
                # Preço caindo recentemente
                (dataframe['price_change_3'] < 0)
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saídas rápidas ao menor sinal de reversão
        """
        dataframe.loc[
            (
                # EMA 3 cruzou abaixo da EMA 5
                ((dataframe['ema_3'] < dataframe['ema_5']) & (dataframe['ema_3'].shift(1) >= dataframe['ema_5'].shift(1))) |
                # Momentum virou negativo
                ((dataframe['momentum'] < 0) & (dataframe['momentum'].shift(1) >= 0)) |
                # Pressure ratio inverteu
                (dataframe['pressure_ratio'] < 1.0)
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # EMA 3 cruzou acima da EMA 5
                ((dataframe['ema_3'] > dataframe['ema_5']) & (dataframe['ema_3'].shift(1) <= dataframe['ema_5'].shift(1))) |
                # Momentum virou positivo
                ((dataframe['momentum'] > 0) & (dataframe['momentum'].shift(1) <= 0)) |
                # Pressure ratio inverteu
                (dataframe['pressure_ratio'] > 1.0)
            ),
            'exit_short'] = 1
        
        return dataframe
