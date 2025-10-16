# core/strategies/day_trading_strategy.py
"""
Day Trading Strategy - Operações Intradiárias
Abre e fecha posições no mesmo dia trading
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class DayTradingStrategy(BaseStrategy):
    """
    Estratégia de Day Trading (Intraday)
    
    Características:
    - Fechamento obrigatório de todas posições no final do dia
    - Análise de volatilidade e volume para entradas
    - Múltiplos timeframes para confirmação
    - Stop loss apertado e take profit rápido
    """
    
    strategy_name = "DayTrading"
    strategy_version = "1.0.0"
    
    # Configurações
    minimal_roi = {
        "0": 0.02,  # 2% profit target
        "30": 0.015,  # 1.5% após 30 min
        "60": 0.01  # 1% após 1h
    }
    
    stoploss = -0.015  # 1.5% stop loss
    timeframe = "5m"
    startup_candle_count = 50
    
    # Parâmetros específicos
    volume_threshold = 1.5  # Volume deve ser 1.5x a média
    volatility_threshold = 0.01  # 1% de volatilidade mínima
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calcula indicadores técnicos
        """
        # EMAs
        dataframe['ema_9'] = dataframe['close'].ewm(span=9, adjust=False).mean()
        dataframe['ema_21'] = dataframe['close'].ewm(span=21, adjust=False).mean()
        
        # RSI
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        dataframe['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # ATR (Average True Range) para volatilidade
        high_low = dataframe['high'] - dataframe['low']
        high_close = np.abs(dataframe['high'] - dataframe['close'].shift())
        low_close = np.abs(dataframe['low'] - dataframe['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        dataframe['atr'] = true_range.rolling(14).mean()
        dataframe['atr_pct'] = (dataframe['atr'] / dataframe['close']) * 100
        
        # VWAP (Volume Weighted Average Price)
        dataframe['vwap'] = (dataframe['close'] * dataframe['volume']).cumsum() / dataframe['volume'].cumsum()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de entrada
        """
        dataframe.loc[
            (
                # Tendência de alta (EMA 9 > EMA 21)
                (dataframe['ema_9'] > dataframe['ema_21']) &
                # RSI não está overbought
                (dataframe['rsi'] < 70) &
                (dataframe['rsi'] > 40) &
                # Volume acima da média
                (dataframe['volume_ratio'] > self.volume_threshold) &
                # Volatilidade suficiente
                (dataframe['atr_pct'] > self.volatility_threshold) &
                # Preço acima do VWAP
                (dataframe['close'] > dataframe['vwap'])
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Tendência de baixa (EMA 9 < EMA 21)
                (dataframe['ema_9'] < dataframe['ema_21']) &
                # RSI não está oversold
                (dataframe['rsi'] > 30) &
                (dataframe['rsi'] < 60) &
                # Volume acima da média
                (dataframe['volume_ratio'] > self.volume_threshold) &
                # Volatilidade suficiente
                (dataframe['atr_pct'] > self.volatility_threshold) &
                # Preço abaixo do VWAP
                (dataframe['close'] < dataframe['vwap'])
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de saída
        """
        dataframe.loc[
            (
                # EMA cruzou para baixo
                (dataframe['ema_9'] < dataframe['ema_21']) |
                # RSI overbought
                (dataframe['rsi'] > 75) |
                # Preço caiu abaixo do VWAP
                (dataframe['close'] < dataframe['vwap'])
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # EMA cruzou para cima
                (dataframe['ema_9'] > dataframe['ema_21']) |
                # RSI oversold
                (dataframe['rsi'] < 25) |
                # Preço subiu acima do VWAP
                (dataframe['close'] > dataframe['vwap'])
            ),
            'exit_short'] = 1
        
        return dataframe
