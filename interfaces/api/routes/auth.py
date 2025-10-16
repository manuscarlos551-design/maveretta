# interfaces/api/routes/auth.py
"""
Authentication Routes - Sistema de autenticação
"""
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from plugins.auth_jwt import jwt_auth, get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """
    Login do usuário
    """
    try:
        # Autenticar usuário
        user = jwt_auth.authenticate_user(request.username, request.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )
        
        # Gerar token
        token = jwt_auth.create_token(user)
        
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=86400,  # 24 horas em segundos
            user={
                "username": user["username"],
                "permissions": user["permissions"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno no login"
        )

@router.post("/logout")
async def logout(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Logout do usuário
    """
    try:
        # Em uma implementação completa, o token seria invalidado
        # Por enquanto, apenas retornamos sucesso
        
        return {
            "message": "Logout realizado com sucesso",
            "username": user["username"],
            "logged_out_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro no logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno no logout"
        )

@router.get("/me")
async def get_current_user_info(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Informações do usuário atual
    """
    try:
        return {
            "username": user["username"],
            "permissions": user["permissions"],
            "authenticated": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter info do usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter informações do usuário"
        )

@router.get("/status")
async def get_auth_status() -> Dict[str, Any]:
    """
    Status do sistema de autenticação
    """
    try:
        from plugins.auth_jwt import get_jwt_status
        
        status_info = get_jwt_status()
        
        return {
            "authentication_enabled": True,
            **status_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status de auth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter status"
        )

@router.get("/users")
async def list_users(admin_user: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    """
    Lista usuários (apenas admin)
    """
    try:
        users = []
        for username, user_data in jwt_auth.users.items():
            users.append({
                "username": username,
                "permissions": user_data["permissions"],
                "active": user_data["active"]
            })
        
        return {
            "users": users,
            "total": len(users),
            "requested_by": admin_user["username"]
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar usuários"
        )