# -*- coding: utf-8 -*-
"""
Bot Engine - Motor principal refatorado
Mantém compatibilidade com bot_runner.py existente
"""

import os
import time
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from plugins.base.plugin_interface import IPlugin
from config.settings.config_manager import ConfigManager
from risk.managers.risk_manager import RiskManager


class BotEngine:
    """
    Motor principal do bot com arquitetura modular
    Mantém compatibilidade com implementação existente
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # Componentes principais
        self.risk_manager = None
        self.exchange_manager = None
        self.ai_coordinator = None
        self.strategy_manager = None
        
        # Plugin registry
        self.plugins: Dict[str, IPlugin] = {}
        
        # Estado do engine
        self.running = False
        self.health_server = None
        
        # Inicialização
        self._initialize_components()
        
    def _initialize_components(self):
        """Inicializa componentes principais"""
        try:
            # Risk Manager
            from risk.managers.risk_manager import RiskManager
            self.risk_manager = RiskManager(self.config)
            
            # Exchange Manager - mantém compatibilidade
            from core.exchanges.exchange_manager import ExchangeManager
            self.exchange_manager = ExchangeManager(self.config)
            
            # AI Coordinator - backward compatible
            from ai.orchestrator.ai_coordinator import AICoordinator
            self.ai_coordinator = AICoordinator(self.config)
            
            # Strategy Manager
            from core.strategies.strategy_manager import StrategyManager
            self.strategy_manager = StrategyManager(self.config)
            
            print("[BOT_ENGINE] Componentes inicializados com sucesso")
            
        except Exception as e:
            print(f"[BOT_ENGINE] Erro na inicialização: {e}")
            raise
    
    def register_plugin(self, name: str, plugin: IPlugin):
        """Registra um plugin no sistema"""
        if plugin.initialize(self.config):
            self.plugins[name] = plugin
            print(f"[BOT_ENGINE] Plugin '{name}' registrado")
        else:
            print(f"[BOT_ENGINE] Falha ao registrar plugin '{name}'")
    
    def get_plugin(self, name: str) -> Optional[IPlugin]:
        """Obtém plugin registrado"""
        return self.plugins.get(name)
    
    def start(self):
        """Inicia o motor do bot"""
        print("[BOT_ENGINE] Iniciando motor principal...")
        self.running = True
        
        # Inicia health server se configurado
        if self.config.get('health_server', {}).get('enabled', True):
            self._start_health_server()
        
        # Loop principal - delega para implementação existente
        # Mantém compatibilidade com bot_runner.py
        return True
    
    def stop(self):
        """Para o motor do bot"""
        print("[BOT_ENGINE] Parando motor principal...")
        self.running = False
        
        if self.health_server:
            self._stop_health_server()
    
    def _start_health_server(self):
        """Inicia servidor de health check"""
        try:
            from http.server import BaseHTTPRequestHandler, HTTPServer
            
            class HealthHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/health":
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        self.wfile.write(b"OK")
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, *_):
                    return  # Silencioso
            
            host = self.config.get('health_server', {}).get('host', '0.0.0.0')
            port = self.config.get('health_server', {}).get('port', 8000)
            
            server = HTTPServer((host, port), HealthHandler)
            server.allow_reuse_address = True
            
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            
            self.health_server = server
            print(f"[BOT_ENGINE] Health server iniciado em http://{host}:{port}/health")
            
        except Exception as e:
            print(f"[BOT_ENGINE] Erro ao iniciar health server: {e}")
    
    def _stop_health_server(self):
        """Para servidor de health check"""
        try:
            if self.health_server:
                self.health_server.shutdown()
                self.health_server.server_close()
                self.health_server = None
                print("[BOT_ENGINE] Health server parado")
        except Exception:
            pass
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema"""
        return {
            'engine': {
                'running': self.running,
                'uptime': time.time() - self._start_time if hasattr(self, '_start_time') else 0
            },
            'components': {
                'risk_manager': self.risk_manager is not None,
                'exchange_manager': self.exchange_manager is not None,
                'ai_coordinator': self.ai_coordinator is not None,
                'strategy_manager': self.strategy_manager is not None
            },
            'plugins': list(self.plugins.keys()),
            'config_loaded': bool(self.config)
        }
    
    # Métodos de compatibilidade com implementação existente
    def get_exchange(self):
        """Compatibilidade com código existente"""
        if self.exchange_manager:
            return self.exchange_manager.get_primary_exchange()
        return None
    
    def get_ai_coordinator(self):
        """Compatibilidade com código existente"""
        return self.ai_coordinator
    
    def get_risk_manager(self):
        """Compatibilidade com código existente"""
        return self.risk_manager