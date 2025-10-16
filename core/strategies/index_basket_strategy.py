# core/strategies/index_basket_strategy.py
"""
Index/Basket Trading Strategy - Operação em Índice/Cesta
Negocia baseado no desempenho coletivo de múltiplos ativos
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class IndexBasketStrategy(BaseStrategy):
    """
    Estratégia de Index/Basket Trading
    
    Características:
    - Opera baseado em índice de múltiplos ativos
    - Diversifica risco automaticamente
    - Pode rebalancear pesos dinamicamente
    - Foco em performance agregada
    """
    
    strategy_name = "IndexBasket"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.05,  # 5% profit target
        "720": 0.035,  # 3.5% após 12h
        "1440": 0.02  # 2% após 24h
    }
    
    stoploss = -0.03  # 3% stop loss
    timeframe = "1h"
    startup_candle_count = 100
    
    # Pesos dos ativos na cesta (exemplo)
    # Em produção, seria configurado dinamicamente
    basket_weights = {
        'BTC': 0.5,
        'ETH': 0.3,
        'BNB': 0.1,
        'ADA': 0.1
    }
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para basket trading
        
        Nota: Simula preços de múltiplos ativos
        Em produção, usaria dados reais de todos ativos da cesta
        """
        # Simula preços de outros ativos da cesta
        # Em produção, seria dados reais
        dataframe['asset_1'] = dataframe['close']  # BTC
        dataframe['asset_2'] = dataframe['close'] * 0.05  # ETH
        dataframe['asset_3'] = dataframe['close'] * 0.01  # BNB
        dataframe['asset_4'] = dataframe['close'] * 0.001  # ADA
        
        # Calcula índice ponderado
        dataframe['index_value'] = (
            dataframe['asset_1'] * 0.5 +
            dataframe['asset_2'] * 0.3 +
            dataframe['asset_3'] * 0.1 +
            dataframe['asset_4'] * 0.1
        )
        
        # Médias do índice
        dataframe['index_sma_20'] = dataframe['index_value'].rolling(window=20).mean()
        dataframe['index_sma_50'] = dataframe['index_value'].rolling(window=50).mean()
        dataframe['index_ema_12'] = dataframe['index_value'].ewm(span=12, adjust=False).mean()
        dataframe['index_ema_26'] = dataframe['index_value'].ewm(span=26, adjust=False).mean()
        
        # MACD do índice
        dataframe['index_macd'] = dataframe['index_ema_12'] - dataframe['index_ema_26']
        dataframe['index_macd_signal'] = dataframe['index_macd'].ewm(span=9, adjust=False).mean()
        
        # Performance individual dos ativos
        dataframe['asset_1_return'] = dataframe['asset_1'].pct_change()
        dataframe['asset_2_return'] = dataframe['asset_2'].pct_change()
        dataframe['asset_3_return'] = dataframe['asset_3'].pct_change()
        dataframe['asset_4_return'] = dataframe['asset_4'].pct_change()
        
        # Correlação média entre ativos
        # Simplified: usar apenas 2 assets
        dataframe['correlation'] = dataframe['asset_1_return'].rolling(window=20).corr(dataframe['asset_2_return'])
        
        # Volatilidade do índice
        dataframe['index_volatility'] = dataframe['index_value'].rolling(window=20).std()
        
        # Divergence detection (quando asset principal diverge do índice)
        dataframe['divergence'] = (dataframe['close'] / dataframe['index_value']) - 1
        dataframe['divergence_ma'] = dataframe['divergence'].rolling(window=10).mean()
        
        # Strength index (quantos ativos estão em uptrend)
        dataframe['assets_up'] = (
            (dataframe['asset_1'] > dataframe['asset_1'].shift(1)).astype(int) +
            (dataframe['asset_2'] > dataframe['asset_2'].shift(1)).astype(int) +
            (dataframe['asset_3'] > dataframe['asset_3'].shift(1)).astype(int) +
            (dataframe['asset_4'] > dataframe['asset_4'].shift(1)).astype(int)
        )
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entrada baseada em tendência do índice
        """
        dataframe.loc[
            (
                # Índice em uptrend
                (dataframe['index_sma_20'] > dataframe['index_sma_50']) &
                # MACD bullish
                (dataframe['index_macd'] > dataframe['index_macd_signal']) &
                # Maioria dos ativos em alta
                (dataframe['assets_up'] >= 3) &
                # Correlação positiva (ativos movendo juntos)
                (dataframe['correlation'] > 0.5) &
                # Volatilidade não muito alta
                (dataframe['index_volatility'] < dataframe['index_value'] * 0.05)
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Índice em downtrend
                (dataframe['index_sma_20'] < dataframe['index_sma_50']) &
                # MACD bearish
                (dataframe['index_macd'] < dataframe['index_macd_signal']) &
                # Maioria dos ativos em queda
                (dataframe['assets_up'] <= 1) &
                # Correlação positiva
                (dataframe['correlation'] > 0.5) &
                # Volatilidade não muito alta
                (dataframe['index_volatility'] < dataframe['index_value'] * 0.05)
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saída quando índice perde força
        """
        dataframe.loc[
            (
                # MACD bearish crossover
                ((dataframe['index_macd'] < dataframe['index_macd_signal']) & 
                 (dataframe['index_macd'].shift(1) >= dataframe['index_macd_signal'].shift(1))) |
                # Assets pararam de subir
                (dataframe['assets_up'] < 2) |
                # Volatilidade spike
                (dataframe['index_volatility'] > dataframe['index_value'] * 0.08)
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # MACD bullish crossover
                ((dataframe['index_macd'] > dataframe['index_macd_signal']) & 
                 (dataframe['index_macd'].shift(1) <= dataframe['index_macd_signal'].shift(1))) |
                # Assets pararam de cair
                (dataframe['assets_up'] > 2) |
                # Volatilidade spike
                (dataframe['index_volatility'] > dataframe['index_value'] * 0.08)
            ),
            'exit_short'] = 1
        
        return dataframe
