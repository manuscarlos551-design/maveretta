"""
Telegram Commands - Sistema completo de comandos para controle remoto do bot.
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


class TelegramCommands:
    """
    Handler de comandos Telegram.
    Integra com o bot manager para controle remoto.
    """
    
    def __init__(self, bot_manager):
        self.bot_manager = bot_manager
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Inicia o trading bot"""
        await update.message.reply_text("🚀 Iniciando trading bot...")
        
        try:
            result = await self.bot_manager.start_bot()
            
            message = f"""
✅ **Trading bot iniciado com sucesso!**

**Status:**
• Modo: {result.get('mode', 'N/A')}
• Exchanges: {result.get('exchanges_count', 0)}
• Estratégias: {result.get('strategies_count', 0)}
• Agentes AI: {result.get('ai_agents', 0)}

Use /status para ver detalhes.
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao iniciar: {str(e)}")
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stop - Para o trading bot"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Sim, parar", callback_data="stop_confirm"),
                InlineKeyboardButton("❌ Cancelar", callback_data="stop_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ **Tem certeza que deseja parar o trading bot?**\n\n"
            "Isto irá:\n"
            "• Parar abertura de novas posições\n"
            "• Manter posições abertas atuais\n"
            "• Desabilitar estratégias automáticas\n",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Mostra status atual"""
        try:
            status = await self.bot_manager.get_status()
            
            # Status do bot
            status_icon = "🟢" if status['active'] else "🔴"
            mode_icon = "📊" if status['mode'] == 'live' else "🧪"
            
            message = f"""
📊 **Status do Trading Bot**

**Estado:** {status_icon} {'Ativo' if status['active'] else 'Inativo'}
**Modo:** {mode_icon} {status['mode'].upper()}
**Uptime:** {status['uptime']}
**Última Atualização:** {status['last_update']}

**💰 Trading:**
• Trades Abertos: {status['open_trades']}
• Profit Hoje: ${status['profit_today']:.2f} ({status['profit_today_pct']:.2f}%)
• Win Rate: {status['win_rate']:.1f}%

**🔄 Exchanges:**
"""
            
            for exchange, info in status['exchanges'].items():
                connected = "✅" if info['connected'] else "❌"
                message += f"• {exchange.upper()}: {connected} "
                if info['connected']:
                    message += f"(${info['balance']:.2f})"
                message += "\n"
            
            message += f"\n**🤖 Agentes AI:** {status['ai_agents_active']}/{status['ai_agents_total']}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao obter status: {str(e)}")
    
    async def cmd_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /profit - Mostra relatório de lucro"""
        try:
            profit_data = await self.bot_manager.get_profit_report()
            
            total_profit = profit_data['total_profit']
            profit_icon = "🟢" if total_profit >= 0 else "🔴"
            
            message = f"""
💰 **Relatório de Lucro**

**Total:** {profit_icon} ${abs(total_profit):.2f}
**ROI:** {profit_data['roi_pct']:.2f}%
**Win Rate:** {profit_data['win_rate']:.2f}%

**📅 Por Período:**
• Hoje: ${profit_data['today']:.2f}
• Esta Semana: ${profit_data['week']:.2f}
• Este Mês: ${profit_data['month']:.2f}
• Total: ${profit_data['all_time']:.2f}

**📊 Trading:**
• Total Trades: {profit_data['total_trades']}
• Ganhos: {profit_data['winning_trades']} ✅
• Perdas: {profit_data['losing_trades']} ❌
• Avg Win: ${profit_data['avg_win']:.2f}
• Avg Loss: ${profit_data['avg_loss']:.2f}
• Profit Factor: {profit_data['profit_factor']:.2f}

**🏆 Best Trade:** ${profit_data['best_trade']:.2f}
**💔 Worst Trade:** ${profit_data['worst_trade']:.2f}
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao obter relatório: {str(e)}")
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /daily - Resumo diário"""
        try:
            daily = await self.bot_manager.get_daily_summary()
            
            profit_icon = "🟢" if daily['profit'] >= 0 else "🔴"
            
            message = f"""
📅 **Resumo Diário**

**Data:** {daily['date']}
**Profit:** {profit_icon} ${abs(daily['profit']):.2f} ({daily['profit_pct']:.2f}%)
**Trades:** {daily['trades']}
**Win Rate:** {daily['win_rate']:.2f}%
**Volume:** ${daily['volume']:.2f}

**📊 Performance:**
• Melhor Trade: ${daily['best_trade']:.2f} ✅
• Pior Trade: ${daily['worst_trade']:.2f} ❌
• Sharpe Ratio: {daily['sharpe_ratio']:.2f}

**🪙 Top 5 Pares Mais Lucrativos:**
"""
            
            for i, (pair, profit) in enumerate(daily['top_pairs'][:5], 1):
                icon = "🟢" if profit >= 0 else "🔴"
                message += f"{i}. {pair}: {icon} ${abs(profit):.2f}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao obter resumo: {str(e)}")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats - Estatísticas gerais"""
        try:
            stats = await self.bot_manager.get_statistics()
            
            message = f"""
📈 **Estatísticas Gerais**

**💰 Performance:**
• Total Profit: ${stats['total_profit']:.2f}
• ROI: {stats['roi']:.2f}%
• Sharpe Ratio: {stats['sharpe_ratio']:.2f}
• Sortino Ratio: {stats['sortino_ratio']:.2f}
• Max Drawdown: {stats['max_drawdown']:.2f}%
• Recovery Factor: {stats['recovery_factor']:.2f}

**📊 Trading:**
• Total Trades: {stats['total_trades']}
• Win Rate: {stats['win_rate']:.2f}%
• Avg Duration: {stats['avg_duration']}
• Avg Win: ${stats['avg_win']:.2f}
• Avg Loss: ${stats['avg_loss']:.2f}
• Profit Factor: {stats['profit_factor']:.2f}
• Expectancy: ${stats['expectancy']:.2f}

**💵 Exposição:**
• Capital Total: ${stats['total_capital']:.2f}
• Capital Alocado: ${stats['allocated_capital']:.2f}
• Posições Abertas: {stats['open_positions']}
• Exposição Total: ${stats['total_exposure']:.2f}
• Utilização: {stats['utilization_pct']:.1f}%
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao obter estatísticas: {str(e)}")
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /balance - Mostra saldos"""
        try:
            balances = await self.bot_manager.get_balances()
            
            message = "💵 **Saldos por Exchange**\n\n"
            
            total_usdt = 0
            for exchange, balance in balances.items():
                usdt_balance = balance.get('USDT', 0)
                total_usdt += usdt_balance
                
                message += f"**{exchange.upper()}:**\n"
                message += f"• USDT: ${usdt_balance:.2f}\n"
                
                # Mostrar outros ativos significativos
                other_assets = []
                for asset, amount in balance.items():
                    if asset != 'USDT' and asset != 'total' and amount > 0:
                        usd_value = balance.get(f'{asset}_USD', 0)
                        if usd_value > 1:
                            other_assets.append(f"{asset}: {amount:.6f} (${usd_value:.2f})")
                
                if other_assets:
                    for asset_str in other_assets[:3]:  # Max 3 assets por exchange
                        message += f"• {asset_str}\n"
                
                message += "\n"
            
            message += f"**💰 Total USDT:** ${total_usdt:.2f}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao obter saldos: {str(e)}")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /positions - Mostra posições abertas"""
        try:
            positions = await self.bot_manager.get_open_positions()
            
            if not positions:
                await update.message.reply_text("📭 Nenhuma posição aberta no momento.")
                return
            
            message = f"📊 **Posições Abertas** ({len(positions)})\n\n"
            
            for pos in positions:
                pnl_icon = "🟢" if pos['pnl'] >= 0 else "🔴"
                side_icon = "📈" if pos['side'] == 'long' else "📉"
                
                message += f"""
{side_icon} **{pos['symbol']}** {pos['side'].upper()}
• Exchange: {pos['exchange'].upper()}
• Entry: ${pos['entry_price']:.4f}
• Current: ${pos['current_price']:.4f}
• Amount: {pos['amount']:.6f}
• PnL: {pnl_icon} ${abs(pos['pnl']):.2f} ({pos['pnl_pct']:.2f}%)
• SL: ${pos['stop_loss']:.4f} | TP: ${pos['take_profit']:.4f}
• Duration: {pos['duration']}
---
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao obter posições: {str(e)}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Ajuda"""
        message = """
🤖 **Comandos Disponíveis**

**🎮 Controle:**
• /start - Inicia o trading bot
• /stop - Para o trading bot
• /reload - Recarrega configurações
• /emergency - Para tudo IMEDIATAMENTE

**📊 Informações:**
• /status - Status atual do bot
• /profit - Relatório de lucro completo
• /daily - Resumo do dia
• /stats - Estatísticas gerais
• /balance - Saldos nas exchanges
• /positions - Posições abertas
• /performance - Performance por estratégia

**🔧 Trading:**
• /force_enter <symbol> - Força entrada
• /force_exit <symbol> - Força saída
• /close_all - Fecha todas as posições

**⚙️ Configuração:**
• /config - Ver configurações atuais
• /risk - Ajustar parâmetros de risco
• /strategies - Listar/ativar estratégias

**🛟 Ajuda:**
• /help - Mostra esta mensagem
• /support - Informações de suporte

💡 **Dica:** Use os botões inline para ações rápidas!
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_reload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /reload - Recarrega configurações"""
        await update.message.reply_text("🔄 Recarregando configurações...")
        
        try:
            result = await self.bot_manager.reload_config()
            
            message = f"""
✅ **Configurações recarregadas com sucesso!**

**Atualizações:**
• Estratégias: {result.get('strategies_loaded', 0)}
• Exchanges: {result.get('exchanges_reloaded', 0)}
• Agentes AI: {result.get('ai_agents_reloaded', 0)}
• Risk Rules: {result.get('risk_rules_updated', 0)}

O bot continuará rodando com as novas configurações.
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao recarregar: {str(e)}")
    
    async def cmd_force_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /force_entry - Força entrada em posição"""
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso incorreto!**\n\n"
                "**Sintaxe:** /force_entry <symbol>\n"
                "**Exemplo:** /force_entry BTC/USDT",
                parse_mode='Markdown'
            )
            return
        
        symbol = context.args[0].upper()
        
        keyboard = [
            [
                InlineKeyboardButton("📈 LONG", callback_data=f"entry_long_{symbol}"),
                InlineKeyboardButton("📉 SHORT", callback_data=f"entry_short_{symbol}")
            ],
            [InlineKeyboardButton("❌ Cancelar", callback_data="entry_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📊 **Forçar entrada em {symbol}**\n\n"
            f"Escolha o lado da operação:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_force_exit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /force_exit - Força saída de posição"""
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso incorreto!**\n\n"
                "**Sintaxe:** /force_exit <symbol>\n"
                "**Exemplo:** /force_exit BTC/USDT",
                parse_mode='Markdown'
            )
            return
        
        symbol = context.args[0].upper()
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Sim, fechar", callback_data=f"exit_confirm_{symbol}"),
                InlineKeyboardButton("❌ Cancelar", callback_data="exit_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ **Fechar posição em {symbol}?**\n\n"
            f"Esta ação fechará a posição atual no mercado.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_emergency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /emergency - Para tudo imediatamente"""
        keyboard = [
            [
                InlineKeyboardButton("🚨 SIM, PARAR TUDO", callback_data="emergency_confirm"),
                InlineKeyboardButton("❌ Cancelar", callback_data="emergency_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🚨 **PARADA DE EMERGÊNCIA**\n\n"
            "⚠️ **ATENÇÃO:** Esta ação irá:\n"
            "• Parar o bot imediatamente\n"
            "• Fechar TODAS as posições abertas\n"
            "• Cancelar TODAS as ordens pendentes\n"
            "• Desabilitar todas as estratégias\n\n"
            "**Esta ação é irreversível!**\n"
            "Tem certeza absoluta?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
