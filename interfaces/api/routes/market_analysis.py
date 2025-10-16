
# interfaces/api/routes/market_analysis.py
"""
Market Analysis Routes - Regime Detection & Whale Monitoring
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/market-analysis", tags=["Market Analysis"])


@router.get("/regime/{symbol}")
async def get_market_regime(
    symbol: str,
    timeframe: str = Query("5m", description="Timeframe for analysis")
):
    """Get current market regime for symbol"""
    try:
        from core.market.regime_detector import regime_detector
        from core.data.ohlcv_loader import get_recent_ohlcv
        
        # Get market data
        df = get_recent_ohlcv(symbol, timeframe=timeframe, limit=100)
        
        if df is None or len(df) < 50:
            raise HTTPException(status_code=404, detail="Insufficient market data")
        
        # Detect regime
        regime, confidence = regime_detector.detect_regime(df)
        
        # Get statistics
        stats = regime_detector.get_regime_stats()
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_regime": regime.value,
            "confidence": confidence,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting market regime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime/best-strategies")
async def get_best_strategies_by_regime():
    """Get best performing strategies for each market regime"""
    try:
        from core.market.regime_detector import regime_detector
        
        best_strategies = regime_detector.get_best_strategies_by_regime()
        
        return {
            "best_strategies_by_regime": best_strategies,
            "total_regimes": len(best_strategies)
        }
        
    except Exception as e:
        logger.error(f"Error getting best strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whale-monitor/alerts")
async def get_whale_alerts(
    symbol: Optional[str] = None,
    activity_type: Optional[str] = None,
    limit: int = Query(50, le=500)
):
    """Get recent whale activity alerts"""
    try:
        from core.market.whale_monitor import whale_monitor
        
        alerts = whale_monitor.get_recent_alerts(
            symbol=symbol,
            activity_type=activity_type,
            limit=limit
        )
        
        return {
            "alerts": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Error getting whale alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whale-monitor/zones/{symbol}")
async def get_whale_zones(symbol: str):
    """Get whale activity zones for symbol"""
    try:
        from core.market.whale_monitor import whale_monitor
        
        zones = whale_monitor.get_whale_zones(symbol)
        stats = whale_monitor.get_statistics()
        
        return {
            "symbol": symbol,
            "whale_zones": zones,
            "zone_count": len(zones),
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting whale zones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-autopsy/patterns")
async def get_trade_patterns():
    """Get trade pattern statistics"""
    try:
        from core.analysis.trade_autopsy import trade_autopsy
        
        patterns = trade_autopsy.get_pattern_statistics()
        comparison = trade_autopsy.compare_winners_vs_losers()
        
        return {
            "patterns": patterns,
            "winners_vs_losers": comparison
        }
        
    except Exception as e:
        logger.error(f"Error getting trade patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-autopsy/analysis/{trade_id}")
async def get_trade_analysis(trade_id: str):
    """Get detailed analysis for a specific trade"""
    try:
        from core.analysis.trade_autopsy import trade_autopsy
        
        # Find analysis in history
        for analysis in trade_autopsy.trade_analyses:
            if analysis.get('trade_id') == trade_id:
                return analysis
        
        raise HTTPException(status_code=404, detail=f"Analysis not found for trade {trade_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
