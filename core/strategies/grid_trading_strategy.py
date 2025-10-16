# core/strategies/grid_trading_strategy.py
"""
Grid Trading Strategy - Adaptado de Hummingbot Order Level Builder
Estratégia de grid com múltiplos níveis de compra e venda
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import logging

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class GridTradingStrategy(BaseStrategy):
    """
    Grid Trading Strategy
    
    Cria uma grade de ordens de compra e venda em níveis pré-definidos
    para lucrar com oscilações de preço em ranges
    """
    
    strategy_name: str = "GridTrading"
    strategy_version: str = "1.0.0"
    
    # Parâmetros do grid
    grid_levels: int = 10  # Número de níveis no grid
    grid_range_pct: float = 0.10  # 10% range total (5% acima, 5% abaixo)
    
    # Tipo de distribuição
    distribution_type: str = "uniform"  # uniform, geometric, exponential
    
    # Parâmetros de ordem
    order_amount_pct: float = 0.05  # 5% do capital por ordem
    
    # Take profit / Stop loss por grid
    tp_per_grid: float = 0.01  # 1% TP por grid
    sl_per_grid: float = 0.02  # 2% SL por grid
    
    # Range detection
    auto_range: bool = True  # Detecta range automaticamente
    range_lookback: int = 100  # Períodos para detectar range
    
    minimal_roi: Dict[int, float] = {
        "0": 0.001,  # 0.1% target por trade
    }
    
    stoploss: float = -0.05  # 5% stop loss global
    timeframe: str = "15m"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        if config:
            self.grid_levels = config.get('grid_levels', self.grid_levels)
            self.grid_range_pct = config.get('grid_range_pct', self.grid_range_pct)
            self.distribution_type = config.get('distribution_type', self.distribution_type)
            self.order_amount_pct = config.get('order_amount_pct', self.order_amount_pct)
            self.tp_per_grid = config.get('tp_per_grid', self.tp_per_grid)
            self.sl_per_grid = config.get('sl_per_grid', self.sl_per_grid)
            self.auto_range = config.get('auto_range', self.auto_range)
            self.range_lookback = config.get('range_lookback', self.range_lookback)
        
        logger.info(f"GridTrading Strategy initialized - Levels: {self.grid_levels}, Range: {self.grid_range_pct*100:.1f}%")
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calcula indicadores para grid trading
        """
        # Detecta range automaticamente
        if self.auto_range:
            dataframe['range_high'] = dataframe['high'].rolling(self.range_lookback).max()
            dataframe['range_low'] = dataframe['low'].rolling(self.range_lookback).min()
            dataframe['range_mid'] = (dataframe['range_high'] + dataframe['range_low']) / 2
            dataframe['range_width'] = (dataframe['range_high'] - dataframe['range_low']) / dataframe['range_mid']
        else:
            # Usa range fixo baseado em preço atual
            dataframe['range_mid'] = dataframe['close']
            dataframe['range_high'] = dataframe['close'] * (1 + self.grid_range_pct / 2)
            dataframe['range_low'] = dataframe['close'] * (1 - self.grid_range_pct / 2)
            dataframe['range_width'] = self.grid_range_pct
        
        # Detecta se está em range ou tendência
        dataframe['atr'] = self._calculate_atr(dataframe, period=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']
        
        # ADX para confirmar range (ADX baixo = range)
        dataframe['adx'] = self._calculate_adx(dataframe, period=14)
        
        # Calcula níveis do grid
        dataframe = self._calculate_grid_levels(dataframe)
        
        # Identifica onde o preço está no grid
        dataframe['grid_position'] = self._identify_grid_position(dataframe)
        
        # Volume profile
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de entrada para grid trading
        """
        # Condições para ativar grid
        in_range_mode = (
            (dataframe['adx'] < 25) &  # ADX baixo indica range
            (dataframe['range_width'] > 0.02) &  # Range mínimo de 2%
            (dataframe['range_width'] < 0.30)  # Range máximo de 30%
        )
        
        # Buy quando preço está na parte baixa do range
        dataframe.loc[
            in_range_mode &
            (dataframe['close'] < dataframe['range_mid']) &
            (dataframe['grid_position'] < 0.4),  # 40% do grid
            'enter_long'
        ] = 1
        
        # Sell quando preço está na parte alta do range
        dataframe.loc[
            in_range_mode &
            (dataframe['close'] > dataframe['range_mid']) &
            (dataframe['grid_position'] > 0.6),  # 60% do grid
            'enter_short'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de saída
        """
        # Exit long quando preço atinge níveis superiores do grid
        dataframe.loc[
            (dataframe['grid_position'] > 0.5) |  # Meio do grid ou acima
            (dataframe['adx'] > 30),  # Saindo de range
            'exit_long'
        ] = 1
        
        # Exit short quando preço atinge níveis inferiores do grid
        dataframe.loc[
            (dataframe['grid_position'] < 0.5) |  # Meio do grid ou abaixo
            (dataframe['adx'] > 30),  # Saindo de range
            'exit_short'
        ] = 1
        
        return dataframe
    
    def _calculate_grid_levels(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula níveis do grid baseado na distribuição escolhida
        """
        range_high = dataframe['range_high'].iloc[-1] if len(dataframe) > 0 else 100
        range_low = dataframe['range_low'].iloc[-1] if len(dataframe) > 0 else 90
        
        if self.distribution_type == "uniform":
            # Distribuição uniforme
            levels = np.linspace(range_low, range_high, self.grid_levels)
        
        elif self.distribution_type == "geometric":
            # Distribuição geométrica (mais níveis no centro)
            ratio = (range_high / range_low) ** (1 / (self.grid_levels - 1))
            levels = [range_low * (ratio ** i) for i in range(self.grid_levels)]
        
        elif self.distribution_type == "exponential":
            # Distribuição exponencial (concentra níveis nas pontas)
            x = np.linspace(0, 1, self.grid_levels)
            levels = range_low + (range_high - range_low) * (np.exp(2*x) - 1) / (np.exp(2) - 1)
        
        else:
            levels = np.linspace(range_low, range_high, self.grid_levels)
        
        # Armazena níveis no dataframe (últimas N linhas)
        for i, level in enumerate(levels):
            dataframe[f'grid_level_{i}'] = level
        
        return dataframe
    
    def _identify_grid_position(self, dataframe: pd.DataFrame) -> pd.Series:
        """
        Identifica posição do preço no grid (0 = bottom, 1 = top)
        """
        range_high = dataframe['range_high']
        range_low = dataframe['range_low']
        close = dataframe['close']
        
        # Normaliza posição entre 0 e 1
        position = (close - range_low) / (range_high - range_low)
        position = position.clip(0, 1)  # Limita entre 0 e 1
        
        return position
    
    def _calculate_atr(self, dataframe: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calcula Average True Range
        """
        high = dataframe['high']
        low = dataframe['low']
        close = dataframe['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    
    def _calculate_adx(self, dataframe: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calcula Average Directional Index
        """
        high = dataframe['high']
        low = dataframe['low']
        close = dataframe['close']
        
        # Calculate +DM and -DM
        up_move = high.diff()
        down_move = -low.diff()
        
        plus_dm = pd.Series(0.0, index=dataframe.index)
        minus_dm = pd.Series(0.0, index=dataframe.index)
        
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
        
        # Calculate ATR
        atr = self._calculate_atr(dataframe, period)
        
        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm.rolling(period).sum() / atr)
        minus_di = 100 * (minus_dm.rolling(period).sum() / atr)
        
        # Calculate DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # Calculate ADX
        adx = dx.rolling(period).mean()
        
        return adx
    
    def get_grid_orders(self, current_price: float) -> List[Dict[str, Any]]:
        """
        Retorna lista de ordens para todas as posições do grid
        
        Args:
            current_price: Preço atual do mercado
        
        Returns:
            Lista de ordens {price, amount_pct, side, level}
        """
        orders = []
        
        # Calcula range
        range_mid = current_price
        range_high = current_price * (1 + self.grid_range_pct / 2)
        range_low = current_price * (1 - self.grid_range_pct / 2)
        
        # Distribui níveis
        if self.distribution_type == "uniform":
            buy_levels = np.linspace(range_low, range_mid, self.grid_levels // 2)
            sell_levels = np.linspace(range_mid, range_high, self.grid_levels // 2)
        else:
            buy_levels = np.linspace(range_low, range_mid, self.grid_levels // 2)
            sell_levels = np.linspace(range_mid, range_high, self.grid_levels // 2)
        
        # Ordens de compra
        for i, price in enumerate(buy_levels):
            orders.append({
                'price': price,
                'amount_pct': self.order_amount_pct,
                'side': 'buy',
                'level': i,
                'tp': price * (1 + self.tp_per_grid),
                'sl': price * (1 - self.sl_per_grid)
            })
        
        # Ordens de venda
        for i, price in enumerate(sell_levels):
            orders.append({
                'price': price,
                'amount_pct': self.order_amount_pct,
                'side': 'sell',
                'level': i + len(buy_levels),
                'tp': price * (1 - self.tp_per_grid),
                'sl': price * (1 + self.sl_per_grid)
            })
        
        return orders
