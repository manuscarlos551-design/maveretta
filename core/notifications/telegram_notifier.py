#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Notifier - Sistema de notificações via Telegram
"""

import os
import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Envia notificações via Telegram Bot
    """

    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = os.getenv('NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        self.timeout = int(os.getenv('TELEGRAM_TIMEOUT', '10'))

        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Voice command processor
        self.voice_processor = None

        if self.enabled and self.bot_token and self.chat_id:
            logger.info(f"✅ Telegram Notifier habilitado (Chat ID: {self.chat_id})")
        else:
            logger.warning("⚠️ Telegram Notifier desabilitado ou não configurado")

    async def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Envia mensagem via Telegram

        Args:
            message: Texto da mensagem (suporta HTML)
            parse_mode: 'HTML' ou 'Markdown'

        Returns:
            True se enviado com sucesso
        """
        if not self.enabled or not self.bot_token or not self.chat_id:
            return False

        try:
            url = f"{self.base_url}/sendMessage"

            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        return True
                    else:
                        logger.error(f"❌ Erro ao enviar Telegram: {resp.status}")
                        return False

        except Exception as e:
            logger.error(f"❌ Erro ao enviar Telegram: {e}")
            return False

    async def notify_trade_opened(self, trade: Dict[str, Any]):
        """Notifica abertura de trade"""
        message = (
            f"🚀 <b>TRADE ABERTO</b>\n"
            f"\n"
            f"🎯 <b>Símbolo:</b> {trade.get('symbol')}\n"
            f"📊 <b>Lado:</b> {trade.get('side').upper()}\n"
            f"💰 <b>Valor:</b> ${trade.get('amount_usd', 0):.2f}\n"
            f"💵 <b>Preço Entrada:</b> ${trade.get('entry_price', 0):.2f}\n"
            f"\n"
            f"🎯 <b>Take Profit:</b> ${trade.get('tp_price', 0):.2f} ({trade.get('tp_pct', 0):.2%})\n"
            f"🛑 <b>Stop Loss:</b> ${trade.get('sl_price', 0):.2f}\n"
            f"\n"
            f"🏛️ <b>Exchange:</b> {trade.get('exchange', '').upper()}\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        await self.send_message(message)

    async def notify_trade_closed(self, trade: Dict[str, Any]):
        """Notifica fechamento de trade"""
        profit = trade.get('profit', {})
        is_profit = profit.get('is_profitable', False)

        icon = "🟢" if is_profit else "🔴"
        status = "LUCRO" if is_profit else "PREJUÍZO"

        message = (
            f"{icon} <b>TRADE FECHADO - {status}</b>\n"
            f"\n"
            f"🎯 <b>Símbolo:</b> {trade.get('symbol')}\n"
            f"📊 <b>Lado:</b> {trade.get('side').upper()}\n"
            f"\n"
            f"💵 <b>Entrada:</b> ${trade.get('entry_price', 0):.2f}\n"
            f"💵 <b>Saída:</b> ${trade.get('close_price', 0):.2f}\n"
            f"\n"
            f"📊 <b>Profit Bruto:</b> ${profit.get('gross_profit_usd', 0):.2f} ({profit.get('gross_profit_pct', 0):.2%})\n"
            f"💸 <b>Taxas:</b> -${profit.get('total_fees', 0):.2f}\n"
            f"💰 <b>Profit Líquido:</b> ${profit.get('net_profit_usd', 0):.2f} ({profit.get('net_profit_pct', 0):.2%})\n"
            f"\n"
            f"🏛️ <b>Exchange:</b> {trade.get('exchange', '').upper()}\n"
            f"📝 <b>Motivo:</b> {trade.get('close_reason', '').replace('_', ' ').title()}\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        await self.send_message(message)

    async def notify_system_status(self, status: str, message: str):
        """Notifica status do sistema"""
        icons = {
            'started': '🚀',
            'stopped': '🛑',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }

        icon = icons.get(status, '🔔')

        msg = (
            f"{icon} <b>SISTEMA MAVERETTA</b>\n"
            f"\n"
            f"{message}\n"
            f"\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        await self.send_message(msg)

    async def notify_daily_summary(self, stats: Dict[str, Any]):
        """Envia resumo diário"""
        message = (
            f"📊 <b>RESUMO DIÁRIO</b>\n"
            f"\n"
            f"💼 <b>Trades Totais:</b> {stats.get('total_trades', 0)}\n"
            f"🟢 <b>Vitórias:</b> {stats.get('winning_trades', 0)}\n"
            f"🔴 <b>Derrotas:</b> {stats.get('losing_trades', 0)}\n"
            f"🎯 <b>Win Rate:</b> {stats.get('win_rate', 0):.1%}\n"
            f"\n"
            f"💰 <b>Profit Total:</b> ${stats.get('total_profit', 0):.2f}\n"
            f"📈 <b>Melhor Trade:</b> ${stats.get('best_trade', 0):.2f}\n"
            f"📉 <b>Pior Trade:</b> ${stats.get('worst_trade', 0):.2f}\n"
            f"\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        await self.send_message(message)
    
    def setup_voice_commands(self):
        """
        Setup voice command processing
        Integra com o VoiceCommandProcessor
        """
        try:
            from core.notifications.voice_commands import voice_command_processor
            self.voice_processor = voice_command_processor
            logger.info("✅ Voice Commands integrados ao Telegram")
        except Exception as e:
            logger.error(f"❌ Erro ao integrar Voice Commands: {e}")
    
    async def process_voice_command(self, text: str, user_id: str) -> str:
        """
        Processa comando de voz/texto
        
        Args:
            text: Texto do comando
            user_id: ID do usuário
        
        Returns:
            Resposta do comando
        """
        if not self.voice_processor:
            self.setup_voice_commands()
        
        if not self.voice_processor:
            return "❌ Voice Commands não disponível"
        
        try:
            # Processar comando
            action, params = self.voice_processor.process_command(text, user_id)
            
            # Executar comando
            response = self.voice_processor.execute_command(action, params)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao processar voice command: {e}")
            return f"❌ Erro ao processar comando: {str(e)}"
    
    async def handle_telegram_update(self, update: Dict[str, Any]):
        """
        Handle incoming Telegram updates (messages)
        
        Args:
            update: Telegram update object
        """
        try:
            if 'message' in update and 'text' in update['message']:
                text = update['message']['text']
                user_id = str(update['message']['from']['id'])
                chat_id = update['message']['chat']['id']
                
                # Verificar se é comando de voz (não começa com /)
                if not text.startswith('/'):
                    response = await self.process_voice_command(text, user_id)
                    
                    # Enviar resposta
                    await self.send_message(response)
                    
        except Exception as e:
            logger.error(f"Erro ao processar update do Telegram: {e}")


# Instância global
telegram_notifier = TelegramNotifier()