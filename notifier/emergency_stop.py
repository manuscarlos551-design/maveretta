"""
Emergency Stop System - Sistema de parada de emergência.
"""

import asyncio
from datetime import datetime
from typing import Dict, List


class EmergencyStop:
    """
    Sistema de parada de emergência.
    Para tudo imediatamente em situações críticas.
    """
    
    def __init__(self, bot_manager, notifier):
        self.bot_manager = bot_manager
        self.notifier = notifier
        self.is_stopping = False
        self.stop_reason = None
        self.stop_timestamp = None
    
    async def trigger(self, reason: str = "Manual", triggered_by: str = "User"):
        """
        Aciona a parada de emergência.
        
        Args:
            reason: Motivo da parada
            triggered_by: Quem acionou
        """
        if self.is_stopping:
            return {
                'success': False,
                'message': 'Parada de emergência já em andamento'
            }
        
        self.is_stopping = True
        self.stop_reason = reason
        self.stop_timestamp = datetime.now()
        
        # Notificar início
        await self.notifier.send_critical(
            f"🚨 **PARADA DE EMERGÊNCIA ACIONADA**\n\n"
            f"**Motivo:** {reason}\n"
            f"**Acionado por:** {triggered_by}\n"
            f"**Timestamp:** {self.stop_timestamp}\n\n"
            f"Iniciando procedimento de parada..."
        )
        
        results = []
        errors = []
        
        try:
            # 1. Parar novas entradas
            result = await self._stop_new_entries()
            results.append(result)
            
            # 2. Cancelar ordens pendentes
            result = await self._cancel_pending_orders()
            results.append(result)
            
            # 3. Fechar posições abertas
            result = await self._close_open_positions()
            results.append(result)
            
            # 4. Desabilitar estratégias
            result = await self._disable_strategies()
            results.append(result)
            
            # 5. Parar bot
            result = await self._stop_bot()
            results.append(result)
            
            # Resumo final
            summary = self._generate_summary(results)
            
            await self.notifier.send_critical(
                f"✅ **PARADA DE EMERGÊNCIA CONCLUÍDA**\n\n{summary}"
            )
            
            return {
                'success': True,
                'results': results,
                'summary': summary
            }
            
        except Exception as e:
            error_msg = f"❌ Erro durante parada de emergência: {str(e)}"
            await self.notifier.send_critical(error_msg)
            
            return {
                'success': False,
                'error': str(e),
                'results': results
            }
        finally:
            self.is_stopping = False
    
    async def _stop_new_entries(self) -> Dict:
        """Para abertura de novas posições"""
        try:
            await self.bot_manager.set_mode('stop_new_entries')
            return {
                'step': 'Stop New Entries',
                'success': True,
                'message': '✅ Novas entradas bloqueadas'
            }
        except Exception as e:
            return {
                'step': 'Stop New Entries',
                'success': False,
                'error': str(e)
            }
    
    async def _cancel_pending_orders(self) -> Dict:
        """Cancela todas as ordens pendentes"""
        try:
            cancelled = await self.bot_manager.cancel_all_orders()
            return {
                'step': 'Cancel Pending Orders',
                'success': True,
                'message': f'✅ {cancelled} ordens canceladas'
            }
        except Exception as e:
            return {
                'step': 'Cancel Pending Orders',
                'success': False,
                'error': str(e)
            }
    
    async def _close_open_positions(self) -> Dict:
        """Fecha todas as posições abertas"""
        try:
            closed = await self.bot_manager.close_all_positions(
                reason='emergency_stop'
            )
            return {
                'step': 'Close Open Positions',
                'success': True,
                'message': f'✅ {closed} posições fechadas'
            }
        except Exception as e:
            return {
                'step': 'Close Open Positions',
                'success': False,
                'error': str(e)
            }
    
    async def _disable_strategies(self) -> Dict:
        """Desabilita todas as estratégias"""
        try:
            disabled = await self.bot_manager.disable_all_strategies()
            return {
                'step': 'Disable Strategies',
                'success': True,
                'message': f'✅ {disabled} estratégias desabilitadas'
            }
        except Exception as e:
            return {
                'step': 'Disable Strategies',
                'success': False,
                'error': str(e)
            }
    
    async def _stop_bot(self) -> Dict:
        """Para o bot completamente"""
        try:
            await self.bot_manager.stop()
            return {
                'step': 'Stop Bot',
                'success': True,
                'message': '✅ Bot parado'
            }
        except Exception as e:
            return {
                'step': 'Stop Bot',
                'success': False,
                'error': str(e)
            }
    
    def _generate_summary(self, results: List[Dict]) -> str:
        """Gera resumo dos resultados"""
        summary = "**Procedimento de Parada:**\n\n"
        
        for result in results:
            if result['success']:
                summary += f"✅ {result['step']}: {result['message']}\n"
            else:
                summary += f"❌ {result['step']}: {result.get('error', 'Erro desconhecido')}\n"
        
        summary += f"\n**Duração:** {(datetime.now() - self.stop_timestamp).seconds}s"
        summary += f"\n**Status Final:** Bot parado e seguro"
        
        return summary
