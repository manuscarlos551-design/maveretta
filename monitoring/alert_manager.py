#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alert Manager - Etapa 7
Sistema de alertas multi-canal (Telegram, Email, SMS, Webhook)
"""

import os
import sys
import json
import time
import requests
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Adiciona path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class AlertManager:
    """
    Gerenciador de alertas multi-canal
    Suporta Telegram, Email, SMS, Webhook integrations
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Configurações de alertas
        self.alert_config = self._load_alert_config()
        
        # Histórico de alertas enviados (para evitar spam)
        self.sent_alerts = {}
        self.cooldown_period = 300  # 5 minutos entre alertas do mesmo tipo
        
    def setup_logging(self):
        """Configura logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_alert_config(self) -> Dict[str, Any]:
        """Carrega configurações de alerta do .env"""
        
        config = {
            'telegram': {
                'enabled': os.getenv('TELEGRAM_BOT_TOKEN') is not None,
                'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
                'chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
                'timeout': int(os.getenv('TELEGRAM_TIMEOUT', 10))
            },
            'discord': {
                'enabled': os.getenv('DISCORD_WEBHOOK_URL') is not None,
                'webhook_url': os.getenv('DISCORD_WEBHOOK_URL', ''),
                'username': os.getenv('DISCORD_BOT_USERNAME', 'Maveretta Bot'),
                'timeout': int(os.getenv('DISCORD_TIMEOUT', 10))
            },
            'email': {
                'enabled': False,  # Não configurado no .env atual
                'smtp_server': os.getenv('EMAIL_SMTP_SERVER', ''),
                'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', 587)),
                'username': os.getenv('EMAIL_USERNAME', ''),
                'password': os.getenv('EMAIL_PASSWORD', ''),
                'from_email': os.getenv('EMAIL_FROM', ''),
                'to_emails': os.getenv('EMAIL_TO', '').split(',') if os.getenv('EMAIL_TO') else []
            },
            'webhook': {
                'enabled': False,  # Configuração personalizada
                'urls': []
            },
            'general': {
                'max_retries': int(os.getenv('NOTIFICATIONS_MAX_RETRIES', 2)),
                'timeout': int(os.getenv('NOTIFICATIONS_TIMEOUT', 30)),
                'enabled': os.getenv('NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
            }
        }
        
        return config
    
    def send_alert(self, alert_type: str, severity: str, message: str, 
                  additional_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Envia alerta através de todos os canais configurados
        
        Args:
            alert_type: Tipo do alerta (system, trading, etc.)
            severity: Severidade (info, warning, critical)
            message: Mensagem do alerta
            additional_data: Dados adicionais opcionais
        """
        
        if not self.alert_config['general']['enabled']:
            self.logger.info("Alerts disabled - skipping")
            return {'status': 'disabled'}
        
        # Verifica cooldown
        if self._is_in_cooldown(alert_type, severity):
            self.logger.info(f"Alert {alert_type} in cooldown - skipping")
            return {'status': 'cooldown'}
        
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type,
            'severity': severity,
            'message': message,
            'additional_data': additional_data or {}
        }
        
        results = {}
        
        # Telegram
        if self.alert_config['telegram']['enabled']:
            results['telegram'] = self._send_telegram_alert(alert_data)
        
        # Discord
        if self.alert_config['discord']['enabled']:
            results['discord'] = self._send_discord_alert(alert_data)
        
        # Email
        if self.alert_config['email']['enabled']:
            results['email'] = self._send_email_alert(alert_data)
        
        # Webhook
        if self.alert_config['webhook']['enabled']:
            results['webhook'] = self._send_webhook_alert(alert_data)
        
        # Registra alerta enviado
        self._record_sent_alert(alert_type, severity)
        
        # Log do resultado
        successful_channels = [channel for channel, result in results.items() 
                             if result.get('status') == 'success']
        
        self.logger.info(f"Alert sent via {len(successful_channels)} channels: {successful_channels}")
        
        return {
            'status': 'sent' if successful_channels else 'failed',
            'channels': results,
            'successful_channels': successful_channels
        }
    
    def _is_in_cooldown(self, alert_type: str, severity: str) -> bool:
        """Verifica se alerta está em cooldown"""
        
        # Alertas críticos sempre passam
        if severity == 'critical':
            return False
        
        key = f"{alert_type}_{severity}"
        if key in self.sent_alerts:
            last_sent = self.sent_alerts[key]
            time_diff = (datetime.now() - last_sent).total_seconds()
            return time_diff < self.cooldown_period
        
        return False
    
    def _record_sent_alert(self, alert_type: str, severity: str):
        """Registra alerta enviado para controle de cooldown"""
        key = f"{alert_type}_{severity}"
        self.sent_alerts[key] = datetime.now()
    
    def _send_telegram_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia alerta via Telegram"""
        
        try:
            bot_token = self.alert_config['telegram']['bot_token']
            chat_id = self.alert_config['telegram']['chat_id']
            timeout = self.alert_config['telegram']['timeout']
            
            if not bot_token or not chat_id:
                return {'status': 'error', 'error': 'Telegram not configured'}
            
            # Formata mensagem
            severity_emoji = {
                'info': '📊',
                'warning': '⚠️',
                'critical': '🚨'
            }
            
            emoji = severity_emoji.get(alert_data['severity'], '📢')
            
            message = f"{emoji} *{alert_data['severity'].upper()} ALERT*\n\n"
            message += f"*Type:* {alert_data['alert_type']}\n"
            message += f"*Time:* {alert_data['timestamp']}\n"
            message += f"*Message:* {alert_data['message']}\n"
            
            # Adiciona dados extras se disponíveis
            if alert_data['additional_data']:
                message += "\n*Additional Data:*\n"
                for key, value in alert_data['additional_data'].items():
                    message += f"• {key}: {value}\n"
            
            # Envia mensagem
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                return {'status': 'success', 'response': response.json()}
            else:
                return {'status': 'error', 'error': f'HTTP {response.status_code}', 'response': response.text}
        
        except Exception as e:
            self.logger.error(f"Error sending Telegram alert: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _send_discord_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia alerta via Discord"""
        
        try:
            webhook_url = self.alert_config['discord']['webhook_url']
            username = self.alert_config['discord']['username']
            timeout = self.alert_config['discord']['timeout']
            
            if not webhook_url:
                return {'status': 'error', 'error': 'Discord not configured'}
            
            # Cores baseadas na severidade
            color_map = {
                'info': 0x3498db,      # Azul
                'warning': 0xf39c12,   # Laranja
                'critical': 0xe74c3c   # Vermelho
            }
            
            color = color_map.get(alert_data['severity'], 0x95a5a6)
            
            # Cria embed
            embed = {
                'title': f"{alert_data['severity'].upper()} Alert",
                'description': alert_data['message'],
                'color': color,
                'timestamp': alert_data['timestamp'],
                'fields': [
                    {
                        'name': 'Alert Type',
                        'value': alert_data['alert_type'],
                        'inline': True
                    }
                ]
            }
            
            # Adiciona campos extras
            if alert_data['additional_data']:
                for key, value in alert_data['additional_data'].items():
                    embed['fields'].append({
                        'name': key.replace('_', ' ').title(),
                        'value': str(value),
                        'inline': True
                    })
            
            payload = {
                'username': username,
                'embeds': [embed]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=timeout)
            
            if response.status_code in [200, 204]:
                return {'status': 'success'}
            else:
                return {'status': 'error', 'error': f'HTTP {response.status_code}'}
        
        except Exception as e:
            self.logger.error(f"Error sending Discord alert: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _send_email_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia alerta via Email"""
        
        try:
            email_config = self.alert_config['email']
            
            if not all([email_config['smtp_server'], email_config['username'], 
                       email_config['password'], email_config['from_email']]):
                return {'status': 'error', 'error': 'Email not configured'}
            
            # Cria mensagem
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = f"[{alert_data['severity'].upper()}] Trading Bot Alert - {alert_data['alert_type']}"
            
            # Corpo do email
            body = f"""
Alert Details:
- Type: {alert_data['alert_type']}
- Severity: {alert_data['severity'].upper()}
- Time: {alert_data['timestamp']}
- Message: {alert_data['message']}
            """
            
            if alert_data['additional_data']:
                body += "\nAdditional Data:\n"
                for key, value in alert_data['additional_data'].items():
                    body += f"- {key}: {value}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Envia email
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            text = msg.as_string()
            server.sendmail(email_config['from_email'], email_config['to_emails'], text)
            server.quit()
            
            return {'status': 'success'}
        
        except Exception as e:
            self.logger.error(f"Error sending email alert: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _send_webhook_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia alerta via Webhook customizado"""
        
        try:
            webhook_urls = self.alert_config['webhook']['urls']
            
            if not webhook_urls:
                return {'status': 'error', 'error': 'No webhook URLs configured'}
            
            results = []
            
            for url in webhook_urls:
                try:
                    response = requests.post(url, json=alert_data, timeout=10)
                    
                    if response.status_code in [200, 201, 202]:
                        results.append({'url': url, 'status': 'success'})
                    else:
                        results.append({'url': url, 'status': 'error', 'error': f'HTTP {response.status_code}'})
                
                except Exception as e:
                    results.append({'url': url, 'status': 'error', 'error': str(e)})
            
            successful = sum(1 for r in results if r['status'] == 'success')
            
            return {
                'status': 'success' if successful > 0 else 'error',
                'results': results,
                'successful_count': successful
            }
        
        except Exception as e:
            self.logger.error(f"Error sending webhook alerts: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def test_all_channels(self) -> Dict[str, Any]:
        """Testa todos os canais de alerta configurados"""
        
        test_results = {}
        
        test_alert = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': 'system_test',
            'severity': 'info',
            'message': 'Test alert - all systems functioning normally',
            'additional_data': {
                'test_id': int(time.time()),
                'source': 'AlertManager test function'
            }
        }
        
        # Testa cada canal
        if self.alert_config['telegram']['enabled']:
            test_results['telegram'] = self._send_telegram_alert(test_alert)
        
        if self.alert_config['discord']['enabled']:
            test_results['discord'] = self._send_discord_alert(test_alert)
        
        if self.alert_config['email']['enabled']:
            test_results['email'] = self._send_email_alert(test_alert)
        
        if self.alert_config['webhook']['enabled']:
            test_results['webhook'] = self._send_webhook_alert(test_alert)
        
        # Sumário
        successful = [channel for channel, result in test_results.items() 
                     if result.get('status') == 'success']
        
        return {
            'test_timestamp': test_alert['timestamp'],
            'channels_tested': list(test_results.keys()),
            'successful_channels': successful,
            'failed_channels': [channel for channel in test_results.keys() 
                              if channel not in successful],
            'results': test_results
        }
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de alertas"""
        
        return {
            'configured_channels': {
                'telegram': self.alert_config['telegram']['enabled'],
                'discord': self.alert_config['discord']['enabled'],
                'email': self.alert_config['email']['enabled'],
                'webhook': self.alert_config['webhook']['enabled']
            },
            'alerts_in_cooldown': len(self.sent_alerts),
            'cooldown_period_seconds': self.cooldown_period,
            'last_alerts': dict(self.sent_alerts),
            'general_config': self.alert_config['general']
        }

def main():
    """Função principal para demonstração"""
    print("🚨 Alert Manager - Etapa 7")
    print("=" * 60)
    
    # Inicializa alert manager
    alert_manager = AlertManager()
    
    # Mostra configurações
    stats = alert_manager.get_alert_statistics()
    print(f"\n📋 Canais Configurados:")
    for channel, enabled in stats['configured_channels'].items():
        status = "✅ Enabled" if enabled else "❌ Disabled"
        print(f"   {channel.title()}: {status}")
    
    # Testa alertas se algum canal estiver configurado
    enabled_channels = [channel for channel, enabled in stats['configured_channels'].items() if enabled]
    
    if enabled_channels:
        print(f"\n🧪 Testando {len(enabled_channels)} canais configurados...")
        
        # Alerta de teste
        test_result = alert_manager.send_alert(
            'system_test',
            'info', 
            'Test alert from Alert Manager - all systems functioning normally',
            {'test_timestamp': datetime.now().isoformat(), 'version': '1.0.0'}
        )
        
        print(f"📤 Status do teste: {test_result['status']}")
        if test_result.get('successful_channels'):
            print(f"✅ Canais com sucesso: {test_result['successful_channels']}")
        
        # Teste completo de todos os canais
        print(f"\n🔍 Executando teste completo...")
        complete_test = alert_manager.test_all_channels()
        
        print(f"📊 Resultados do teste completo:")
        print(f"   Testados: {len(complete_test['channels_tested'])}")
        print(f"   Sucessos: {len(complete_test['successful_channels'])}")
        print(f"   Falhas: {len(complete_test['failed_channels'])}")
        
    else:
        print("\n⚠️  Nenhum canal de alerta configurado")
        print("   Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env para ativar alertas")

if __name__ == "__main__":
    main()