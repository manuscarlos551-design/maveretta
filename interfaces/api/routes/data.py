"""Data API routes for OHLCV and market data."""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from datetime import datetime

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/ohlcv")
async def get_ohlcv_data(
    symbol: str = Query(..., description="Trading pair symbol"),
    timeframe: str = Query(default="1h", description="Timeframe (1m, 5m, 1h, 1d)"),
    limit: Optional[int] = Query(default=100, description="Number of candles")
) -> Dict[str, Any]:
    """Get OHLCV data for a trading pair."""
    try:
        # Return mock OHLCV data structure
        mock_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": [],
            "columns": ["timestamp", "open", "high", "low", "close", "volume"],
            "count": 0
        }
        
        return {
            "success": True,
            "data": mock_data,
            "message": "OHLCV data retrieved (mock)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pairs")
async def get_available_pairs() -> Dict[str, Any]:
    """Get available trading pairs."""
    try:
        mock_pairs = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT"
        ]
        
        return {
            "success": True,
            "pairs": mock_pairs,
            "count": len(mock_pairs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
