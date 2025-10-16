# core/strategies/mean_reversion_strategy.py
"""
Mean Reversion Strategy - Reversão à Média
Aposta que preço retornará à média após movimento extremo
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """
    Estratégia de Mean Reversion
    
    Características:
    - Identifica afastamentos extremos da média
    - Opera contra a tendência de curto prazo
    - Baseada em Bollinger Bands e Z-Score
    - Stop loss importante (pode falhar se tendência continuar)
    """
    
    strategy_name = "MeanReversion"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.03,  # 3% profit target
        "120": 0.02,  # 2% após 2h
        "240": 0.01  # 1% após 4h
    }
    
    stoploss = -0.03  # 3% stop loss
    timeframe = "15m"
    startup_candle_count = 50
    
    # Thresholds
    zscore_threshold = 2.0  # 2 desvios padrão
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para mean reversion
        """
        # Média móvel
        dataframe['sma_20'] = dataframe['close'].rolling(window=20).mean()
        dataframe['sma_50'] = dataframe['close'].rolling(window=50).mean()
        
        # Desvio padrão
        dataframe['std_20'] = dataframe['close'].rolling(window=20).std()
        
        # Z-Score (quantos desvios padrão o preço está da média)
        dataframe['zscore'] = (dataframe['close'] - dataframe['sma_20']) / dataframe['std_20']
        
        # Bollinger Bands
        dataframe['bb_upper'] = dataframe['sma_20'] + (2 * dataframe['std_20'])
        dataframe['bb_middle'] = dataframe['sma_20']
        dataframe['bb_lower'] = dataframe['sma_20'] - (2 * dataframe['std_20'])
        
        # Posição dentro das Bollinger Bands
        dataframe['bb_position'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])
        
        # RSI para confirmação
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        dataframe['rsi'] = 100 - (100 / (1 + rs))
        
        # Keltner Channels (alternativa)
        dataframe['ema_20'] = dataframe['close'].ewm(span=20, adjust=False).mean()
        high_low = dataframe['high'] - dataframe['low']
        high_close = np.abs(dataframe['high'] - dataframe['close'].shift())
        low_close = np.abs(dataframe['low'] - dataframe['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        dataframe['atr'] = true_range.rolling(14).mean()
        
        dataframe['kc_upper'] = dataframe['ema_20'] + (1.5 * dataframe['atr'])
        dataframe['kc_lower'] = dataframe['ema_20'] - (1.5 * dataframe['atr'])
        
        # Mean reversion score
        dataframe['reversion_score'] = abs(dataframe['zscore'])
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Compra quando preço está muito abaixo da média
        Vende quando preço está muito acima da média
        """
        dataframe.loc[
            (
                # Preço muito abaixo da média (oversold)
                (dataframe['zscore'] < -self.zscore_threshold) &
                # Preço abaixo da banda inferior de Bollinger
                (dataframe['close'] < dataframe['bb_lower']) &
                # RSI oversold
                (dataframe['rsi'] < 30) &
                # Preço também abaixo de Keltner inferior
                (dataframe['close'] < dataframe['kc_lower']) &
                # Score alto de reversão
                (dataframe['reversion_score'] > self.zscore_threshold)
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Preço muito acima da média (overbought)
                (dataframe['zscore'] > self.zscore_threshold) &
                # Preço acima da banda superior de Bollinger
                (dataframe['close'] > dataframe['bb_upper']) &
                # RSI overbought
                (dataframe['rsi'] > 70) &
                # Preço também acima de Keltner superior
                (dataframe['close'] > dataframe['kc_upper']) &
                # Score alto de reversão
                (dataframe['reversion_score'] > self.zscore_threshold)
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Sai quando preço retorna à média
        """
        dataframe.loc[
            (
                # Preço voltou para a média
                (dataframe['zscore'] > -0.5) |
                # Ou cruzou a banda do meio
                ((dataframe['close'] > dataframe['bb_middle']) & (dataframe['close'].shift(1) <= dataframe['bb_middle'].shift(1))) |
                # Ou RSI normalizou
                (dataframe['rsi'] > 50)
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # Preço voltou para a média
                (dataframe['zscore'] < 0.5) |
                # Ou cruzou a banda do meio
                ((dataframe['close'] < dataframe['bb_middle']) & (dataframe['close'].shift(1) >= dataframe['bb_middle'].shift(1))) |
                # Ou RSI normalizou
                (dataframe['rsi'] < 50)
            ),
            'exit_short'] = 1
        
        return dataframe
