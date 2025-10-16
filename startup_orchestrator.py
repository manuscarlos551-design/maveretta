#!/usr/bin/env python3
"""Startup script for continuous orchestration

Automatically starts orchestrator on container boot.
"""

import asyncio
import logging
import signal
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Graceful shutdown
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main entry point"""
    try:
        from core.orchestrator.runner import orchestrator
        
        logger.info("🚀 Starting Maveretta Orchestrator...")
        logger.info(f"📊 Agent tick interval: {orchestrator.tick_interval}s")
        logger.info(f"🔒 Kill switch: {os.getenv('KILL_SWITCH', 'false')}")
        
        # Start orchestrator
        orchestrator_task = asyncio.create_task(orchestrator.run_forever())
        
        # Wait for shutdown signal or orchestrator completion
        done, pending = await asyncio.wait(
            [orchestrator_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel orchestrator if still running
        if orchestrator_task in pending:
            logger.info("Cancelling orchestrator...")
            orchestrator_task.cancel()
            try:
                await orchestrator_task
            except asyncio.CancelledError:
                logger.info("Orchestrator cancelled")
        
        # Cancel shutdown waiter if needed
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ Orchestrator shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in orchestrator startup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
