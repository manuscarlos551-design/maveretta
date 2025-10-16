
# core/market/regime_detector.py
"""
Market Regime Detector - Classifica condições de mercado em tempo real
Usa análise de volatilidade, volume e tendência para identificar regimes
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Tipos de regime de mercado"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CALM = "calm"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


class RegimeDetector:
    """
    Detecta regime de mercado usando múltiplos indicadores
    """
    
    def __init__(self):
        self.regime_history: List[Dict[str, Any]] = []
        self.performance_by_regime: Dict[str, Dict[str, float]] = {}
        
        # Thresholds para classificação
        self.volatility_threshold_high = 2.0  # ATR > 2x média
        self.volatility_threshold_low = 0.5   # ATR < 0.5x média
        self.trend_threshold = 0.02           # 2% movimento direcional
        self.volume_threshold = 1.5           # 1.5x volume médio
        
        logger.info("✅ Market Regime Detector initialized")
    
    def detect_regime(
        self,
        df: pd.DataFrame,
        lookback_period: int = 50
    ) -> Tuple[MarketRegime, float]:
        """
        Detecta regime atual do mercado
        
        Args:
            df: DataFrame com OHLCV + indicadores
            lookback_period: Janela para análise
        
        Returns:
            (regime, confidence)
        """
        try:
            if len(df) < lookback_period:
                return MarketRegime.CALM, 0.5
            
            recent = df.tail(lookback_period)
            
            # Calcula métricas
            volatility_score = self._calculate_volatility_score(recent)
            trend_score = self._calculate_trend_score(recent)
            volume_score = self._calculate_volume_score(recent)
            
            # Classifica regime
            regime, confidence = self._classify_regime(
                volatility_score,
                trend_score,
                volume_score
            )
            
            # Registra no histórico
            self.regime_history.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'regime': regime.value,
                'confidence': confidence,
                'volatility_score': volatility_score,
                'trend_score': trend_score,
                'volume_score': volume_score
            })
            
            # Mantém apenas últimas 1000 entradas
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-1000:]
            
            logger.debug(
                f"Regime detected: {regime.value} "
                f"(confidence: {confidence:.2%}, "
                f"vol: {volatility_score:.2f}, "
                f"trend: {trend_score:.2f})"
            )
            
            return regime, confidence
            
        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            return MarketRegime.CALM, 0.0
    
    def _calculate_volatility_score(self, df: pd.DataFrame) -> float:
        """Calcula score de volatilidade (0-1)"""
        if 'atr' not in df.columns:
            # Calcula ATR se não existir
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(14).mean()
        else:
            atr = df['atr']
        
        current_atr = atr.iloc[-1]
        avg_atr = atr.mean()
        
        if avg_atr == 0:
            return 0.5
        
        volatility_ratio = current_atr / avg_atr
        
        # Normaliza para 0-1
        return min(1.0, volatility_ratio / 3.0)
    
    def _calculate_trend_score(self, df: pd.DataFrame) -> float:
        """Calcula score de tendência (-1 a +1)"""
        # Usa múltiplas EMAs
        if 'ema_fast' not in df.columns:
            ema_fast = df['close'].ewm(span=12).mean()
            ema_slow = df['close'].ewm(span=26).mean()
        else:
            ema_fast = df['ema_fast']
            ema_slow = df['ema_slow']
        
        # Tendência baseada em EMA
        ema_trend = (ema_fast.iloc[-1] - ema_slow.iloc[-1]) / ema_slow.iloc[-1]
        
        # Tendência baseada em regressão linear
        prices = df['close'].values
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        linear_trend = slope / prices[-1]
        
        # Combina ambas (peso igual)
        trend_score = (ema_trend + linear_trend) / 2
        
        # Normaliza para -1 a +1
        return np.clip(trend_score * 50, -1.0, 1.0)
    
    def _calculate_volume_score(self, df: pd.DataFrame) -> float:
        """Calcula score de volume (0-1)"""
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].mean()
        
        if avg_volume == 0:
            return 0.5
        
        volume_ratio = current_volume / avg_volume
        
        # Normaliza para 0-1
        return min(1.0, volume_ratio / 3.0)
    
    def _classify_regime(
        self,
        volatility: float,
        trend: float,
        volume: float
    ) -> Tuple[MarketRegime, float]:
        """
        Classifica regime baseado em scores
        
        Returns:
            (regime, confidence)
        """
        confidence = 0.0
        
        # VOLATILE: Alta volatilidade
        if volatility > 0.7:
            confidence = volatility
            return MarketRegime.VOLATILE, confidence
        
        # CALM: Baixa volatilidade
        if volatility < 0.3:
            confidence = 1.0 - volatility
            return MarketRegime.CALM, confidence
        
        # TRENDING_UP: Tendência positiva forte
        if trend > 0.3 and volume > 0.5:
            confidence = (abs(trend) + volume) / 2
            return MarketRegime.TRENDING_UP, confidence
        
        # TRENDING_DOWN: Tendência negativa forte
        if trend < -0.3 and volume > 0.5:
            confidence = (abs(trend) + volume) / 2
            return MarketRegime.TRENDING_DOWN, confidence
        
        # BREAKOUT: Volume alto + movimento direcional
        if volume > 0.7 and abs(trend) > 0.2:
            confidence = volume
            return MarketRegime.BREAKOUT, confidence
        
        # REVERSAL: Mudança de tendência
        if len(self.regime_history) > 0:
            last_regime = self.regime_history[-1]['regime']
            if (last_regime == 'trending_up' and trend < -0.2) or \
               (last_regime == 'trending_down' and trend > 0.2):
                confidence = abs(trend)
                return MarketRegime.REVERSAL, confidence
        
        # RANGING: Padrão
        confidence = 0.5
        return MarketRegime.RANGING, confidence
    
    def get_regime_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos regimes detectados"""
        if not self.regime_history:
            return {}
        
        df = pd.DataFrame(self.regime_history)
        
        regime_counts = df['regime'].value_counts().to_dict()
        avg_confidence = df.groupby('regime')['confidence'].mean().to_dict()
        
        return {
            'total_detections': len(self.regime_history),
            'regime_distribution': regime_counts,
            'avg_confidence_by_regime': avg_confidence,
            'current_regime': self.regime_history[-1]['regime'],
            'current_confidence': self.regime_history[-1]['confidence']
        }
    
    def track_performance(
        self,
        regime: MarketRegime,
        strategy: str,
        pnl: float
    ):
        """
        Rastreia performance de estratégia por regime
        
        Args:
            regime: Regime de mercado
            strategy: Nome da estratégia
            pnl: P&L do trade
        """
        key = f"{regime.value}_{strategy}"
        
        if key not in self.performance_by_regime:
            self.performance_by_regime[key] = {
                'trades': 0,
                'total_pnl': 0.0,
                'wins': 0,
                'losses': 0
            }
        
        stats = self.performance_by_regime[key]
        stats['trades'] += 1
        stats['total_pnl'] += pnl
        
        if pnl > 0:
            stats['wins'] += 1
        else:
            stats['losses'] += 1
    
    def get_best_strategies_by_regime(self) -> Dict[str, List[str]]:
        """Retorna melhores estratégias para cada regime"""
        best_strategies = {}
        
        for key, stats in self.performance_by_regime.items():
            regime, strategy = key.split('_', 1)
            
            if stats['trades'] < 5:  # Mínimo de trades
                continue
            
            avg_pnl = stats['total_pnl'] / stats['trades']
            win_rate = stats['wins'] / stats['trades']
            
            if regime not in best_strategies:
                best_strategies[regime] = []
            
            best_strategies[regime].append({
                'strategy': strategy,
                'avg_pnl': avg_pnl,
                'win_rate': win_rate,
                'trades': stats['trades']
            })
        
        # Ordena por avg_pnl
        for regime in best_strategies:
            best_strategies[regime].sort(
                key=lambda x: x['avg_pnl'],
                reverse=True
            )
        
        return best_strategies


# Instância global
regime_detector = RegimeDetector()
