#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structured Logging Plugin - Bot AI Trading
Sistema de logs estruturados com integração ao Prometheus
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from .base.plugin_interface import IPlugin

logger = logging.getLogger(__name__)

# Métricas Prometheus
log_counter = Counter('bot_logs_total', 'Total number of log entries', ['level', 'component'])
log_errors = Counter('bot_errors_total', 'Total number of errors', ['component', 'error_type'])
log_processing_time = Histogram('bot_log_processing_seconds', 'Time spent processing logs')
active_components = Gauge('bot_active_components', 'Number of active components logging')

class StructuredLoggingPlugin(IPlugin):
    """
    Plugin de Logging Estruturado com métricas
    """
    
    def __init__(self):
        """Inicializa o plugin de logging"""
        self.name = "StructuredLoggingPlugin"
        self.version = "1.0.0"
        self.description = "Sistema de logs estruturados com métricas Prometheus"
        self.enabled = True
        self.structlog_configured = False
        self.log_level = "INFO"
        self.log_format = "json"
        self.components = set()
        
        logger.info(f"📝 {self.name} v{self.version} initialized")
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informações do plugin"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "type": "observability",
            "dependencies": ["structlog", "prometheus-client"],
            "config": {
                "log_level": self.log_level,
                "log_format": self.log_format,
                "metrics_enabled": True
            }
        }
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Inicializa o sistema de logging estruturado"""
        
        try:
            # Configuração padrão
            default_config = {
                "log_level": "INFO",
                "log_format": "json",  # json, console, dev
                "log_file": "/app/logs/bot_structured.log",
                "metrics_enabled": True,
                "console_output": True,
                "file_output": True
            }
            
            if config:
                default_config.update(config)
            
            self.config = default_config
            self.log_level = default_config["log_level"]
            self.log_format = default_config["log_format"]
            
            # Configurar structlog
            self._configure_structlog()
            
            # Configurar handlers tradicionais do Python
            self._configure_python_logging()
            
            logger.info("✅ Structured logging system initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing structured logging: {e}")
            return False
    
    def _configure_structlog(self):
        """Configura structlog com processadores personalizados"""
        
        try:
            # Processadores básicos
            processors = [
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                self._add_timestamp,
                self._add_component_info,
                self._metrics_processor,
            ]
            
            # Processador final baseado no formato
            if self.log_format == "json":
                processors.append(structlog.processors.JSONRenderer())
            elif self.log_format == "console":
                processors.append(structlog.dev.ConsoleRenderer(colors=True))
            else:  # dev format
                processors.append(
                    structlog.dev.ConsoleRenderer(
                        colors=True,
                        exception_formatter=structlog.dev.plain_traceback,
                    )
                )
            
            # Configurar structlog
            structlog.configure(
                processors=processors,
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            
            self.structlog_configured = True
            logger.info("✅ Structlog configured successfully")
            
        except Exception as e:
            logger.error(f"Error configuring structlog: {e}")
    
    def _configure_python_logging(self):
        """Configura logging tradicional do Python"""
        
        try:
            # Configurar nível
            logging.getLogger().setLevel(getattr(logging, self.log_level.upper()))
            
            # Handler para arquivo
            if self.config.get("file_output", True):
                os.makedirs(os.path.dirname(self.config["log_file"]), exist_ok=True)
                file_handler = logging.FileHandler(self.config["log_file"])
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logging.getLogger().addHandler(file_handler)
            
            # Handler para console
            if self.config.get("console_output", True):
                console_handler = logging.StreamHandler()
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
                logging.getLogger().addHandler(console_handler)
            
        except Exception as e:
            logger.error(f"Error configuring Python logging: {e}")
    
    def _add_timestamp(self, _, __, event_dict):
        """Adiciona timestamp ISO aos logs"""
        event_dict["timestamp"] = datetime.now().isoformat()
        return event_dict
    
    def _add_component_info(self, _, __, event_dict):
        """Adiciona informações do componente"""
        # Tentar identificar o componente pelo nome do logger
        logger_name = event_dict.get("logger", "unknown")
        component = self._extract_component_name(logger_name)
        event_dict["component"] = component
        
        # Rastrear componentes ativos
        self.components.add(component)
        active_components.set(len(self.components))
        
        return event_dict
    
    def _metrics_processor(self, _, method_name, event_dict):
        """Processa métricas dos logs"""
        
        try:
            if self.config.get("metrics_enabled", True):
                level = method_name.upper()
                component = event_dict.get("component", "unknown")
                
                # Contar logs por nível e componente
                log_counter.labels(level=level, component=component).inc()
                
                # Contar erros específicos
                if level in ["ERROR", "CRITICAL"]:
                    error_type = event_dict.get("error_type", "generic")
                    log_errors.labels(component=component, error_type=error_type).inc()
            
        except Exception as e:
            # Não falhar o processamento de log por erro de métricas
            pass
        
        return event_dict
    
    def _extract_component_name(self, logger_name: str) -> str:
        """Extrai nome do componente do logger"""
        
        # Mapear nomes de logger para componentes
        component_map = {
            "bot_runner": "bot_engine",
            "interfaces.api": "api",
            "core.engine": "bot_engine", 
            "ai.orchestrator": "ai_system",
            "backtest": "backtest_engine",
            "ml": "ml_system",
            "plugins": "plugin_system"
        }
        
        for key, component in component_map.items():
            if key in logger_name:
                return component
        
        return logger_name.split('.')[0] if '.' in logger_name else logger_name
    
    def get_structured_logger(self, component_name: str):
        """Retorna logger estruturado para um componente"""
        
        if not self.structlog_configured:
            logger.warning("Structlog not configured, returning standard logger")
            return logging.getLogger(component_name)
        
        # Criar logger estruturado com contexto
        struct_logger = structlog.get_logger(component_name)
        return struct_logger.bind(component=component_name)
    
    def log_trading_event(self, event_type: str, symbol: str, data: Dict[str, Any]):
        """Log especializado para eventos de trading"""
        
        trading_logger = self.get_structured_logger("trading")
        trading_logger.info(
            "Trading event occurred",
            event_type=event_type,
            symbol=symbol,
            trading_data=data,
            category="trading"
        )
    
    def log_api_request(self, method: str, endpoint: str, status_code: int, 
                       duration: float, user: str = None):
        """Log especializado para requests API"""
        
        api_logger = self.get_structured_logger("api")
        api_logger.info(
            "API request processed",
            http_method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration * 1000,
            user=user,
            category="api"
        )
    
    def log_system_metric(self, metric_name: str, value: float, unit: str = None):
        """Log para métricas do sistema"""
        
        metrics_logger = self.get_structured_logger("metrics")
        metrics_logger.info(
            "System metric recorded",
            metric_name=metric_name,
            value=value,
            unit=unit,
            category="metrics"
        )
    
    def get_log_metrics(self) -> str:
        """Retorna métricas em formato Prometheus"""
        
        try:
            return generate_latest().decode('utf-8')
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return ""
    
    def get_component_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos componentes"""
        
        return {
            "active_components": list(self.components),
            "total_components": len(self.components),
            "log_level": self.log_level,
            "log_format": self.log_format,
            "metrics_enabled": self.config.get("metrics_enabled", True)
        }
    
    def execute(self) -> Dict[str, Any]:
        """Executa verificações do sistema de logging"""
        
        try:
            status = {
                "plugin": self.name,
                "timestamp": datetime.now().isoformat(),
                "structlog_configured": self.structlog_configured,
                "log_level": self.log_level,
                "log_format": self.log_format,
                "components": self.get_component_stats()
            }
            
            # Verificar se arquivo de log existe
            log_file = self.config.get("log_file")
            if log_file and os.path.exists(log_file):
                stat_info = os.stat(log_file)
                status["log_file"] = {
                    "path": log_file,
                    "size_bytes": stat_info.st_size,
                    "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                }
            
            # Testar logging
            test_logger = self.get_structured_logger("logging_plugin")
            test_logger.info("Logging system health check", test=True)
            
            return status
            
        except Exception as e:
            logger.error(f"Error executing logging checks: {e}")
            return {
                "plugin": self.name,
                "status": "error", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def shutdown(self) -> bool:
        """Shutdown do plugin"""
        
        try:
            # Log final
            if self.structlog_configured:
                final_logger = self.get_structured_logger("system")
                final_logger.info("Logging system shutting down")
            
            logger.info(f"🛑 {self.name} shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False

# Instância global do plugin
structured_logging_plugin = StructuredLoggingPlugin()

# Utilitários de conveniência
def setup_structured_logging(config: Optional[Dict[str, Any]] = None):
    """Setup rápido de logging estruturado"""
    return structured_logging_plugin.initialize(config)

def get_logger(component: str):
    """Retorna logger estruturado para componente"""
    return structured_logging_plugin.get_structured_logger(component)

def log_trading_event(event_type: str, symbol: str, data: Dict[str, Any]):
    """Log de evento de trading"""
    structured_logging_plugin.log_trading_event(event_type, symbol, data)

def log_api_request(method: str, endpoint: str, status_code: int, duration: float, user: str = None):
    """Log de request API"""
    structured_logging_plugin.log_api_request(method, endpoint, status_code, duration, user)