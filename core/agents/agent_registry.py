"""
Registry Global de Agentes de IA
Instancia e gerencia todos os agentes configurados no .env
"""

from ai.agents.intelligent_agent import IntelligentAgent
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentRegistry:
    """Registry centralizado de agentes de IA"""
    
    def __init__(self):
        self.agents = {}
        self.start_time = datetime.utcnow()
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Inicializa agentes baseado nas API keys do .env"""
        logger.info("🤖 Inicializando agentes de IA...")
        
        # Agente 1: Scalper GPT-4O (Grupo 1)
        if os.getenv("IA_G1_SCALP_GPT4O"):
            try:
                self.agents["scalp_g1"] = {
                    "id": "scalp_g1",
                    "name": "Scalper G1",
                    "strategy_type": "scalp",
                    "model": "gpt-4o",
                    "status": "GREEN",
                    "description": "Agente focado em scalping de curto prazo",
                    "uptime": 0,
                    "last_decision": None,
                    "total_decisions": 0,
                    "successful_decisions": 0
                }
                logger.info("✅ Agente scalp_g1 inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar scalp_g1: {e}")
        
        # Agente 2: Tendência GPT-4O (Grupo 2)
        if os.getenv("IA_G2_TENDENCIA_GPT4O"):
            try:
                self.agents["trend_g2"] = {
                    "id": "trend_g2",
                    "name": "Tendência G2",
                    "strategy_type": "trend",
                    "model": "gpt-4o",
                    "status": "GREEN",
                    "description": "Agente focado em seguir tendências de médio prazo",
                    "uptime": 0,
                    "last_decision": None,
                    "total_decisions": 0,
                    "successful_decisions": 0
                }
                logger.info("✅ Agente trend_g2 inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar trend_g2: {e}")
        
        # Agente 3: Orquestradora Claude
        if os.getenv("IA_ORQUESTRADORA_CLAUDE"):
            try:
                self.agents["orchestrator"] = {
                    "id": "orchestrator",
                    "name": "Orquestradora",
                    "strategy_type": "orchestration",
                    "model": "claude-3-sonnet",
                    "status": "GREEN",
                    "description": "Agente coordenador que arbitra decisões",
                    "uptime": 0,
                    "last_decision": None,
                    "total_decisions": 0,
                    "successful_decisions": 0
                }
                logger.info("✅ Agente orchestrator inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar orchestrator: {e}")
        
        # Agente 4: Reserva G1 Hot
        if os.getenv("IA_RESERVA_G1_HOT_HAIKU"):
            try:
                self.agents["reserve_g1_hot"] = {
                    "id": "reserve_g1_hot",
                    "name": "Reserva G1 Hot",
                    "strategy_type": "scalp_backup",
                    "model": "claude-3-haiku",
                    "status": "STANDBY",
                    "description": "Backup rápido para scalping",
                    "uptime": 0,
                    "last_decision": None,
                    "total_decisions": 0,
                    "successful_decisions": 0
                }
                logger.info("✅ Agente reserve_g1_hot inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar reserve_g1_hot: {e}")
        
        logger.info(f"🎯 Total de agentes inicializados: {len(self.agents)}")
    
    def get_agent(self, agent_id: str):
        """Obtém agente por ID"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self):
        """Retorna lista de todos os agentes"""
        return list(self.agents.values())
    
    def update_agent_status(self, agent_id: str, status: str):
        """Atualiza status de um agente"""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = status
    
    def record_decision(self, agent_id: str, decision: dict):
        """Registra uma decisão do agente"""
        if agent_id in self.agents:
            self.agents[agent_id]["total_decisions"] += 1
            self.agents[agent_id]["last_decision"] = decision
            if decision.get("success"):
                self.agents[agent_id]["successful_decisions"] += 1
    
    def get_agent_stats(self, agent_id: str):
        """Obtém estatísticas de um agente"""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        accuracy = 0
        if agent["total_decisions"] > 0:
            accuracy = (agent["successful_decisions"] / agent["total_decisions"]) * 100
        
        return {
            "id": agent["id"],
            "name": agent["name"],
            "status": agent["status"],
            "strategy_type": agent["strategy_type"],
            "model": agent["model"],
            "uptime": uptime,
            "last_decision": agent["last_decision"],
            "total_decisions": agent["total_decisions"],
            "accuracy": round(accuracy, 2)
        }
    
    def get_all_stats(self):
        """Retorna estatísticas de todos os agentes"""
        return [self.get_agent_stats(agent_id) for agent_id in self.agents.keys()]


# Instância global
_registry = None

def get_agent_registry():
    """Obtém instância global do registry"""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry

def get_agent(agent_id: str):
    """Obtém agente por ID"""
    return get_agent_registry().get_agent(agent_id)

def get_all_agents():
    """Obtém todos os agentes"""
    return get_agent_registry().get_all_agents()

def get_agent_stats(agent_id: str):
    """Obtém estatísticas de um agente"""
    return get_agent_registry().get_agent_stats(agent_id)

def get_all_agent_stats():
    """Obtém estatísticas de todos os agentes"""
    return get_agent_registry().get_all_stats()
