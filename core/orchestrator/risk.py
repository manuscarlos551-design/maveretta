# core/orchestrator/risk.py
"""Dynamic Risk Management - Phase 4

Evaluates and adjusts consensus decisions based on real-time risk metrics
"""

import os
import logging
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)


def evaluate_dynamic_risk(
    consensus: Dict[str, Any],
    market_ctx: Dict[str, Any],
    agent_metrics: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Dict[str, Any], str]:
    """Evaluate dynamic risk and adjust consensus parameters - Phase 4
    
    Inputs:
    - ATR recent, volatility
    - agent_drawdown_pct, session_equity_protection_pct
    - MAX_DRAWDOWN_PER_SYMBOL_PCT from env
    - PnL recente
    
    Args:
        consensus: Consensus result dict with action, confidence_avg, notional_usdt, tp_pct, sl_pct
        market_ctx: Market context with symbol, volatility, atr_14, price
        agent_metrics: Optional agent-specific metrics (drawdown, pnl, positions_open)
    
    Returns:
        Tuple of (approved, adjusted_params, reason)
        - approved: bool - Whether to allow execution
        - adjusted_params: dict - Adjusted trading parameters
        - reason: str - Explanation
    """
    symbol = consensus.get('symbol', market_ctx.get('symbol', 'UNKNOWN'))
    action = consensus.get('action', 'hold')
    confidence = consensus.get('confidence_avg', 0)
    notional = consensus.get('notional_usdt', 0)
    tp_pct = consensus.get('tp_pct', 0.7)
    sl_pct = consensus.get('sl_pct', 0.4)
    
    # Load risk parameters from environment
    max_drawdown_per_symbol = float(os.getenv('MAX_DRAWDOWN_PER_SYMBOL_PCT', '8.0'))
    session_equity_protection = float(os.getenv('SESSION_EQUITY_PROTECTION_PCT', '10.0'))
    
    # Initialize adjusted parameters
    adjusted = {
        'notional_usdt': notional,
        'tp_pct': tp_pct,
        'sl_pct': sl_pct,
        'approved': True,
        'adjustments': []
    }
    
    # Risk check 1: Market volatility
    volatility = market_ctx.get('volatility', 0)
    if volatility > 0.05:  # 5% volatility threshold
        # High volatility: reduce position size, widen stops
        reduction_factor = 1 - (volatility - 0.05) * 2  # Reduce proportionally
        reduction_factor = max(0.5, min(1.0, reduction_factor))  # Clamp to [0.5, 1.0]
        
        adjusted['notional_usdt'] = round(notional * reduction_factor, 2)
        adjusted['sl_pct'] = round(sl_pct * 1.2, 2)  # Widen stop loss by 20%
        adjusted['adjustments'].append(
            f"High volatility ({volatility:.2%}): reduced position by {(1-reduction_factor)*100:.0f}%, widened SL"
        )
        logger.info(f"Risk: High volatility adjustment for {symbol}")
    
    # Risk check 2: ATR-based position sizing
    atr = market_ctx.get('atr_14', 0)
    price = market_ctx.get('price', 1)
    if atr > 0 and price > 0:
        atr_pct = (atr / price) * 100
        if atr_pct > 3.0:  # High ATR relative to price
            # Reduce position further
            atr_factor = min(1.0, 3.0 / atr_pct)
            adjusted['notional_usdt'] = round(adjusted['notional_usdt'] * atr_factor, 2)
            adjusted['adjustments'].append(
                f"High ATR ({atr_pct:.1f}%): reduced position to ${adjusted['notional_usdt']:.0f}"
            )
            logger.info(f"Risk: ATR adjustment for {symbol}")
    
    # Risk check 3: Agent drawdown
    if agent_metrics:
        drawdown_pct = agent_metrics.get('drawdown_pct', 0)
        if drawdown_pct > max_drawdown_per_symbol * 0.7:  # 70% of max drawdown
            # Near max drawdown: block trading
            adjusted['approved'] = False
            reason = f"Agent drawdown too high: {drawdown_pct:.1f}% (max: {max_drawdown_per_symbol:.1f}%)"
            logger.warning(f"Risk BLOCKED: {reason}")
            return False, adjusted, reason
        elif drawdown_pct > max_drawdown_per_symbol * 0.5:  # 50% of max drawdown
            # Moderate drawdown: reduce position
            dd_factor = 1 - (drawdown_pct / max_drawdown_per_symbol)
            adjusted['notional_usdt'] = round(adjusted['notional_usdt'] * dd_factor, 2)
            adjusted['adjustments'].append(
                f"Drawdown at {drawdown_pct:.1f}%: reduced position by {(1-dd_factor)*100:.0f}%"
            )
            logger.info(f"Risk: Drawdown adjustment for {symbol}")
    
    # Risk check 4: Recent PnL (if negative, be more conservative)
    if agent_metrics:
        realized_pnl = agent_metrics.get('realized_pnl', 0)
        if realized_pnl < -500:  # Negative PnL threshold
            # Recent losses: reduce position
            pnl_factor = 0.7
            adjusted['notional_usdt'] = round(adjusted['notional_usdt'] * pnl_factor, 2)
            adjusted['adjustments'].append(
                f"Recent losses (${realized_pnl:.0f}): reduced position by 30%"
            )
            logger.info(f"Risk: PnL adjustment for {symbol}")
    
    # Risk check 5: Minimum position size
    if adjusted['notional_usdt'] < 50:  # Minimum viable position
        adjusted['approved'] = False
        reason = f"Position too small after adjustments: ${adjusted['notional_usdt']:.0f} < $50"
        logger.warning(f"Risk BLOCKED: {reason}")
        return False, adjusted, reason
    
    # Risk check 6: Stop loss too tight
    if adjusted['sl_pct'] < 0.2:  # Minimum 0.2% stop loss
        adjusted['sl_pct'] = 0.2
        adjusted['adjustments'].append("Increased SL to minimum 0.2%")
    
    # Risk check 7: Take profit too ambitious
    if adjusted['tp_pct'] > 5.0:  # Maximum 5% take profit
        adjusted['tp_pct'] = 5.0
        adjusted['adjustments'].append("Capped TP at maximum 5.0%")
    
    # Build success reason
    if adjusted['adjustments']:
        reason = f"Approved with adjustments: {'; '.join(adjusted['adjustments'])}"
    else:
        reason = "Approved: all risk checks passed"
    
    logger.info(f"Risk: {symbol} - {reason}")
    
    return True, adjusted, reason


def get_market_context_from_prometheus(symbol: str) -> Dict[str, Any]:
    """Fetch market context from Prometheus metrics - Phase 4
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Market context dictionary
    """
    # This would query Prometheus for real-time metrics
    # For Phase 4, we'll return reasonable defaults
    # In production, this would use prometheus_client or requests to query
    
    try:
        prometheus_url = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
        
        # TODO: Implement real Prometheus queries
        # Example:
        # - risk_atr_14{symbol="BTCUSDT"}
        # - binance_best_ask{symbol="BTCUSDT"}
        # - market_volatility_24h{symbol="BTCUSDT"}
        
        # For now, return simulated values
        return {
            'symbol': symbol,
            'price': 50000.0 if 'BTC' in symbol else 3000.0,
            'volatility': 0.02,  # 2%
            'atr_14': 1000.0 if 'BTC' in symbol else 60.0,
            'volume_24h': 1000000.0,
            'trend': 'neutral'
        }
    except Exception as e:
        logger.warning(f"Failed to fetch market context from Prometheus: {e}")
        return {
            'symbol': symbol,
            'price': 0,
            'volatility': 0,
            'atr_14': 0,
            'volume_24h': 0,
            'trend': 'unknown'
        }


def get_agent_metrics_summary(agent_ids: List[str]) -> Dict[str, Any]:
    """Get aggregated metrics for participating agents - Phase 4
    
    Args:
        agent_ids: List of agent IDs
    
    Returns:
        Aggregated metrics dictionary
    """
    # This would aggregate metrics from all participating agents
    # For Phase 4, return reasonable defaults
    
    return {
        'drawdown_pct': 0.0,
        'realized_pnl': 0.0,
        'positions_open': 0,
        'win_rate': 0.0
    }
