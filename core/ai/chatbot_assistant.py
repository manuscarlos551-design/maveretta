
"""
AI Chatbot Assistant - Interface conversacional com IA
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ChatbotAssistant:
    """
    Assistente conversacional com IA
    """
    
    def __init__(self):
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 10
        
        logger.info("✅ AI Chatbot Assistant initialized")
    
    async def chat(self, user_message: str, user_id: str = "default") -> str:
        """
        Processa mensagem do usuário e gera resposta
        
        Args:
            user_message: Mensagem do usuário
            user_id: ID do usuário
        
        Returns:
            Resposta do assistente
        """
        # Adicionar ao histórico
        self.conversation_history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Limitar histórico
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history*2:]
        
        # Processar query
        response = await self._generate_response(user_message)
        
        # Adicionar resposta ao histórico
        self.conversation_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        return response
    
    async def _generate_response(self, query: str) -> str:
        """Gera resposta usando lógica ou LLM"""
        query_lower = query.lower()
        
        # Queries sobre performance
        if 'lucro' in query_lower or 'pnl' in query_lower:
            from core.positions.position_manager import position_manager
            
            if position_manager:
                trades = position_manager.get_open_trades()
                total_pnl = sum(t.get('unrealized_pnl', 0) for t in trades)
                
                return f"📊 Seu PnL não realizado atual é de ${total_pnl:,.2f}"
            else:
                return "❌ Position manager não disponível"
        
        # Queries sobre posições
        elif 'posições' in query_lower or 'trades' in query_lower:
            from core.positions.position_manager import position_manager
            
            if position_manager:
                trades = position_manager.get_open_trades()
                count = len(trades)
                
                if count == 0:
                    return "ℹ️ Você não tem posições abertas no momento"
                
                response = f"📊 Você tem {count} posições abertas:\n\n"
                for trade in trades[:3]:
                    response += f"• {trade['symbol']}: ${trade.get('notional_usdt', 0):.0f}\n"
                
                if count > 3:
                    response += f"\n... e mais {count - 3}"
                
                return response
            else:
                return "❌ Position manager não disponível"
        
        # Queries sobre estratégias
        elif 'estratégia' in query_lower or 'strategy' in query_lower:
            return (
                "🎯 Estratégias disponíveis:\n\n"
                "• Scalping - Trades rápidos\n"
                "• Swing Trading - Médio prazo\n"
                "• Mean Reversion - Reversão à média\n"
                "• Trend Following - Seguir tendências\n\n"
                "Qual você quer saber mais?"
            )
        
        # Queries sobre ajuda
        elif 'ajuda' in query_lower or 'help' in query_lower:
            return (
                "💬 Eu posso te ajudar com:\n\n"
                "• Consultar PnL e posições\n"
                "• Informações sobre estratégias\n"
                "• Explicar métricas\n"
                "• Recomendações de trading\n\n"
                "O que você gostaria de saber?"
            )
        
        # Resposta padrão
        else:
            return (
                "🤖 Desculpe, não entendi completamente sua pergunta. "
                "Tente perguntar sobre:\n"
                "• Lucro/PnL\n"
                "• Posições abertas\n"
                "• Estratégias\n"
                "• Ajuda geral"
            )


# Instância global
chatbot_assistant = ChatbotAssistant()
