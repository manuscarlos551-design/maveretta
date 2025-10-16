# core/orchestrator/router.py
"""FastAPI Router for Agent Orchestration Endpoints"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import asyncio
import json as json_lib
from datetime import datetime

from .engine import agent_engine

logger = logging.getLogger(__name__)

# Router with /orchestration prefix
orchestration_router = APIRouter(prefix="/orchestration", tags=["orchestration"])


# Request/Response models
class SetModeRequest(BaseModel):
    mode: str  # shadow | paper | live


class StandardResponse(BaseModel):
    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None


@orchestration_router.get("/agents", response_model=StandardResponse)
async def list_agents():
    """
    List all agents with their current state
    
    Returns agent_id, mode, status, last_tick for each agent
    """
    try:
        agents = agent_engine.list_agents()
        return StandardResponse(ok=True, data=agents, error=None)
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return StandardResponse(ok=False, data=None, error=str(e))


@orchestration_router.post("/agents/{agent_id}/start", response_model=StandardResponse)
async def start_agent(agent_id: str):
    """
    Start an agent's shadow loop
    
    Args:
        agent_id: ID of the agent to start
    """
    try:
        success, message = agent_engine.start_agent(agent_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return StandardResponse(
            ok=True, 
            data={"agent_id": agent_id, "status": "running"},
            error=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@orchestration_router.post("/agents/{agent_id}/stop", response_model=StandardResponse)
async def stop_agent(agent_id: str):
    """
    Stop an agent's shadow loop
    
    Args:
        agent_id: ID of the agent to stop
    """
    try:
        success, message = agent_engine.stop_agent(agent_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return StandardResponse(
            ok=True,
            data={"agent_id": agent_id, "status": "stopped"},
            error=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@orchestration_router.post("/agents/{agent_id}/mode", response_model=StandardResponse)
async def set_agent_mode(agent_id: str, request: SetModeRequest):
    """
    Set agent execution mode (shadow/paper/live)
    
    Phase 1: Only changes state, no actual execution difference
    
    Args:
        agent_id: ID of the agent
        request: Mode to set (shadow, paper, live)
    """
    try:
        success, message = agent_engine.set_mode(agent_id, request.mode)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return StandardResponse(
            ok=True,
            data={"agent_id": agent_id, "mode": request.mode},
            error=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting mode for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@orchestration_router.get("/stats", response_model=StandardResponse)
async def get_orchestration_stats():
    """Get orchestration engine statistics"""
    try:
        stats = agent_engine.get_stats()
        return StandardResponse(ok=True, data=stats, error=None)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return StandardResponse(ok=False, data=None, error=str(e))


@orchestration_router.post("/dialog", response_model=StandardResponse)
async def trigger_dialog(agent_id: str, symbol: str):
    """
    Manually trigger a dialog for an agent on a symbol
    
    Args:
        agent_id: ID of the agent to trigger dialog for
        symbol: Trading symbol
    """
    try:
        from .events import create_dialog, save_dialog, AgentMessage, event_publisher
        from .metrics import increment_dialog
        
        # Get agent
        agent_state = agent_engine.get_agent(agent_id)
        if not agent_state:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Get agent config
        if agent_id not in agent_engine.agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not initialized")
        
        config = agent_engine.agents[agent_id].config
        partners = config.talks_with
        
        if not partners:
            return StandardResponse(
                ok=False,
                data=None,
                error=f"Agent {agent_id} has no dialog partners configured"
            )
        
        # Create dialog
        participants = [agent_id] + partners
        topic = f"Manual dialog on {symbol}"
        dialog = create_dialog(topic, participants)
        
        # Add initial message
        message = AgentMessage(
            from_agent=agent_id,
            to_agent=partners[0],
            topic=topic,
            message=f"Manual dialog request for {symbol}",
            metadata={"manual": True, "symbol": symbol}
        )
        dialog.add_message(message)
        event_publisher.send_message(message)
        
        # Simulate response
        response = AgentMessage(
            from_agent=partners[0],
            to_agent=agent_id,
            topic=topic,
            message=f"Acknowledged: {symbol}",
            metadata={"manual_response": True}
        )
        dialog.add_message(response)
        event_publisher.send_message(response)
        
        # Update metrics
        increment_dialog(agent_id, partners[0])
        
        # Close and save dialog
        dialog.close(outcome="manual_completion")
        save_dialog(dialog)
        
        logger.info(f"Manual dialog triggered: {agent_id} ↔ {partners} on {symbol}")
        
        return StandardResponse(
            ok=True,
            data={
                "dialog_id": dialog.dialog_id,
                "participants": participants,
                "messages_count": len(dialog.messages)
            },
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering dialog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@orchestration_router.get("/decisions", response_model=StandardResponse)
async def get_decisions(
    agent_id: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100
):
    """
    Get recent decisions from MongoDB
    
    Args:
        agent_id: Filter by agent ID (optional)
        symbol: Filter by symbol (optional)
        limit: Maximum number of results (default: 100)
    """
    try:
        from .events import event_publisher
        
        decisions = event_publisher.get_recent_decisions(
            agent_id=agent_id,
            symbol=symbol,
            limit=limit
        )
        
        return StandardResponse(
            ok=True,
            data={"decisions": decisions, "count": len(decisions)},
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error getting decisions: {e}")
        return StandardResponse(ok=False, data=None, error=str(e))


@orchestration_router.get("/dialogs", response_model=StandardResponse)
async def get_dialogs(
    participant: Optional[str] = None,
    limit: int = 50
):
    """
    Get recent dialogs from MongoDB
    
    Args:
        participant: Filter by participant agent ID (optional)
        limit: Maximum number of results (default: 50)
    """
    try:
        from .events import event_publisher
        
        dialogs = event_publisher.get_recent_dialogs(
            participant=participant,
            limit=limit
        )
        
        return StandardResponse(
            ok=True,
            data={"dialogs": dialogs, "count": len(dialogs)},
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error getting dialogs: {e}")
        return StandardResponse(ok=False, data=None, error=str(e))


# ========== PHASE 3: CONSENSUS & PAPER TRADING ENDPOINTS ==========

@orchestration_router.get("/consensus/rounds", response_model=StandardResponse)
async def get_consensus_rounds(
    symbol: Optional[str] = None,
    limit: int = 50
):
    """
    Get recent consensus rounds - Phase 3
    
    Args:
        symbol: Filter by symbol (optional)
        limit: Maximum number of results (default: 50)
    """
    try:
        from .events import get_recent_consensus_rounds
        
        rounds = get_recent_consensus_rounds(symbol=symbol, limit=limit)
        
        return StandardResponse(
            ok=True,
            data={"rounds": rounds, "count": len(rounds)},
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error getting consensus rounds: {e}")
        return StandardResponse(ok=False, data=None, error=str(e))


@orchestration_router.post("/consensus/force", response_model=StandardResponse)
async def force_consensus_round(symbol: str = "BTCUSDT"):
    """
    Force a consensus round for a symbol - Phase 3
    
    Args:
        symbol: Trading symbol
    """
    try:
        # Get all running agents
        agents = agent_engine.list_agents()
        running_agents = [
            agent_id for agent_id, agent_data in agents.items()
            if agent_data.get('status') == 'running'
        ]
        
        if len(running_agents) < 2:
            return StandardResponse(
                ok=False,
                data=None,
                error="Need at least 2 running agents for consensus"
            )
        
        # Run consensus round
        result = agent_engine.run_consensus_round(symbol, running_agents)
        
        # If approved, apply the action
        if result.get('approved'):
            apply_result = apply_consensus_action(result)
            result['paper_trade'] = apply_result
        
        return StandardResponse(
            ok=True,
            data=result,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error forcing consensus: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@orchestration_router.get("/paper/open", response_model=StandardResponse)
async def get_open_paper_trades():
    """
    Get all open paper trades - Phase 3
    """
    try:
        from core.slots.manager import slot_manager
        
        open_trades = slot_manager.get_open_paper_trades()
        
        return StandardResponse(
            ok=True,
            data={"trades": open_trades, "count": len(open_trades)},
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error getting open paper trades: {e}")
        return StandardResponse(ok=False, data=None, error=str(e))


class ClosePaperTradeRequest(BaseModel):
    paper_id: str
    close_price: Optional[float] = None


@orchestration_router.post("/paper/close", response_model=StandardResponse)
async def close_paper_trade(request: ClosePaperTradeRequest):
    """
    Close a paper trade - Phase 3
    
    Args:
        request: Close request with paper_id and optional close_price
    """
    try:
        from core.slots.manager import slot_manager
        from .metrics import increment_paper_trade_closed, update_paper_pnl_unrealized
        
        # Get the paper trade to get symbol
        trade = slot_manager.get_paper_trade(request.paper_id)
        if not trade:
            raise HTTPException(status_code=404, detail=f"Paper trade {request.paper_id} not found")
        
        # Use provided close_price or simulate current price
        close_price = request.close_price if request.close_price else trade['entry_price'] * 1.01
        
        # Close the trade
        success, message, trade_data = slot_manager.close_paper_trade(
            request.paper_id,
            close_price,
            reason="manual"
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        # Update metrics
        if trade_data:
            increment_paper_trade_closed(trade_data['symbol'], 'manual')
            update_paper_pnl_unrealized(trade_data['symbol'], 0)  # Reset to 0 when closed
        
        return StandardResponse(
            ok=True,
            data=trade_data,
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing paper trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== PHASE 4: SSE AND ADDITIONAL ENDPOINTS ==========

@orchestration_router.get("/stream")
async def stream_orchestration_events():
    """
    Server-Sent Events (SSE) stream for real-time orchestration updates - Phase 4
    
    Events:
    - heartbeat
    - consensus_started
    - consensus_proposal_text
    - consensus_challenge_text
    - consensus_decision_text
    - paper_trade_opened
    - paper_trade_closed
    - risk_blocked
    """
    async def event_generator():
        \"\"\"Generate SSE events\"\"\"
        event_id = 0
        
        try:
            while True:
                # Heartbeat every 15 seconds
                event_id += 1
                yield f\"id: {event_id}\\nevent: heartbeat\\ndata: {{\\\"timestamp\\\": \\\"{datetime.now().isoformat()}\\\", \\\"status\\\": \\\"alive\\\"}}\\n\\n\"
                
                # TODO: In production, subscribe to Redis pub/sub or event queue
                # For now, just send heartbeat
                # Future: Listen to event_publisher events and stream them
                
                await asyncio.sleep(15)
                
        except asyncio.CancelledError:
            logger.info(\"SSE stream cancelled\")
    
    return StreamingResponse(
        event_generator(),
        media_type=\"text/event-stream\",
        headers={
            \"Cache-Control\": \"no-cache\",
            \"Connection\": \"keep-alive\",
            \"X-Accel-Buffering\": \"no\"
        }
    )


@orchestration_router.get(\"/consensus/recent\", response_model=StandardResponse)
async def get_recent_consensus_rounds(
    symbol: Optional[str] = None,
    limit: int = 50
):
    \"\"\"
    Get recent consensus rounds - Phase 4
    
    Args:
        symbol: Filter by symbol (optional)
        limit: Maximum number of results (default: 50)
    \"\"\"
    try:
        from .events import get_recent_consensus_rounds as get_rounds
        
        rounds = get_rounds(symbol=symbol, limit=limit)
        
        return StandardResponse(
            ok=True,
            data={\"rounds\": rounds, \"count\": len(rounds)},
            error=None
        )
    except Exception as e:
        logger.error(f\"Error getting recent consensus rounds: {e}\")
        return StandardResponse(ok=False, data=None, error=str(e))


@orchestration_router.get(\"/dialogs\", response_model=StandardResponse)
async def get_consensus_dialogs(consensus_id: Optional[str] = None):
    \"\"\"
    Get dialog messages for a consensus round - Phase 4
    
    Args:
        consensus_id: Consensus round ID (required)
    \"\"\"
    try:
        if not consensus_id:
            raise HTTPException(status_code=400, detail=\"consensus_id is required\")
        
        from .events import get_dialogs_by_consensus
        
        dialogs = get_dialogs_by_consensus(consensus_id)
        
        return StandardResponse(
            ok=True,
            data={
                \"consensus_id\": consensus_id,
                \"dialogs\": dialogs,
                \"count\": len(dialogs)
            },
            error=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f\"Error getting dialogs: {e}\")
        return StandardResponse(ok=False, data=None, error=str(e))


def apply_consensus_action(consensus_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply consensus action by opening a paper trade - Phase 3
    
    Args:
        consensus_result: Consensus result from run_consensus_round
    
    Returns:
        Paper trade result
    """
    from core.slots.manager import slot_manager
    from .metrics import increment_paper_trade_opened, update_paper_pnl_unrealized
    
    try:
        consensus_id = consensus_result['consensus_id']
        symbol = consensus_result['symbol']
        action = consensus_result['action']
        agent_ids = consensus_result.get('participating_agents', 
                                         [p['agent_id'] for p in consensus_result.get('proposals', [])])
        
        # Simplified entry price (would come from market data in production)
        entry_price = 50000.0 if 'BTC' in symbol else 3000.0
        
        # Open paper trade
        success, message = slot_manager.open_paper_trade(
            consensus_id=consensus_id,
            agent_ids=agent_ids,
            action=action,
            symbol=symbol,
            notional_usdt=300.0,
            tp_pct=0.7,
            sl_pct=0.4,
            entry_price=entry_price
        )
        
        if success:
            # Update metrics
            increment_paper_trade_opened(symbol, action)
            update_paper_pnl_unrealized(symbol, 0)  # Initial PnL is 0
            
            logger.info(f"Paper trade opened from consensus {consensus_id}: {action} {symbol}")
        
        return {
            "success": success,
            "message": message,
            "consensus_id": consensus_id,
            "symbol": symbol,
            "action": action
        }
        
    except Exception as e:
        logger.error(f"Error applying consensus action: {e}")
        return {
            "success": False,
            "message": str(e)
        }
