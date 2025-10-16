
# core/learning/meta_learning.py
"""
Meta-Learning System - Agentes aprendem uns com os outros
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class MetaLearningSystem:
    """
    Sistema de meta-aprendizado que permite agentes aprenderem
    com os erros e acertos uns dos outros
    """
    
    def __init__(self):
        self.shared_knowledge: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.agent_reputation: Dict[str, float] = {}
        self.successful_patterns: List[Dict[str, Any]] = []
        self.failed_patterns: List[Dict[str, Any]] = []
        
        logger.info("✅ Meta-Learning System initialized")
    
    def share_experience(
        self,
        agent_id: str,
        pattern: str,
        success: bool,
        context: Dict[str, Any],
        pnl: float
    ):
        """
        Compartilha experiência de um agente com todos os outros
        
        Args:
            agent_id: ID do agente
            pattern: Padrão identificado
            success: Se foi sucesso ou falha
            context: Contexto da decisão
            pnl: Resultado financeiro
        """
        experience = {
            'agent_id': agent_id,
            'pattern': pattern,
            'success': success,
            'context': context,
            'pnl': pnl,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reputation_weight': self.agent_reputation.get(agent_id, 0.5)
        }
        
        self.shared_knowledge[pattern].append(experience)
        
        if success:
            self.successful_patterns.append(experience)
        else:
            self.failed_patterns.append(experience)
        
        # Atualiza reputação do agente
        self._update_reputation(agent_id, success, pnl)
        
        # Mantém apenas últimas 1000 experiências
        if len(self.shared_knowledge[pattern]) > 1000:
            self.shared_knowledge[pattern] = self.shared_knowledge[pattern][-1000:]
        
        logger.debug(f"Agent {agent_id} shared {pattern}: {'SUCCESS' if success else 'FAIL'}")
    
    def _update_reputation(self, agent_id: str, success: bool, pnl: float):
        """Atualiza score de reputação do agente"""
        current = self.agent_reputation.get(agent_id, 0.5)
        
        # Fator de aprendizado
        alpha = 0.1
        
        # Novo score baseado em sucesso e magnitude do PnL
        if success:
            delta = alpha * (1 + abs(pnl) / 100)  # Aumenta mais se PnL for maior
        else:
            delta = -alpha * (1 + abs(pnl) / 100)  # Diminui mais se perda for maior
        
        new_reputation = max(0.0, min(1.0, current + delta))
        self.agent_reputation[agent_id] = new_reputation
    
    def get_collective_wisdom(self, pattern: str) -> Dict[str, Any]:
        """
        Retorna sabedoria coletiva sobre um padrão
        
        Args:
            pattern: Padrão a consultar
        
        Returns:
            Análise agregada das experiências
        """
        experiences = self.shared_knowledge.get(pattern, [])
        
        if not experiences:
            return {
                'pattern': pattern,
                'consensus': 'unknown',
                'confidence': 0.0,
                'sample_size': 0
            }
        
        # Calcula consenso ponderado por reputação
        weighted_success = 0.0
        total_weight = 0.0
        
        for exp in experiences:
            weight = exp['reputation_weight']
            weighted_success += weight if exp['success'] else 0
            total_weight += weight
        
        confidence = weighted_success / total_weight if total_weight > 0 else 0.5
        consensus = 'bullish' if confidence > 0.6 else 'bearish' if confidence < 0.4 else 'neutral'
        
        return {
            'pattern': pattern,
            'consensus': consensus,
            'confidence': confidence,
            'sample_size': len(experiences),
            'top_agents': self._get_top_agents_for_pattern(pattern)
        }
    
    def _get_top_agents_for_pattern(self, pattern: str, limit: int = 3) -> List[str]:
        """Retorna top agentes para um padrão específico"""
        experiences = self.shared_knowledge.get(pattern, [])
        
        agent_performance: Dict[str, Dict[str, Any]] = defaultdict(lambda: {'wins': 0, 'total': 0, 'pnl': 0.0})
        
        for exp in experiences:
            agent_id = exp['agent_id']
            agent_performance[agent_id]['total'] += 1
            if exp['success']:
                agent_performance[agent_id]['wins'] += 1
            agent_performance[agent_id]['pnl'] += exp['pnl']
        
        # Ordena por win rate e PnL
        sorted_agents = sorted(
            agent_performance.items(),
            key=lambda x: (x[1]['wins'] / x[1]['total'] if x[1]['total'] > 0 else 0, x[1]['pnl']),
            reverse=True
        )
        
        return [agent_id for agent_id, _ in sorted_agents[:limit]]
    
    def transfer_learning(self, from_agent: str, to_agent: str, pattern: str):
        """
        Transfere aprendizado de um agente para outro
        
        Args:
            from_agent: Agente fonte
            to_agent: Agente destino
            pattern: Padrão a transferir
        """
        source_experiences = [
            exp for exp in self.shared_knowledge.get(pattern, [])
            if exp['agent_id'] == from_agent and exp['success']
        ]
        
        if source_experiences:
            # Cria "boost" de reputação para o agente destino neste padrão
            avg_pnl = sum(exp['pnl'] for exp in source_experiences) / len(source_experiences)
            
            logger.info(
                f"Transfer learning: {from_agent} -> {to_agent} for pattern '{pattern}' "
                f"(avg PnL: {avg_pnl:.2f})"
            )
            
            return {
                'pattern': pattern,
                'source_agent': from_agent,
                'target_agent': to_agent,
                'transferred_experiences': len(source_experiences),
                'expected_improvement': avg_pnl
            }
        
        return None
    
    def get_agent_score(self, agent_id: str) -> float:
        """Retorna score de reputação do agente"""
        return self.agent_reputation.get(agent_id, 0.5)
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna ranking de agentes por reputação"""
        sorted_agents = sorted(
            self.agent_reputation.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {
                'agent_id': agent_id,
                'reputation': score,
                'rank': idx + 1
            }
            for idx, (agent_id, score) in enumerate(sorted_agents[:limit])
        ]


# Instância global
meta_learning = MetaLearningSystem()
