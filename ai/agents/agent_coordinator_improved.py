# ai/agents/agent_coordinator_improved.py
"""
Coordenador de Agentes IA - Versão Melhorada
Sistema de voting inteligente entre múltiplos agentes
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentCoordinatorImproved:
    """
    Coordenador que gerencia múltiplos agentes e implementa voting system
    """
    
    def __init__(self, agents: List[Any] = None):
        self.agents = agents or []
        self.threshold = 0.70  # 70% consensus para ação
        self.history = []
        
        # Pesos dos grupos
        self.group_weights = {
            "G1": {"A1": 0.25, "A2": 0.25, "A3": 0.25, "A4": 0.0833, "A5": 0.0833, "A6": 0.0834},
            "G2": {"A4": 0.25, "A5": 0.25, "A6": 0.25, "A1": 0.0833, "A2": 0.0833, "A3": 0.0834}
        }
        
        logger.info(f"✅ AgentCoordinatorImproved inicializado com {len(self.agents)} agentes")
    
    def add_agent(self, agent):
        """Adiciona um agente ao coordenador"""
        self.agents.append(agent)
        logger.info(f"Agente {agent.agent_id} adicionado ao coordenador")
    
    def coordinate_decision(self, market_data: Dict[str, Any], group_id: str = "G1") -> Dict[str, Any]:
        """
        Coordena decisão entre todos os agentes
        
        Args:
            market_data: Dados do mercado para análise
            group_id: Grupo de agentes (G1 ou G2)
        
        Returns:
            Decisão consolidada com voting results
        """
        if not self.agents:
            return {
                'decision': 'HOLD',
                'confidence': 0.0,
                'reason': 'Nenhum agente disponível',
                'votes': {}
            }
        
        # Coletar análises de todos os agentes
        agent_analyses = []
        for agent in self.agents:
            try:
                analysis = agent.analyze_market(market_data)
                agent_analyses.append(analysis)
            except Exception as e:
                logger.error(f"Erro ao analisar com agente {agent.agent_id}: {e}")
        
        if not agent_analyses:
            return {
                'decision': 'HOLD',
                'confidence': 0.0,
                'reason': 'Nenhuma análise válida',
                'votes': {}
            }
        
        # Sistema de voting
        votes = self._count_votes(agent_analyses, group_id)
        
        # Decisão final baseada em consensus
        decision, confidence, reason = self._make_consensus_decision(votes, agent_analyses)
        
        # Armazenar no histórico
        decision_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'decision': decision,
            'confidence': confidence,
            'reason': reason,
            'votes': votes,
            'num_agents': len(agent_analyses)
        }
        self.history.append(decision_record)
        
        # Manter histórico limitado (últimas 100 decisões)
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        return decision_record
    
    def _count_votes(self, analyses: List[Dict[str, Any]], group_id: str) -> Dict[str, Any]:
        """
        Conta votos ponderados dos agentes
        
        Args:
            analyses: Lista de análises dos agentes
            group_id: ID do grupo para pesos
        
        Returns:
            Contagem de votos por sinal
        """
        weights = self.group_weights.get(group_id, {})
        
        votes = {
            'BUY': {'count': 0, 'weighted_score': 0.0, 'confidence_sum': 0.0},
            'SELL': {'count': 0, 'weighted_score': 0.0, 'confidence_sum': 0.0},
            'HOLD': {'count': 0, 'weighted_score': 0.0, 'confidence_sum': 0.0}
        }
        
        for analysis in analyses:
            signal = analysis.get('signal', 'HOLD')
            confidence = analysis.get('confidence', 0.0)
            agent_id = analysis.get('agent_id', 'unknown')
            
            # Peso do agente
            weight = weights.get(agent_id, 0.1)
            
            if signal in votes:
                votes[signal]['count'] += 1
                votes[signal]['weighted_score'] += weight * confidence
                votes[signal]['confidence_sum'] += confidence
        
        # Calcular médias
        for signal in votes:
            if votes[signal]['count'] > 0:
                votes[signal]['avg_confidence'] = votes[signal]['confidence_sum'] / votes[signal]['count']
            else:
                votes[signal]['avg_confidence'] = 0.0
        
        return votes
    
    def _make_consensus_decision(self, votes: Dict[str, Any], analyses: List[Dict]) -> Tuple[str, float, str]:
        """
        Toma decisão baseada em consensus
        
        Args:
            votes: Votos contados
            analyses: Análises originais dos agentes
        
        Returns:
            (decision, confidence, reason)
        """
        total_agents = len(analyses)
        
        # Encontrar sinal com maior score ponderado
        max_signal = max(votes.items(), key=lambda x: x[1]['weighted_score'])
        decision = max_signal[0]
        weighted_score = max_signal[1]['weighted_score']
        vote_count = max_signal[1]['count']
        
        # Calcular confiança baseada em:
        # 1. Proporção de votos
        # 2. Score ponderado
        # 3. Confiança média dos agentes que votaram
        vote_proportion = vote_count / total_agents if total_agents > 0 else 0
        avg_confidence = max_signal[1]['avg_confidence']
        
        # Confiança final é média ponderada
        confidence = (vote_proportion * 0.4 + weighted_score * 0.4 + avg_confidence * 0.2)
        
        # Verificar threshold
        if confidence < self.threshold:
            decision = 'HOLD'
            reason = f'Consensus abaixo do threshold ({confidence:.2%} < {self.threshold:.2%})'
        else:
            # Coletar razões dos agentes que votaram no sinal vencedor
            reasons = []
            for analysis in analyses:
                if analysis.get('signal') == decision:
                    agent_reason = analysis.get('reason', '')
                    if agent_reason:
                        reasons.append(agent_reason)
            
            reason = f'{vote_count}/{total_agents} agentes votaram {decision}'
            if reasons:
                reason += f': {reasons[0]}'  # Primeira razão como exemplo
        
        return decision, min(confidence, 1.0), reason
    
    def get_regime_params(self, regime: str) -> Dict[str, float]:
        """
        Retorna parâmetros de trading para o regime especificado
        
        Args:
            regime: conservative, neutral ou aggressive
        
        Returns:
            Dicionário com parâmetros de trading
        """
        params = {
            'conservative': {
                'take_profit': 0.06,
                'stop_loss': 0.02,
                'trail_trigger': 0.04,
                'trail_distance': 0.02,
                'max_slots': 1,
                'position_size_multiplier': 0.5,
                'max_open_trades': 1
            },
            'neutral': {
                'take_profit': 0.10,
                'stop_loss': 0.03,
                'trail_trigger': 0.06,
                'trail_distance': 0.03,
                'max_slots': 3,
                'position_size_multiplier': 1.0,
                'max_open_trades': 3
            },
            'aggressive': {
                'take_profit': 0.15,
                'stop_loss': 0.04,
                'trail_trigger': 0.08,
                'trail_distance': 0.04,
                'max_slots': 5,
                'position_size_multiplier': 1.5,
                'max_open_trades': 5
            }
        }
        
        return params.get(regime, params['neutral'])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas das decisões"""
        if not self.history:
            return {
                'total_decisions': 0,
                'buy_count': 0,
                'sell_count': 0,
                'hold_count': 0,
                'avg_confidence': 0.0
            }
        
        buy_count = sum(1 for d in self.history if d['decision'] == 'BUY')
        sell_count = sum(1 for d in self.history if d['decision'] == 'SELL')
        hold_count = sum(1 for d in self.history if d['decision'] == 'HOLD')
        
        confidences = [d['confidence'] for d in self.history]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'total_decisions': len(self.history),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'avg_confidence': round(avg_confidence, 3),
            'last_decision': self.history[-1] if self.history else None
        }
