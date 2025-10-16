# ai/agents/multi_agent_system.py
"""
Sistema Multi-Agente com Votação e Consenso
Coordena múltiplos agentes IA para decisões de trading
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import json

from .intelligent_agent import IntelligentAgent
from .real_agent_logic import RealAgentLogic, AgentStrategy

logger = logging.getLogger(__name__)


class VoteResult(str, Enum):
    """Resultado de votação"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_CONSENSUS = "NO_CONSENSUS"


class MultiAgentSystem:
    """
    Sistema que coordena múltiplos agentes IA
    Implementa votação ponderada e consenso
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agents: Dict[str, IntelligentAgent] = {}
        self.agent_logic: Dict[str, RealAgentLogic] = {}  # Lógica real dos agentes
        
        # Configurações de consenso
        self.consensus_threshold = self.config.get('consensus_threshold', 0.65)  # 65% de confiança mínima
        self.min_agents_voting = self.config.get('min_agents_voting', 2)  # Mínimo 2 agentes
        
        # Pesos dos agentes (podem ser ajustados dinamicamente)
        self.agent_weights = {}
        
        # Histórico de decisões
        self.decision_history: List[Dict[str, Any]] = []
        
        # Inicializar agentes configurados
        self._initialize_agents()
        
        logger.info(
            f"Multi-Agent System inicializado com {len(self.agents)} agentes | "
            f"Threshold: {self.consensus_threshold} | Min voting: {self.min_agents_voting}"
        )
    
    def _initialize_agents(self):
        """Inicializa agentes baseado no .env"""
        
        # Agente G1 - Scalping (GPT-4o)
        if os.getenv('IA_G1_SCALP_GPT4O'):
            agent = IntelligentAgent(
                agent_id='G1_SCALP',
                group='scalping',
                config={'strategy': 'scalping', 'timeframe': '1m'}
            )
            self.agents['G1_SCALP'] = agent
            self.agent_logic['G1_SCALP'] = RealAgentLogic('G1_SCALP', AgentStrategy.SCALPING)
            self.agent_weights['G1_SCALP'] = 1.0
            logger.info("✅ Agente G1 Scalping (GPT-4o) inicializado com lógica real")
        
        # Agente G2 - Tendência (GPT-4o)
        if os.getenv('IA_G2_TENDENCIA_GPT4O'):
            agent = IntelligentAgent(
                agent_id='G2_TENDENCIA',
                group='trend',
                config={'strategy': 'trend_following', 'timeframe': '5m'}
            )
            self.agents['G2_TENDENCIA'] = agent
            self.agent_logic['G2_TENDENCIA'] = RealAgentLogic('G2_TENDENCIA', AgentStrategy.TREND_FOLLOWING)
            self.agent_weights['G2_TENDENCIA'] = 1.0
            logger.info("✅ Agente G2 Tendência (GPT-4o) inicializado com lógica real")
        
        # Agente Orquestrador (Claude) - Se disponível
        if os.getenv('IA_ORQUESTRADORA_CLAUDE'):
            agent = IntelligentAgent(
                agent_id='ORCHESTRATOR',
                group='orchestrator',
                config={'strategy': 'risk_management', 'timeframe': '15m'}
            )
            self.agents['ORCHESTRATOR'] = agent
            self.agent_weights['ORCHESTRATOR'] = 1.5  # Peso maior
            logger.info("✅ Agente Orquestrador (Claude) inicializado")
        
        # Agentes de Reserva (Hot)
        if os.getenv('IA_RESERVA_G1_HOT_HAIKU'):
            agent = IntelligentAgent(
                agent_id='G1_BACKUP_HOT',
                group='scalping_backup',
                config={'strategy': 'scalping', 'timeframe': '1m', 'backup': True}
            )
            self.agents['G1_BACKUP_HOT'] = agent
            self.agent_weights['G1_BACKUP_HOT'] = 0.8
            logger.info("✅ Agente G1 Backup Hot (Haiku) inicializado")
        
        if os.getenv('IA_RESERVA_G2_HOT_HAIKU'):
            agent = IntelligentAgent(
                agent_id='G2_BACKUP_HOT',
                group='trend_backup',
                config={'strategy': 'trend_following', 'timeframe': '5m', 'backup': True}
            )
            self.agents['G2_BACKUP_HOT'] = agent
            self.agent_weights['G2_BACKUP_HOT'] = 0.8
            logger.info("✅ Agente G2 Backup Hot (Haiku) inicializado")
        
        # Agentes Warm (GPT-4All Local) 
        if os.getenv('IA_RESERVA_G1_WARM_GPT4ALL'):
            agent = IntelligentAgent(
                agent_id='G1_BACKUP_WARM',
                group='scalping_backup',
                config={'strategy': 'scalping', 'timeframe': '1m', 'backup': True, 'local': True}
            )
            self.agents['G1_BACKUP_WARM'] = agent
            self.agent_weights['G1_BACKUP_WARM'] = 0.6
            logger.info("✅ Agente G1 Backup Warm (GPT-4All) inicializado")
        
        if os.getenv('IA_RESERVA_G2_WARM_GPT4ALL'):
            agent = IntelligentAgent(
                agent_id='G2_BACKUP_WARM',
                group='trend_backup',
                config={'strategy': 'trend_following', 'timeframe': '5m', 'backup': True, 'local': True}
            )
            self.agents['G2_BACKUP_WARM'] = agent
            self.agent_weights['G2_BACKUP_WARM'] = 0.6
            logger.info("✅ Agente G2 Backup Warm (GPT-4All) inicializado")
    
    def analyze_market_consensus(
        self,
        market_data: Dict[str, Any],
        symbol: str = "BTC/USDT"
    ) -> Dict[str, Any]:
        """
        Analisa mercado usando todos os agentes e retorna consenso
        
        Args:
            market_data: Dados do mercado (closes, volumes, etc.)
            symbol: Símbolo sendo analisado
        
        Returns:
            Consenso com votação e decisão final
        """
        if not self.agents:
            return {
                'consensus': VoteResult.NO_CONSENSUS.value,
                'confidence': 0.0,
                'reason': 'Nenhum agente disponível',
                'votes': []
            }
        
        # Coletar votos de todos os agentes
        votes: List[Dict[str, Any]] = []
        
        for agent_id, agent in self.agents.items():
            try:
                # Usa lógica real se disponível
                if agent_id in self.agent_logic:
                    analysis = self.agent_logic[agent_id].analyze_market(market_data)
                else:
                    analysis = agent.analyze_market(market_data)
                
                weight = self.agent_weights.get(agent_id, 1.0)
                
                vote = {
                    'agent_id': agent_id,
                    'signal': analysis['signal'],
                    'confidence': analysis['confidence'],
                    'weight': weight,
                    'weighted_confidence': analysis['confidence'] * weight,
                    'reason': analysis['reason'],
                    'indicators': analysis.get('indicators', {})
                }
                votes.append(vote)
                
                logger.debug(
                    f"Voto de {agent_id}: {analysis['signal']} "
                    f"(confiança: {analysis['confidence']:.2%}, peso: {weight})"
                )
                
            except Exception as e:
                logger.error(f"Erro ao coletar voto de {agent_id}: {e}")
                continue
        
        # Verificar mínimo de votos
        if len(votes) < self.min_agents_voting:
            return {
                'consensus': VoteResult.NO_CONSENSUS.value,
                'confidence': 0.0,
                'reason': f'Votos insuficientes ({len(votes)}/{self.min_agents_voting})',
                'votes': votes,
                'symbol': symbol
            }
        
        # Calcular consenso
        consensus_result = self._calculate_consensus(votes)
        consensus_result['symbol'] = symbol
        consensus_result['votes'] = votes
        consensus_result['timestamp'] = datetime.utcnow().isoformat()
        
        # Armazenar no histórico
        self.decision_history.append(consensus_result)
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
        
        # Log da decisão
        logger.info(
            f"📊 CONSENSO para {symbol}: {consensus_result['consensus']} | "
            f"Confiança: {consensus_result['confidence']:.2%} | "
            f"Votos: {len(votes)} | Razão: {consensus_result['reason']}"
        )
        
        return consensus_result
    
    def _calculate_consensus(self, votes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula consenso baseado em votação ponderada
        
        Algoritmo:
        1. Soma confiança ponderada para cada sinal (BUY/SELL/HOLD)
        2. Normaliza pelo peso total
        3. Verifica se atinge threshold mínimo
        4. Retorna sinal vencedor ou NO_CONSENSUS
        """
        # Acumular votos ponderados
        weighted_scores = {
            'BUY': 0.0,
            'SELL': 0.0,
            'HOLD': 0.0
        }
        
        total_weight = 0.0
        
        for vote in votes:
            signal = vote['signal']
            weighted_conf = vote['weighted_confidence']
            weight = vote['weight']
            
            if signal in weighted_scores:
                weighted_scores[signal] += weighted_conf
                total_weight += weight
        
        # Normalizar scores
        if total_weight > 0:
            normalized_scores = {
                signal: score / total_weight
                for signal, score in weighted_scores.items()
            }
        else:
            normalized_scores = weighted_scores
        
        # Encontrar sinal vencedor
        winner_signal = max(normalized_scores.items(), key=lambda x: x[1])
        consensus_signal = winner_signal[0]
        consensus_confidence = winner_signal[1]
        
        # Verificar se atinge threshold
        if consensus_confidence < self.consensus_threshold:
            return {
                'consensus': VoteResult.NO_CONSENSUS.value,
                'confidence': consensus_confidence,
                'reason': f'Confiança abaixo do threshold ({consensus_confidence:.2%} < {self.consensus_threshold:.2%})',
                'scores': normalized_scores,
                'vote_breakdown': self._get_vote_breakdown(votes)
            }
        
        # Construir razão do consenso
        supporting_votes = [v for v in votes if v['signal'] == consensus_signal]
        reasons = [v['reason'] for v in supporting_votes[:3]]  # Top 3
        combined_reason = ' | '.join(reasons)
        
        return {
            'consensus': consensus_signal,
            'confidence': consensus_confidence,
            'reason': combined_reason,
            'scores': normalized_scores,
            'vote_breakdown': self._get_vote_breakdown(votes),
            'supporting_agents': [v['agent_id'] for v in supporting_votes]
        }
    
    def _get_vote_breakdown(self, votes: List[Dict[str, Any]]) -> Dict[str, int]:
        """Conta votos por sinal"""
        breakdown = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        for vote in votes:
            signal = vote['signal']
            if signal in breakdown:
                breakdown[signal] += 1
        return breakdown
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retorna status de um agente específico"""
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        return agent.get_status()
    
    def get_all_agents_status(self) -> List[Dict[str, Any]]:
        """Retorna status de todos os agentes"""
        return [
            {
                **agent.get_status(),
                'weight': self.agent_weights.get(agent_id, 1.0)
            }
            for agent_id, agent in self.agents.items()
        ]
    
    def update_agent_weight(self, agent_id: str, new_weight: float) -> bool:
        """Atualiza peso de um agente"""
        if agent_id not in self.agents:
            logger.error(f"Agente {agent_id} não encontrado")
            return False
        
        old_weight = self.agent_weights.get(agent_id, 1.0)
        self.agent_weights[agent_id] = new_weight
        
        logger.info(f"Peso do agente {agent_id} atualizado: {old_weight} → {new_weight}")
        return True
    
    def get_decision_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna histórico de decisões"""
        return self.decision_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema"""
        total_decisions = len(self.decision_history)
        
        if total_decisions == 0:
            return {
                'total_decisions': 0,
                'consensus_rate': 0.0,
                'avg_confidence': 0.0,
                'signal_distribution': {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'NO_CONSENSUS': 0}
            }
        
        # Contar decisões por tipo
        signal_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'NO_CONSENSUS': 0}
        total_confidence = 0.0
        
        for decision in self.decision_history:
            signal = decision['consensus']
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
            total_confidence += decision['confidence']
        
        consensus_decisions = total_decisions - signal_counts.get('NO_CONSENSUS', 0)
        
        return {
            'total_decisions': total_decisions,
            'consensus_rate': consensus_decisions / total_decisions if total_decisions > 0 else 0.0,
            'avg_confidence': total_confidence / total_decisions,
            'signal_distribution': signal_counts,
            'active_agents': len(self.agents),
            'consensus_threshold': self.consensus_threshold
        }


# Instância global
multi_agent_system = MultiAgentSystem()
