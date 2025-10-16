# core/strategies/ml_rl_strategy.py
"""
ML/RL Strategy - Baseada em Machine Learning e Reinforcement Learning
Usa modelos preditivos para tomada de decisão
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class MLRLStrategy(BaseStrategy):
    """
    Estratégia baseada em Machine Learning / Reinforcement Learning
    
    Características:
    - Usa features de mercado para predição
    - Modelo treinado continuamente
    - Adapta-se a condições de mercado
    - Pode combinar múltiplos modelos (ensemble)
    
    Nota: Esta é uma versão simplificada
    Em produção, usaria modelos reais treinados
    """
    
    strategy_name = "ML_RL"
    strategy_version = "1.0.0"
    
    minimal_roi = {
        "0": 0.04,  # 4% profit target
        "240": 0.03,  # 3% após 4h
        "480": 0.02  # 2% após 8h
    }
    
    stoploss = -0.025  # 2.5% stop loss
    timeframe = "15m"
    startup_candle_count = 100
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Cria features para modelo ML
        """
        # ===== PRICE FEATURES =====
        # Returns
        dataframe['returns_1'] = dataframe['close'].pct_change(1)
        dataframe['returns_5'] = dataframe['close'].pct_change(5)
        dataframe['returns_10'] = dataframe['close'].pct_change(10)
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            dataframe[f'sma_{period}'] = dataframe['close'].rolling(window=period).mean()
            dataframe[f'ema_{period}'] = dataframe['close'].ewm(span=period, adjust=False).mean()
        
        # Price position relative to MA
        dataframe['price_vs_sma20'] = (dataframe['close'] - dataframe['sma_20']) / dataframe['sma_20']
        dataframe['price_vs_sma50'] = (dataframe['close'] - dataframe['sma_50']) / dataframe['sma_50']
        
        # ===== VOLATILITY FEATURES =====
        # Standard deviation
        dataframe['volatility_10'] = dataframe['returns_1'].rolling(window=10).std()
        dataframe['volatility_20'] = dataframe['returns_1'].rolling(window=20).std()
        
        # ATR
        high_low = dataframe['high'] - dataframe['low']
        high_close = np.abs(dataframe['high'] - dataframe['close'].shift())
        low_close = np.abs(dataframe['low'] - dataframe['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        dataframe['atr'] = true_range.rolling(14).mean()
        dataframe['atr_pct'] = (dataframe['atr'] / dataframe['close']) * 100
        
        # ===== VOLUME FEATURES =====
        dataframe['volume_ma_10'] = dataframe['volume'].rolling(window=10).mean()
        dataframe['volume_ma_20'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma_20']
        
        # Volume-price correlation
        dataframe['volume_price_corr'] = dataframe['volume'].rolling(window=20).corr(dataframe['close'])
        
        # ===== MOMENTUM FEATURES =====
        # RSI
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        dataframe['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = dataframe['close'].ewm(span=12, adjust=False).mean()
        exp2 = dataframe['close'].ewm(span=26, adjust=False).mean()
        dataframe['macd'] = exp1 - exp2
        dataframe['macd_signal'] = dataframe['macd'].ewm(span=9, adjust=False).mean()
        dataframe['macd_hist'] = dataframe['macd'] - dataframe['macd_signal']
        
        # Stochastic
        low_14 = dataframe['low'].rolling(window=14).min()
        high_14 = dataframe['high'].rolling(window=14).max()
        dataframe['stoch'] = 100 * (dataframe['close'] - low_14) / (high_14 - low_14)
        
        # ===== TREND FEATURES =====
        # ADX
        plus_dm = dataframe['high'].diff()
        minus_dm = -dataframe['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr_sum = true_range.rolling(14).sum()
        plus_di = 100 * (plus_dm.rolling(14).sum() / tr_sum)
        minus_di = 100 * (minus_dm.rolling(14).sum() / tr_sum)
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        dataframe['adx'] = dx.rolling(14).mean()
        
        # ===== PATTERN FEATURES =====
        # Candle patterns (simplified)
        dataframe['candle_body'] = abs(dataframe['close'] - dataframe['open'])
        dataframe['candle_range'] = dataframe['high'] - dataframe['low']
        dataframe['body_ratio'] = dataframe['candle_body'] / (dataframe['candle_range'] + 0.0001)
        
        # Bullish/Bearish candles sequence
        dataframe['is_bullish'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['bullish_sequence'] = dataframe['is_bullish'].rolling(window=5).sum()
        
        # ===== ML PREDICTION (SIMULADO) =====
        # Em produção, aqui seria chamada de modelo treinado
        # Por ora, usa weighted combination de indicators
        
        # Normalize features
        rsi_norm = (dataframe['rsi'] - 50) / 50  # -1 to 1
        macd_norm = np.tanh(dataframe['macd_hist'] / 10)  # -1 to 1
        adx_norm = dataframe['adx'] / 100  # 0 to 1
        
        # Ensemble score (simulated ML prediction)
        dataframe['ml_score'] = (
            0.3 * rsi_norm +
            0.3 * macd_norm +
            0.2 * (dataframe['price_vs_sma20']) +
            0.2 * ((dataframe['volume_ratio'] - 1) / 2)
        )
        
        # Confidence score
        dataframe['ml_confidence'] = (
            0.5 * adx_norm +
            0.3 * dataframe['body_ratio'] +
            0.2 * (1 - dataframe['volatility_20'] / 0.05)  # Lower vol = higher confidence
        )
        
        # ===== REGIME DETECTION =====
        # Market regime (trending vs ranging)
        dataframe['regime_trending'] = dataframe['adx'] > 25
        dataframe['regime_volatile'] = dataframe['atr_pct'] > 2.0
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entrada baseada em predição do modelo ML
        """
        dataframe.loc[
            (
                # ML score positivo (predicts up)
                (dataframe['ml_score'] > 0.3) &
                # High confidence
                (dataframe['ml_confidence'] > 0.6) &
                # Supporting technical indicators
                (dataframe['rsi'] > 40) &
                (dataframe['rsi'] < 70) &
                (dataframe['macd_hist'] > 0) &
                # Volume confirmation
                (dataframe['volume_ratio'] > 0.8) &
                # Not in extreme volatile regime
                (dataframe['regime_volatile'] == False)
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # ML score negativo (predicts down)
                (dataframe['ml_score'] < -0.3) &
                # High confidence
                (dataframe['ml_confidence'] > 0.6) &
                # Supporting technical indicators
                (dataframe['rsi'] < 60) &
                (dataframe['rsi'] > 30) &
                (dataframe['macd_hist'] < 0) &
                # Volume confirmation
                (dataframe['volume_ratio'] > 0.8) &
                # Not in extreme volatile regime
                (dataframe['regime_volatile'] == False)
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Saída quando modelo muda de direção ou confidence cai
        """
        dataframe.loc[
            (
                # ML score virou negativo
                (dataframe['ml_score'] < 0) |
                # Confidence caiu
                (dataframe['ml_confidence'] < 0.4) |
                # Extreme overbought
                (dataframe['rsi'] > 75) |
                # MACD bearish crossover
                ((dataframe['macd'] < dataframe['macd_signal']) & 
                 (dataframe['macd'].shift(1) >= dataframe['macd_signal'].shift(1)))
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # ML score virou positivo
                (dataframe['ml_score'] > 0) |
                # Confidence caiu
                (dataframe['ml_confidence'] < 0.4) |
                # Extreme oversold
                (dataframe['rsi'] < 25) |
                # MACD bullish crossover
                ((dataframe['macd'] > dataframe['macd_signal']) & 
                 (dataframe['macd'].shift(1) <= dataframe['macd_signal'].shift(1)))
            ),
            'exit_short'] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                       current_profit: float, **kwargs) -> float:
        """
        Dynamic stop loss baseado em volatilidade
        """
        # Em produção, ajustaria baseado em ATR
        if current_profit > 0.03:  # Se lucro > 3%
            return -0.01  # Trailing stop em 1%
        
        return self.stoploss
