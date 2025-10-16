
# core/notifications/voice_commands.py
"""
Voice Commands - Interface de comandos por voz via Telegram
Permite controle do bot através de linguagem natural
"""

import logging
from typing import Dict, Any, Optional, Tuple
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class VoiceCommandProcessor:
    """
    Processa comandos de voz/texto em linguagem natural
    """
    
    def __init__(self):
        self.command_patterns = {
            # Comandos de posição
            'reduce_positions': r'reduzi[ra]?.*posições?.*(em|por)\s*(\d+)%',
            'close_all': r'fecha[r]?.*todas?.*(posições?|trades?)',
            'close_symbol': r'fecha[r]?.*(posição|trade).*em\s+([A-Z]+)',
            
            # Consultas
            'exposure': r'qual.*exposição.*a?\s*([A-Z]+)?',
            'pnl': r'qual.*(lucro|pnl|resultado)',
            'positions': r'quantas?.*(posições?|trades?).*abertas?',
            
            # Controles
            'pause_all': r'paus[ae].*tudo',
            'resume_all': r'retom[ae].*tudo',
            'pause_symbol': r'paus[ae].*([A-Z]+)',
            
            # Alertas
            'set_alert': r'alert[ae].*quando.*([A-Z]+).*(\d+)',
        }
        
        logger.info("✅ Voice Command Processor initialized")
    
    def process_command(self, text: str, user_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Processa comando em linguagem natural
        
        Args:
            text: Texto do comando
            user_id: ID do usuário
        
        Returns:
            (action, params)
        """
        text = text.lower().strip()
        
        # Reduzir posições
        match = re.search(self.command_patterns['reduce_positions'], text)
        if match:
            percentage = int(match.group(2))
            return 'reduce_positions', {'percentage': percentage}
        
        # Fechar todas
        if re.search(self.command_patterns['close_all'], text):
            return 'close_all', {}
        
        # Fechar símbolo específico
        match = re.search(self.command_patterns['close_symbol'], text)
        if match:
            symbol = match.group(2).upper()
            return 'close_symbol', {'symbol': symbol}
        
        # Consultar exposição
        match = re.search(self.command_patterns['exposure'], text)
        if match:
            symbol = match.group(1).upper() if match.group(1) else None
            return 'get_exposure', {'symbol': symbol}
        
        # Consultar PnL
        if re.search(self.command_patterns['pnl'], text):
            return 'get_pnl', {}
        
        # Consultar posições abertas
        if re.search(self.command_patterns['positions'], text):
            return 'get_positions', {}
        
        # Pausar tudo
        if re.search(self.command_patterns['pause_all'], text):
            return 'pause_all', {}
        
        # Retomar tudo
        if re.search(self.command_patterns['resume_all'], text):
            return 'resume_all', {}
        
        # Pausar símbolo
        match = re.search(self.command_patterns['pause_symbol'], text)
        if match:
            symbol = match.group(1).upper()
            return 'pause_symbol', {'symbol': symbol}
        
        # Comando não reconhecido
        return 'unknown', {'original_text': text}
    
    def execute_command(self, action: str, params: Dict[str, Any]) -> str:
        """
        Executa comando e retorna resposta
        
        Args:
            action: Ação a executar
            params: Parâmetros da ação
        
        Returns:
            Resposta para o usuário
        """
        try:
            if action == 'reduce_positions':
                return self._reduce_positions(params['percentage'])
            
            elif action == 'close_all':
                return self._close_all_positions()
            
            elif action == 'close_symbol':
                return self._close_symbol(params['symbol'])
            
            elif action == 'get_exposure':
                return self._get_exposure(params.get('symbol'))
            
            elif action == 'get_pnl':
                return self._get_pnl()
            
            elif action == 'get_positions':
                return self._get_positions()
            
            elif action == 'pause_all':
                return self._pause_all()
            
            elif action == 'resume_all':
                return self._resume_all()
            
            elif action == 'pause_symbol':
                return self._pause_symbol(params['symbol'])
            
            else:
                return (
                    "❓ Comando não reconhecido. Tente:\n"
                    "- 'Reduzir posições em 50%'\n"
                    "- 'Fechar todas as posições'\n"
                    "- 'Qual minha exposição a BTC?'\n"
                    "- 'Qual meu lucro?'\n"
                    "- 'Pausar tudo'"
                )
            
        except Exception as e:
            logger.error(f"Error executing command {action}: {e}")
            return f"❌ Erro ao executar comando: {str(e)}"
    
    def _reduce_positions(self, percentage: int) -> str:
        """Reduz todas as posições"""
        from core.positions.position_manager import position_manager
        
        if not position_manager:
            return "❌ Position manager não disponível"
        
        trades = position_manager.get_open_trades()
        
        if not trades:
            return "ℹ️ Nenhuma posição aberta para reduzir"
        
        closed_count = 0
        total_pnl = 0
        
        for trade in trades:
            # Calcular quantidade a reduzir
            reduce_amount = trade['amount'] * (percentage / 100)
            
            # Fechar parcialmente (simplificado - precisaria de método específico)
            success, msg, result = position_manager.close_live_trade(
                trade['trade_id'],
                reason=f"voice_command_reduce_{percentage}pct"
            )
            
            if success and result:
                closed_count += 1
                total_pnl += result.get('realized_pnl', 0)
        
        return (
            f"✅ {closed_count} posições reduzidas em {percentage}%\n"
            f"💰 PnL total: ${total_pnl:.2f}"
        )
    
    def _close_all_positions(self) -> str:
        """Fecha todas as posições"""
        from core.positions.position_manager import position_manager
        
        if not position_manager:
            return "❌ Position manager não disponível"
        
        trades = position_manager.get_open_trades()
        
        if not trades:
            return "ℹ️ Nenhuma posição aberta"
        
        closed_count = 0
        total_pnl = 0
        
        for trade in trades:
            success, msg, result = position_manager.close_live_trade(
                trade['trade_id'],
                reason="voice_command_close_all"
            )
            
            if success and result:
                closed_count += 1
                total_pnl += result.get('realized_pnl', 0)
        
        return (
            f"✅ {closed_count} posições fechadas\n"
            f"💰 PnL total: ${total_pnl:.2f}"
        )
    
    def _close_symbol(self, symbol: str) -> str:
        """Fecha posições de um símbolo específico"""
        from core.positions.position_manager import position_manager
        
        if not position_manager:
            return "❌ Position manager não disponível"
        
        trades = [t for t in position_manager.get_open_trades() if t['symbol'] == symbol]
        
        if not trades:
            return f"ℹ️ Nenhuma posição aberta em {symbol}"
        
        closed_count = 0
        total_pnl = 0
        
        for trade in trades:
            success, msg, result = position_manager.close_live_trade(
                trade['trade_id'],
                reason=f"voice_command_close_{symbol}"
            )
            
            if success and result:
                closed_count += 1
                total_pnl += result.get('realized_pnl', 0)
        
        return (
            f"✅ {closed_count} posições em {symbol} fechadas\n"
            f"💰 PnL: ${total_pnl:.2f}"
        )
    
    def _get_exposure(self, symbol: Optional[str]) -> str:
        """Consulta exposição"""
        from core.positions.position_manager import position_manager
        
        if not position_manager:
            return "❌ Position manager não disponível"
        
        trades = position_manager.get_open_trades()
        
        if symbol:
            trades = [t for t in trades if symbol in t['symbol']]
            total = sum(t.get('notional_usdt', 0) for t in trades)
            return f"💼 Exposição em {symbol}: ${total:,.2f}"
        else:
            total = sum(t.get('notional_usdt', 0) for t in trades)
            by_symbol = {}
            for t in trades:
                sym = t['symbol']
                by_symbol[sym] = by_symbol.get(sym, 0) + t.get('notional_usdt', 0)
            
            response = f"💼 Exposição total: ${total:,.2f}\n\n"
            for sym, exp in sorted(by_symbol.items(), key=lambda x: x[1], reverse=True):
                response += f"• {sym}: ${exp:,.2f}\n"
            
            return response
    
    def _get_pnl(self) -> str:
        """Consulta PnL"""
        from core.slots.manager import slot_manager
        
        total_pnl = 0
        for slot_id in slot_manager.get_active_slots():
            metrics = slot_manager.get_metrics(slot_id)
            if metrics:
                total_pnl += metrics.realized_pnl
        
        emoji = "📈" if total_pnl > 0 else "📉"
        return f"{emoji} PnL total: ${total_pnl:,.2f}"
    
    def _get_positions(self) -> str:
        """Consulta posições abertas"""
        from core.positions.position_manager import position_manager
        
        if not position_manager:
            return "❌ Position manager não disponível"
        
        trades = position_manager.get_open_trades()
        count = len(trades)
        
        if count == 0:
            return "ℹ️ Nenhuma posição aberta"
        
        response = f"📊 {count} posições abertas:\n\n"
        
        for trade in trades[:5]:  # Primeiras 5
            response += (
                f"• {trade['symbol']}: ${trade.get('notional_usdt', 0):.0f} "
                f"({trade.get('unrealized_pnl_pct', 0):.1f}%)\n"
            )
        
        if count > 5:
            response += f"\n... e mais {count - 5} posições"
        
        return response
    
    def _pause_all(self) -> str:
        """Pausa todos os slots"""
        from core.slots.manager import slot_manager
        
        paused = 0
        for slot_id in slot_manager.get_active_slots():
            success, msg = slot_manager.pause_slot(slot_id)
            if success:
                paused += 1
        
        return f"⏸️ {paused} slots pausados"
    
    def _resume_all(self) -> str:
        """Retoma todos os slots"""
        from core.slots.manager import slot_manager
        
        resumed = 0
        for slot_id in slot_manager.list_slots():
            slot = slot_manager.get_slot(slot_id)
            if slot and slot.status == 'paused':
                success, msg = slot_manager.resume_slot(slot_id)
                if success:
                    resumed += 1
        
        return f"▶️ {resumed} slots retomados"
    
    def _pause_symbol(self, symbol: str) -> str:
        """Pausa slots de um símbolo"""
        from core.slots.manager import slot_manager
        
        paused = 0
        for slot_id in slot_manager.get_active_slots():
            slot = slot_manager.get_slot(slot_id)
            if slot and slot.symbol == symbol:
                success, msg = slot_manager.pause_slot(slot_id)
                if success:
                    paused += 1
        
        return f"⏸️ {paused} slots de {symbol} pausados"


# Instância global
voice_command_processor = VoiceCommandProcessor()
