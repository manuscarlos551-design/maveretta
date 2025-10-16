# core/strategies/fading_strategy.py
"""
Fading Strategy - Contra-Tendência
Aposta contra movimentos exagerados (fade the move)
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class FadingStrategy(BaseStrategy):
    """
    Estratégia de Fading (Contra-Tendência)
    
    Características:
    - Opera contra movimentos exagerados
    - Identifica exaustão de tendência
    - Alto risco, requer timing preciso
    - Stop loss apertado
    """
    
    strategy_name = "Fading"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.025,  # 2.5% profit target
        "60": 0.015,  # 1.5% após 1h
        "120": 0.01  # 1% após 2h
    }
    
    stoploss = -0.02  # 2% stop loss
    timeframe = "15m"
    startup_candle_count = 50
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para detectar movimentos exagerados
        """
        # Mudança de preço recente
        dataframe['price_change_5'] = dataframe['close'].pct_change(5) * 100
        dataframe['price_change_10'] = dataframe['close'].pct_change(10) * 100
        
        # RSI
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        dataframe['rsi'] = 100 - (100 / (1 + rs))
        
        # Stochastic RSI (mais sensível)
        rsi_min = dataframe['rsi'].rolling(window=14).min()
        rsi_max = dataframe['rsi'].rolling(window=14).max()
        dataframe['stoch_rsi'] = (dataframe['rsi'] - rsi_min) / (rsi_max - rsi_min)
        
        # Volume
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # Bollinger Bands %B
        sma_20 = dataframe['close'].rolling(window=20).mean()
        std_20 = dataframe['close'].rolling(window=20).std()
        bb_upper = sma_20 + (2 * std_20)
        bb_lower = sma_20 - (2 * std_20)
        dataframe['bb_percent'] = (dataframe['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # Williams %R (indica overbought/oversold)
        high_14 = dataframe['high'].rolling(window=14).max()
        low_14 = dataframe['low'].rolling(window=14).min()
        dataframe['williams_r'] = -100 * (high_14 - dataframe['close']) / (high_14 - low_14)
        
        # CCI (Commodity Channel Index)
        tp = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        sma_tp = tp.rolling(window=20).mean()
        mad = tp.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean())
        dataframe['cci'] = (tp - sma_tp) / (0.015 * mad)
        
        # Exhaustion indicators
        dataframe['is_exhausted_up'] = (
            (dataframe['rsi'] > 75) &
            (dataframe['stoch_rsi'] > 0.9) &
            (dataframe['bb_percent'] > 1.0) &
            (dataframe['williams_r'] > -10) &
            (dataframe['cci'] > 150)
        )
        
        dataframe['is_exhausted_down'] = (
            (dataframe['rsi'] < 25) &
            (dataframe['stoch_rsi'] < 0.1) &
            (dataframe['bb_percent'] < 0.0) &
            (dataframe['williams_r'] < -90) &
            (dataframe['cci'] < -150)
        )
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Fade em movimentos exagerados de alta/baixa
        """
        dataframe.loc[
            (
                # Movimento exagerado de baixa (fade para cima)
                (dataframe['is_exhausted_down'] == True) &
                # Queda recente significativa
                (dataframe['price_change_5'] < -3) &
                # Volume alto (panic selling)
                (dataframe['volume_ratio'] > 1.5) &
                # Primeiros sinais de reversão
                (dataframe['rsi'] > dataframe['rsi'].shift(1))
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Movimento exagerado de alta (fade para baixo)
                (dataframe['is_exhausted_up'] == True) &
                # Subida recente significativa
                (dataframe['price_change_5'] > 3) &
                # Volume alto (euphoria buying)
                (dataframe['volume_ratio'] > 1.5) &
                # Primeiros sinais de reversão
                (dataframe['rsi'] < dataframe['rsi'].shift(1))
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saída rápida se reversão continuar contra posição
        """
        dataframe.loc[
            (
                # RSI normalizou
                (dataframe['rsi'] > 50) |
                # Ou preço voltou a cair
                (dataframe['price_change_5'] < -1) |
                # Ou volume secou (sem força)
                (dataframe['volume_ratio'] < 0.7)
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # RSI normalizou
                (dataframe['rsi'] < 50) |
                # Ou preço voltou a subir
                (dataframe['price_change_5'] > 1) |
                # Ou volume secou
                (dataframe['volume_ratio'] < 0.7)
            ),
            'exit_short'] = 1
        
        return dataframe
