# core/strategies/pair_trading_strategy.py
"""
Pair Trading Strategy - Trading de Pares Correlacionados
Explora convergência de ativos correlacionados
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class PairTradingStrategy(BaseStrategy):
    """
    Estratégia de Pair Trading
    
    Características:
    - Opera dois ativos correlacionados
    - Long no ativo subvalorizado, Short no sobrevalorizado
    - Market neutral (hedge)
    - Baseado em spread e z-score
    """
    
    strategy_name = "PairTrading"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.04,  # 4% profit target
        "360": 0.03,  # 3% após 6h
        "720": 0.02  # 2% após 12h
    }
    
    stoploss = -0.03  # 3% stop loss
    timeframe = "15m"
    startup_candle_count = 100
    
    # Par correlacionado (exemplo: ETH quando trading BTC)
    # Em produção, seria configurado dinamicamente
    correlation_threshold = 0.7
    zscore_entry = 2.0
    zscore_exit = 0.5
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Indicadores para pair trading
        
        Nota: Em produção real, precisaria dados de ambos os pares
        Aqui simulamos com análise de ratio e desvios
        """
        # Simula preço do par correlacionado usando transformação
        # Em produção, seria dados reais de outro par
        dataframe['pair_price'] = dataframe['close'] * 0.05  # Simula ETH/BTC ratio
        
        # Spread (ratio entre os dois ativos)
        dataframe['spread'] = dataframe['close'] / dataframe['pair_price']
        
        # Média e desvio padrão do spread
        dataframe['spread_ma'] = dataframe['spread'].rolling(window=30).mean()
        dataframe['spread_std'] = dataframe['spread'].rolling(window=30).std()
        
        # Z-Score do spread
        dataframe['spread_zscore'] = (dataframe['spread'] - dataframe['spread_ma']) / dataframe['spread_std']
        
        # Correlação rolling
        dataframe['correlation'] = dataframe['close'].rolling(window=30).corr(dataframe['pair_price'])
        
        # Half-life of mean reversion (simplified)
        # Indica quão rápido o spread tende a reverter
        spread_change = dataframe['spread'].diff()
        dataframe['mean_revert_speed'] = abs(spread_change) / dataframe['spread_std']
        
        # Beta (sensibilidade relativa)
        returns_asset = dataframe['close'].pct_change()
        returns_pair = dataframe['pair_price'].pct_change()
        
        covariance = returns_asset.rolling(window=30).cov(returns_pair)
        pair_variance = returns_pair.rolling(window=30).var()
        dataframe['beta'] = covariance / pair_variance
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entrada quando spread diverge significativamente
        """
        dataframe.loc[
            (
                # Spread muito abaixo da média (Asset A undervalued vs Asset B)
                (dataframe['spread_zscore'] < -self.zscore_entry) &
                # Correlação ainda forte
                (abs(dataframe['correlation']) > self.correlation_threshold) &
                # Velocidade de reversão dentro do esperado
                (dataframe['mean_revert_speed'] < 2.0)
            ),
            'enter_long'] = 1  # Long Asset A, Short Asset B
        
        dataframe.loc[
            (
                # Spread muito acima da média (Asset A overvalued vs Asset B)
                (dataframe['spread_zscore'] > self.zscore_entry) &
                # Correlação ainda forte
                (abs(dataframe['correlation']) > self.correlation_threshold) &
                # Velocidade de reversão dentro do esperado
                (dataframe['mean_revert_speed'] < 2.0)
            ),
            'enter_short'] = 1  # Short Asset A, Long Asset B
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saída quando spread converge
        """
        dataframe.loc[
            (
                # Spread voltou próximo da média
                (dataframe['spread_zscore'] > -self.zscore_exit) |
                # Ou correlação quebrou
                (abs(dataframe['correlation']) < 0.5) |
                # Ou spread divergiu ainda mais (stop loss)
                (dataframe['spread_zscore'] < -3.0)
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # Spread voltou próximo da média
                (dataframe['spread_zscore'] < self.zscore_exit) |
                # Ou correlação quebrou
                (abs(dataframe['correlation']) < 0.5) |
                # Ou spread divergiu ainda mais (stop loss)
                (dataframe['spread_zscore'] > 3.0)
            ),
            'exit_short'] = 1
        
        return dataframe
