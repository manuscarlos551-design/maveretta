# core/data/ohlcv_loader.py
from __future__ import annotations
from typing import Optional, Dict, List
import time
import pandas as pd
import ccxt

__all__ = [
    "MaverettaOHLCVLoader",
    "ohlcv_loader",
    "load_slot_pair_history",
    "load_multi_slot_data",
]

class MaverettaOHLCVLoader:
    """
    Loader simples baseado em ccxt.
    Usa credenciais/env já presentes no projeto para instanciar o exchange primário (Binance por padrão).
    """

    def __init__(self, exchange_name: str = "binance", timeframe_default: str = "1m"):
        self.exchange_name = exchange_name
        self.timeframe_default = timeframe_default
        self.exchange = self._make_exchange()

    def _make_exchange(self):
        name = self.exchange_name.lower()
        if not hasattr(ccxt, name):
            raise RuntimeError(f"Exchange CCXT '{name}' não encontrada")
        klass = getattr(ccxt, name)
        # credenciais podem ser estendidas aqui se necessário (já existem no .env)
        return klass({
            "enableRateLimit": True,
            "options": {"adjustForTimeDifference": True},
        })

    def fetch_ohlcv(self, symbol: str, timeframe: Optional[str] = None, since: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
        tf = timeframe or self.timeframe_default
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=tf, since=since, limit=limit)
        if not raw:
            return pd.DataFrame(columns=["timestamp","open","high","low","close","volume"])
        df = pd.DataFrame(raw, columns=["timestamp","open","high","low","close","volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

# Instância default para quem importa "ohlcv_loader"
ohlcv_loader = MaverettaOHLCVLoader()

def load_slot_pair_history(symbol: str, timeframe: str, since: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
    return ohlcv_loader.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=since, limit=limit)

def load_multi_slot_data(pairs: List[str], timeframe: str, since: Optional[int] = None, limit: int = 1000) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    for sym in pairs:
        out[sym] = load_slot_pair_history(sym, timeframe=timeframe, since=since, limit=limit)
    return out