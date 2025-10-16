# core/strategies/multi_timeframe_strategy.py
"""
Multi-Timeframe Strategy - Adaptado de Hummingbot
Analisa múltiplos timeframes para melhores sinais de entrada/saída
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
import logging

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class MultiTimeframeStrategy(BaseStrategy):
    """
    Multi-Timeframe Strategy
    
    Analisa tendências e sinais em múltiplos timeframes para confirmar trades
    Hierarquia: TF maior define tendência, TF menor define timing
    """
    
    strategy_name: str = "MultiTimeframe"
    strategy_version: str = "1.0.0"
    
    # Timeframes para análise
    primary_timeframe: str = "1h"  # TF principal
    secondary_timeframes: List[str] = ["15m", "4h"]  # TFs complementares
    
    # Parâmetros de análise
    trend_alignment_required: bool = True  # Requer alinhamento de tendências
    min_timeframes_aligned: int = 2  # Mínimo de TFs alinhados
    
    # Indicadores por timeframe
    use_rsi: bool = True
    use_macd: bool = True
    use_ema: bool = True
    
    # Pesos por timeframe (para scoring)
    timeframe_weights: Dict[str, float] = {
        "1m": 0.5,
        "5m": 1.0,
        "15m": 1.5,
        "1h": 2.0,
        "4h": 2.5,
        "1d": 3.0
    }
    
    # Thresholds
    signal_threshold: float = 0.7  # 70% de confiança mínima
    
    minimal_roi: Dict[int, float] = {
        "0": 0.03,  # 3% target
        "30": 0.02,  # 2% após 30min
        "60": 0.01,  # 1% após 1h
    }
    
    stoploss: float = -0.02  # 2% stop loss
    timeframe: str = "15m"  # TF de execução
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        if config:
            self.primary_timeframe = config.get('primary_timeframe', self.primary_timeframe)
            self.secondary_timeframes = config.get('secondary_timeframes', self.secondary_timeframes)
            self.trend_alignment_required = config.get('trend_alignment_required', self.trend_alignment_required)
            self.min_timeframes_aligned = config.get('min_timeframes_aligned', self.min_timeframes_aligned)
            self.use_rsi = config.get('use_rsi', self.use_rsi)
            self.use_macd = config.get('use_macd', self.use_macd)
            self.use_ema = config.get('use_ema', self.use_ema)
            self.signal_threshold = config.get('signal_threshold', self.signal_threshold)
        
        # Cache de dados de outros timeframes
        self.tf_data_cache: Dict[str, pd.DataFrame] = {}
        
        logger.info(f"MultiTimeframe Strategy initialized - Primary: {self.primary_timeframe}, Secondary: {self.secondary_timeframes}")
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calcula indicadores para o timeframe principal
        """
        # Indicadores básicos do TF atual
        if self.use_ema:
            dataframe['ema_9'] = dataframe['close'].ewm(span=9).mean()
            dataframe['ema_21'] = dataframe['close'].ewm(span=21).mean()
            dataframe['ema_50'] = dataframe['close'].ewm(span=50).mean()
            dataframe['ema_200'] = dataframe['close'].ewm(span=200).mean()
        
        if self.use_rsi:
            dataframe['rsi'] = self._calculate_rsi(dataframe, period=14)
            dataframe['rsi_6'] = self._calculate_rsi(dataframe, period=6)
        
        if self.use_macd:
            dataframe = self._calculate_macd(dataframe)
        
        # Bollinger Bands
        dataframe = self._calculate_bollinger_bands(dataframe)
        
        # ATR para volatilidade
        dataframe['atr'] = self._calculate_atr(dataframe)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']
        
        # Identifica tendência no TF atual
        dataframe['trend'] = self._identify_trend(dataframe)
        
        # Score de momentum
        dataframe['momentum_score'] = self._calculate_momentum_score(dataframe)
        
        # Volume
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de entrada baseado em análise multi-timeframe
        """
        # Analisa outros timeframes (simulado - em produção, receberia dados reais)
        # Por enquanto, usamos o TF atual como proxy
        
        # Score agregado de todos os timeframes
        dataframe['mtf_long_score'] = self._calculate_mtf_score(dataframe, 'long')
        dataframe['mtf_short_score'] = self._calculate_mtf_score(dataframe, 'short')
        
        # Condições de entrada LONG
        long_conditions = (
            # Score suficiente
            (dataframe['mtf_long_score'] >= self.signal_threshold) &
            
            # Confirmações no TF atual
            (dataframe['trend'] == 1) &
            
            # RSI não overbought
            (dataframe['rsi'] < 70) &
            (dataframe['rsi'] > 30) &
            
            # MACD bullish
            (dataframe['macd'] > dataframe['macd_signal']) &
            
            # Volume confirmação
            (dataframe['volume_ratio'] > 0.8)
        )
        
        dataframe.loc[long_conditions, 'enter_long'] = 1
        
        # Condições de entrada SHORT
        short_conditions = (
            # Score suficiente
            (dataframe['mtf_short_score'] >= self.signal_threshold) &
            
            # Confirmações no TF atual
            (dataframe['trend'] == -1) &
            
            # RSI não oversold
            (dataframe['rsi'] > 30) &
            (dataframe['rsi'] < 70) &
            
            # MACD bearish
            (dataframe['macd'] < dataframe['macd_signal']) &
            
            # Volume confirmação
            (dataframe['volume_ratio'] > 0.8)
        )
        
        dataframe.loc[short_conditions, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de saída
        """
        # Exit LONG
        dataframe.loc[
            # Tendência reverte em TF superior
            (dataframe['mtf_short_score'] > 0.6) |
            
            # RSI overbought
            (dataframe['rsi'] > 75) |
            
            # MACD bearish cross
            ((dataframe['macd'] < dataframe['macd_signal']) & 
             (dataframe['macd'].shift(1) >= dataframe['macd_signal'].shift(1))) |
            
            # Trend reversal
            (dataframe['trend'] == -1),
            'exit_long'
        ] = 1
        
        # Exit SHORT
        dataframe.loc[
            # Tendência reverte em TF superior
            (dataframe['mtf_long_score'] > 0.6) |
            
            # RSI oversold
            (dataframe['rsi'] < 25) |
            
            # MACD bullish cross
            ((dataframe['macd'] > dataframe['macd_signal']) & 
             (dataframe['macd'].shift(1) <= dataframe['macd_signal'].shift(1))) |
            
            # Trend reversal
            (dataframe['trend'] == 1),
            'exit_short'
        ] = 1
        
        return dataframe
    
    def _calculate_mtf_score(self, dataframe: pd.DataFrame, direction: str = 'long') -> pd.Series:
        """
        Calcula score agregado de múltiplos timeframes
        
        Args:
            dataframe: Dados do TF atual
            direction: 'long' ou 'short'
        
        Returns:
            Score normalizado (0 a 1)
        """
        # Simula análise de múltiplos TFs
        # Em produção, analisaria dados reais de cada TF
        
        score = pd.Series(0.0, index=dataframe.index)
        total_weight = 0
        
        # Score do TF atual
        current_tf_score = self._score_timeframe(dataframe, direction)
        current_weight = self.timeframe_weights.get(self.timeframe, 1.0)
        
        score += current_tf_score * current_weight
        total_weight += current_weight
        
        # Simula scores de outros TFs (baseado em suavização dos dados atuais)
        for tf in self.secondary_timeframes:
            # Em produção, pegaria dados reais do TF
            # Por ora, usa dados suavizados como proxy
            tf_multiplier = self._get_tf_multiplier(tf)
            smoothed_df = self._smooth_dataframe(dataframe, tf_multiplier)
            
            tf_score = self._score_timeframe(smoothed_df, direction)
            tf_weight = self.timeframe_weights.get(tf, 1.0)
            
            score += tf_score * tf_weight
            total_weight += tf_weight
        
        # Normaliza score
        if total_weight > 0:
            score = score / total_weight
        
        return score.clip(0, 1)
    
    def _score_timeframe(self, dataframe: pd.DataFrame, direction: str) -> pd.Series:
        """
        Calcula score de sinal para um timeframe específico
        """
        score = pd.Series(0.0, index=dataframe.index)
        
        if direction == 'long':
            # Fatores bullish
            if 'trend' in dataframe.columns:
                score += (dataframe['trend'] == 1).astype(float) * 0.3
            
            if 'rsi' in dataframe.columns:
                # RSI entre 40-60 é ideal
                rsi_score = 1 - abs(dataframe['rsi'] - 50) / 50
                score += rsi_score.clip(0, 1) * 0.2
            
            if 'macd' in dataframe.columns:
                score += (dataframe['macd'] > dataframe['macd_signal']).astype(float) * 0.3
            
            if 'momentum_score' in dataframe.columns:
                score += dataframe['momentum_score'].clip(0, 1) * 0.2
        
        elif direction == 'short':
            # Fatores bearish
            if 'trend' in dataframe.columns:
                score += (dataframe['trend'] == -1).astype(float) * 0.3
            
            if 'rsi' in dataframe.columns:
                # RSI acima de 60 ou abaixo de 40
                rsi_score = abs(dataframe['rsi'] - 50) / 50
                score += rsi_score.clip(0, 1) * 0.2
            
            if 'macd' in dataframe.columns:
                score += (dataframe['macd'] < dataframe['macd_signal']).astype(float) * 0.3
            
            if 'momentum_score' in dataframe.columns:
                score += (1 - dataframe['momentum_score']).clip(0, 1) * 0.2
        
        return score.clip(0, 1)
    
    def _identify_trend(self, dataframe: pd.DataFrame) -> pd.Series:
        """
        Identifica tendência: 1 (up), -1 (down), 0 (neutral)
        """
        trend = pd.Series(0, index=dataframe.index)
        
        if 'ema_21' in dataframe.columns and 'ema_50' in dataframe.columns:
            # Uptrend
            trend[(dataframe['ema_21'] > dataframe['ema_50']) & 
                  (dataframe['close'] > dataframe['ema_21'])] = 1
            
            # Downtrend
            trend[(dataframe['ema_21'] < dataframe['ema_50']) & 
                  (dataframe['close'] < dataframe['ema_21'])] = -1
        
        return trend
    
    def _calculate_momentum_score(self, dataframe: pd.DataFrame) -> pd.Series:
        """
        Calcula score de momentum (0 a 1)
        """
        # ROC (Rate of Change)
        roc = dataframe['close'].pct_change(10)
        
        # Normaliza entre 0 e 1
        roc_normalized = (roc + 0.1) / 0.2  # Assume range de -10% a +10%
        
        return roc_normalized.clip(0, 1)
    
    def _get_tf_multiplier(self, timeframe: str) -> int:
        """
        Retorna multiplicador para suavização baseado no timeframe
        """
        tf_map = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }
        
        current_tf = self.timeframe
        current_minutes = tf_map.get(current_tf, 15)
        target_minutes = tf_map.get(timeframe, 60)
        
        return max(1, target_minutes // current_minutes)
    
    def _smooth_dataframe(self, dataframe: pd.DataFrame, multiplier: int) -> pd.DataFrame:
        """
        Suaviza dataframe para simular timeframe maior
        """
        smoothed = dataframe.copy()
        
        # Suaviza OHLC
        smoothed['open'] = dataframe['open'].rolling(multiplier).first()
        smoothed['high'] = dataframe['high'].rolling(multiplier).max()
        smoothed['low'] = dataframe['low'].rolling(multiplier).min()
        smoothed['close'] = dataframe['close']
        smoothed['volume'] = dataframe['volume'].rolling(multiplier).sum()
        
        # Recalcula indicadores
        if self.use_ema:
            smoothed['ema_21'] = smoothed['close'].ewm(span=21).mean()
            smoothed['ema_50'] = smoothed['close'].ewm(span=50).mean()
        
        if self.use_rsi:
            smoothed['rsi'] = self._calculate_rsi(smoothed)
        
        if self.use_macd:
            smoothed = self._calculate_macd(smoothed)
        
        smoothed['trend'] = self._identify_trend(smoothed)
        smoothed['momentum_score'] = self._calculate_momentum_score(smoothed)
        
        return smoothed
    
    # Helper methods (reusados de outras estratégias)
    def _calculate_rsi(self, dataframe: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, dataframe: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
        """Calcula MACD"""
        dataframe['macd'] = dataframe['close'].ewm(span=fast).mean() - dataframe['close'].ewm(span=slow).mean()
        dataframe['macd_signal'] = dataframe['macd'].ewm(span=signal).mean()
        dataframe['macd_hist'] = dataframe['macd'] - dataframe['macd_signal']
        return dataframe
    
    def _calculate_bollinger_bands(self, dataframe: pd.DataFrame, period=20, std=2) -> pd.DataFrame:
        """Calcula Bollinger Bands"""
        dataframe['bb_middle'] = dataframe['close'].rolling(period).mean()
        dataframe['bb_std'] = dataframe['close'].rolling(period).std()
        dataframe['bb_upper'] = dataframe['bb_middle'] + (dataframe['bb_std'] * std)
        dataframe['bb_lower'] = dataframe['bb_middle'] - (dataframe['bb_std'] * std)
        return dataframe
    
    def _calculate_atr(self, dataframe: pd.DataFrame, period=14) -> pd.Series:
        """Calcula ATR"""
        high = dataframe['high']
        low = dataframe['low']
        close = dataframe['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()
