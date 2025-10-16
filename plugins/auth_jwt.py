# plugins/auth_jwt.py
"""
JWT Authentication System - Sistema de autenticação JWT
"""
import logging
import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib
import json
import redis

logger = logging.getLogger(__name__)

# Configurações JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "maveretta-bot-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Security scheme
security = HTTPBearer()

class JWTAuthManager:
    """Gerenciador de autenticação JWT"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        
        # Usuários padrão (em produção usar banco de dados)
        self.users = {
            "admin": {
                "username": "admin",
                "password_hash": self._hash_password("admin123"),
                "permissions": ["read", "write", "admin"],
                "active": True
            },
            "trader": {
                "username": "trader", 
                "password_hash": self._hash_password("trader123"),
                "permissions": ["read", "write"],
                "active": True
            },
            "viewer": {
                "username": "viewer",
                "password_hash": self._hash_password("viewer123"),
                "permissions": ["read"],
                "active": True
            }
        }
    
    def _get_redis_client(self):
        """Obtém cliente Redis para blacklist de tokens"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            return redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Erro ao conectar Redis para JWT: {e}")
            return None
    
    def _hash_password(self, password: str) -> str:
        """Hash da senha"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Autentica usuário com username/password
        
        Args:
            username: Nome do usuário
            password: Senha
            
        Returns:
            Dados do usuário se autenticado, None caso contrário
        """
        try:
            user = self.users.get(username)
            if not user or not user.get("active", False):
                return None
            
            password_hash = self._hash_password(password)
            if password_hash != user["password_hash"]:
                return None
            
            # Retornar dados do usuário (sem senha)
            return {
                "username": user["username"],
                "permissions": user["permissions"]
            }
            
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return None
    
    def create_token(self, user: Dict[str, Any]) -> str:
        """
        Cria token JWT para usuário autenticado
        
        Args:
            user: Dados do usuário
            
        Returns:
            Token JWT
        """
        try:
            now = datetime.utcnow()
            expiration = now + timedelta(hours=JWT_EXPIRATION_HOURS)
            
            payload = {
                "sub": user["username"],
                "permissions": user["permissions"],
                "iat": now.timestamp(),
                "exp": expiration.timestamp(),
                "jti": f"{user['username']}_{int(now.timestamp())}"  # Unique token ID
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"Token criado para usuário {user['username']}")
            return token
            
        except Exception as e:
            logger.error(f"Erro ao criar token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao gerar token"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verifica e decodifica token JWT
        
        Args:
            token: Token JWT
            
        Returns:
            Payload do token
        """
        try:
            # Verificar se token está na blacklist
            if self._is_token_blacklisted(token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token revogado"
                )
            
            # Decodificar token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verificar se usuário ainda existe e está ativo
            username = payload.get("sub")
            user = self.users.get(username)
            
            if not user or not user.get("active", False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário inválido"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        except Exception as e:
            logger.error(f"Erro ao verificar token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Erro de autenticação"
            )
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Verifica se token está na blacklist"""
        if not self.redis_client:
            return False
        
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            return self.redis_client.exists(f"blacklist:{token_hash}")
        except Exception:
            return False
    
    def blacklist_token(self, token: str):
        """Adiciona token à blacklist"""
        if not self.redis_client:
            return
        
        try:
            # Decodificar para obter tempo de expiração
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            exp = payload.get("exp", 0)
            
            # Calcular TTL
            now = datetime.utcnow().timestamp()
            ttl = max(1, int(exp - now))
            
            # Adicionar à blacklist
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            self.redis_client.setex(f"blacklist:{token_hash}", ttl, "1")
            
            logger.info(f"Token adicionado à blacklist")
            
        except Exception as e:
            logger.warning(f"Erro ao adicionar token à blacklist: {e}")
    
    def refresh_token(self, token: str) -> str:
        """
        Renova token JWT
        
        Args:
            token: Token atual
            
        Returns:
            Novo token
        """
        try:
            # Verificar token atual
            payload = self.verify_token(token)
            
            # Criar novo token
            user = {
                "username": payload["sub"],
                "permissions": payload["permissions"]
            }
            
            # Blacklist do token atual
            self.blacklist_token(token)
            
            # Gerar novo token
            new_token = self.create_token(user)
            
            return new_token
            
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Não foi possível renovar token"
            )
    
    def get_user_info(self, token: str) -> Dict[str, Any]:
        """Obtém informações do usuário a partir do token"""
        try:
            payload = self.verify_token(token)
            
            username = payload["sub"]
            user = self.users.get(username, {})
            
            return {
                "username": username,
                "permissions": payload["permissions"],
                "token_issued_at": datetime.fromtimestamp(payload["iat"]).isoformat(),
                "token_expires_at": datetime.fromtimestamp(payload["exp"]).isoformat(),
                "active": user.get("active", False)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter info do usuário: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

# Instância global
jwt_auth = JWTAuthManager()

# Dependency functions
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency para obter usuário atual autenticado
    """
    token = credentials.credentials
    payload = jwt_auth.verify_token(token)
    
    return {
        "username": payload["sub"],
        "permissions": payload["permissions"]
    }

def require_permission(permission: str):
    """
    Decorator para requerer permissão específica
    
    Args:
        permission: Permissão necessária (read, write, admin)
    """
    def permission_dependency(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if permission not in user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão '{permission}' necessária"
            )
        return user
    
    return permission_dependency

def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency para requerer permissão de admin"""
    if "admin" not in user.get("permissions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão de administrador necessária"
        )
    return user

def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """
    Dependency para autenticação opcional
    Retorna None se não autenticado
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt_auth.verify_token(token)
        
        return {
            "username": payload["sub"],
            "permissions": payload["permissions"]
        }
    except:
        return None

# Funções auxiliares para setup
def setup_jwt_auth():
    """Setup inicial do sistema JWT"""
    logger.info("Sistema JWT configurado")
    logger.info(f"Usuários disponíveis: {list(jwt_auth.users.keys())}")
    logger.info(f"Expiração de tokens: {JWT_EXPIRATION_HOURS} horas")

def get_jwt_status() -> Dict[str, Any]:
    """Obtém status do sistema JWT"""
    return {
        "jwt_enabled": True,
        "algorithm": JWT_ALGORITHM,
        "token_expiration_hours": JWT_EXPIRATION_HOURS,
        "users_count": len(jwt_auth.users),
        "redis_available": jwt_auth.redis_client is not None
    }