# core/orchestrator/runner.py
"""Continuous Multi-Agent Orchestration Runner

Asynchronous event loop that keeps agents always active.
Tick-based + event-driven architecture.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# P1: Try to use uvloop for better async performance
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    logger = logging.getLogger(__name__)
    logger.info("✅ uvloop enabled for better async performance")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.info("⚠️ uvloop not available, using default asyncio")

from .engine import agent_engine
from .metrics import (
    agent_ticks_total, agent_decisions_total, agent_errors_total,
    consensus_rounds_total, update_agent_heartbeat
)
from .supervisor import supervisor

logger = logging.getLogger(__name__)

# Global state
_running = False
_tasks: Dict[str, asyncio.Task] = {}


class ContinuousOrchestrator:
    """Manages continuous multi-agent orchestration loop"""
    
    def __init__(self):
        self.tick_interval = int(os.getenv('AGENT_TICK_SECONDS', '3'))
        self.kill_switch = False
        self.event_queue = asyncio.Queue()
        
        logger.info(f"ContinuousOrchestrator initialized (tick={self.tick_interval}s)")
    
    async def run_forever(self):
        """Main orchestration loop - runs continuously"""
        global _running
        
        logger.info("🚀 Starting continuous orchestration...")
        
        # Initialize agent engine
        success, msg = agent_engine.initialize()
        if not success:
            logger.error(f"❌ Failed to initialize agent engine: {msg}")
            return
        
        logger.info(f"✅ Agent engine initialized: {msg}")
        
        # Start all agents
        agents = agent_engine.list_agents()
        for agent_id in agents.keys():
            success, msg = agent_engine.start_agent(agent_id)
            if success:
                logger.info(f"▶️ Started agent: {agent_id}")
            else:
                logger.warning(f"⚠️ Failed to start agent {agent_id}: {msg}")
        
        # Start supervisor
        supervisor.start()
        
        _running = True
        
        # Spawn agent tasks
        for agent_id in agents.keys():
            task = asyncio.create_task(
                self._agent_loop(agent_id),
                name=f"agent-{agent_id}"
            )
            _tasks[agent_id] = task
        
        # Spawn event consumer
        event_task = asyncio.create_task(
            self._event_consumer(),
            name="event-consumer"
        )
        _tasks['event_consumer'] = event_task
        
        logger.info(f"🔄 {len(_tasks)} tasks spawned")
        
        try:
            # Keep running until kill switch
            while _running and not self.kill_switch:
                # Check kill switch from environment
                self.kill_switch = os.getenv('KILL_SWITCH', 'false').lower() == 'true'
                
                if self.kill_switch:
                    logger.warning("🛑 Kill switch activated!")
                    break
                
                await asyncio.sleep(10)  # Check every 10s
            
            logger.info("🛑 Stopping continuous orchestration...")
            
        except asyncio.CancelledError:
            logger.info("🛑 Orchestration cancelled")
        except Exception as e:
            logger.error(f"❌ Error in orchestration loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()
    
    async def _agent_loop(self, agent_id: str):
        """Continuous loop for a single agent"""
        logger.info(f"Agent loop started: {agent_id}")
        
        tick_count = 0
        
        try:
            while _running and not self.kill_switch:
                tick_count += 1
                current_time = time.time()
                
                # Heartbeat
                update_agent_heartbeat(agent_id, current_time)
                agent_ticks_total.labels(agent=agent_id).inc()
                
                # Get agent state
                agent_state = agent_engine.get_agent(agent_id)
                if not agent_state or agent_state['status'] != 'running':
                    logger.debug(f"Agent {agent_id} not running, skipping tick")
                    await asyncio.sleep(self.tick_interval)
                    continue
                
                try:
                    # Process agent tick (decision making)
                    await self._process_agent_tick(agent_id, agent_state)
                    
                except Exception as e:
                    logger.error(f"Error in agent {agent_id} tick: {e}")
                    agent_errors_total.labels(agent=agent_id, error_type='tick_error').inc()
                
                # Log heartbeat every 10 ticks
                if tick_count % 10 == 0:
                    logger.debug(f"Agent {agent_id} heartbeat: tick #{tick_count}")
                
                # Sleep until next tick
                await asyncio.sleep(self.tick_interval)
        
        except asyncio.CancelledError:
            logger.info(f"Agent loop cancelled: {agent_id}")
        except Exception as e:
            logger.error(f"Fatal error in agent loop {agent_id}: {e}")
            agent_errors_total.labels(agent=agent_id, error_type='fatal').inc()
    
    async def _process_agent_tick(self, agent_id: str, agent_state: Dict[str, Any]):
        """Process a single agent tick (decision + consensus)"""
        from core.slots.manager import slot_manager
        import random
        
        # Get active slots
        active_slots = slot_manager.get_active_slots() if slot_manager else []
        
        if not active_slots:
            # No slots available, skip
            return
        
        # Select symbol (simplified - can be extended)
        symbols = agent_state.get('symbols', ['BTCUSDT'])
        symbol = random.choice(symbols)
        
        # Check if should trigger consensus
        # For now, trigger consensus probabilistically (10% chance per tick)
        # In production, this would be based on market signals
        should_consensus = random.random() < 0.1
        
        if should_consensus:
            # Get other active agents for consensus
            all_agents = agent_engine.list_agents()
            active_agents = [
                aid for aid, state in all_agents.items()
                if state['status'] == 'running' and aid != agent_id
            ]
            
            if len(active_agents) >= 1:
                participating = [agent_id] + active_agents[:2]  # Max 3 agents
                
                logger.info(f"🎯 Triggering consensus for {symbol} with {participating}")
                
                # Run consensus round (synchronous call, but quick)
                result = agent_engine.run_consensus_round(
                    symbol=symbol,
                    participating_agents=participating,
                    timeframe='5m'
                )
                
                if result.get('approved'):
                    agent_decisions_total.labels(agent=agent_id, action='consensus_approved').inc()
                else:
                    agent_decisions_total.labels(agent=agent_id, action='consensus_rejected').inc()
    
    async def _event_consumer(self):
        """Consume events from queue and trigger actions"""
        logger.info("Event consumer started")
        
        try:
            while _running and not self.kill_switch:
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=5.0
                    )
                    
                    # Process event
                    await self._handle_event(event)
                    
                except asyncio.TimeoutError:
                    # No event, continue
                    continue
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
        
        except asyncio.CancelledError:
            logger.info("Event consumer cancelled")
    
    async def _handle_event(self, event: Dict[str, Any]):
        """Handle market/system events"""
        event_type = event.get('type')
        
        if event_type == 'market_significant_move':
            # Trigger immediate analysis for all agents
            logger.info(f"📊 Market move detected: {event.get('symbol')}")
            # Trigger consensus for affected symbol
            # (Implementation would go here)
        
        elif event_type == 'risk_alert':
            # Handle risk alert
            logger.warning(f"⚠️ Risk alert: {event.get('reason')}")
            # (Implementation would go here)
    
    async def _cleanup(self):
        """Cleanup tasks on shutdown"""
        global _running
        _running = False
        
        logger.info("🧹 Cleaning up tasks...")
        
        # Cancel all tasks
        for task_name, task in _tasks.items():
            if not task.done():
                logger.info(f"Cancelling task: {task_name}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        _tasks.clear()
        
        # Stop supervisor
        supervisor.stop()
        
        logger.info("✅ Cleanup complete")


# Global orchestrator instance
orchestrator = ContinuousOrchestrator()


async def run_forever():
    """Entry point for continuous orchestration"""
    await orchestrator.run_forever()
