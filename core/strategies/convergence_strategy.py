# core/strategies/convergence_strategy.py
"""
Convergence Strategy - Convergência de Ativos
Similar a pair trading mas com foco em convergência de preços
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class ConvergenceStrategy(BaseStrategy):
    """
    Estratégia de Convergence Trade
    
    Características:
    - Opera convergência entre ativos relacionados
    - Pode ser usado para futures vs spot
    - Ou entre diferentes maturities
    - Market neutral quando balanceado
    """
    
    strategy_name = "Convergence"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.035,  # 3.5% profit target
        "480": 0.025,  # 2.5% após 8h
        "960": 0.015  # 1.5% após 16h
    }
    
    stoploss = -0.025  # 2.5% stop loss
    timeframe = "15m"
    startup_candle_count = 100
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para convergence trading
        
        Nota: Simula dados de instrumento relacionado
        Em produção, usaria dados reais de futures/spot
        """
        # Simula preço de instrumento relacionado (ex: futures)
        # Em produção, seria dado real
        dataframe['related_price'] = dataframe['close'] * 1.01  # Premium de 1%
        
        # Basis (diferença entre spot e futures)
        dataframe['basis'] = dataframe['related_price'] - dataframe['close']
        dataframe['basis_pct'] = (dataframe['basis'] / dataframe['close']) * 100
        
        # Média histórica do basis
        dataframe['basis_ma'] = dataframe['basis'].rolling(window=30).mean()
        dataframe['basis_std'] = dataframe['basis'].rolling(window=30).std()
        
        # Z-score do basis
        dataframe['basis_zscore'] = (dataframe['basis'] - dataframe['basis_ma']) / dataframe['basis_std']
        
        # Velocidade de convergência
        dataframe['convergence_speed'] = dataframe['basis'].diff().rolling(window=5).mean()
        
        # Tempo até expiração (simulado)
        # Em produção, seria calculado com data real
        dataframe['days_to_expiry'] = 30  # Fixo para simulação
        
        # Implied carry cost
        dataframe['implied_carry'] = (dataframe['basis'] / dataframe['close']) * (365 / dataframe['days_to_expiry']) * 100
        
        # Volume em ambos instrumentos
        dataframe['volume_spot'] = dataframe['volume']
        dataframe['volume_futures'] = dataframe['volume'] * 0.8  # Simulado
        dataframe['volume_ratio'] = dataframe['volume_spot'] / (dataframe['volume_futures'] + 1)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entrada quando basis diverge da média
        """
        dataframe.loc[
            (
                # Basis muito acima da média (futures overpriced)
                (dataframe['basis_zscore'] > 2.0) &
                # Velocidade de convergência começou
                (dataframe['convergence_speed'] < 0) &
                # Tempo suficiente até expiração
                (dataframe['days_to_expiry'] > 5) &
                # Volume adequado
                (dataframe['volume_ratio'] > 0.5)
            ),
            'enter_long'] = 1  # Long spot, Short futures
        
        dataframe.loc[
            (
                # Basis muito abaixo da média (futures underpriced)
                (dataframe['basis_zscore'] < -2.0) &
                # Velocidade de convergência começou
                (dataframe['convergence_speed'] > 0) &
                # Tempo suficiente até expiração
                (dataframe['days_to_expiry'] > 5) &
                # Volume adequado
                (dataframe['volume_ratio'] > 0.5)
            ),
            'enter_short'] = 1  # Short spot, Long futures
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saída quando basis converge
        """
        dataframe.loc[
            (
                # Basis normalizou
                (dataframe['basis_zscore'] < 0.5) |
                # Próximo da expiração (forçar convergência)
                (dataframe['days_to_expiry'] < 2) |
                # Basis divergiu ainda mais (stop loss)
                (dataframe['basis_zscore'] > 3.0)
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # Basis normalizou
                (dataframe['basis_zscore'] > -0.5) |
                # Próximo da expiração
                (dataframe['days_to_expiry'] < 2) |
                # Basis divergiu ainda mais (stop loss)
                (dataframe['basis_zscore'] < -3.0)
            ),
            'exit_short'] = 1
        
        return dataframe
