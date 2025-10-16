# core/strategies/market_making_strategy.py
"""
Market Making Strategy - Adaptado de Hummingbot PMM
Estratégia de market making profissional com múltiplos níveis
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class MarketMakingStrategy(BaseStrategy):
    """
    Pure Market Making (PMM) Strategy
    
    Cria ordens de compra e venda em múltiplos níveis ao redor do preço de mercado
    para capturar o spread bid-ask
    """
    
    strategy_name: str = "MarketMaking"
    strategy_version: str = "1.0.0"
    
    # Parâmetros específicos de market making
    bid_spread: float = 0.001  # 0.1% spread de compra
    ask_spread: float = 0.001  # 0.1% spread de venda
    order_levels: int = 3  # Número de níveis de ordens
    order_level_spread: float = 0.002  # Spread entre níveis
    order_refresh_time: int = 300  # 5 minutos
    
    # Parâmetros de tamanho
    order_amount_pct: float = 0.1  # 10% do capital por ordem
    inventory_skew_enabled: bool = True
    
    # Risk management
    position_limit_pct: float = 0.5  # Máximo 50% do capital em posição
    
    minimal_roi: Dict[int, float] = {
        "0": 0.002,  # 0.2% target
    }
    
    stoploss: float = -0.01  # 1% stop loss
    timeframe: str = "1m"  # Alta frequência
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Carrega configurações customizadas
        if config:
            self.bid_spread = config.get('bid_spread', self.bid_spread)
            self.ask_spread = config.get('ask_spread', self.ask_spread)
            self.order_levels = config.get('order_levels', self.order_levels)
            self.order_level_spread = config.get('order_level_spread', self.order_level_spread)
            self.order_refresh_time = config.get('order_refresh_time', self.order_refresh_time)
            self.order_amount_pct = config.get('order_amount_pct', self.order_amount_pct)
            self.inventory_skew_enabled = config.get('inventory_skew_enabled', self.inventory_skew_enabled)
            self.position_limit_pct = config.get('position_limit_pct', self.position_limit_pct)
        
        logger.info(f"MarketMaking Strategy initialized - Levels: {self.order_levels}, Spread: {self.bid_spread*100:.2f}%")
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calcula indicadores para market making
        """
        # Mid price (média entre bid e ask)
        if 'bid' in dataframe.columns and 'ask' in dataframe.columns:
            dataframe['mid_price'] = (dataframe['bid'] + dataframe['ask']) / 2
        else:
            dataframe['mid_price'] = dataframe['close']
        
        # Spread atual
        if 'bid' in dataframe.columns and 'ask' in dataframe.columns:
            dataframe['current_spread'] = (dataframe['ask'] - dataframe['bid']) / dataframe['mid_price']
        else:
            dataframe['current_spread'] = 0.001  # Spread estimado
        
        # Volatilidade (para ajuste dinâmico de spread)
        dataframe['volatility'] = dataframe['close'].pct_change().rolling(20).std()
        
        # Volume profile
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # Calcula reservation price (preço ideal baseado em inventário)
        dataframe['reservation_price'] = self._calculate_reservation_price(dataframe)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de entrada para market making
        
        Market making sempre mantém ordens ativas, não tem sinal de entrada tradicional
        """
        # Para market making, sempre há oportunidade se as condições forem favoráveis
        conditions_favorable = (
            (dataframe['current_spread'] > 0.0005) &  # Spread mínimo
            (dataframe['volume_ratio'] > 0.5)  # Volume razoável
        )
        
        # Long side (buy orders)
        dataframe.loc[conditions_favorable, 'enter_long'] = 1
        
        # Short side (sell orders) - sempre que houver inventário
        dataframe.loc[conditions_favorable, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de saída
        
        Market making fecha posições quando spread se torna desfavorável
        """
        # Exit long (vender inventário)
        dataframe.loc[
            (dataframe['current_spread'] < 0.0002) |  # Spread muito baixo
            (dataframe['volatility'] > 0.02),  # Volatilidade alta
            'exit_long'
        ] = 1
        
        # Exit short (comprar de volta)
        dataframe.loc[
            (dataframe['current_spread'] < 0.0002) |
            (dataframe['volatility'] > 0.02),
            'exit_short'
        ] = 1
        
        return dataframe
    
    def _calculate_reservation_price(self, dataframe: pd.DataFrame) -> pd.Series:
        """
        Calcula preço de reserva baseado em inventário (Avellaneda-Stoikov)
        
        reservation_price = mid_price - inventory * gamma * volatility^2
        """
        if not self.inventory_skew_enabled:
            return dataframe['mid_price']
        
        # Parâmetros do modelo
        gamma = 0.1  # Risk aversion parameter
        
        # Inventário normalizado seria obtido do position manager
        # Por enquanto, usamos 0 (neutro)
        inventory = 0
        
        reservation_price = dataframe['mid_price'] - inventory * gamma * dataframe['volatility'] ** 2
        
        return reservation_price
    
    def get_order_levels(self, current_price: float, side: str = 'buy') -> List[Dict[str, float]]:
        """
        Calcula níveis de ordens para market making
        
        Args:
            current_price: Preço atual do mercado
            side: 'buy' ou 'sell'
        
        Returns:
            Lista de dicionários com price e amount para cada nível
        """
        levels = []
        
        base_spread = self.bid_spread if side == 'buy' else self.ask_spread
        direction = -1 if side == 'buy' else 1
        
        for level in range(self.order_levels):
            # Calcula spread para este nível
            level_spread = base_spread + (level * self.order_level_spread)
            
            # Calcula preço
            price = current_price * (1 + direction * level_spread)
            
            # Calcula tamanho (pode ser ajustado por nível)
            amount_pct = self.order_amount_pct / self.order_levels
            
            levels.append({
                'price': price,
                'amount_pct': amount_pct,
                'level': level,
                'side': side
            })
        
        return levels
    
    def adjust_spreads_for_volatility(self, volatility: float) -> tuple:
        """
        Ajusta spreads baseado na volatilidade do mercado
        
        Args:
            volatility: Volatilidade atual
        
        Returns:
            (bid_spread, ask_spread) ajustados
        """
        # Aumenta spread em alta volatilidade
        volatility_multiplier = 1 + (volatility * 50)  # Fator de ajuste
        
        adjusted_bid_spread = self.bid_spread * volatility_multiplier
        adjusted_ask_spread = self.ask_spread * volatility_multiplier
        
        return adjusted_bid_spread, adjusted_ask_spread
    
    def calculate_inventory_skew(self, current_position: float, max_position: float) -> float:
        """
        Calcula skew de inventário para ajustar ordens
        
        Args:
            current_position: Posição atual
            max_position: Posição máxima permitida
        
        Returns:
            Fator de skew (-1 a 1)
        """
        if max_position == 0:
            return 0
        
        inventory_ratio = current_position / max_position
        
        # Limita entre -1 e 1
        inventory_skew = max(-1, min(1, inventory_ratio))
        
        return inventory_skew
