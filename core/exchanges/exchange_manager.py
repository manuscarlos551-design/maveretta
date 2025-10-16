# -*- coding: utf-8 -*-
"""
Exchange Manager Refatorado - Mantém compatibilidade
Integra com exchange_manager.py existente
"""

import os
import ccxt
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Import do sistema existente para compatibilidade
try:
    from exchange_manager import ExchangeManager as LegacyExchangeManager
except ImportError:
    LegacyExchangeManager = None

load_dotenv()


class ExchangeManager:
    """
    Gerenciador de exchanges modular
    Mantém compatibilidade com sistema existente
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.primary_exchange = None
        self.backup_exchanges = []
        self.exchange_configs = {}
        
        # Usa sistema existente se disponível
        self.legacy_manager = None
        if LegacyExchangeManager:
            try:
                self.legacy_manager = LegacyExchangeManager()
                print("[EXCHANGE_MANAGER] Sistema legado integrado")
            except Exception as e:
                print(f"[EXCHANGE_MANAGER] Erro ao integrar sistema legado: {e}")
        
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Inicializa exchanges configuradas"""
        try:
            # Usa exchange do sistema legado se disponível
            if self.legacy_manager:
                self.primary_exchange = self.legacy_manager.get_exchange()
                print(f"[EXCHANGE_MANAGER] Exchange principal: {self.legacy_manager.get_exchange_name()}")
                return
            
            # Fallback: inicialização própria
            exchange_name = os.getenv("EXCHANGE", "binance").lower()
            self.primary_exchange = self._create_exchange(exchange_name)
            print(f"[EXCHANGE_MANAGER] Exchange principal criada: {exchange_name}")
            
        except Exception as e:
            print(f"[EXCHANGE_MANAGER] Erro na inicialização: {e}")
            raise
    
    def _create_exchange(self, exchange_name: str) -> ccxt.Exchange:
        """Cria instância de exchange"""
        if exchange_name == "binance":
            return self._create_binance()
        else:
            raise NotImplementedError(f"Exchange {exchange_name} não suportada ainda")
    
    def _create_binance(self) -> ccxt.binance:
        """Cria instância Binance"""
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        
        if not api_key or not api_secret:
            raise RuntimeError("Credenciais Binance não encontradas")
        
        exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "timeout": int(os.getenv("BINANCE_HTTP_TIMEOUT_MS", "20000")),
            "options": {
                "adjustForTimeDifference": True,
                "recvWindow": 20000,
                "defaultType": "spot",
            },
        })
        
        # Validação
        try:
            exchange.load_time_difference()
            exchange.fetch_time()
        except Exception as e:
            raise RuntimeError(f"Erro ao conectar com Binance: {e}")
        
        return exchange
    
    def get_primary_exchange(self) -> Optional[ccxt.Exchange]:
        """Retorna exchange principal"""
        return self.primary_exchange
    
    def get_exchange_name(self) -> str:
        """Retorna nome da exchange principal"""
        if self.legacy_manager:
            return self.legacy_manager.get_exchange_name()
        return "binance"
    
    def add_backup_exchange(self, exchange_name: str, credentials: Dict[str, str]):
        """Adiciona exchange de backup"""
        try:
            backup_exchange = self._create_exchange_with_credentials(exchange_name, credentials)
            self.backup_exchanges.append({
                'name': exchange_name,
                'exchange': backup_exchange
            })
            print(f"[EXCHANGE_MANAGER] Exchange de backup adicionada: {exchange_name}")
        except Exception as e:
            print(f"[EXCHANGE_MANAGER] Erro ao adicionar backup {exchange_name}: {e}")
    
    def _create_exchange_with_credentials(self, name: str, credentials: Dict[str, str]) -> ccxt.Exchange:
        """Cria exchange com credenciais específicas"""
        # Implementação futura para múltiplas exchanges
        raise NotImplementedError("Múltiplas exchanges em desenvolvimento")
    
    def execute_with_failover(self, operation, *args, **kwargs):
        """Executa operação com failover automático"""
        exchanges_to_try = [self.primary_exchange] + [b['exchange'] for b in self.backup_exchanges]
        
        for exchange in exchanges_to_try:
            if not exchange:
                continue
            
            try:
                return operation(exchange, *args, **kwargs)
            except Exception as e:
                print(f"[EXCHANGE_MANAGER] Falha em {exchange.name}: {e}")
                continue
        
        raise Exception("Todas as exchanges falharam")
    
    def test_connection(self) -> Dict[str, Any]:
        """Testa conexão com exchange principal"""
        try:
            if self.legacy_manager:
                return self.legacy_manager.test_connection()
            
            # Teste próprio
            balance = self.primary_exchange.fetch_balance()
            return {
                "success": True,
                "exchange": self.get_exchange_name(),
                "message": "Conexão estabelecida com sucesso"
            }
        except Exception as e:
            return {
                "success": False,
                "exchange": self.get_exchange_name(),
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status das exchanges"""
        return {
            'primary': {
                'name': self.get_exchange_name(),
                'connected': self.primary_exchange is not None,
                'legacy_integration': self.legacy_manager is not None
            },
            'backups': [
                {
                    'name': backup['name'],
                    'connected': backup['exchange'] is not None
                }
                for backup in self.backup_exchanges
            ]
        }


# Função de compatibilidade para código existente
def get_exchange():
    """Função global de compatibilidade"""
    try:
        # Primeiro tenta sistema legado
        if LegacyExchangeManager:
            manager = LegacyExchangeManager()
            return manager.get_exchange()
    except Exception:
        pass
    
    # Fallback
    manager = ExchangeManager({})
    return manager.get_primary_exchange()


def get_exchange_manager():
    """Função global de compatibilidade"""
    try:
        if LegacyExchangeManager:
            return LegacyExchangeManager()
    except Exception:
        pass
    
    return ExchangeManager({})