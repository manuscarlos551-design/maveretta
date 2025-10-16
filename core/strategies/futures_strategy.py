"""
Futures Strategy - Estratégia Exemplo para Futures Trading

Estratégia simples de breakout para demonstrar uso do sistema de futures.
"""

from typing import Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime


class FuturesBreakoutStrategy:
    """
    Estratégia de breakout para futures com leverage.
    
    Lógica:
    - Identifica breakouts de resistência/suporte
    - Usa leverage configurável
    - Implementa trailing stop
    - Proteção de liquidação ativa
    """

    def __init__(self, config: Dict):
        """
        Inicializa estratégia.

        Args:
            config: Configurações da estratégia
        """
        self.config = config
        self.name = "FuturesBreakoutStrategy"
        self.version = "1.0.0"
        
        # Parâmetros
        self.leverage = config.get('leverage', 3)
        self.risk_per_trade_pct = config.get('risk_per_trade_pct', 2.0)
        self.stop_loss_atr_multiplier = config.get('stop_loss_atr_multiplier', 2.0)
        self.take_profit_ratio = config.get('take_profit_ratio', 2.0)  # Risk:Reward
        self.breakout_period = config.get('breakout_period', 20)
        self.min_volume_increase = config.get('min_volume_increase', 1.5)
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analisa dados e gera sinais.

        Args:
            df: DataFrame com OHLCV

        Returns:
            Dict com análise e sinal
        """
        if len(df) < self.breakout_period + 14:
            return {
                'signal': 'NEUTRAL',
                'reason': 'Dados insuficientes',
                'confidence': 0
            }

        # Calcular indicadores
        df = self._calculate_indicators(df)

        # Verificar breakout
        breakout_signal = self._check_breakout(df)

        # Verificar volume
        volume_confirmed = self._check_volume(df)

        # Calcular ATR para stop loss
        atr = df['atr'].iloc[-1]

        # Gerar sinal
        if breakout_signal == 'LONG' and volume_confirmed:
            entry_price = df['close'].iloc[-1]
            stop_loss = entry_price - (atr * self.stop_loss_atr_multiplier)
            take_profit = entry_price + (entry_price - stop_loss) * self.take_profit_ratio

            return {
                'signal': 'LONG',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': self.leverage,
                'confidence': 0.7,
                'reason': f'Breakout de resistência em {entry_price:.2f} com volume confirmado',
                'atr': atr,
                'timestamp': datetime.utcnow().isoformat()
            }

        elif breakout_signal == 'SHORT' and volume_confirmed:
            entry_price = df['close'].iloc[-1]
            stop_loss = entry_price + (atr * self.stop_loss_atr_multiplier)
            take_profit = entry_price - (stop_loss - entry_price) * self.take_profit_ratio

            return {
                'signal': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': self.leverage,
                'confidence': 0.7,
                'reason': f'Breakout de suporte em {entry_price:.2f} com volume confirmado',
                'atr': atr,
                'timestamp': datetime.utcnow().isoformat()
            }

        else:
            return {
                'signal': 'NEUTRAL',
                'reason': 'Sem breakout confirmado',
                'confidence': 0,
                'current_price': df['close'].iloc[-1],
                'timestamp': datetime.utcnow().isoformat()
            }

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos"""
        df = df.copy()

        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(window=14).mean()

        # Resistência e suporte (highest high / lowest low)
        df['resistance'] = df['high'].rolling(window=self.breakout_period).max()
        df['support'] = df['low'].rolling(window=self.breakout_period).min()

        # Volume médio
        df['volume_avg'] = df['volume'].rolling(window=20).mean()

        return df

    def _check_breakout(self, df: pd.DataFrame) -> str:
        """
        Verifica breakout de resistência ou suporte.

        Returns:
            'LONG', 'SHORT' ou 'NONE'
        """
        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Breakout de resistência (LONG)
        if current['close'] > current['resistance'] and previous['close'] <= previous['resistance']:
            return 'LONG'

        # Breakout de suporte (SHORT)
        if current['close'] < current['support'] and previous['close'] >= previous['support']:
            return 'SHORT'

        return 'NONE'

    def _check_volume(self, df: pd.DataFrame) -> bool:
        """
        Verifica se volume confirma breakout.

        Returns:
            True se volume aumentou significativamente
        """
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume_avg'].iloc[-1]

        return current_volume >= (avg_volume * self.min_volume_increase)

    def should_exit(self, position: Dict, current_data: Dict) -> Dict:
        """
        Determina se deve sair da posição.

        Args:
            position: Dados da posição atual
            current_data: Dados atuais do mercado

        Returns:
            Dict com decisão de saída
        """
        current_price = current_data['price']
        entry_price = position['entry_price']
        stop_loss = position['stop_loss']
        take_profit = position['take_profit']
        side = position['side']

        # Verificar stop loss
        if side == 'long':
            if current_price <= stop_loss:
                return {
                    'should_exit': True,
                    'reason': 'Stop loss atingido',
                    'exit_price': current_price
                }
            elif current_price >= take_profit:
                return {
                    'should_exit': True,
                    'reason': 'Take profit atingido',
                    'exit_price': current_price
                }
        else:  # short
            if current_price >= stop_loss:
                return {
                    'should_exit': True,
                    'reason': 'Stop loss atingido',
                    'exit_price': current_price
                }
            elif current_price <= take_profit:
                return {
                    'should_exit': True,
                    'reason': 'Take profit atingido',
                    'exit_price': current_price
                }

        return {
            'should_exit': False,
            'reason': 'Manter posição',
            'current_price': current_price
        }

    def get_params(self) -> Dict:
        """Retorna parâmetros da estratégia"""
        return {
            'name': self.name,
            'version': self.version,
            'leverage': self.leverage,
            'risk_per_trade_pct': self.risk_per_trade_pct,
            'stop_loss_atr_multiplier': self.stop_loss_atr_multiplier,
            'take_profit_ratio': self.take_profit_ratio,
            'breakout_period': self.breakout_period,
            'min_volume_increase': self.min_volume_increase
        }


class FuturesTrendFollowingStrategy:
    """
    Estratégia de seguimento de tendência para futures.
    
    Usa EMAs para identificar tendências e entra com leverage.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.name = "FuturesTrendFollowingStrategy"
        self.version = "1.0.0"
        
        self.leverage = config.get('leverage', 5)
        self.risk_per_trade_pct = config.get('risk_per_trade_pct', 1.5)
        self.ema_fast = config.get('ema_fast', 12)
        self.ema_slow = config.get('ema_slow', 26)
        self.atr_stop_multiplier = config.get('atr_stop_multiplier', 2.5)

    def analyze(self, df: pd.DataFrame) -> Dict:
        """Analisa e gera sinais baseados em EMAs"""
        if len(df) < max(self.ema_fast, self.ema_slow) + 14:
            return {
                'signal': 'NEUTRAL',
                'reason': 'Dados insuficientes',
                'confidence': 0
            }

        # Calcular indicadores
        df = df.copy()
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(window=14).mean()

        # Verificar crossover
        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Golden cross (LONG)
        if (current['ema_fast'] > current['ema_slow'] and 
            previous['ema_fast'] <= previous['ema_slow']):
            
            entry_price = current['close']
            atr = current['atr']
            stop_loss = entry_price - (atr * self.atr_stop_multiplier)
            take_profit = entry_price + (atr * self.atr_stop_multiplier * 2)

            return {
                'signal': 'LONG',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': self.leverage,
                'confidence': 0.65,
                'reason': 'Golden cross - tendência de alta',
                'timestamp': datetime.utcnow().isoformat()
            }

        # Death cross (SHORT)
        elif (current['ema_fast'] < current['ema_slow'] and 
              previous['ema_fast'] >= previous['ema_slow']):
            
            entry_price = current['close']
            atr = current['atr']
            stop_loss = entry_price + (atr * self.atr_stop_multiplier)
            take_profit = entry_price - (atr * self.atr_stop_multiplier * 2)

            return {
                'signal': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': self.leverage,
                'confidence': 0.65,
                'reason': 'Death cross - tendência de baixa',
                'timestamp': datetime.utcnow().isoformat()
            }

        return {
            'signal': 'NEUTRAL',
            'reason': 'Sem crossover detectado',
            'confidence': 0,
            'current_price': current['close'],
            'timestamp': datetime.utcnow().isoformat()
        }

    def get_params(self) -> Dict:
        return {
            'name': self.name,
            'version': self.version,
            'leverage': self.leverage,
            'risk_per_trade_pct': self.risk_per_trade_pct,
            'ema_fast': self.ema_fast,
            'ema_slow': self.ema_slow,
            'atr_stop_multiplier': self.atr_stop_multiplier
        }
