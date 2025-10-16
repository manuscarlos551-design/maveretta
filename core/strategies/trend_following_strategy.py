# core/strategies/trend_following_strategy.py
"""
Trend Following Strategy - Seguir Tendências de Longo Prazo
Identifica e segue tendências fortes do mercado
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    """
    Estratégia de Trend Following
    
    Características:
    - Identifica tendências fortes
    - Aguarda confirmação antes de entrar
    - Stop loss trailing
    - Maximiza ganhos em tendências longas
    """
    
    strategy_name = "TrendFollowing"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.15,  # 15% profit target
        "1440": 0.10,  # 10% após 24h
        "2880": 0.05  # 5% após 48h
    }
    
    stoploss = -0.05  # 5% stop loss
    timeframe = "1h"
    startup_candle_count = 200
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para trend following
        """
        # Múltiplas EMAs para identificar tendência
        dataframe['ema_10'] = dataframe['close'].ewm(span=10, adjust=False).mean()
        dataframe['ema_20'] = dataframe['close'].ewm(span=20, adjust=False).mean()
        dataframe['ema_50'] = dataframe['close'].ewm(span=50, adjust=False).mean()
        dataframe['ema_100'] = dataframe['close'].ewm(span=100, adjust=False).mean()
        dataframe['ema_200'] = dataframe['close'].ewm(span=200, adjust=False).mean()
        
        # ADX (Average Directional Index) para força da tendência
        high_low = dataframe['high'] - dataframe['low']
        high_close = np.abs(dataframe['high'] - dataframe['close'].shift())
        low_close = np.abs(dataframe['low'] - dataframe['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        dataframe['atr'] = true_range.rolling(14).mean()
        
        # +DI e -DI
        plus_dm = dataframe['high'].diff()
        minus_dm = -dataframe['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr_sum = true_range.rolling(14).sum()
        plus_di = 100 * (plus_dm.rolling(14).sum() / tr_sum)
        minus_di = 100 * (minus_dm.rolling(14).sum() / tr_sum)
        
        dataframe['plus_di'] = plus_di
        dataframe['minus_di'] = minus_di
        
        # ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        dataframe['adx'] = dx.rolling(14).mean()
        
        # Supertrend indicator
        hl2 = (dataframe['high'] + dataframe['low']) / 2
        dataframe['basic_ub'] = hl2 + (3 * dataframe['atr'])
        dataframe['basic_lb'] = hl2 - (3 * dataframe['atr'])
        
        # Volume
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entrada em tendências confirmadas
        """
        dataframe.loc[
            (
                # Alinhamento de EMAs (uptrend)
                (dataframe['ema_10'] > dataframe['ema_20']) &
                (dataframe['ema_20'] > dataframe['ema_50']) &
                (dataframe['ema_50'] > dataframe['ema_100']) &
                (dataframe['ema_100'] > dataframe['ema_200']) &
                # ADX indica tendência forte (> 25)
                (dataframe['adx'] > 25) &
                # +DI > -DI (tendência de alta)
                (dataframe['plus_di'] > dataframe['minus_di']) &
                # Preço acima de todas as EMAs
                (dataframe['close'] > dataframe['ema_10']) &
                # Volume confirmando
                (dataframe['volume'] > dataframe['volume_ma'])
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Alinhamento de EMAs (downtrend)
                (dataframe['ema_10'] < dataframe['ema_20']) &
                (dataframe['ema_20'] < dataframe['ema_50']) &
                (dataframe['ema_50'] < dataframe['ema_100']) &
                (dataframe['ema_100'] < dataframe['ema_200']) &
                # ADX indica tendência forte (> 25)
                (dataframe['adx'] > 25) &
                # -DI > +DI (tendência de baixa)
                (dataframe['minus_di'] > dataframe['plus_di']) &
                # Preço abaixo de todas as EMAs
                (dataframe['close'] < dataframe['ema_10']) &
                # Volume confirmando
                (dataframe['volume'] > dataframe['volume_ma'])
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saída quando tendência enfraquece
        """
        dataframe.loc[
            (
                # EMA 10 cruzou abaixo da EMA 20
                ((dataframe['ema_10'] < dataframe['ema_20']) & (dataframe['ema_10'].shift(1) >= dataframe['ema_20'].shift(1))) |
                # ADX caindo abaixo de 20 (tendência fraca)
                (dataframe['adx'] < 20) |
                # -DI cruzou acima de +DI
                ((dataframe['minus_di'] > dataframe['plus_di']) & (dataframe['minus_di'].shift(1) <= dataframe['plus_di'].shift(1)))
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # EMA 10 cruzou acima da EMA 20
                ((dataframe['ema_10'] > dataframe['ema_20']) & (dataframe['ema_10'].shift(1) <= dataframe['ema_20'].shift(1))) |
                # ADX caindo abaixo de 20
                (dataframe['adx'] < 20) |
                # +DI cruzou acima de -DI
                ((dataframe['plus_di'] > dataframe['minus_di']) & (dataframe['plus_di'].shift(1) <= dataframe['minus_di'].shift(1)))
            ),
            'exit_short'] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                       current_profit: float, **kwargs) -> float:
        """
        Trailing stop loss dinâmico
        """
        if current_profit > 0.05:  # Se lucro > 5%
            # Move stop para breakeven + 2%
            return -0.02
        elif current_profit > 0.10:  # Se lucro > 10%
            # Move stop para breakeven + 5%
            return -0.05
        
        return self.stoploss
