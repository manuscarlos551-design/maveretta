#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Gateway Authentication Module
Sistema de autenticação e segurança para o gateway
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
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifica se a senha está correta
        
        Args:
            plain_password: Senha em texto plano
            hashed_password: Hash da senha armazenada
            
        Returns:
            bool: True se a senha é válida
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def get_password_hash(self, password: str) -> str:
        """
        Gera hash da senha
        
        Args:
            password: Senha em texto plano
            
        Returns:
            str: Hash da senha
        """
        return pwd_context.hash(password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Cria token JWT de acesso
        
        Args:
            data: Dados para incluir no token
            expires_delta: Tempo de expiração customizado
            
        Returns:
            str: Token JWT
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode, 
                self.secret_key, 
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise
    
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
    
    def authenticate_user(
        self, 
        username: str, 
        password: str,
        user_db: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Autentica usuário
        
        Args:
            username: Nome de usuário
            password: Senha
            user_db: Base de dados de usuários (opcional)
            
        Returns:
            Dict com dados do usuário ou None se falhar
        """
        # User DB padrão (produção deve usar banco de dados real)
        if user_db is None:
            user_db = {
                "admin": {
                    "username": "admin",
                    "hashed_password": self.get_password_hash("admin123"),
                    "roles": ["admin"],
                    "active": True
                },
                "trader": {
                    "username": "trader",
                    "hashed_password": self.get_password_hash("trader123"),
                    "roles": ["trader"],
                    "active": True
                }
            }
        
        user = user_db.get(username)
        
        if not user:
            logger.warning(f"User not found: {username}")
            return None
        
        if not user.get("active"):
            logger.warning(f"User inactive: {username}")
            return None
        
        if not self.verify_password(password, user["hashed_password"]):
            logger.warning(f"Invalid password for user: {username}")
            return None
        
        logger.info(f"✅ User authenticated: {username}")
        return {
            "username": user["username"],
            "roles": user.get("roles", []),
            "active": user.get("active", True)
        }


# Instância global
_auth_manager = None


def get_auth_manager() -> AuthManager:
    """
    Retorna instância singleton do AuthManager
    
    Returns:
        AuthManager: Instância do gerenciador
    """
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


__all__ = ["AuthManager", "get_auth_manager"]
