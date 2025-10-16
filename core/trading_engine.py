# core/trading_engine.py
"""
Motor de Trading Principal
Integra agentes IA, slots em cascata e execução de trades
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

# Imports do sistema
from ai.agents.multi_agent_system import multi_agent_system, VoteResult
from core.slots.cascade_manager import cascade_manager, CascadeStage
from core.slots.manager import slot_manager

logger = logging.getLogger(__name__)


class TradingMode(str, Enum):
    """Modos de operação do trading"""
    PAPER = "paper"       # Simulação completa
    LIVE = "live"         # Trading real
    HYBRID = "hybrid"     # Parte paper, parte live


class TradingEngine:
    """
    Motor principal de trading
    Coordena todo o fluxo: análise → decisão → execução
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Modo de operação
        self.mode = TradingMode(os.getenv('TRADING_MODE', 'paper'))
        
        # Configurações de trading
        self.min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.70'))  # 70%
        self.max_exposure_pct = float(os.getenv('MAX_EXPOSURE_PCT', '50.0'))  # 50%
        self.risk_per_trade_pct = float(os.getenv('RISK_PER_TRADE_PCT', '2.0'))  # 2%
        
        # Estado
        self.is_running = False
        self.total_trades = 0
        self.successful_trades = 0
        
        # Histórico
        self.trade_history: List[Dict[str, Any]] = []
        
        logger.info(
            f"Trading Engine inicializado | "
            f"Modo: {self.mode.value} | "
            f"Min Confidence: {self.min_confidence:.0%} | "
            f"Max Exposure: {self.max_exposure_pct}%"
        )
    
    async def analyze_and_trade(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        slot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fluxo completo: análise de mercado → decisão → execução
        
        Args:
            symbol: Par de trading (ex: BTC/USDT)
            market_data: Dados do mercado
            slot_id: ID do slot (opcional, usa slot com mais capital disponível)
        
        Returns:
            Resultado da operação
        """
        try:
            # 1. Análise Multi-Agente
            logger.info(f"📊 Analisando {symbol}...")
            consensus = multi_agent_system.analyze_market_consensus(market_data, symbol)
            
            # 2. Validar Consenso
            if consensus['consensus'] == VoteResult.NO_CONSENSUS.value:
                logger.info(f"⏸️ Sem consenso para {symbol}: {consensus['reason']}")
                return {
                    'status': 'no_action',
                    'reason': 'no_consensus',
                    'consensus': consensus
                }
            
            if consensus['confidence'] < self.min_confidence:
                logger.info(
                    f"⏸️ Confiança baixa para {symbol}: "
                    f"{consensus['confidence']:.2%} < {self.min_confidence:.2%}"
                )
                return {
                    'status': 'no_action',
                    'reason': 'low_confidence',
                    'consensus': consensus
                }
            
            # 3. Determinar Ação
            signal = consensus['consensus']
            
            if signal == VoteResult.HOLD.value:
                logger.info(f"⏸️ Sinal HOLD para {symbol}")
                return {
                    'status': 'hold',
                    'reason': 'hold_signal',
                    'consensus': consensus
                }
            
            # 4. Selecionar Slot
            selected_slot = self._select_best_slot(slot_id)
            if not selected_slot:
                logger.warning(f"❌ Nenhum slot disponível para {symbol}")
                return {
                    'status': 'no_action',
                    'reason': 'no_available_slot',
                    'consensus': consensus
                }
            
            # 5. Calcular Posição
            position_size = self._calculate_position_size(
                selected_slot,
                consensus['confidence']
            )
            
            if position_size <= 0:
                logger.warning(f"❌ Tamanho de posição inválido: ${position_size:.2f}")
                return {
                    'status': 'no_action',
                    'reason': 'invalid_position_size',
                    'consensus': consensus
                }
            
            # 6. Executar Trade
            trade_result = await self._execute_trade(
                slot_id=selected_slot['slot_id'],
                symbol=symbol,
                signal=signal,
                position_size=position_size,
                consensus=consensus,
                market_data=market_data
            )
            
            # 7. Atualizar Estatísticas
            self.total_trades += 1
            if trade_result.get('success'):
                self.successful_trades += 1
            
            # 8. Registrar no Histórico
            self.trade_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'symbol': symbol,
                'signal': signal,
                'consensus': consensus,
                'slot_id': selected_slot['slot_id'],
                'position_size': position_size,
                'result': trade_result
            })
            
            return trade_result
            
        except Exception as e:
            logger.error(f"❌ Erro em analyze_and_trade: {e}", exc_info=True)
            return {
                'status': 'error',
                'reason': str(e)
            }
    
    def _select_best_slot(self, preferred_slot_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Seleciona melhor slot para trading
        
        Prioridade:
        1. Slot específico (se fornecido e disponível)
        2. Slot com maior capital disponível
        3. Slot com melhor performance recente
        """
        # Se slot específico foi solicitado
        if preferred_slot_id:
            slot = cascade_manager.get_slot(preferred_slot_id)
            if slot and slot.get_available_capital() > 0:
                return slot.to_dict()
        
        # Obter todos os slots
        all_slots = cascade_manager.get_all_slots()
        
        # Filtrar slots com capital disponível
        available_slots = [
            s for s in all_slots
            if s['available_capital'] > 0
        ]
        
        if not available_slots:
            return None
        
        # Ordenar por: 1) Win rate, 2) Capital disponível
        sorted_slots = sorted(
            available_slots,
            key=lambda s: (s['win_rate'], s['available_capital']),
            reverse=True
        )
        
        return sorted_slots[0]
    
    def _calculate_position_size(
        self,
        slot: Dict[str, Any],
        confidence: float
    ) -> float:
        """
        Calcula tamanho da posição baseado em:
        - Capital disponível no slot
        - Confiança do consenso
        - Risk management rules
        """
        available_capital = slot['available_capital']
        
        # Base: usar % do capital baseado em risco configurado
        base_size = available_capital * (self.risk_per_trade_pct / 100)
        
        # Ajuste por confiança (quanto maior confiança, maior posição)
        # Confiança de 70% = 0.7x, 80% = 0.9x, 90% = 1.1x, 100% = 1.3x
        confidence_multiplier = 0.5 + (confidence * 0.8)
        
        position_size = base_size * confidence_multiplier
        
        # Limitar ao capital disponível
        position_size = min(position_size, available_capital)
        
        logger.debug(
            f"Position sizing: Base=${base_size:.2f} * "
            f"Conf({confidence:.2%})={confidence_multiplier:.2f} = "
            f"${position_size:.2f}"
        )
        
        return position_size
    
    async def _execute_trade(
        self,
        slot_id: str,
        symbol: str,
        signal: str,
        position_size: float,
        consensus: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executa trade (paper ou live)
        """
        current_price = market_data['closes'][-1]
        
        # Calcular SL/TP baseado no regime
        stop_loss_pct = 3.0  # 3% default
        take_profit_pct = 10.0  # 10% default
        
        # Ajustar baseado na volatilidade
        if 'volatility' in market_data:
            vol = market_data['volatility']
            stop_loss_pct = max(2.0, min(5.0, vol * 100))
            take_profit_pct = stop_loss_pct * 3  # Risco/reward 1:3
        
        # Preços de SL/TP
        if signal == VoteResult.BUY.value:
            side = 'long'
            stop_loss_price = current_price * (1 - stop_loss_pct / 100)
            take_profit_price = current_price * (1 + take_profit_pct / 100)
        else:  # SELL
            side = 'short'
            stop_loss_price = current_price * (1 + stop_loss_pct / 100)
            take_profit_price = current_price * (1 - take_profit_pct / 100)
        
        logger.info(
            f"🚀 TRADE: {signal} {symbol} | "
            f"Slot: {slot_id} | "
            f"Size: ${position_size:.2f} | "
            f"Entry: ${current_price:.2f} | "
            f"SL: ${stop_loss_price:.2f} ({stop_loss_pct}%) | "
            f"TP: ${take_profit_price:.2f} ({take_profit_pct}%)"
        )
        
        # Modo PAPER
        if self.mode == TradingMode.PAPER:
            # Registrar paper trade no slot manager
            success, msg = slot_manager.open_paper_trade(
                consensus_id=f"trade_{datetime.utcnow().timestamp()}",
                agent_ids=[v['agent_id'] for v in consensus['votes']],
                action=f"open_{side}",
                symbol=symbol,
                notional_usdt=position_size,
                tp_pct=take_profit_pct,
                sl_pct=stop_loss_pct,
                entry_price=current_price
            )
            
            return {
                'status': 'executed',
                'mode': 'paper',
                'success': success,
                'message': msg,
                'trade': {
                    'slot_id': slot_id,
                    'symbol': symbol,
                    'side': side,
                    'position_size': position_size,
                    'entry_price': current_price,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        
        # Modo LIVE (implementação futura com APIs das exchanges)
        elif self.mode == TradingMode.LIVE:
            logger.warning("⚠️ Modo LIVE não implementado ainda - usando PAPER")
            return await self._execute_trade(slot_id, symbol, signal, position_size, consensus, market_data)
        
        else:
            return {
                'status': 'error',
                'reason': f'Modo não suportado: {self.mode}'
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do motor de trading"""
        win_rate = (self.successful_trades / self.total_trades) if self.total_trades > 0 else 0.0
        
        # Estatísticas dos agentes
        agent_stats = multi_agent_system.get_statistics()
        
        # Estatísticas dos slots
        cascade_stats = cascade_manager.get_global_statistics()
        
        return {
            'trading_engine': {
                'mode': self.mode.value,
                'is_running': self.is_running,
                'total_trades': self.total_trades,
                'successful_trades': self.successful_trades,
                'win_rate': win_rate,
                'recent_trades': len(self.trade_history[-100:])
            },
            'agents': agent_stats,
            'slots': cascade_stats
        }
    
    def start(self):
        """Inicia o motor de trading"""
        self.is_running = True
        logger.info("🚀 Trading Engine INICIADO")
    
    def stop(self):
        """Para o motor de trading"""
        self.is_running = False
        logger.info("⏹️ Trading Engine PARADO")
    
    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna histórico de trades"""
        return self.trade_history[-limit:]


# Instância global
trading_engine = TradingEngine()
