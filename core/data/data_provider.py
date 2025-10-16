# core/data/data_provider.py
"""
Data Provider - Provedor de dados unificado
Adaptado do Freqtrade DataProvider
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from .ohlcv_loader import ohlcv_loader

logger = logging.getLogger(__name__)

class MaverettaDataProvider:
    """
    Provedor de dados unificado para o sistema Maveretta
    Interface central para obter dados OHLCV, tickers e métricas
    """
    
    @staticmethod
    def candles(symbol: str, timeframe: str, since: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
        return ohlcv_loader.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=since, limit=limit)