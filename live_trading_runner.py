#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Trading Runner - Inicia o bot em modo LIVE
Executa trades reais nas exchanges configuradas
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional

# Adiciona path para imports
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class LiveTradingRunner:
    """
    Runner para trading ao vivo
    Integra TradingEngine com o sistema de consenso
    """
    
    def __init__(self):
        """Inicializa o runner de trading ao vivo"""
        self.running = False
        self.trading_engine = None
        self.exchange_manager = None
        self.position_manager = None
        
        logger.info("🚀 Live Trading Runner initialized")
    
    def initialize_components(self):
        """Inicializa componentes necessários para trading ao vivo"""
        try:
            logger.info("📊 Initializing live trading components...")
            
            # 1. Initialize Exchange Manager
            logger.info("  • Exchange Manager: Initializing...")
            from core.exchanges.exchange_manager import ExchangeManager
            
            exchange_config = {
                'primary': os.getenv('EXCHANGE', 'binance'),
                'testnet': os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
            }
            
            self.exchange_manager = ExchangeManager(exchange_config)
            
            # Test connection
            test_result = self.exchange_manager.test_connection()
            if not test_result.get('success'):
                logger.error(f"  ❌ Exchange connection failed: {test_result.get('error')}")
                return False
            
            logger.info(f"  ✅ Exchange Manager: Connected to {self.exchange_manager.get_exchange_name()}")
            
            # 2. Create Trading Engine
            logger.info("  • Trading Engine: Creating...")
            from core.engine.trading_engine import create_trading_engine
            
            # Get trading configuration
            config = {
                'pairs': self._get_trading_pairs(),
                'timeframe': os.getenv('TIMEFRAME', '5m'),
                'loop_interval': int(os.getenv('SCAN_INTERVAL_SEC', '60')),
                'max_open_positions': int(os.getenv('MAX_CONCURRENT_POSITIONS', '3')),
                'position_size_usdt': float(os.getenv('BASE_AMOUNT', '300')),
                'take_profit_pct': float(os.getenv('TAKE_PROFIT', '2.0')) * 100,
                'stop_loss_pct': float(os.getenv('STOP_LOSS', '1.0')) * 100
            }
            
            # Select strategy
            strategy_name = os.getenv('STRATEGY_NAME', 'example')
            
            self.trading_engine = create_trading_engine(
                exchange_manager=self.exchange_manager,
                strategy_name=strategy_name,
                config=config
            )
            
            if not self.trading_engine:
                logger.error("  ❌ Failed to create Trading Engine")
                return False
            
            logger.info(f"  ✅ Trading Engine: Created with {strategy_name} strategy")
            logger.info(f"     • Pairs: {', '.join(config['pairs'])}")
            logger.info(f"     • Timeframe: {config['timeframe']}")
            logger.info(f"     • Max positions: {config['max_open_positions']}")
            
            # 3. Get Position Manager reference
            if hasattr(self.trading_engine, 'position_manager'):
                self.position_manager = self.trading_engine.position_manager
                logger.info("  ✅ Position Manager: Ready")
            
            logger.info("✅ All live trading components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing components: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_trading_pairs(self):
        """Obtém pares de trading da configuração"""
        # Tenta obter de SYMBOL (compatibilidade)
        symbol = os.getenv('SYMBOL')
        if symbol:
            return [symbol]
        
        # Ou lista de pares configurados
        pairs_str = os.getenv('TRADING_PAIRS', 'BTC/USDT,ETH/USDT')
        return [p.strip() for p in pairs_str.split(',') if p.strip()]
    
    def start_live_trading(self):
        """Inicia trading ao vivo"""
        logger.info("\n" + "="*80)
        logger.info("🤖 STARTING LIVE TRADING MODE")
        logger.info("="*80)
        logger.info("")
        logger.info("⚠️  WARNING: This will execute REAL trades on the exchange!")
        logger.info("⚠️  Make sure you understand the risks involved.")
        logger.info("")
        
        # Confirmar início
        confirm = os.getenv('LIVE_TRADING_CONFIRMED', 'false').lower()
        if confirm != 'true':
            logger.error("❌ Live trading not confirmed!")
            logger.error("   Set LIVE_TRADING_CONFIRMED=true in .env to enable live trading")
            return False
        
        # Inicializar componentes
        if not self.initialize_components():
            logger.error("❌ Failed to initialize components, aborting")
            return False
        
        # Iniciar Trading Engine
        logger.info("\n🚀 Starting Trading Engine...")
        self.trading_engine.start()
        self.running = True
        
        logger.info("✅ Live trading started successfully")
        logger.info("")
        logger.info("📊 Trading Status:")
        self._show_status()
        
        # Loop principal de monitoramento
        self._monitoring_loop()
        
        return True
    
    def _monitoring_loop(self):
        """Loop de monitoramento do trading ao vivo"""
        logger.info("\n📈 Monitoring live trading... (Press Ctrl+C to stop)")
        logger.info("-" * 80)
        
        try:
            cycle_count = 0
            
            while self.running:
                cycle_count += 1
                
                # A cada 60 segundos, mostra status
                if cycle_count % 12 == 0:  # 12 * 5s = 60s
                    self._show_status()
                
                # Sleep por 5 segundos
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️  Live trading interrupted by user")
            self.stop()
        except Exception as e:
            logger.error(f"\n❌ Error in monitoring loop: {e}")
            self.stop()
    
    def _show_status(self):
        """Mostra status atual do trading"""
        try:
            if not self.trading_engine:
                return
            
            status = self.trading_engine.get_status()
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("📊 LIVE TRADING STATUS")
            logger.info("=" * 80)
            logger.info(f"Engine Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
            logger.info(f"Strategy: {status['strategy']}")
            logger.info(f"Pairs: {', '.join(status['pairs'])}")
            logger.info(f"Timeframe: {status['timeframe']}")
            logger.info(f"Max Open Positions: {status['max_open_positions']}")
            
            # Estatísticas
            stats = status.get('statistics', {})
            if stats:
                logger.info("")
                logger.info("📈 STATISTICS:")
                logger.info(f"  • Total Trades: {stats.get('total_trades', 0)}")
                logger.info(f"  • Open Trades: {stats.get('open_trades', 0)}")
                logger.info(f"  • Closed Trades: {stats.get('closed_trades', 0)}")
                logger.info(f"  • Total PnL: ${stats.get('total_realized_pnl', 0):.2f}")
                logger.info(f"  • Total Fees: ${stats.get('total_fees_paid', 0):.2f}")
                logger.info(f"  • Net PnL: ${stats.get('net_pnl', 0):.2f}")
            
            # Posições abertas
            if self.position_manager:
                open_trades = self.position_manager.get_open_trades()
                if open_trades:
                    logger.info("")
                    logger.info("💼 OPEN POSITIONS:")
                    for trade in open_trades:
                        logger.info(
                            f"  • {trade['symbol']}: {trade['action']} | "
                            f"Entry: ${trade['entry_price']:.2f} | "
                            f"Current: ${trade['current_price']:.2f} | "
                            f"PnL: ${trade['unrealized_pnl']:.2f}"
                        )
                else:
                    logger.info("")
                    logger.info("💼 No open positions")
            
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Error showing status: {e}")
    
    def stop(self):
        """Para o trading ao vivo"""
        logger.info("\n🛑 Stopping live trading...")
        self.running = False
        
        if self.trading_engine:
            self.trading_engine.stop()
            logger.info("  • Trading Engine stopped")
        
        logger.info("✅ Live trading stopped successfully")
    
    def emergency_stop(self):
        """Para tudo e fecha todas as posições"""
        logger.warning("\n🚨 EMERGENCY STOP ACTIVATED")
        logger.warning("🚨 Closing all positions...")
        
        if self.trading_engine:
            self.trading_engine.force_close_all_positions(reason="emergency_stop")
            logger.info("  • All positions closed")
            
            self.trading_engine.stop()
            logger.info("  • Trading Engine stopped")
        
        self.running = False
        logger.info("✅ Emergency stop completed")


def main():
    """Função principal"""
    try:
        # Criar instância do runner
        runner = LiveTradingRunner()
        
        # Verificar argumentos
        if len(sys.argv) > 1:
            if sys.argv[1] == '--status':
                logger.info("Checking live trading status...")
                if runner.initialize_components():
                    runner._show_status()
                return
            
            elif sys.argv[1] == '--emergency-stop':
                logger.warning("Emergency stop requested!")
                if runner.initialize_components():
                    runner.emergency_stop()
                return
        
        # Iniciar trading ao vivo
        runner.start_live_trading()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Live trading interrupted by user")
    except Exception as e:
        logger.error(f"❌ Critical error in live trading runner: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
