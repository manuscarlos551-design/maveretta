# core/strategies/dca_strategy.py
"""
DCA (Dollar Cost Averaging) Strategy
Estratégia de acumulação gradual com pyramid trading
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class DCAStrategy(BaseStrategy):
    """
    Dollar Cost Averaging Strategy
    
    Compra (ou vende) gradualmente em múltiplos níveis de preço
    para reduzir risco de timing e melhorar preço médio
    """
    
    strategy_name: str = "DCA"
    strategy_version: str = "1.0.0"
    
    # Parâmetros DCA
    dca_levels: int = 5  # Número de níveis de DCA
    dca_step_pct: float = 0.02  # 2% de queda entre níveis
    dca_amount_scaling: str = "linear"  # linear, exponential, fibonacci
    
    # Parâmetros de posição
    initial_amount_pct: float = 0.10  # 10% do capital inicial
    max_position_pct: float = 0.50  # Máximo 50% do capital
    
    # Condições de ativação
    activate_on_dip: bool = True  # Ativa DCA em quedas
    dip_threshold_pct: float = 0.05  # 5% de queda para ativar
    
    # Take profit agregado
    aggregate_tp_pct: float = 0.10  # 10% TP no preço médio
    
    # Time-based DCA
    time_based: bool = False  # DCA baseado em tempo
    time_interval_hours: int = 24  # 24h entre compras
    
    minimal_roi: Dict[int, float] = {
        "0": 0.10,  # 10% target
        "60": 0.05,  # 5% após 1h
        "120": 0.02,  # 2% após 2h
    }
    
    stoploss: float = -0.15  # 15% stop loss (mais largo para DCA)
    timeframe: str = "1h"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        if config:
            self.dca_levels = config.get('dca_levels', self.dca_levels)
            self.dca_step_pct = config.get('dca_step_pct', self.dca_step_pct)
            self.dca_amount_scaling = config.get('dca_amount_scaling', self.dca_amount_scaling)
            self.initial_amount_pct = config.get('initial_amount_pct', self.initial_amount_pct)
            self.max_position_pct = config.get('max_position_pct', self.max_position_pct)
            self.activate_on_dip = config.get('activate_on_dip', self.activate_on_dip)
            self.dip_threshold_pct = config.get('dip_threshold_pct', self.dip_threshold_pct)
            self.aggregate_tp_pct = config.get('aggregate_tp_pct', self.aggregate_tp_pct)
            self.time_based = config.get('time_based', self.time_based)
            self.time_interval_hours = config.get('time_interval_hours', self.time_interval_hours)
        
        # Estado interno
        self.last_dca_time = None
        self.entry_prices = []
        self.entry_amounts = []
        
        logger.info(f"DCA Strategy initialized - Levels: {self.dca_levels}, Step: {self.dca_step_pct*100:.1f}%")
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calcula indicadores para DCA strategy
        """
        # Moving averages para identificar tendência
        dataframe['ema_20'] = dataframe['close'].ewm(span=20).mean()
        dataframe['ema_50'] = dataframe['close'].ewm(span=50).mean()
        dataframe['ema_200'] = dataframe['close'].ewm(span=200).mean()
        
        # Identifica tendência
        dataframe['uptrend'] = (
            (dataframe['ema_20'] > dataframe['ema_50']) &
            (dataframe['ema_50'] > dataframe['ema_200'])
        )
        
        dataframe['downtrend'] = (
            (dataframe['ema_20'] < dataframe['ema_50']) &
            (dataframe['ema_50'] < dataframe['ema_200'])
        )
        
        # Detecta dips (quedas acentuadas)
        dataframe['high_20'] = dataframe['high'].rolling(20).max()
        dataframe['dip_from_high'] = (dataframe['high_20'] - dataframe['close']) / dataframe['high_20']
        
        # RSI para identificar oversold
        dataframe['rsi'] = self._calculate_rsi(dataframe)
        
        # Bollinger Bands
        dataframe = self._calculate_bollinger_bands(dataframe)
        
        # Volume profile
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_spike'] = dataframe['volume'] > dataframe['volume_ma'] * 1.5
        
        # Calcula níveis DCA baseado em preço atual
        dataframe = self._calculate_dca_levels(dataframe)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de entrada para DCA
        """
        if self.time_based:
            # DCA baseado em tempo (sempre compra no intervalo)
            # Implementação simplificada - em produção, verificaria timestamps
            dataframe['enter_long'] = 1
        
        else:
            # DCA baseado em preço/condições
            
            # Condição 1: Dip significativo
            dip_condition = (
                self.activate_on_dip &
                (dataframe['dip_from_high'] >= self.dip_threshold_pct)
            )
            
            # Condição 2: Oversold em uptrend
            oversold_condition = (
                dataframe['uptrend'] &
                (dataframe['rsi'] < 35)
            )
            
            # Condição 3: Preço abaixo da Bollinger inferior
            bollinger_condition = (
                dataframe['close'] < dataframe['bb_lower']
            )
            
            # Condição 4: Volume spike em queda (compra em pânico)
            panic_buy_condition = (
                dataframe['volume_spike'] &
                (dataframe['close'] < dataframe['close'].shift(1))
            )
            
            # Ativa DCA em qualquer das condições
            dataframe.loc[
                dip_condition | oversold_condition | bollinger_condition | panic_buy_condition,
                'enter_long'
            ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de saída
        """
        # Exit quando atingir target de take profit agregado
        # Ou quando tendência reverter fortemente
        
        dataframe.loc[
            dataframe['downtrend'] &
            (dataframe['rsi'] > 70) &
            (dataframe['close'] > dataframe['bb_upper']),
            'exit_long'
        ] = 1
        
        return dataframe
    
    def _calculate_dca_levels(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula níveis de preço para DCA
        """
        current_price = dataframe['close'].iloc[-1] if len(dataframe) > 0 else 100
        
        # Calcula níveis baseado em scaling method
        amounts = self._calculate_dca_amounts()
        
        for i in range(self.dca_levels):
            # Preço diminui a cada nível (compra mais barato)
            level_price = current_price * (1 - i * self.dca_step_pct)
            dataframe[f'dca_level_{i}_price'] = level_price
            dataframe[f'dca_level_{i}_amount_pct'] = amounts[i]
        
        return dataframe
    
    def _calculate_dca_amounts(self) -> List[float]:
        """
        Calcula montantes para cada nível DCA baseado em scaling method
        
        Returns:
            Lista de percentuais para cada nível
        """
        if self.dca_amount_scaling == "linear":
            # Distribuição linear (igual para todos)
            amounts = [self.initial_amount_pct] * self.dca_levels
        
        elif self.dca_amount_scaling == "exponential":
            # Distribuição exponencial (aumenta a cada nível)
            amounts = []
            for i in range(self.dca_levels):
                amount = self.initial_amount_pct * (1.5 ** i)
                amounts.append(amount)
            
            # Normaliza para não ultrapassar max_position_pct
            total = sum(amounts)
            if total > self.max_position_pct:
                amounts = [a * (self.max_position_pct / total) for a in amounts]
        
        elif self.dca_amount_scaling == "fibonacci":
            # Distribuição Fibonacci
            fib = [1, 1]
            for i in range(2, self.dca_levels):
                fib.append(fib[-1] + fib[-2])
            
            # Normaliza
            fib = fib[:self.dca_levels]
            total_fib = sum(fib)
            amounts = [(f / total_fib) * self.max_position_pct for f in fib]
        
        else:
            amounts = [self.initial_amount_pct] * self.dca_levels
        
        return amounts
    
    def _calculate_rsi(self, dataframe: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calcula RSI
        """
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_bollinger_bands(self, dataframe: pd.DataFrame, period: int = 20, std: float = 2) -> pd.DataFrame:
        """
        Calcula Bollinger Bands
        """
        dataframe['bb_middle'] = dataframe['close'].rolling(period).mean()
        dataframe['bb_std'] = dataframe['close'].rolling(period).std()
        dataframe['bb_upper'] = dataframe['bb_middle'] + (dataframe['bb_std'] * std)
        dataframe['bb_lower'] = dataframe['bb_middle'] - (dataframe['bb_std'] * std)
        
        return dataframe
    
    def get_dca_orders(self, entry_price: float) -> List[Dict[str, Any]]:
        """
        Retorna lista de ordens DCA
        
        Args:
            entry_price: Preço de entrada inicial
        
        Returns:
            Lista de ordens {price, amount_pct, level}
        """
        orders = []
        amounts = self._calculate_dca_amounts()
        
        for i in range(self.dca_levels):
            level_price = entry_price * (1 - i * self.dca_step_pct)
            
            orders.append({
                'price': level_price,
                'amount_pct': amounts[i],
                'level': i,
                'side': 'buy'
            })
        
        return orders
    
    def calculate_average_entry_price(self) -> float:
        """
        Calcula preço médio de entrada ponderado
        
        Returns:
            Preço médio de entrada
        """
        if not self.entry_prices or not self.entry_amounts:
            return 0
        
        total_amount = sum(self.entry_amounts)
        if total_amount == 0:
            return 0
        
        weighted_sum = sum(p * a for p, a in zip(self.entry_prices, self.entry_amounts))
        avg_price = weighted_sum / total_amount
        
        return avg_price
    
    def record_entry(self, price: float, amount: float):
        """
        Registra uma entrada DCA
        """
        self.entry_prices.append(price)
        self.entry_amounts.append(amount)
        self.last_dca_time = datetime.now()
        
        logger.info(f"DCA Entry recorded - Price: {price}, Amount: {amount}, Avg: {self.calculate_average_entry_price()}")
