"""
Validador de configuração do Maveretta.
Identifica configurações faltantes ou inválidas.
"""

import os
from typing import Dict, List, Tuple
from pathlib import Path
from dotenv import load_dotenv


class ConfigValidator:
    """
    Valida configurações do .env e identifica gaps.
    """
    
    CRITICAL_CONFIGS = {
        # Agentes AI
        'IA_ORQUESTRADORA_CLAUDE': 'Agente Orquestrador Claude (CRÍTICO)',
        'IA_RESERVA_G2_HOT_HAIKU': 'Agente G2 Reserva Hot (CRÍTICO)',
        'IA_G1_SCALP_GPT4O': 'Agente G1 Scalping GPT-4o',
        'IA_G2_TENDENCIA_GPT4O': 'Agente G2 Tendência GPT-4o',
        
        # Exchanges
        'BINANCE_API_KEY': 'Binance API Key',
        'BINANCE_API_SECRET': 'Binance API Secret',
        'KUCOIN_API_KEY': 'KuCoin API Key',
        'KUCOIN_API_SECRET': 'KuCoin API Secret',
        'KUCOIN_API_PASSPHRASE': 'KuCoin API Passphrase (CRÍTICO)',
        'BYBIT_API_KEY': 'Bybit API Key',
        'BYBIT_API_SECRET': 'Bybit API Secret',
        'OKX_API_KEY': 'OKX API Key',
        'OKX_API_SECRET': 'OKX API Secret',
        'OKX_API_PASSPHRASE': 'OKX API Passphrase (CRÍTICO)',
        'COINBASE_API_KEY': 'Coinbase API Key',
        'COINBASE_PRIVATE_KEY_PEM': 'Coinbase Private Key',
        
        # Segurança
        'API_SECRET_KEY': 'API Secret Key (CRÍTICO)',
        'JWT_SECRET_KEY': 'JWT Secret Key (CRÍTICO)',
        
        # Notificações
        'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
        'TELEGRAM_CHAT_ID': 'Telegram Chat ID',
    }
    
    OPTIONAL_CONFIGS = {
        'EMAIL_SMTP_SERVER': 'Email SMTP Server',
        'EMAIL_USERNAME': 'Email Username',
        'EMAIL_PASSWORD': 'Email Password',
        'COINGECKO_API_KEY': 'CoinGecko API Key',
        'IA_SENTIMENTO_SENTIAI': 'Sentimento SentiAI',
        'IA_ARBITRAGEM_COINGECKO_BINANCE': 'Arbitragem CoinGecko/Binance',
    }
    
    def __init__(self, env_path: str = '.env'):
        self.env_path = Path(env_path)
        self.config = {}
        self.missing = []
        self.invalid = []
        
        # Carregar .env
        if self.env_path.exists():
            load_dotenv(self.env_path)
            self._load_config()
        else:
            raise FileNotFoundError(f".env não encontrado em {self.env_path}")
    
    def _load_config(self):
        """Carrega configurações do ambiente"""
        for key in list(self.CRITICAL_CONFIGS.keys()) + list(self.OPTIONAL_CONFIGS.keys()):
            self.config[key] = os.getenv(key, '')
    
    def validate(self) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Valida todas as configurações.
        
        Returns:
            (is_valid, report)
        """
        self.missing = []
        self.invalid = []
        
        # Validar configs críticas
        for key, description in self.CRITICAL_CONFIGS.items():
            value = self.config.get(key, '')
            
            if not value or value.strip() == '':
                self.missing.append({
                    'key': key,
                    'description': description,
                    'severity': 'CRITICAL'
                })
            elif not self._validate_format(key, value):
                self.invalid.append({
                    'key': key,
                    'description': description,
                    'reason': 'Formato inválido',
                    'severity': 'CRITICAL'
                })
        
        # Validar configs opcionais
        missing_optional = []
        for key, description in self.OPTIONAL_CONFIGS.items():
            value = self.config.get(key, '')
            
            if not value or value.strip() == '':
                missing_optional.append({
                    'key': key,
                    'description': description,
                    'severity': 'OPTIONAL'
                })
        
        is_valid = len(self.missing) == 0 and len(self.invalid) == 0
        
        report = {
            'missing_critical': self.missing,
            'missing_optional': missing_optional,
            'invalid': self.invalid,
            'total_critical_missing': len(self.missing),
            'total_invalid': len(self.invalid)
        }
        
        return is_valid, report
    
    def _validate_format(self, key: str, value: str) -> bool:
        """Valida formato de valores específicos"""
        # API Keys geralmente começam com prefixos conhecidos
        if 'OPENAI' in key or 'GPT' in key:
            return value.startswith('sk-proj-') or value.startswith('sk-')
        
        if 'CLAUDE' in key or 'ANTHROPIC' in key:
            return value.startswith('sk-ant-')
        
        if 'TELEGRAM_BOT_TOKEN' in key:
            return ':' in value and len(value.split(':')) == 2
        
        if 'TELEGRAM_CHAT_ID' in key:
            return value.isdigit()
        
        # Outros não validamos formato, apenas presença
        return True
    
    def print_report(self, report: Dict):
        """Imprime relatório formatado"""
        print("\n" + "="*60)
        print("📋 RELATÓRIO DE VALIDAÇÃO DE CONFIGURAÇÃO")
        print("="*60 + "\n")
        
        if report['total_critical_missing'] == 0 and report['total_invalid'] == 0:
            print("✅ TODAS AS CONFIGURAÇÕES CRÍTICAS ESTÃO OK!\n")
        else:
            print("❌ PROBLEMAS ENCONTRADOS!\n")
        
        # Configs críticas faltando
        if report['missing_critical']:
            print("🔴 CONFIGURAÇÕES CRÍTICAS FALTANDO:")
            print("-" * 60)
            for item in report['missing_critical']:
                print(f"  ❌ {item['key']}")
                print(f"     Descrição: {item['description']}")
                print()
        
        # Configs inválidas
        if report['invalid']:
            print("⚠️  CONFIGURAÇÕES INVÁLIDAS:")
            print("-" * 60)
            for item in report['invalid']:
                print(f"  ❌ {item['key']}")
                print(f"     Descrição: {item['description']}")
                print(f"     Motivo: {item['reason']}")
                print()
        
        # Configs opcionais faltando
        if report['missing_optional']:
            print("🟡 CONFIGURAÇÕES OPCIONAIS FALTANDO:")
            print("-" * 60)
            for item in report['missing_optional']:
                print(f"  ⚠️  {item['key']}")
                print(f"     Descrição: {item['description']}")
            print()
        
        # Resumo
        print("="*60)
        print("📊 RESUMO:")
        print(f"  • Críticas Faltando: {report['total_critical_missing']}")
        print(f"  • Inválidas: {report['total_invalid']}")
        print(f"  • Opcionais Faltando: {len(report['missing_optional'])}")
        print("="*60 + "\n")
        
        if report['total_critical_missing'] > 0 or report['total_invalid'] > 0:
            print("⚠️  AÇÃO NECESSÁRIA:")
            print("  Execute: python3 scripts/setup_missing_configs.py")
            print("  Para gerar as configurações faltantes.\n")


if __name__ == '__main__':
    # Teste
    validator = ConfigValidator('/app/maveretta/.env')
    is_valid, report = validator.validate()
    validator.print_report(report)
    
    if not is_valid:
        exit(1)
