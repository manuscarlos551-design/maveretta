"""
AI Module - Sistema de IA Modular
Mantém compatibilidade com sistema existente
"""

from .orchestrator.ai_coordinator import AICoordinator
from .agents.multi_agent_coordinator import MultiAgentCoordinator

__all__ = ['AICoordinator', 'MultiAgentCoordinator']