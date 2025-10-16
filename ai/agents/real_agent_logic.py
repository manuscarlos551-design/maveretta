# ai/agents/real_agent_logic.py
"""
Lógica Real dos Agentes de IA
Implementa análise técnica de mercado para tomada de decisões
"""

import logging
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class Signal(str, Enum):
    """Sinais de trading"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class AgentStrategy(str, Enum):
    """Estratégias dos agentes"""
    SCALPING = "scalping"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"


class TechnicalIndicators:
    """Calculadora de indicadores técnicos"""
    
    @staticmethod
    def sma(prices: List[float], period: int) -> Optional[float]:
        """Simple Moving Average"""
        if len(prices) < period:
            return None
        return np.mean(prices[-period:])
    
    @staticmethod
    def ema(prices: List[float], period: int) -> Optional[float]:
        """Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        prices_array = np.array(prices[-period:])
        multiplier = 2 / (period + 1)
        ema = prices_array[0]
        
        for price in prices_array[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices[-period-1:])
        gains = deltas.copy()
        losses = deltas.copy()
        
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, float]]:
        """MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow + signal:
            return None
        
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)
        
        if ema_fast is None or ema_slow is None:
            return None
        
        macd_line = ema_fast - ema_slow
        
        # Calcular signal line (simplificado)
        signal_line = macd_line * 0.9  # Aproximação
        histogram = macd_line - signal_line
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
        """Bollinger Bands"""
        if len(prices) < period:
            return None
        
        sma = TechnicalIndicators.sma(prices, period)
        if sma is None:
            return None
        
        std = np.std(prices[-period:])
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return {
            "upper": upper_band,
            "middle": sma,
            "lower": lower_band,
            "current": prices[-1]
        }
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
        """Average True Range (volatilidade)"""
        if len(closes) < period + 1:
            return None
        
        true_ranges = []
        
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        
        return np.mean(true_ranges[-period:])
    
    @staticmethod
    def volume_profile(volumes: List[float], period: int = 20) -> Dict[str, Any]:
        """Análise de volume"""
        if len(volumes) < period:
            return {"status": "insufficient_data"}
        
        recent_volumes = volumes[-period:]
        avg_volume = np.mean(recent_volumes)
        current_volume = volumes[-1]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        return {
            "avg_volume": avg_volume,
            "current_volume": current_volume,
            "volume_ratio": volume_ratio,
            "volume_surge": volume_ratio > 1.5,
            "volume_dry": volume_ratio < 0.5
        }


class RealAgentLogic:
    """
    Lógica Real de Análise de Mercado para Agentes
    Implementa estratégias de trading baseadas em análise técnica
    """
    
    def __init__(self, agent_id: str, strategy: AgentStrategy):
        self.agent_id = agent_id
        self.strategy = strategy
        self.indicators = TechnicalIndicators()
        
        # Parâmetros por estratégia
        self.params = self._get_strategy_params()
        
        logger.info(f"Agent {agent_id} initialized with {strategy.value} strategy")
    
    def _get_strategy_params(self) -> Dict[str, Any]:
        """Retorna parâmetros específicos da estratégia"""
        
        if self.strategy == AgentStrategy.SCALPING:
            return {
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "ema_fast": 5,
                "ema_slow": 13,
                "confidence_threshold": 0.65,
                "timeframe": "1m",
                "hold_time_max": 300  # 5 minutos
            }
        
        elif self.strategy == AgentStrategy.TREND_FOLLOWING:
            return {
                "ema_fast": 12,
                "ema_slow": 26,
                "atr_multiplier": 2.0,
                "confidence_threshold": 0.70,
                "timeframe": "5m",
                "trend_strength_min": 0.6
            }
        
        elif self.strategy == AgentStrategy.MEAN_REVERSION:
            return {
                "bb_period": 20,
                "bb_std": 2.0,
                "rsi_period": 14,
                "confidence_threshold": 0.65,
                "timeframe": "15m"
            }
        
        elif self.strategy == AgentStrategy.MOMENTUM:
            return {
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "confidence_threshold": 0.68,
                "timeframe": "5m"
            }
        
        else:  # BREAKOUT
            return {
                "lookback_period": 20,
                "volume_threshold": 1.5,
                "confidence_threshold": 0.72,
                "timeframe": "15m"
            }
    
    def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa mercado e retorna sinal de trading
        
        Args:
            market_data: {
                "symbol": str,
                "closes": List[float],
                "highs": List[float],
                "lows": List[float],
                "volumes": List[float],
                "timestamp": str
            }
        
        Returns:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "confidence": float (0-1),
                "reason": str,
                "indicators": dict,
                "agent_id": str,
                "strategy": str
            }
        """
        
        try:
            # Validação de dados
            if not self._validate_market_data(market_data):
                return self._create_hold_response("Dados de mercado insuficientes")
            
            # Análise baseada na estratégia
            if self.strategy == AgentStrategy.SCALPING:
                return self._analyze_scalping(market_data)
            
            elif self.strategy == AgentStrategy.TREND_FOLLOWING:
                return self._analyze_trend_following(market_data)
            
            elif self.strategy == AgentStrategy.MEAN_REVERSION:
                return self._analyze_mean_reversion(market_data)
            
            elif self.strategy == AgentStrategy.MOMENTUM:
                return self._analyze_momentum(market_data)
            
            elif self.strategy == AgentStrategy.BREAKOUT:
                return self._analyze_breakout(market_data)
            
            else:
                return self._create_hold_response("Estratégia não implementada")
        
        except Exception as e:
            logger.error(f"Error analyzing market for {self.agent_id}: {e}")
            return self._create_hold_response(f"Erro na análise: {str(e)}")
    
    def _validate_market_data(self, data: Dict[str, Any]) -> bool:
        """Valida se dados de mercado são suficientes"""
        required_keys = ["closes", "highs", "lows", "volumes"]
        
        for key in required_keys:
            if key not in data or not data[key]:
                return False
            
            if len(data[key]) < 30:  # Mínimo 30 candles
                return False
        
        return True
    
    def _analyze_scalping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estratégia de Scalping (operações rápidas)"""
        closes = data["closes"]
        volumes = data["volumes"]
        
        # Indicadores
        rsi = self.indicators.rsi(closes, 14)
        ema_fast = self.indicators.ema(closes, self.params["ema_fast"])
        ema_slow = self.indicators.ema(closes, self.params["ema_slow"])
        volume_data = self.indicators.volume_profile(volumes, 20)
        
        current_price = closes[-1]
        
        indicators = {
            "rsi": rsi,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "current_price": current_price,
            "volume_ratio": volume_data.get("volume_ratio", 1.0)
        }
        
        # Lógica de decisão
        signal = Signal.HOLD
        confidence = 0.5
        reason = "Aguardando setup"
        
        if rsi and ema_fast and ema_slow:
            # Condição de COMPRA (Scalp Long)
            if (rsi < self.params["rsi_oversold"] and 
                ema_fast > ema_slow and 
                volume_data.get("volume_ratio", 0) > 1.2):
                
                signal = Signal.BUY
                confidence = min(0.85, 0.65 + (self.params["rsi_oversold"] - rsi) / 100)
                reason = f"RSI oversold ({rsi:.1f}) + EMA bullish + volume surge"
            
            # Condição de VENDA (Scalp Short ou Take Profit)
            elif (rsi > self.params["rsi_overbought"] and 
                  ema_fast < ema_slow):
                
                signal = Signal.SELL
                confidence = min(0.85, 0.65 + (rsi - self.params["rsi_overbought"]) / 100)
                reason = f"RSI overbought ({rsi:.1f}) + EMA bearish"
            
            # HOLD com monitoramento
            elif 40 < rsi < 60:
                confidence = 0.45
                reason = f"Mercado neutro (RSI: {rsi:.1f})"
        
        return {
            "signal": signal.value,
            "confidence": confidence,
            "reason": reason,
            "indicators": indicators,
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _analyze_trend_following(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estratégia de Seguir Tendência"""
        closes = data["closes"]
        highs = data["highs"]
        lows = data["lows"]
        
        # Indicadores
        ema_fast = self.indicators.ema(closes, self.params["ema_fast"])
        ema_slow = self.indicators.ema(closes, self.params["ema_slow"])
        macd_data = self.indicators.macd(closes)
        atr = self.indicators.atr(highs, lows, closes, 14)
        
        current_price = closes[-1]
        
        indicators = {
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "macd": macd_data.get("macd") if macd_data else None,
            "atr": atr,
            "current_price": current_price
        }
        
        signal = Signal.HOLD
        confidence = 0.5
        reason = "Aguardando tendência clara"
        
        if ema_fast and ema_slow and macd_data:
            ema_diff_pct = ((ema_fast - ema_slow) / ema_slow) * 100
            
            # Tendência de ALTA
            if ema_fast > ema_slow and macd_data["macd"] > macd_data["signal"]:
                signal = Signal.BUY
                trend_strength = min(abs(ema_diff_pct) / 2, 1.0)
                confidence = min(0.88, 0.70 + trend_strength * 0.18)
                reason = f"Tendência de alta confirmada (EMA diff: {ema_diff_pct:.2f}%)"
            
            # Tendência de BAIXA
            elif ema_fast < ema_slow and macd_data["macd"] < macd_data["signal"]:
                signal = Signal.SELL
                trend_strength = min(abs(ema_diff_pct) / 2, 1.0)
                confidence = min(0.88, 0.70 + trend_strength * 0.18)
                reason = f"Tendência de baixa confirmada (EMA diff: {ema_diff_pct:.2f}%)"
            
            else:
                confidence = 0.40
                reason = "Sem tendência definida ou sinais conflitantes"
        
        return {
            "signal": signal.value,
            "confidence": confidence,
            "reason": reason,
            "indicators": indicators,
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _analyze_mean_reversion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estratégia de Reversão à Média"""
        closes = data["closes"]
        
        # Indicadores
        bb_data = self.indicators.bollinger_bands(closes, self.params["bb_period"], self.params["bb_std"])
        rsi = self.indicators.rsi(closes, self.params["rsi_period"])
        
        indicators = {
            "bollinger": bb_data,
            "rsi": rsi
        }
        
        signal = Signal.HOLD
        confidence = 0.5
        reason = "Aguardando extremos de banda"
        
        if bb_data and rsi:
            current_price = bb_data["current"]
            lower_band = bb_data["lower"]
            upper_band = bb_data["upper"]
            middle_band = bb_data["middle"]
            
            # Preço tocou banda inferior (oversold)
            if current_price <= lower_band and rsi < 35:
                signal = Signal.BUY
                confidence = 0.75
                reason = f"Reversão à média: preço na banda inferior + RSI {rsi:.1f}"
            
            # Preço tocou banda superior (overbought)
            elif current_price >= upper_band and rsi > 65:
                signal = Signal.SELL
                confidence = 0.75
                reason = f"Reversão à média: preço na banda superior + RSI {rsi:.1f}"
            
            # Dentro das bandas
            else:
                confidence = 0.35
                reason = "Preço dentro das bandas normais"
        
        return {
            "signal": signal.value,
            "confidence": confidence,
            "reason": reason,
            "indicators": indicators,
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _analyze_momentum(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estratégia de Momentum"""
        closes = data["closes"]
        volumes = data["volumes"]
        
        # Indicadores
        rsi = self.indicators.rsi(closes, self.params["rsi_period"])
        macd_data = self.indicators.macd(
            closes,
            self.params["macd_fast"],
            self.params["macd_slow"],
            self.params["macd_signal"]
        )
        volume_data = self.indicators.volume_profile(volumes, 20)
        
        indicators = {
            "rsi": rsi,
            "macd": macd_data,
            "volume_ratio": volume_data.get("volume_ratio", 1.0)
        }
        
        signal = Signal.HOLD
        confidence = 0.5
        reason = "Aguardando momentum"
        
        if rsi and macd_data:
            # Momentum POSITIVO (forte alta)
            if (rsi > 55 and rsi < 75 and 
                macd_data["histogram"] > 0 and 
                volume_data.get("volume_ratio", 0) > 1.3):
                
                signal = Signal.BUY
                confidence = 0.78
                reason = f"Momentum positivo: RSI {rsi:.1f} + MACD bullish + volume"
            
            # Momentum NEGATIVO (forte baixa)
            elif (rsi < 45 and rsi > 25 and 
                  macd_data["histogram"] < 0 and 
                  volume_data.get("volume_ratio", 0) > 1.3):
                
                signal = Signal.SELL
                confidence = 0.78
                reason = f"Momentum negativo: RSI {rsi:.1f} + MACD bearish + volume"
            
            else:
                confidence = 0.42
                reason = "Momentum fraco ou indefinido"
        
        return {
            "signal": signal.value,
            "confidence": confidence,
            "reason": reason,
            "indicators": indicators,
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _analyze_breakout(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estratégia de Breakout (rompimento de níveis)"""
        closes = data["closes"]
        highs = data["highs"]
        lows = data["lows"]
        volumes = data["volumes"]
        
        lookback = self.params["lookback_period"]
        
        # Níveis de suporte/resistência
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        
        resistance = max(recent_highs)
        support = min(recent_lows)
        
        current_price = closes[-1]
        volume_data = self.indicators.volume_profile(volumes, 20)
        
        indicators = {
            "resistance": resistance,
            "support": support,
            "current_price": current_price,
            "volume_ratio": volume_data.get("volume_ratio", 1.0)
        }
        
        signal = Signal.HOLD
        confidence = 0.5
        reason = "Aguardando breakout"
        
        # Breakout de RESISTÊNCIA
        if (current_price > resistance * 1.002 and  # 0.2% acima
            volume_data.get("volume_ratio", 0) > self.params["volume_threshold"]):
            
            signal = Signal.BUY
            confidence = 0.82
            reason = f"Breakout de resistência ({resistance:.2f}) com volume"
        
        # Breakout de SUPORTE
        elif (current_price < support * 0.998 and  # 0.2% abaixo
              volume_data.get("volume_ratio", 0) > self.params["volume_threshold"]):
            
            signal = Signal.SELL
            confidence = 0.82
            reason = f"Breakout de suporte ({support:.2f}) com volume"
        
        # Dentro do range
        else:
            confidence = 0.38
            reason = f"Preço em range (S:{support:.2f} - R:{resistance:.2f})"
        
        return {
            "signal": signal.value,
            "confidence": confidence,
            "reason": reason,
            "indicators": indicators,
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _create_hold_response(self, reason: str) -> Dict[str, Any]:
        """Cria resposta padrão de HOLD"""
        return {
            "signal": Signal.HOLD.value,
            "confidence": 0.0,
            "reason": reason,
            "indicators": {},
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
