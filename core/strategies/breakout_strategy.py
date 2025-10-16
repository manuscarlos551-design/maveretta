# core/strategies/breakout_strategy.py
"""
Breakout Strategy - Rompe Suporte/Resistência
Identifica e opera rompimentos de níveis importantes
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class BreakoutStrategy(BaseStrategy):
    """
    Estratégia de Breakout (Ruptura)
    
    Características:
    - Identifica níveis de suporte e resistência
    - Opera rompimentos com volume
    - Aguarda confirmação de breakout
    - Stop loss abaixo do nível rompido
    """
    
    strategy_name = "Breakout"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.06,  # 6% profit target
        "180": 0.04,  # 4% após 3h
        "360": 0.02  # 2% após 6h
    }
    
    stoploss = -0.03  # 3% stop loss
    timeframe = "15m"
    startup_candle_count = 100
    
    # Volume threshold para confirmar breakout
    volume_multiplier = 1.8
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para detectar breakouts
        """
        # Máximas e mínimas recentes (suporte/resistência)
        dataframe['resistance'] = dataframe['high'].rolling(window=20).max()
        dataframe['support'] = dataframe['low'].rolling(window=20).min()
        
        # Distância do preço até resistência/suporte
        dataframe['dist_resistance'] = ((dataframe['resistance'] - dataframe['close']) / dataframe['close']) * 100
        dataframe['dist_support'] = ((dataframe['close'] - dataframe['support']) / dataframe['close']) * 100
        
        # Volume médio
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # Range (volatility)
        dataframe['range'] = dataframe['high'] - dataframe['low']
        dataframe['range_ma'] = dataframe['range'].rolling(window=20).mean()
        dataframe['range_ratio'] = dataframe['range'] / dataframe['range_ma']
        
        # ATR para stop loss dinâmico
        high_low = dataframe['high'] - dataframe['low']
        high_close = np.abs(dataframe['high'] - dataframe['close'].shift())
        low_close = np.abs(dataframe['low'] - dataframe['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        dataframe['atr'] = true_range.rolling(14).mean()
        
        # Donchian Channels (alternativa para identificar breakouts)
        dataframe['donchian_high'] = dataframe['high'].rolling(window=20).max()
        dataframe['donchian_low'] = dataframe['low'].rolling(window=20).min()
        dataframe['donchian_mid'] = (dataframe['donchian_high'] + dataframe['donchian_low']) / 2
        
        # Consolidation detection (preço em range apertado)
        dataframe['price_std'] = dataframe['close'].rolling(window=20).std()
        dataframe['is_consolidating'] = dataframe['price_std'] < (dataframe['close'] * 0.02)  # 2% std
        
        # RSI para filter
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        dataframe['rsi'] = 100 - (100 / (1 + rs))
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entrada em breakouts confirmados
        """
        dataframe.loc[
            (
                # Preço rompeu resistência
                (dataframe['close'] > dataframe['resistance'].shift(1)) &
                # Confirmação: close do candle acima da resistência
                (dataframe['close'] > dataframe['donchian_high'].shift(1)) &
                # Volume elevado (confirmação)
                (dataframe['volume_ratio'] > self.volume_multiplier) &
                # Range do candle maior que média (movimento forte)
                (dataframe['range_ratio'] > 1.2) &
                # RSI não muito overbought
                (dataframe['rsi'] < 75) &
                # Estava consolidando antes
                (dataframe['is_consolidating'].shift(1) == True)
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Preço rompeu suporte
                (dataframe['close'] < dataframe['support'].shift(1)) &
                # Confirmação: close do candle abaixo do suporte
                (dataframe['close'] < dataframe['donchian_low'].shift(1)) &
                # Volume elevado
                (dataframe['volume_ratio'] > self.volume_multiplier) &
                # Range do candle maior que média
                (dataframe['range_ratio'] > 1.2) &
                # RSI não muito oversold
                (dataframe['rsi'] > 25) &
                # Estava consolidando antes
                (dataframe['is_consolidating'].shift(1) == True)
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saída se breakout falhar (falso breakout)
        """
        dataframe.loc[
            (
                # Preço voltou abaixo da resistência rompida
                (dataframe['close'] < dataframe['resistance'].shift(1)) |
                # Ou volume caiu significativamente
                (dataframe['volume_ratio'] < 0.5) |
                # Ou RSI muito overbought
                (dataframe['rsi'] > 80)
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # Preço voltou acima do suporte rompido
                (dataframe['close'] > dataframe['support'].shift(1)) |
                # Ou volume caiu significativamente
                (dataframe['volume_ratio'] < 0.5) |
                # Ou RSI muito oversold
                (dataframe['rsi'] < 20)
            ),
            'exit_short'] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                       current_profit: float, **kwargs) -> float:
        """
        Stop loss baseado em ATR
        """
        # Em produção, usaria ATR do momento de entrada
        # Por simplicidade, usa stop loss fixo
        return self.stoploss
