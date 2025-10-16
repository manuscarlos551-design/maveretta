#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Autonomous Trading Bot - Sistema de Trading Autônomo
Executa trading real com agentes IA
"""

import os
import sys
import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
import signal

# Adiciona path
sys.path.insert(0, '/app/maveretta')

from core.execution.real_exchange_executor import real_exchange_executor, Exchange, OrderSide
from core.exchanges.fee_manager import fee_manager
from core.notifications.telegram_notifier import telegram_notifier

logger = logging.getLogger(__name__)


class AutonomousTradingBot:
    """
    Bot de Trading Autônomo
    Executa trades reais baseado em sinais de IA
    """
    
    def __init__(self):
        self.running = False
        self.initial_capital_per_exchange = float(os.getenv('INITIAL_CAPITAL_USD', '18.0'))
        self.max_risk_per_trade = float(os.getenv('MAX_RISK_PER_TRADE_PCT', '2.0')) / 100
        self.scan_interval = int(os.getenv('SCAN_INTERVAL_SEC', '30'))
        
        # Pares de trading
        self.trading_pairs = [
            'BTC/USDT',
            'ETH/USDT',
            'BNB/USDT',
            'SOL/USDT',
            'XRP/USDT'
        ]
        
        # Capital tracking por exchange
        self.capital_per_exchange = {}
        
        # Estatísticas
        self.stats = {
            'trades_today': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit_usd': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'start_time': None
        }
        
        logger.info("✅ Autonomous Trading Bot inicializado")
    
    def _setup_signal_handlers(self):
        """Configura handlers para shutdown gracioso"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de interrupção"""
        logger.info("⚠️ Sinal de interrupção recebido, parando bot...")
        self.running = False
    
    async def initialize(self):
        """Inicializa o bot"""
        logger.info("\n" + "="*70)
        logger.info("🤖 MAVERETTA AUTONOMOUS TRADING BOT")
        logger.info("="*70)
        
        # Inicializa capital tracking
        for exchange in real_exchange_executor.exchanges.keys():
            self.capital_per_exchange[exchange.value] = self.initial_capital_per_exchange
            logger.info(
                f"  💰 {exchange.value.upper()}: "
                f"${self.initial_capital_per_exchange:.2f} inicial"
            )
        
        # Envia notificação de início
        await telegram_notifier.notify_system_status(
            'started',
            f"🚀 <b>Bot iniciado!</b>\n\n"
            f"💰 Capital inicial: ${self.initial_capital_per_exchange:.2f} por exchange\n"
            f"🏛️ Exchanges: {len(self.capital_per_exchange)}\n"
            f"📊 Pares: {len(self.trading_pairs)}\n"
            f"⏱️ Intervalo: {self.scan_interval}s"
        )
        
        self.stats['start_time'] = datetime.utcnow()
        logger.info("✅ Bot inicializado com sucesso\n")
    
    async def analyze_market_simple(self, exchange: Exchange, symbol: str) -> Dict[str, Any]:
        """
        Análise simples de mercado (placeholder para integração futura com IA)
        
        Retorna:
            - signal: 'buy', 'sell', 'hold'
            - confidence: 0.0 a 1.0
            - reason: motivo do sinal
        """
        try:
            # Obtém preço atual
            ticker = await real_exchange_executor.get_ticker(exchange, symbol)
            if 'error' in ticker:
                return {'signal': 'hold', 'confidence': 0.0, 'reason': 'ticker_error'}
            
            # TODO: Integrar com sistema de agentes IA
            # Por enquanto, usa lógica simples de placeholder
            
            # Simulação: analisa variação do preço
            # Em produção, isso seria substituído por análise real dos agentes
            
            return {
                'signal': 'hold',  # Começa conservador
                'confidence': 0.65,
                'reason': 'placeholder_analysis',
                'current_price': ticker.get('last', 0)
            }
        
        except Exception as e:
            logger.error(f"❌ Erro na análise: {e}")
            return {'signal': 'hold', 'confidence': 0.0, 'reason': 'analysis_error'}
    
    async def execute_trade_if_signal(self, exchange: Exchange, symbol: str):
        """
        Executa trade se houver sinal válido
        """
        try:
            # Verifica se há capital disponível
            available_capital = self.capital_per_exchange.get(exchange.value, 0)
            
            if available_capital < 1.0:  # Mínimo $1
                logger.debug(f"Capital insuficiente em {exchange.value}: ${available_capital:.2f}")
                return
            
            # Verifica posições abertas
            active_positions = real_exchange_executor.get_active_positions()
            active_on_exchange = [p for p in active_positions if p['exchange'] == exchange.value]
            
            max_positions = int(os.getenv('MAX_CONCURRENT_POSITIONS', '3'))
            if len(active_on_exchange) >= max_positions:
                logger.debug(f"Máximo de posições atingido em {exchange.value}: {len(active_on_exchange)}")
                return
            
            # Analisa mercado
            analysis = await self.analyze_market_simple(exchange, symbol)
            
            signal = analysis.get('signal')
            confidence = analysis.get('confidence', 0.0)
            min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.70'))
            
            # Verifica se deve tradear
            if signal == 'hold' or confidence < min_confidence:
                return
            
            # Calcula tamanho da posição
            position_size = available_capital * self.max_risk_per_trade
            position_size = min(position_size, available_capital * 0.5)  # Máx 50% do capital
            
            if position_size < 1.0:
                logger.debug(f"Posição muito pequena: ${position_size:.2f}")
                return
            
            # Determina lado
            side = OrderSide.BUY if signal == 'buy' else OrderSide.SELL
            
            logger.info(
                f"\n🚨 SINAL DETECTADO: {signal.upper()} {symbol} em {exchange.value.upper()} | "
                f"Confidence: {confidence:.1%} | Size: ${position_size:.2f}"
            )
            
            # Executa ordem com SL/TP automático
            result = await real_exchange_executor.create_limit_order_with_sltp(
                exchange=exchange,
                symbol=symbol,
                side=side,
                amount_usd=position_size
            )
            
            if result['success']:
                # Atualiza capital disponível
                self.capital_per_exchange[exchange.value] -= position_size
                
                # Atualiza estatísticas
                self.stats['trades_today'] += 1
                
                # Notifica
                await telegram_notifier.notify_trade_opened(result['position'])
                
                logger.info(
                    f"✅ Trade executado com sucesso! "
                    f"Position ID: {result['position_id']}"
                )
            else:
                logger.error(f"❌ Erro ao executar trade: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"❌ Erro ao executar trade: {e}", exc_info=True)
    
    async def check_positions(self):
        """Verifica e gerencia posições abertas"""
        try:
            # Verifica SL/TP
            await real_exchange_executor.check_and_close_positions()
            
            # Processa posições recém fechadas
            closed_positions = real_exchange_executor.get_closed_positions(limit=10)
            
            for position in closed_positions:
                # Verifica se já foi processada
                if position.get('_processed'):
                    continue
                
                # Marca como processada
                position['_processed'] = True
                
                # Atualiza capital
                exchange_name = position['exchange']
                profit = position.get('profit', {})
                net_profit = profit.get('net_profit_usd', 0)
                
                # Devolve capital + profit
                self.capital_per_exchange[exchange_name] += position['amount_usd'] + net_profit
                
                # Atualiza estatísticas
                if profit.get('is_profitable', False):
                    self.stats['winning_trades'] += 1
                else:
                    self.stats['losing_trades'] += 1
                
                self.stats['total_profit_usd'] += net_profit
                self.stats['best_trade'] = max(self.stats['best_trade'], net_profit)
                self.stats['worst_trade'] = min(self.stats['worst_trade'], net_profit)
                
                # Notifica
                await telegram_notifier.notify_trade_closed(position)
                
                logger.info(
                    f"📊 Posição processada: {position['symbol']} | "
                    f"P/L: ${net_profit:.2f} | "
                    f"Capital em {exchange_name}: ${self.capital_per_exchange[exchange_name]:.2f}"
                )
        
        except Exception as e:
            logger.error(f"❌ Erro ao verificar posições: {e}", exc_info=True)
    
    async def trading_loop(self):
        """Loop principal de trading"""
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                logger.info(f"\n{'='*70}")
                logger.info(f"🔄 Ciclo #{cycle} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                logger.info(f"{'='*70}")
                
                # 1. Verifica posições abertas
                await self.check_positions()
                
                # 2. Busca novas oportunidades
                for exchange in real_exchange_executor.exchanges.keys():
                    for symbol in self.trading_pairs:
                        await self.execute_trade_if_signal(exchange, symbol)
                        await asyncio.sleep(1)  # Rate limiting
                
                # 3. Log de status
                active_positions = real_exchange_executor.get_active_positions()
                logger.info(f"\n📊 Status:")
                logger.info(f"  Posições abertas: {len(active_positions)}")
                logger.info(f"  Trades hoje: {self.stats['trades_today']}")
                logger.info(f"  Win rate: {self._calculate_win_rate():.1%}")
                logger.info(f"  Profit total: ${self.stats['total_profit_usd']:.2f}")
                
                # 4. Aguarda próximo ciclo
                logger.info(f"\n⏳ Aguardando {self.scan_interval}s até próximo ciclo...")
                await asyncio.sleep(self.scan_interval)
            
            except Exception as e:
                logger.error(f"❌ Erro no ciclo de trading: {e}", exc_info=True)
                await asyncio.sleep(10)
        
        logger.info("⚠️ Trading loop finalizado")
    
    def _calculate_win_rate(self) -> float:
        """Calcula win rate"""
        total = self.stats['winning_trades'] + self.stats['losing_trades']
        if total == 0:
            return 0.0
        return self.stats['winning_trades'] / total
    
    async def send_daily_summary(self):
        """Envia resumo diário"""
        await telegram_notifier.notify_daily_summary({
            'total_trades': self.stats['trades_today'],
            'winning_trades': self.stats['winning_trades'],
            'losing_trades': self.stats['losing_trades'],
            'win_rate': self._calculate_win_rate(),
            'total_profit': self.stats['total_profit_usd'],
            'best_trade': self.stats['best_trade'],
            'worst_trade': self.stats['worst_trade']
        })
    
    async def start(self):
        """Inicia o bot"""
        self._setup_signal_handlers()
        
        await self.initialize()
        
        self.running = True
        
        try:
            await self.trading_loop()
        except KeyboardInterrupt:
            logger.info("\n⚠️ Interrupção pelo usuário")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown gracioso"""
        logger.info("\n" + "="*70)
        logger.info("🛑 ENCERRANDO BOT")
        logger.info("="*70)
        
        self.running = False
        
        # Fecha todas as posições abertas
        active_positions = real_exchange_executor.get_active_positions()
        if active_positions:
            logger.info(f"\n⚠️ Fechando {len(active_positions)} posições abertas...")
            
            for position in active_positions:
                position_id = f"{position['exchange']}_{position['symbol']}_{position.get('opened_at', '')}"
                await real_exchange_executor.close_position(position_id, 'manual_shutdown')
        
        # Envia resumo final
        await self.send_daily_summary()
        
        # Notifica shutdown
        await telegram_notifier.notify_system_status(
            'stopped',
            f"🛑 <b>Bot encerrado</b>\n\n"
            f"📊 Estatísticas finais:\n"
            f"Trades: {self.stats['trades_today']}\n"
            f"Win Rate: {self._calculate_win_rate():.1%}\n"
            f"Profit Total: ${self.stats['total_profit_usd']:.2f}"
        )
        
        logger.info("✅ Shutdown completo\n")


async def main():
    """Função principal"""
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/app/maveretta/logs/trading_bot.log'),
            logging.StreamHandler()
        ]
    )
    
    # Cria e inicia bot
    bot = AutonomousTradingBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
