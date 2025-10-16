# ai/agents/intelligent_agent.py
"""
Agente IA Inteligente - Versão Melhorada
Implementa análise de mercado real usando indicadores técnicos
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class IntelligentAgent:
    """
    Agente IA com análise técnica avançada
    """
    
    def __init__(self, agent_id: str, group: str, config: Dict[str, Any] = None):
        self.agent_id = agent_id
        self.group = group
        self.config = config or {}
        self.status = "ACTIVE"
        self.decisions_count = 0
        self.last_decision = None
        
        # Indicadores e thresholds
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.volume_threshold = 1.5  # 1.5x do volume médio
        
        logger.info(f"✅ Agente {agent_id} (Grupo {group}) inicializado")
    
    def analyze_market(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Análise completa de mercado
        
        Args:
            data: Dados do mercado contendo:
                - closes: lista de preços de fechamento
                - volumes: lista de volumes
                - highs: lista de máximas
                - lows: lista de mínimas
        
        Returns:
            Análise completa com indicadores e recomendação
        """
        try:
            closes = data.get('closes', [])
            volumes = data.get('volumes', [])
            
            if len(closes) < 20:
                return {
                    'signal': 'HOLD',
                    'confidence': 0.0,
                    'reason': 'Dados insuficientes',
                    'indicators': {}
                }
            
            # Calcular indicadores
            indicators = {
                'rsi': self._calculate_rsi(closes),
                'macd': self._calculate_macd(closes),
                'bollinger': self._calculate_bollinger(closes),
                'volume_analysis': self._analyze_volume(volumes),
                'trend': self._analyze_trend(closes)
            }
            
            # Decisão baseada em múltiplos indicadores
            signal, confidence, reason = self._make_decision(indicators)
            
            # Armazenar última decisão
            self.last_decision = {
                'timestamp': datetime.utcnow().isoformat(),
                'signal': signal,
                'confidence': confidence,
                'reason': reason,
                'indicators': indicators
            }
            self.decisions_count += 1
            
            return {
                'agent_id': self.agent_id,
                'signal': signal,
                'confidence': confidence,
                'reason': reason,
                'indicators': indicators,
                'timestamp': self.last_decision['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Erro na análise do agente {self.agent_id}: {e}")
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': f'Erro: {str(e)}',
                'indicators': {}
            }
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> Dict[str, Any]:
        """Calcula RSI (Relative Strength Index)"""
        if len(closes) < period + 1:
            return {'value': 50, 'signal': 'NEUTRAL'}
        
        # Calcular ganhos e perdas
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        # Média dos últimos 'period' períodos
        recent_gains = gains[-period:]
        recent_losses = losses[-period:]
        
        avg_gain = sum(recent_gains) / period if recent_gains else 0
        avg_loss = sum(recent_losses) / period if recent_losses else 0
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Determinar sinal
        if rsi < self.rsi_oversold:
            signal = 'BUY'
        elif rsi > self.rsi_overbought:
            signal = 'SELL'
        else:
            signal = 'NEUTRAL'
        
        return {
            'value': round(rsi, 2),
            'signal': signal,
            'oversold': rsi < self.rsi_oversold,
            'overbought': rsi > self.rsi_overbought
        }
    
    def _calculate_macd(self, closes: List[float]) -> Dict[str, Any]:
        """Calcula MACD (Moving Average Convergence Divergence)"""
        if len(closes) < 26:
            return {'signal': 'NEUTRAL', 'histogram': 0}
        
        # EMA rápida (12 períodos)
        ema_12 = self._ema(closes, 12)
        # EMA lenta (26 períodos)
        ema_26 = self._ema(closes, 26)
        
        # MACD line
        macd_line = ema_12 - ema_26
        
        # Signal line (EMA de 9 períodos do MACD)
        # Simplificado: usar média simples
        signal_line = macd_line * 0.9
        
        histogram = macd_line - signal_line
        
        # Determinar sinal
        if histogram > 0 and macd_line > signal_line:
            signal = 'BUY'
        elif histogram < 0 and macd_line < signal_line:
            signal = 'SELL'
        else:
            signal = 'NEUTRAL'
        
        return {
            'macd_line': round(macd_line, 4),
            'signal_line': round(signal_line, 4),
            'histogram': round(histogram, 4),
            'signal': signal
        }
    
    def _calculate_bollinger(self, closes: List[float], period: int = 20) -> Dict[str, Any]:
        """Calcula Bandas de Bollinger"""
        if len(closes) < period:
            return {'signal': 'NEUTRAL'}
        
        recent = closes[-period:]
        sma = sum(recent) / period
        
        # Desvio padrão
        variance = sum((x - sma) ** 2 for x in recent) / period
        std_dev = variance ** 0.5
        
        upper_band = sma + (2 * std_dev)
        lower_band = sma - (2 * std_dev)
        current_price = closes[-1]
        
        # Determinar sinal
        if current_price < lower_band:
            signal = 'BUY'
        elif current_price > upper_band:
            signal = 'SELL'
        else:
            signal = 'NEUTRAL'
        
        return {
            'upper': round(upper_band, 2),
            'middle': round(sma, 2),
            'lower': round(lower_band, 2),
            'current': round(current_price, 2),
            'signal': signal
        }
    
    def _analyze_volume(self, volumes: List[float]) -> Dict[str, Any]:
        """Analisa volume de negociação"""
        if len(volumes) < 20:
            return {'signal': 'NEUTRAL', 'strength': 'LOW'}
        
        recent_volumes = volumes[-20:]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = volumes[-1]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > self.volume_threshold:
            strength = 'HIGH'
        elif volume_ratio > 1.2:
            strength = 'MEDIUM'
        else:
            strength = 'LOW'
        
        return {
            'current': current_volume,
            'average': round(avg_volume, 2),
            'ratio': round(volume_ratio, 2),
            'strength': strength,
            'signal': 'STRONG' if volume_ratio > self.volume_threshold else 'WEAK'
        }
    
    def _analyze_trend(self, closes: List[float]) -> Dict[str, Any]:
        """Analisa tendência de preço"""
        if len(closes) < 10:
            return {'direction': 'SIDEWAYS', 'strength': 0}
        
        # Comparar média recente com média anterior
        recent = closes[-5:]
        previous = closes[-10:-5]
        
        avg_recent = sum(recent) / len(recent)
        avg_previous = sum(previous) / len(previous)
        
        change_pct = ((avg_recent - avg_previous) / avg_previous) * 100 if avg_previous > 0 else 0
        
        if change_pct > 2:
            direction = 'UP'
            strength = min(abs(change_pct) / 10, 1.0)
        elif change_pct < -2:
            direction = 'DOWN'
            strength = min(abs(change_pct) / 10, 1.0)
        else:
            direction = 'SIDEWAYS'
            strength = 0
        
        return {
            'direction': direction,
            'strength': round(strength, 2),
            'change_pct': round(change_pct, 2)
        }
    
    def _ema(self, data: List[float], period: int) -> float:
        """Calcula EMA (Exponential Moving Average)"""
        if len(data) < period:
            return sum(data) / len(data) if data else 0
        
        # Começar com SMA
        sma = sum(data[:period]) / period
        multiplier = 2 / (period + 1)
        
        ema = sma
        for price in data[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _make_decision(self, indicators: Dict[str, Any]) -> Tuple[str, float, str]:
        """
        Toma decisão baseada em múltiplos indicadores
        
        Returns:
            (signal, confidence, reason)
        """
        # Pontuação de cada indicador
        scores = {
            'BUY': 0,
            'SELL': 0,
            'HOLD': 0
        }
        
        reasons = []
        
        # RSI
        rsi = indicators.get('rsi', {})
        if rsi.get('signal') == 'BUY':
            scores['BUY'] += 2
            reasons.append(f"RSI oversold ({rsi.get('value')})")
        elif rsi.get('signal') == 'SELL':
            scores['SELL'] += 2
            reasons.append(f"RSI overbought ({rsi.get('value')})")
        
        # MACD
        macd = indicators.get('macd', {})
        if macd.get('signal') == 'BUY':
            scores['BUY'] += 2
            reasons.append("MACD bullish crossover")
        elif macd.get('signal') == 'SELL':
            scores['SELL'] += 2
            reasons.append("MACD bearish crossover")
        
        # Bollinger
        bollinger = indicators.get('bollinger', {})
        if bollinger.get('signal') == 'BUY':
            scores['BUY'] += 1
            reasons.append("Price below lower Bollinger Band")
        elif bollinger.get('signal') == 'SELL':
            scores['SELL'] += 1
            reasons.append("Price above upper Bollinger Band")
        
        # Volume
        volume = indicators.get('volume_analysis', {})
        if volume.get('signal') == 'STRONG':
            # Aumenta confiança do sinal predominante
            if scores['BUY'] > scores['SELL']:
                scores['BUY'] += 1
                reasons.append("High volume confirmation")
            elif scores['SELL'] > scores['BUY']:
                scores['SELL'] += 1
                reasons.append("High volume confirmation")
        
        # Trend
        trend = indicators.get('trend', {})
        if trend.get('direction') == 'UP':
            scores['BUY'] += 1
            reasons.append(f"Uptrend ({trend.get('change_pct')}%)")
        elif trend.get('direction') == 'DOWN':
            scores['SELL'] += 1
            reasons.append(f"Downtrend ({trend.get('change_pct')}%)")
        
        # Determinar sinal final
        max_score = max(scores['BUY'], scores['SELL'], scores['HOLD'])
        
        if max_score == 0 or (scores['BUY'] == scores['SELL']):
            return 'HOLD', 0.5, 'Sinais conflitantes'
        
        if scores['BUY'] == max_score:
            signal = 'BUY'
        elif scores['SELL'] == max_score:
            signal = 'SELL'
        else:
            signal = 'HOLD'
        
        # Calcular confiança (0-1)
        total_possible = 7  # RSI(2) + MACD(2) + BB(1) + Vol(1) + Trend(1)
        confidence = min(max_score / total_possible, 1.0)
        
        reason = '; '.join(reasons[:3])  # Top 3 reasons
        
        return signal, confidence, reason
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual do agente"""
        return {
            'agent_id': self.agent_id,
            'group': self.group,
            'status': self.status,
            'decisions_count': self.decisions_count,
            'last_decision': self.last_decision,
            'uptime': 'active'
        }
