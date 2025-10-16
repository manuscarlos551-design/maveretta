#!/usr/bin/env python3
# core/cli.py
"""CLI for Maveretta Bot core services

Provides commands for starting the continuous orchestration daemon.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def autostart():
    """Start continuous orchestration daemon"""
    logger.info("="*80)
    logger.info("🚀 MAVERETTA BOT - CONTINUOUS ORCHESTRATION DAEMON")
    logger.info("="*80)
    logger.info(f"Tick interval: {os.getenv('AGENT_TICK_SECONDS', '60')}s")
    logger.info(f"Kill switch: {os.getenv('KILL_SWITCH', 'false')}")
    logger.info(f"Learning enabled: {os.getenv('LEARNING_ENABLED', 'false')}")
    logger.info("="*80)
    
    try:
        # Import and run orchestrator
        from core.orchestrator.runner import run_forever
        
        logger.info("Starting orchestration loop...")
        asyncio.run(run_forever())
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Daemon stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m core.cli <command>")
        print("")
        print("Commands:")
        print("  autostart    Start continuous orchestration daemon")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'autostart':
        autostart()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
