# core/strategies/hft_strategy.py
"""
High-Frequency Trading Strategy - Trading de Altíssima Frequência
Explora microestruturas de mercado e order flow
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class HFTStrategy(BaseStrategy):
    """
    Estratégia de High-Frequency Trading (HFT)
    
    Características:
    - Operações em frações de segundo
    - Explora microestruturas de mercado
    - Baseado em order book imbalance
    - Lucros minimos por trade, alta frequência
    
    AVISO: HFT real requer infraestrutura especializada
    Esta é uma simulação didática
    """
    
    strategy_name = "HFT"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.003,  # 0.3% profit target
        "1": 0.002,  # 0.2% após 1 min
        "2": 0.001  # 0.1% após 2 min
    }
    
    stoploss = -0.002  # 0.2% stop loss
    timeframe = "1m"
    startup_candle_count = 20
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para HFT (baseado em price action micro)
        """
        # Microtrend (mudança instantânea)
        dataframe['price_change_1'] = dataframe['close'].diff()
        dataframe['price_change_pct'] = dataframe['close'].pct_change() * 100
        
        # Order flow proxy (usando volume e wick analysis)
        dataframe['upper_wick'] = dataframe['high'] - dataframe[['open', 'close']].max(axis=1)
        dataframe['lower_wick'] = dataframe[['open', 'close']].min(axis=1) - dataframe['low']
        dataframe['body'] = abs(dataframe['close'] - dataframe['open'])
        
        # Wick ratio (seller vs buyer pressure)
        dataframe['wick_ratio'] = dataframe['lower_wick'] / (dataframe['upper_wick'] + 0.0001)
        
        # Imbalance proxy
        dataframe['buy_volume'] = dataframe['volume'] * (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['sell_volume'] = dataframe['volume'] * (dataframe['close'] <= dataframe['open']).astype(int)
        dataframe['volume_imbalance'] = (dataframe['buy_volume'] - dataframe['sell_volume']) / (dataframe['volume'] + 1)
        
        # Tick direction
        dataframe['tick_up'] = (dataframe['close'] > dataframe['close'].shift(1)).astype(int)
        dataframe['tick_down'] = (dataframe['close'] < dataframe['close'].shift(1)).astype(int)
        dataframe['tick_balance'] = dataframe['tick_up'].rolling(5).sum() - dataframe['tick_down'].rolling(5).sum()
        
        # Spread proxy (high-low)
        dataframe['spread'] = dataframe['high'] - dataframe['low']
        dataframe['spread_pct'] = (dataframe['spread'] / dataframe['close']) * 100
        
        # Momentum microscópico
        dataframe['micro_momentum'] = dataframe['close'].rolling(3).mean() - dataframe['close'].rolling(5).mean()
        
        # Volatility spike
        dataframe['volatility'] = dataframe['close'].rolling(10).std()
        dataframe['volatility_spike'] = dataframe['volatility'] / dataframe['volatility'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entradas baseadas em microestruturas
        """
        dataframe.loc[
            (
                # Imbalance positivo (mais compras)
                (dataframe['volume_imbalance'] > 0.3) &
                # Tick balance positivo
                (dataframe['tick_balance'] > 2) &
                # Wick ratio indica pressão compradora
                (dataframe['wick_ratio'] > 1.5) &
                # Spread não muito largo
                (dataframe['spread_pct'] < 0.1) &
                # Momentum micro positivo
                (dataframe['micro_momentum'] > 0) &
                # Volatilidade controlada
                (dataframe['volatility_spike'] < 2.0)
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Imbalance negativo (mais vendas)
                (dataframe['volume_imbalance'] < -0.3) &
                # Tick balance negativo
                (dataframe['tick_balance'] < -2) &
                # Wick ratio indica pressão vendedora
                (dataframe['wick_ratio'] < 0.7) &
                # Spread não muito largo
                (dataframe['spread_pct'] < 0.1) &
                # Momentum micro negativo
                (dataframe['micro_momentum'] < 0) &
                # Volatilidade controlada
                (dataframe['volatility_spike'] < 2.0)
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saídas rápidas ao menor sinal de reversão
        """
        dataframe.loc[
            (
                # Imbalance inverteu
                (dataframe['volume_imbalance'] < 0) |
                # Tick balance inverteu
                (dataframe['tick_balance'] < 0) |
                # Spread alargou (liquidez caiu)
                (dataframe['spread_pct'] > 0.15) |
                # Volatilidade spike (risco)
                (dataframe['volatility_spike'] > 2.5)
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # Imbalance inverteu
                (dataframe['volume_imbalance'] > 0) |
                # Tick balance inverteu
                (dataframe['tick_balance'] > 0) |
                # Spread alargou
                (dataframe['spread_pct'] > 0.15) |
                # Volatilidade spike
                (dataframe['volatility_spike'] > 2.5)
            ),
            'exit_short'] = 1
        
        return dataframe
