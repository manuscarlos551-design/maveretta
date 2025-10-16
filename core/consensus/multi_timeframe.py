
# core/consensus/multi_timeframe.py
"""
Multi-Timeframe Consensus - Agentes votam em sinais através de diferentes timeframes
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TimeframeSignal:
    """Sinal de um timeframe específico"""
    timeframe: str
    action: str  # 'buy', 'sell', 'hold'
    confidence: float
    agent_id: str
    indicators: Dict[str, float]
    timestamp: datetime


class MultiTimeframeConsensus:
    """
    Motor de consenso que agrega sinais de múltiplos timeframes
    """
    
    def __init__(self):
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        self.timeframe_weights = {
            '1m': 0.1,
            '5m': 0.15,
            '15m': 0.2,
            '1h': 0.25,
            '4h': 0.2,
            '1d': 0.1
        }
        self.consensus_history: List[Dict[str, Any]] = []
        
        logger.info("✅ Multi-Timeframe Consensus initialized")
    
    def aggregate_signals(
        self,
        signals: List[TimeframeSignal],
        symbol: str
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Agrega sinais de múltiplos timeframes
        
        Args:
            signals: Lista de sinais de diferentes timeframes
            symbol: Par de trading
        
        Returns:
            (action, confidence, details)
        """
        try:
            if not signals:
                return 'hold', 0.0, {}
            
            # Agrupa por timeframe
            signals_by_tf = {}
            for signal in signals:
                if signal.timeframe not in signals_by_tf:
                    signals_by_tf[signal.timeframe] = []
                signals_by_tf[signal.timeframe].append(signal)
            
            # Calcula score ponderado por timeframe
            buy_score = 0.0
            sell_score = 0.0
            total_weight = 0.0
            
            for tf, tf_signals in signals_by_tf.items():
                weight = self.timeframe_weights.get(tf, 0.1)
                
                # Consenso dentro do timeframe
                tf_buy = sum(1 for s in tf_signals if s.action == 'buy')
                tf_sell = sum(1 for s in tf_signals if s.action == 'sell')
                tf_total = len(tf_signals)
                
                if tf_total > 0:
                    buy_score += (tf_buy / tf_total) * weight
                    sell_score += (tf_sell / tf_total) * weight
                    total_weight += weight
            
            # Normaliza scores
            if total_weight > 0:
                buy_score /= total_weight
                sell_score /= total_weight
            
            # Decide ação final
            if buy_score > sell_score and buy_score > 0.6:
                action = 'buy'
                confidence = buy_score
            elif sell_score > buy_score and sell_score > 0.6:
                action = 'sell'
                confidence = sell_score
            else:
                action = 'hold'
                confidence = 1.0 - abs(buy_score - sell_score)
            
            # Verifica alinhamento de timeframes
            alignment_score = self._calculate_alignment(signals_by_tf)
            
            # Ajusta confiança baseado em alinhamento
            confidence *= alignment_score
            
            details = {
                'buy_score': buy_score,
                'sell_score': sell_score,
                'alignment_score': alignment_score,
                'timeframes_analyzed': list(signals_by_tf.keys()),
                'total_signals': len(signals)
            }
            
            # Registra no histórico
            self.consensus_history.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': symbol,
                'action': action,
                'confidence': confidence,
                'details': details
            })
            
            logger.info(
                f"Multi-TF consensus for {symbol}: {action} "
                f"(confidence: {confidence:.2%}, alignment: {alignment_score:.2%})"
            )
            
            return action, confidence, details
            
        except Exception as e:
            logger.error(f"Error in multi-timeframe consensus: {e}")
            return 'hold', 0.0, {}
    
    def _calculate_alignment(
        self,
        signals_by_tf: Dict[str, List[TimeframeSignal]]
    ) -> float:
        """
        Calcula score de alinhamento entre timeframes
        
        Returns:
            Score de 0-1 (1 = perfeito alinhamento)
        """
        if not signals_by_tf:
            return 0.0
        
        # Conta votos por ação em cada timeframe
        tf_votes = {}
        for tf, signals in signals_by_tf.items():
            votes = {'buy': 0, 'sell': 0, 'hold': 0}
            for signal in signals:
                votes[signal.action] += 1
            
            # Ação majoritária do timeframe
            majority = max(votes, key=votes.get)
            tf_votes[tf] = majority
        
        # Calcula consenso entre timeframes
        total_tfs = len(tf_votes)
        if total_tfs < 2:
            return 0.5
        
        # Conta quantos timeframes concordam
        vote_counts = {'buy': 0, 'sell': 0, 'hold': 0}
        for vote in tf_votes.values():
            vote_counts[vote] += 1
        
        max_agreement = max(vote_counts.values())
        alignment = max_agreement / total_tfs
        
        return alignment
    
    def get_dynamic_position_size(
        self,
        base_size: float,
        alignment_score: float,
        confidence: float
    ) -> float:
        """
        Calcula tamanho de posição dinâmico baseado em consenso
        
        Args:
            base_size: Tamanho base da posição
            alignment_score: Score de alinhamento (0-1)
            confidence: Confiança da decisão (0-1)
        
        Returns:
            Tamanho ajustado da posição
        """
        # Multiplica tamanho por consenso
        multiplier = (alignment_score * 0.5) + (confidence * 0.5)
        
        # Limita entre 0.3x e 1.5x do tamanho base
        adjusted_size = base_size * multiplier
        adjusted_size = max(base_size * 0.3, min(base_size * 1.5, adjusted_size))
        
        return adjusted_size


# Instância global
multi_timeframe_consensus = MultiTimeframeConsensus()
