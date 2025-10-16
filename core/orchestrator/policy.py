# core/orchestrator/policy.py
"""Agent Consensus Policy - Phase 4

Builds prompts and manages consensus decision logic
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def build_proposal_prompt(agent_cfg: Dict[str, Any], market_ctx: Dict[str, Any]) -> str:
    """Build standardized prompt for agent consensus proposal - Phase 4
    
    Args:
        agent_cfg: Agent configuration
        market_ctx: Market context (symbol, price, indicators, etc.)
    
    Returns:
        Prompt string for LLM to generate {action, confidence, rationale}
    """
    agent_id = agent_cfg.get('agent_id', 'unknown')
    role = agent_cfg.get('role', 'trader')
    symbol = market_ctx.get('symbol', 'UNKNOWN')
    price = market_ctx.get('price', 0)
    timeframe = market_ctx.get('timeframe', '5m')
    
    # Get risk constraints from agent config
    risk_cfg = agent_cfg.get('risk', {})
    max_position = risk_cfg.get('max_position_notional_usdt', 1000)
    max_drawdown = risk_cfg.get('max_daily_drawdown_pct', 2.0)
    
    prompt = f"""You are {agent_id}, a specialized {role} AI trading agent in a multi-agent consensus system.

MARKET CONTEXT:
- Symbol: {symbol}
- Timeframe: {timeframe}
- Current Price: ${price:,.2f}
- Trend: {market_ctx.get('trend', 'neutral')}
- Volatility (24h): {market_ctx.get('volatility', 0):.2%}
- Volume (24h): ${market_ctx.get('volume_24h', 0):,.0f}
- ATR(14): {market_ctx.get('atr_14', 0):.2f}

YOUR ROLE: {role}

RISK CONSTRAINTS:
- Max Position Size: ${max_position:,.0f} USDT
- Max Daily Drawdown: {max_drawdown:.1f}%

TASK: Analyze the market and propose a trading action.

IMPORTANT:
- Be decisive but conservative
- Consider your role specialty ({role})
- Only recommend actions you're confident about
- Lower confidence means other agents will challenge your proposal

Respond in valid JSON format:
{{
    "action": "open_long" | "open_short" | "hold",
    "confidence": 0.0-1.0,
    "rationale": "Brief explanation (1-2 sentences) of your reasoning",
    "suggested_notional_usdt": 100-{max_position},
    "tp_pct": 0.3-2.0,
    "sl_pct": 0.2-1.5
}}

Your proposal:"""
    
    return prompt


def build_challenge_prompt(
    agent_cfg: Dict[str, Any],
    proposal: Dict[str, Any],
    market_ctx: Dict[str, Any]
) -> str:
    """Build prompt for challenge phase - Phase 4
    
    Args:
        agent_cfg: Challenging agent configuration
        proposal: Proposal to challenge
        market_ctx: Market context
    
    Returns:
        Prompt string for challenge
    """
    agent_id = agent_cfg.get('agent_id', 'unknown')
    role = agent_cfg.get('role', 'trader')
    proposer = proposal.get('agent_id', 'unknown')
    action = proposal.get('action', 'unknown')
    confidence = proposal.get('confidence', 0)
    rationale = proposal.get('rationale', 'No rationale provided')
    notional = proposal.get('suggested_notional_usdt', 0)
    tp_pct = proposal.get('tp_pct', 0)
    sl_pct = proposal.get('sl_pct', 0)
    
    prompt = f"""You are {agent_id}, a {role} AI trading agent reviewing a proposal from {proposer}.

PROPOSAL DETAILS:
- Proposer: {proposer}
- Action: {action}
- Confidence: {confidence:.2f}
- Rationale: {rationale}
- Position Size: ${notional:,.0f} USDT
- Take Profit: {tp_pct:.1f}%
- Stop Loss: {sl_pct:.1f}%

MARKET CONTEXT:
- Symbol: {market_ctx.get('symbol', 'UNKNOWN')}
- Current Price: ${market_ctx.get('price', 0):,.2f}
- Trend: {market_ctx.get('trend', 'neutral')}
- Volatility: {market_ctx.get('volatility', 0):.2%}

YOUR ROLE: {role}

TASK: Review this proposal critically.
- Do you agree with the action?
- Is the confidence justified?
- Are the risk parameters appropriate?
- What concerns do you have?

Respond in valid JSON format:
{{
    "agree": true | false,
    "comment": "Your challenge or approval (1-2 sentences)",
    "confidence_adjustment": -0.3 to +0.3,
    "suggested_changes": {{
        "notional_usdt": <new_value> | null,
        "tp_pct": <new_value> | null,
        "sl_pct": <new_value> | null
    }}
}}

Your review:"""
    
    return prompt


def evaluate_consensus(
    proposals: List[Dict[str, Any]],
    challenges: List[Dict[str, Any]] = None,
    confidence_threshold: float = 0.6
) -> Dict[str, Any]:
    """Evaluate consensus from agent proposals and challenges - Phase 4
    
    Rules:
    - Approve if ≥2 agents converge on same direction (open_long/open_short)
    - Average confidence must be ≥ confidence_threshold
    - Challenges reduce confidence
    - Ties result in hold
    
    Args:
        proposals: List of proposals [{agent_id, action, confidence, rationale, ...}]
        challenges: List of challenges [{from_agent, agree, comment, confidence_adjustment}]
        confidence_threshold: Minimum average confidence required
    
    Returns:
        {
            "approved": bool,
            "action": str,
            "confidence_avg": float,
            "reason": str,
            "participating_agents": List[str],
            "notional_usdt": float,
            "tp_pct": float,
            "sl_pct": float
        }
    """
    if not proposals:
        return {
            "approved": False,
            "action": "hold",
            "confidence_avg": 0.0,
            "reason": "No proposals received",
            "participating_agents": [],
            "notional_usdt": 0,
            "tp_pct": 0,
            "sl_pct": 0
        }
    
    # Count votes by action
    action_votes: Dict[str, List[Dict[str, Any]]] = {}
    for proposal in proposals:
        action = proposal.get('action', 'hold')
        if action not in action_votes:
            action_votes[action] = []
        action_votes[action].append(proposal)
    
    # Find action with most votes
    max_votes = 0
    winning_action = 'hold'
    winning_proposals = []
    
    for action, votes in action_votes.items():
        if len(votes) > max_votes:
            max_votes = len(votes)
            winning_action = action
            winning_proposals = votes
    
    # Check if we have consensus (≥2 agents)
    if max_votes < 2:
        return {
            "approved": False,
            "action": "hold",
            "confidence_avg": 0.0,
            "reason": "No consensus: insufficient agreement between agents",
            "participating_agents": [p.get('agent_id', 'unknown') for p in proposals],
            "notional_usdt": 0,
            "tp_pct": 0,
            "sl_pct": 0
        }
    
    # Calculate average confidence from winning proposals
    confidences = [p.get('confidence', 0) for p in winning_proposals]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    # Apply challenge adjustments if provided
    if challenges:
        for challenge in challenges:
            if not challenge.get('agree', True):
                adjustment = challenge.get('confidence_adjustment', -0.1)
                avg_confidence += adjustment
    
    # Clamp confidence to [0, 1]
    avg_confidence = max(0.0, min(1.0, avg_confidence))
    
    # Check confidence threshold
    if avg_confidence < confidence_threshold:
        return {
            "approved": False,
            "action": winning_action,
            "confidence_avg": avg_confidence,
            "reason": f"Confidence too low: {avg_confidence:.2f} < {confidence_threshold}",
            "participating_agents": [p.get('agent_id', 'unknown') for p in winning_proposals],
            "notional_usdt": 0,
            "tp_pct": 0,
            "sl_pct": 0
        }
    
    # Calculate consensus parameters (average from winning proposals)
    notional_values = [p.get('suggested_notional_usdt', 300) for p in winning_proposals]
    tp_values = [p.get('tp_pct', 0.7) for p in winning_proposals]
    sl_values = [p.get('sl_pct', 0.4) for p in winning_proposals]
    
    avg_notional = sum(notional_values) / len(notional_values) if notional_values else 300
    avg_tp = sum(tp_values) / len(tp_values) if tp_values else 0.7
    avg_sl = sum(sl_values) / len(sl_values) if sl_values else 0.4
    
    # Apply challenge suggestions if any
    if challenges:
        for challenge in challenges:
            suggestions = challenge.get('suggested_changes', {})
            if suggestions.get('notional_usdt'):
                avg_notional = (avg_notional + suggestions['notional_usdt']) / 2
            if suggestions.get('tp_pct'):
                avg_tp = (avg_tp + suggestions['tp_pct']) / 2
            if suggestions.get('sl_pct'):
                avg_sl = (avg_sl + suggestions['sl_pct']) / 2
    
    participating_agents = [p.get('agent_id', 'unknown') for p in winning_proposals]
    
    return {
        "approved": True,
        "action": winning_action,
        "confidence_avg": avg_confidence,
        "reason": f"Consensus achieved: {max_votes} agents agree with {avg_confidence:.2f} confidence",
        "participating_agents": participating_agents,
        "notional_usdt": round(avg_notional, 2),
        "tp_pct": round(avg_tp, 2),
        "sl_pct": round(avg_sl, 2)
    }
