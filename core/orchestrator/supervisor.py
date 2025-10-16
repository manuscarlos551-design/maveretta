# core/orchestrator/supervisor.py
"""Agent Supervisor - Watchdog for agent health monitoring

Monitors agent heartbeats and restarts failed agents with exponential backoff.
"""

import asyncio
import logging
import time
import os
from typing import Dict, Optional
from datetime import datetime, timezone

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# Metrics
agent_supervisor_restarts_total = Counter(
    'agent_supervisor_restarts_total',
    'Total agent restarts by supervisor',
    ['agent', 'reason']
)

agent_supervisor_last_check_ts = Gauge(
    'agent_supervisor_last_check_ts',
    'Timestamp of last supervisor check'
)


class AgentSupervisor:
    """Monitors agent heartbeats and restarts failed agents"""
    
    def __init__(self):
        self.heartbeat_timeout = int(os.getenv('SUPERVISOR_HEARTBEAT_TIMEOUT_SEC', '120'))
        self.backoff_base = int(os.getenv('SUPERVISOR_RESTART_BACKOFF_SEC', '5'))
        self.backoff_cap = 30  # Max 30s backoff
        
        self.last_heartbeats: Dict[str, float] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_restart: Dict[str, float] = {}
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info(
            f"Supervisor initialized: timeout={self.heartbeat_timeout}s, "
            f"backoff={self.backoff_base}s (cap {self.backoff_cap}s)"
        )
    
    def start(self):
        """Start supervisor loop"""
        if self._running:
            logger.warning("Supervisor already running")
            return
        
        self._running = True
        
        # Start in thread (for sync compatibility)
        import threading
        thread = threading.Thread(target=self._run_sync_loop, daemon=True)
        thread.start()
        
        logger.info("🔍 Supervisor started")
    
    def _run_sync_loop(self):
        """Synchronous wrapper for async loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._run_async_loop())
        finally:
            loop.close()
    
    async def _run_async_loop(self):
        """Main async supervisor loop"""
        logger.info("Supervisor async loop started")
        
        try:
            while self._running:
                # Check kill switch
                if os.getenv('KILL_SWITCH', 'false').lower() == 'true':
                    logger.warning("Kill switch detected, stopping supervisor")
                    break
                
                # Check heartbeats
                await self._check_heartbeats()
                
                # Update metrics
                agent_supervisor_last_check_ts.set(time.time())
                
                # Sleep for check interval
                await asyncio.sleep(30)  # Check every 30s
        
        except asyncio.CancelledError:
            logger.info("Supervisor loop cancelled")
        except Exception as e:
            logger.error(f"Error in supervisor loop: {e}")
            import traceback
            traceback.print_exc()
    
    def update_heartbeat(self, agent_id: str, timestamp: float):
        """Update agent heartbeat timestamp"""
        self.last_heartbeats[agent_id] = timestamp
    
    async def _check_heartbeats(self):
        """Check all agent heartbeats and restart if needed"""
        from .engine import agent_engine
        
        current_time = time.time()
        agents = agent_engine.list_agents()
        
        for agent_id, state in agents.items():
            if state['status'] != 'running':
                continue
            
            last_hb = self.last_heartbeats.get(agent_id, 0)
            time_since_hb = current_time - last_hb
            
            # Check if agent is stuck
            if last_hb > 0 and time_since_hb > self.heartbeat_timeout:
                logger.warning(
                    f"⚠️ Agent {agent_id} heartbeat timeout: "
                    f"{time_since_hb:.0f}s since last heartbeat"
                )
                
                # Calculate backoff
                restart_count = self.restart_counts.get(agent_id, 0)
                backoff = min(
                    self.backoff_base * (2 ** restart_count),
                    self.backoff_cap
                )
                
                # Check if we should wait before restart
                last_restart_time = self.last_restart.get(agent_id, 0)
                time_since_restart = current_time - last_restart_time
                
                if time_since_restart < backoff:
                    logger.debug(
                        f"Waiting {backoff - time_since_restart:.1f}s before restarting {agent_id}"
                    )
                    continue
                
                # Restart agent
                await self._restart_agent(agent_id)
    
    async def _restart_agent(self, agent_id: str):
        """Restart a failed agent - FIX P0: Recriar asyncio.Task"""
        from .engine import agent_engine
        from .runner import _tasks, orchestrator
        
        logger.info(f"🔄 Restarting agent: {agent_id}")
        
        try:
            # Stop agent
            agent_engine.stop_agent(agent_id)
            
            # Wait a bit
            await asyncio.sleep(2)
            
            # Start agent
            success, msg = agent_engine.start_agent(agent_id)
            
            if success:
                # FIX P0: CRITICAL - Recreate asyncio.Task
                # Cancel old task if exists
                if agent_id in _tasks:
                    old_task = _tasks[agent_id]
                    if not old_task.done():
                        old_task.cancel()
                        try:
                            await old_task
                        except asyncio.CancelledError:
                            pass
                
                # Create new task
                task = asyncio.create_task(
                    orchestrator._agent_loop(agent_id),
                    name=f"agent-{agent_id}"
                )
                _tasks[agent_id] = task
                
                logger.info(f"✅ Agent {agent_id} restarted successfully (task recreated)")
                
                # Update tracking
                self.restart_counts[agent_id] = self.restart_counts.get(agent_id, 0) + 1
                self.last_restart[agent_id] = time.time()
                self.last_heartbeats[agent_id] = time.time()  # Reset heartbeat
                
                # Metrics
                agent_supervisor_restarts_total.labels(
                    agent=agent_id,
                    reason='heartbeat_timeout'
                ).inc()
            else:
                logger.error(f"❌ Failed to restart agent {agent_id}: {msg}")
        
        except Exception as e:
            logger.error(f"Error restarting agent {agent_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def stop(self):
        """Stop supervisor"""
        self._running = False
        logger.info("🛑 Supervisor stopped")


# Global supervisor instance
supervisor = AgentSupervisor()
