#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface base para plugins do sistema
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class IPlugin(ABC):
    """
    Interface base para todos os plugins do sistema
    
    Todos os plugins devem herdar desta classe e implementar
    os métodos abstratos necessários.
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        """
        Inicializa o plugin
        
        Args:
            name: Nome do plugin
            version: Versão do plugin
        """
        self.name = name
        self.version = version
        self.enabled = False
        self.config = {}
        self.logger = logging.getLogger(f"plugin.{name}")
    
    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Inicializa o plugin com configuração
        
        Args:
            config: Configuração do plugin
            
        Returns:
            True se inicializado com sucesso
        """
        pass
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Executa a funcionalidade principal do plugin
        
        Returns:
            Resultado da execução
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Finaliza o plugin e limpa recursos
        
        Returns:
            True se finalizado com sucesso
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Retorna informações do plugin
        
        Returns:
            Dict com informações do plugin
        """
        return {
            'name': self.name,
            'version': self.version,
            'enabled': self.enabled,
            'type': self.__class__.__name__
        }
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """
        Define configuração do plugin
        
        Args:
            config: Nova configuração
        """
        self.config = config
        self.logger.info(f"Configuration updated for plugin {self.name}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Retorna configuração atual do plugin
        
        Returns:
            Configuração atual
        """
        return self.config.copy()
    
    def enable(self) -> bool:
        """
        Habilita o plugin
        
        Returns:
            True se habilitado com sucesso
        """
        try:
            self.enabled = True
            self.logger.info(f"Plugin {self.name} enabled")
            return True
        except Exception as e:
            self.logger.error(f"Error enabling plugin {self.name}: {e}")
            return False
    
    def disable(self) -> bool:
        """
        Desabilita o plugin
        
        Returns:
            True se desabilitado com sucesso
        """
        try:
            self.enabled = False
            self.logger.info(f"Plugin {self.name} disabled")
            return True
        except Exception as e:
            self.logger.error(f"Error disabling plugin {self.name}: {e}")
            return False
    
    def is_enabled(self) -> bool:
        """
        Verifica se plugin está habilitado
        
        Returns:
            True se habilitado
        """
        return self.enabled


class PluginBase(IPlugin):
    """
    Classe base concreta para plugins simples
    
    Fornece implementação padrão para casos básicos
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        self._initialized = False
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Implementação padrão de inicialização
        """
        try:
            if config:
                self.set_config(config)
            
            self._initialized = True
            self.enable()
            self.logger.info(f"Plugin {self.name} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing plugin {self.name}: {e}")
            return False
    
    def execute(self, *args, **kwargs) -> Any:
        """
        Implementação padrão (vazia) de execução
        """
        if not self._initialized or not self.enabled:
            self.logger.warning(f"Plugin {self.name} not initialized or disabled")
            return None
        
        self.logger.info(f"Executing plugin {self.name}")
        return {"status": "executed", "plugin": self.name}
    
    def shutdown(self) -> bool:
        """
        Implementação padrão de finalização
        """
        try:
            self.disable()
            self._initialized = False
            self.logger.info(f"Plugin {self.name} shut down successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error shutting down plugin {self.name}: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """
        Verifica se plugin foi inicializado
        
        Returns:
            True se inicializado
        """
        return self._initialized