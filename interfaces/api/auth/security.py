#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication & Security - Bot AI Multi-Agente API
Etapa 6: Sistema de autenticação e segurança para API
"""

import os
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

try:
    from passlib.context import CryptContext
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False
    logging.warning("Passlib not available - install: pip install passlib[bcrypt]")

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Gerenciador de autenticação e segurança
    
    Funcionalidades:
    - JWT token generation/validation
    - API key management
    - Rate limiting (básico)
    - Password hashing (se passlib disponível)
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Inicializar Auth Manager
        
        Args:
            secret_key: Chave secreta para JWT (usa .env se não fornecida)
        """
        
        self.secret_key = secret_key or os.getenv('API_SECRET_KEY', 'default_secret_key_change_in_production')
        self.algorithm = 'HS256'
        self.token_expire_hours = 24
        
        # Password hashing context
        if PASSLIB_AVAILABLE:
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        else:
            self.pwd_context = None
            logger.warning("Password hashing not available - using simple hash")
        
        # API keys válidas (em produção, usar banco de dados)
        self.valid_api_keys = {
            'demo_key_123': {
                'name': 'Demo API Key',
                'permissions': ['read', 'backtest'],
                'rate_limit': 100,
                'created_at': datetime.now()
            }
        }
        
        # Rate limiting storage (em produção, usar Redis)
        self.rate_limit_storage = {}
        
        logger.info("🔐 Auth Manager inicializado")
    
    def hash_password(self, password: str) -> str:
        """Hash de senha"""
        
        if self.pwd_context:
            return self.pwd_context.hash(password)
        else:
            # Fallback simples (não usar em produção)
            return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar senha"""
        
        if self.pwd_context:
            return self.pwd_context.verify(plain_password, hashed_password)
        else:
            # Fallback simples
            return self.hash_password(plain_password) == hashed_password
    
    def create_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """
        Criar JWT token
        
        Args:
            user_data: Dados do usuário para incluir no token
            
        Returns:
            JWT token string
        """
        
        try:
            # Payload do token
            payload = {
                'user_id': user_data.get('user_id', 'anonymous'),
                'username': user_data.get('username', 'anonymous'),
                'permissions': user_data.get('permissions', ['read']),
                'exp': datetime.utcnow() + timedelta(hours=self.token_expire_hours),
                'iat': datetime.utcnow(),
                'iss': 'bot-ai-multi-agent'
            }
            
            # Gerar token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"JWT token criado para usuário: {payload['username']}")
            return token
            
        except Exception as e:
            logger.error(f"Erro ao criar JWT token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verificar e decodificar JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Payload decodificado ou None se inválido
        """
        
        try:
            # Decodificar token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verificar expiração
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                logger.warning("Token expirado")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao verificar token: {e}")
            return None
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Verificar API key
        
        Args:
            api_key: API key string
            
        Returns:
            Dados da API key ou None se inválida
        """
        
        if api_key in self.valid_api_keys:
            key_data = self.valid_api_keys[api_key].copy()
            
            # Rate limiting check
            if self.check_rate_limit(api_key):
                return key_data
            else:
                logger.warning(f"Rate limit excedido para API key: {api_key[:8]}...")
                return None
        
        logger.warning(f"API key inválida: {api_key[:8]}...")
        return None
    
    def check_rate_limit(self, identifier: str, limit: int = 100) -> bool:
        """
        Verificar rate limit
        
        Args:
            identifier: Identificador (API key, IP, user_id)
            limit: Limite de requests por minuto
            
        Returns:
            True se dentro do limite
        """
        
        now = datetime.now()
        minute_key = now.strftime('%Y%m%d%H%M')
        
        # Limpar dados antigos (mais de 2 minutos)
        old_keys = [
            key for key in self.rate_limit_storage.keys()
            if key.startswith(identifier) and key != f"{identifier}_{minute_key}"
        ]
        for key in old_keys:
            del self.rate_limit_storage[key]
        
        # Verificar limite atual
        current_key = f"{identifier}_{minute_key}"
        current_count = self.rate_limit_storage.get(current_key, 0)
        
        if current_count >= limit:
            return False
        
        # Incrementar contador
        self.rate_limit_storage[current_key] = current_count + 1
        return True
    
    def add_api_key(self, key: str, name: str, permissions: list = None) -> Dict[str, Any]:
        """
        Adicionar nova API key
        
        Args:
            key: API key string
            name: Nome da key
            permissions: Lista de permissões
            
        Returns:
            Dados da API key criada
        """
        
        permissions = permissions or ['read']
        
        key_data = {
            'name': name,
            'permissions': permissions,
            'rate_limit': 100,
            'created_at': datetime.now()
        }
        
        self.valid_api_keys[key] = key_data
        
        logger.info(f"Nova API key adicionada: {name}")
        return key_data
    
    def revoke_api_key(self, key: str) -> bool:
        """
        Revogar API key
        
        Args:
            key: API key para revogar
            
        Returns:
            True se revogada com sucesso
        """
        
        if key in self.valid_api_keys:
            del self.valid_api_keys[key]
            logger.info(f"API key revogada: {key[:8]}...")
            return True
        
        return False
    
    def get_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """Listar todas API keys (sem mostrar keys completas)"""
        
        return {
            key[:8] + "...": {
                **data,
                'created_at': data['created_at'].isoformat()
            }
            for key, data in self.valid_api_keys.items()
        }
    
    def authenticate_request(self, token: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Autenticar request (JWT ou API key)
        
        Args:
            token: JWT token
            api_key: API key
            
        Returns:
            Dados de autenticação
        """
        
        # Tentar JWT token primeiro
        if token:
            payload = self.verify_token(token)
            if payload:
                return {
                    'authenticated': True,
                    'auth_type': 'jwt',
                    'user_id': payload['user_id'],
                    'username': payload['username'],
                    'permissions': payload['permissions']
                }
        
        # Tentar API key
        if api_key:
            key_data = self.verify_api_key(api_key)
            if key_data:
                return {
                    'authenticated': True,
                    'auth_type': 'api_key',
                    'api_key_name': key_data['name'],
                    'permissions': key_data['permissions']
                }
        
        # Não autenticado
        return {
            'authenticated': False,
            'auth_type': None,
            'error': 'Invalid or missing authentication'
        }
    
    def has_permission(self, auth_data: Dict[str, Any], required_permission: str) -> bool:
        """
        Verificar se usuário tem permissão específica
        
        Args:
            auth_data: Dados de autenticação
            required_permission: Permissão necessária
            
        Returns:
            True se tem permissão
        """
        
        if not auth_data.get('authenticated'):
            return False
        
        permissions = auth_data.get('permissions', [])
        
        # 'admin' tem todas as permissões
        if 'admin' in permissions:
            return True
        
        return required_permission in permissions


def test_auth_manager():
    """Teste básico do Auth Manager"""
    
    print("🧪 TESTE AUTH MANAGER")
    print("=" * 40)
    
    # 1. Inicializar
    auth = AuthManager(secret_key="test_secret_key")
    
    # 2. Teste de hash de senha
    if PASSLIB_AVAILABLE:
        password = "test_password_123"
        hashed = auth.hash_password(password)
        is_valid = auth.verify_password(password, hashed)
        print(f"Password hash: {'✅' if is_valid else '❌'}")
    else:
        print("Password hashing: ⚠️ Passlib not available")
    
    # 3. Teste JWT
    user_data = {
        'user_id': 'test_user',
        'username': 'testuser',
        'permissions': ['read', 'backtest']
    }
    
    token = auth.create_jwt_token(user_data)
    decoded = auth.verify_token(token)
    
    print(f"JWT Token: {'✅' if decoded else '❌'}")
    if decoded:
        print(f"   User: {decoded['username']}")
        print(f"   Permissions: {decoded['permissions']}")
    
    # 4. Teste API Key
    api_key = "demo_key_123"
    key_data = auth.verify_api_key(api_key)
    
    print(f"API Key: {'✅' if key_data else '❌'}")
    if key_data:
        print(f"   Name: {key_data['name']}")
        print(f"   Permissions: {key_data['permissions']}")
    
    # 5. Teste Rate Limiting
    rate_ok = auth.check_rate_limit("test_user", limit=5)
    print(f"Rate Limit: {'✅' if rate_ok else '❌'}")
    
    # 6. Teste autenticação completa
    auth_result = auth.authenticate_request(token=token)
    print(f"Authentication: {'✅' if auth_result['authenticated'] else '❌'}")
    
    # 7. Teste permissões
    has_read = auth.has_permission(auth_result, 'read')
    has_admin = auth.has_permission(auth_result, 'admin')
    
    print(f"Permission 'read': {'✅' if has_read else '❌'}")
    print(f"Permission 'admin': {'❌' if not has_admin else '✅'} (expected ❌)")
    
    print("\n✅ Teste concluído")


if __name__ == "__main__":
    test_auth_manager()