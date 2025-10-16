#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Orchestrator - Sistema de Orquestração de Agentes IA
Gerencia execução, decisões e integração com slots de trading
"""

import logging
import asyncio
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import time

from ai.agents.intelligent_agent import IntelligentAgent

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Status do agente"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PAUSED = "paused"


class AgentGroup(str, Enum):
    """Grupos de agentes"""
    G1_SCALP = "g1_scalp"  # Scalping - trades rápidos
    G2_TREND = "g2_trend"  # Tendência - trades médio prazo


class AgentOrchestrator:
    """
    Orquestrador central de agentes IA
    Gerencia ciclo de vida, decisões e integração com slots
    """
    
    def __init__(self, exchange_manager, slot_manager):
        """
        Inicializa orchestrator
        
        Args:
            exchange_manager: MultiExchangeManager instance
            slot_manager: RealSlotManager instance
        """
        self.exchange_manager = exchange_manager
        self.slot_manager = slot_manager
        
        self.agents: Dict[str, IntelligentAgent] = {}
        self.agent_status: Dict[str, AgentStatus] = {}
        self.agent_stats: Dict[str, Dict] = {}
        
        self._running = False
        self._loop_thread = None
        self._lock = threading.Lock()
        
        # Configurações
        self.scan_interval = 30  # Segundos entre scans
        self.min_confidence = 0.65  # Confiança mínima para operar
        
        # Inicializar agentes
        self._initialize_agents()
        
        logger.info("✅ AgentOrchestrator inicializado")
    
    def _initialize_agents(self):
        """Inicializa agentes IA padrão"""
        
        # Grupo 1: Scalpers (4 agentes)
        for i in range(1, 5):
            agent_id = f"g1_scalp_{i}"
            agent = IntelligentAgent(
                agent_id=agent_id,
                group=AgentGroup.G1_SCALP,
                config={
                    'timeframe': '5m',
                    'strategy': 'scalp',
                    'risk_tolerance': 'medium'
                }
            )
            self.agents[agent_id] = agent
            self.agent_status[agent_id] = AgentStatus.INACTIVE
            self.agent_stats[agent_id] = {
                'decisions_count': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'last_decision': None,
                'last_execution': None
            }
            
        # Grupo 2: Trend Followers (3 agentes)
        for i in range(1, 4):
            agent_id = f"g2_trend_{i}"
            agent = IntelligentAgent(
                agent_id=agent_id,
                group=AgentGroup.G2_TREND,
                config={
                    'timeframe': '15m',
                    'strategy': 'trend',
                    'risk_tolerance': 'low'
                }
            )
            self.agents[agent_id] = agent
            self.agent_status[agent_id] = AgentStatus.INACTIVE
            self.agent_stats[agent_id] = {
                'decisions_count': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'last_decision': None,
                'last_execution': None
            }
        
        logger.info(f"✅ {len(self.agents)} agentes inicializados")
    
    def start(self):
        """Inicia orquestração de agentes"""
        if self._running:
            logger.warning("Orchestrator já está rodando")
            return
        
        self._running = True
        self._loop_thread = threading.Thread(target=self._orchestration_loop, daemon=True)
        self._loop_thread.start()
        
        logger.info("🚀 Agent Orchestrator iniciado")
    
    def stop(self):
        """Para orquestração de agentes"""
        self._running = False
        if self._loop_thread:
            self._loop_thread.join(timeout=5)
        
        logger.info("🛑 Agent Orchestrator parado")
    
    def _orchestration_loop(self):
        """Loop principal de orquestração"""
        logger.info("🔄 Orchestration loop iniciado")
        
        while self._running:
            try:
                self._execute_cycle()
                time.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Erro no orchestration loop: {e}")
                time.sleep(10)  # Wait before retry
        
        logger.info("🔄 Orchestration loop finalizado")
    
    def _execute_cycle(self):
        """Executa um ciclo de análise e decisão"""
        
        # 1. Buscar slots ativos
        active_slots = self.slot_manager.get_active_slots()
        
        if not active_slots:
            logger.debug("Nenhum slot ativo para processar")
            return
        
        logger.info(f"📊 Processando {len(active_slots)} slots ativos")
        
        # 2. Para cada slot ativo
        for slot in active_slots:
            try:
                self._process_slot(slot)
            except Exception as e:
                logger.error(f"Erro ao processar slot {slot['slot_id']}: {e}")
    
    def _process_slot(self, slot: Dict[str, Any]):
        """
        Processa um slot: busca dados, analisa com agente, executa decisão
        
        Args:
            slot: Dados do slot
        """
        slot_id = slot['slot_id']
        exchange = slot['exchange']
        assigned_agent_id = slot.get('assigned_agent')
        
        # Verificar se tem agente atribuído
        if not assigned_agent_id:
            logger.debug(f"Slot {slot_id} sem agente atribuído")
            return
        
        # Verificar se agente existe e está ativo
        if assigned_agent_id not in self.agents:
            logger.warning(f"Agente {assigned_agent_id} não encontrado")
            return
        
        if self.agent_status[assigned_agent_id] != AgentStatus.ACTIVE:
            logger.debug(f"Agente {assigned_agent_id} não está ativo")
            return
        
        agent = self.agents[assigned_agent_id]
        
        # Verificar se slot pode abrir nova posição
        open_positions = self.slot_manager.get_positions(slot_id, status="open")
        max_positions = slot['risk_config']['max_concurrent_positions']
        
        if len(open_positions) >= max_positions:
            logger.debug(f"Slot {slot_id} já tem {len(open_positions)} posições abertas (max: {max_positions})")
            return
        
        # Buscar dados de mercado
        # TODO: Implementar seleção inteligente de símbolo
        # Por enquanto usa BTC/USDT
        symbol = "BTC/USDT"
        
        market_data = self._fetch_market_data(exchange, symbol)
        
        if not market_data:
            logger.warning(f"Não foi possível buscar dados de mercado para {symbol}")
            return
        
        # Analisar com agente
        decision = agent.analyze_market(market_data)
        
        # Atualizar stats
        with self._lock:
            self.agent_stats[assigned_agent_id]['decisions_count'] += 1
            self.agent_stats[assigned_agent_id]['last_decision'] = decision
            self.agent_stats[assigned_agent_id]['last_execution'] = datetime.utcnow().isoformat()
        
        # Verificar se deve executar trade
        signal = decision.get('signal')
        confidence = decision.get('confidence', 0)
        
        if signal in ['BUY', 'SELL'] and confidence >= self.min_confidence:
            logger.info(f"🎯 Agente {assigned_agent_id}: {signal} {symbol} (confiança: {confidence:.2%})")
            self._execute_trade(slot, symbol, signal, decision, market_data)
        else:
            logger.debug(f"Agente {assigned_agent_id}: {signal} {symbol} (confiança: {confidence:.2%}) - Aguardando")
    
    def _fetch_market_data(self, exchange: str, symbol: str) -> Optional[Dict]:
        """
        Busca dados de mercado para análise
        
        Args:
            exchange: Nome da exchange
            symbol: Símbolo (ex: BTC/USDT)
        
        Returns:
            Dict com dados OHLCV ou None se falhar
        """
        try:
            exchange_obj = self.exchange_manager.get_exchange(exchange)
            if not exchange_obj:
                return None
            
            # Buscar últimas 50 velas (suficiente para indicadores)
            ohlcv = exchange_obj.fetch_ohlcv(symbol, timeframe='5m', limit=50)
            
            if not ohlcv or len(ohlcv) < 20:
                return None
            
            # Extrair dados
            closes = [candle[4] for candle in ohlcv]
            volumes = [candle[5] for candle in ohlcv]
            highs = [candle[2] for candle in ohlcv]
            lows = [candle[3] for candle in ohlcv]
            
            return {
                'symbol': symbol,
                'closes': closes,
                'volumes': volumes,
                'highs': highs,
                'lows': lows,
                'current_price': closes[-1],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de mercado {symbol} de {exchange}: {e}")
            return None
    
    def _execute_trade(
        self,
        slot: Dict,
        symbol: str,
        signal: str,
        decision: Dict,
        market_data: Dict
    ):
        """
        Executa um trade baseado na decisão do agente
        
        Args:
            slot: Dados do slot
            symbol: Símbolo
            signal: BUY ou SELL
            decision: Decisão completa do agente
            market_data: Dados de mercado
        """
        slot_id = slot['slot_id']
        
        try:
            # Calcular tamanho da posição
            capital_available = slot['capital_available']
            risk_pct = slot['risk_config']['max_position_size_pct'] / 100
            position_value = capital_available * risk_pct
            
            current_price = market_data['current_price']
            size = position_value / current_price
            
            # Definir lado
            side = "long" if signal == "BUY" else "short"
            
            # Tentar abrir posição
            position_id = self.slot_manager.open_position(
                slot_id=slot_id,
                symbol=symbol,
                side=side,
                size=size,
                entry_price=current_price
            )
            
            if position_id:
                logger.info(f"✅ Trade executado: {position_id} - {side} {size:.6f} {symbol} @ {current_price}")
                
                # Atualizar stats do agente
                agent_id = slot.get('assigned_agent')
                if agent_id:
                    with self._lock:
                        self.agent_stats[agent_id]['successful_trades'] += 1
            else:
                logger.warning(f"❌ Falha ao executar trade para slot {slot_id}")
                
                # Atualizar stats do agente
                agent_id = slot.get('assigned_agent')
                if agent_id:
                    with self._lock:
                        self.agent_stats[agent_id]['failed_trades'] += 1
        
        except Exception as e:
            logger.error(f"Erro ao executar trade: {e}")
    
    def activate_agent(self, agent_id: str) -> bool:
        """Ativa um agente"""
        with self._lock:
            if agent_id not in self.agents:
                logger.error(f"Agente {agent_id} não encontrado")
                return False
            
            self.agent_status[agent_id] = AgentStatus.ACTIVE
            logger.info(f"✅ Agente {agent_id} ativado")
            return True
    
    def deactivate_agent(self, agent_id: str) -> bool:
        """Desativa um agente"""
        with self._lock:
            if agent_id not in self.agents:
                logger.error(f"Agente {agent_id} não encontrado")
                return False
            
            self.agent_status[agent_id] = AgentStatus.INACTIVE
            logger.info(f"🛑 Agente {agent_id} desativado")
            return True
    
    def get_all_agents(self) -> List[Dict]:
        """Retorna lista de todos os agentes com status"""
        with self._lock:
            agents_list = []
            
            for agent_id, agent in self.agents.items():
                agents_list.append({
                    'agent_id': agent_id,
                    'group': agent.group,
                    'status': self.agent_status[agent_id],
                    'config': agent.config,
                    'stats': self.agent_stats[agent_id]
                })
            
            return agents_list
    
    def get_agent_health(self) -> List[Dict]:
        """Retorna health de todos os agentes (compatível com dashboard)"""
        with self._lock:
            health_list = []
            
            for agent_id, agent in self.agents.items():
                status = self.agent_status[agent_id]
                stats = self.agent_stats[agent_id]
                
                health_list.append({
                    'agent_id': agent_id,
                    'group': agent.group,
                    'status': status,
                    'health': 'healthy' if status == AgentStatus.ACTIVE else 'inactive',
                    'decisions_count': stats['decisions_count'],
                    'successful_trades': stats['successful_trades'],
                    'failed_trades': stats['failed_trades'],
                    'last_decision': stats['last_decision'],
                    'last_execution': stats['last_execution']
                })
            
            return health_list
    
    def get_summary(self) -> Dict:
        """Retorna resumo do orchestrator"""
        with self._lock:
            total = len(self.agents)
            active = sum(1 for s in self.agent_status.values() if s == AgentStatus.ACTIVE)
            
            total_decisions = sum(s['decisions_count'] for s in self.agent_stats.values())
            total_successful = sum(s['successful_trades'] for s in self.agent_stats.values())
            total_failed = sum(s['failed_trades'] for s in self.agent_stats.values())
            
            return {
                'total_agents': total,
                'active_agents': active,
                'inactive_agents': total - active,
                'orchestrator_running': self._running,
                'total_decisions': total_decisions,
                'successful_trades': total_successful,
                'failed_trades': total_failed,
                'success_rate': (total_successful / (total_successful + total_failed) * 100)
                    if (total_successful + total_failed) > 0 else 0
            }
