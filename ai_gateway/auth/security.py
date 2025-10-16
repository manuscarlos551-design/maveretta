#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Gateway Security Module
Componentes de segurança adicionais
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Context para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthManager:
    """
    Gerenciador de autenticação para o AI Gateway
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Inicializa o gerenciador de autenticação
        
        Args:
            secret_key: Chave secreta para JWT (usa env se não fornecida)
        """
        self.secret_key = secret_key or os.getenv(
            "API_SECRET_KEY", 
            "botai_secret_key_2025_production"
        )
        self.algorithm = "HS256"
        self.token_expire_minutes = 30
        
        logger.info("✅ AuthManager initialized")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verifica e decodifica token JWT
        
        Args:
            token: Token JWT para verificar
            
        Returns:
            Dict com payload do token ou None se inválido
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"Invalid token: {e}")
            return None


def get_auth_manager() -> AuthManager:
    """
    Retorna instância singleton do AuthManager
    
    Returns:
        AuthManager: Instância do gerenciador
    """
    return AuthManager()


__all__ = ["AuthManager", "get_auth_manager"]

