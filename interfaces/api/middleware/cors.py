#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORS Middleware - Bot AI Multi-Agente API
Etapa 6: Configuração de CORS para API
"""

import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)


def get_cors_origins() -> List[str]:
    """
    Obter origins permitidas para CORS
    
    Returns:
        Lista de origins permitidas
    """
    
    # Padrão: localhost para desenvolvimento
    default_origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]
    
    # Ler do .env se disponível
    env_origins = os.getenv('CORS_ORIGINS', '')
    
    if env_origins:
        # Parse origins do .env
        env_origins_list = [origin.strip() for origin in env_origins.split(',')]
        # Combinar com padrões
        all_origins = list(set(default_origins + env_origins_list))
    else:
        all_origins = default_origins
    
    logger.info(f"CORS origins configuradas: {all_origins}")
    return all_origins


def setup_cors(app: FastAPI) -> None:
    """
    Configurar CORS middleware para FastAPI app
    
    Args:
        app: Instância FastAPI
    """
    
    try:
        # Obter configurações
        allowed_origins = get_cors_origins()
        
        # Configurações de CORS
        cors_config = {
            "allow_origins": allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Accept",
                "Accept-Language", 
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-API-Key",
                "X-Requested-With"
            ],
        }
        
        # Adicionar middleware
        app.add_middleware(CORSMiddleware, **cors_config)
        
        logger.info("✅ CORS middleware configurado")
        
    except Exception as e:
        logger.error(f"Erro ao configurar CORS: {e}")
        raise


def setup_security_headers(app: FastAPI) -> None:
    """
    Adicionar headers de segurança
    
    Args:
        app: Instância FastAPI
    """
    
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        """Middleware para adicionar headers de segurança"""
        
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
        }
        
        # Adicionar apenas se não existirem
        for header, value in security_headers.items():
            if header not in response.headers:
                response.headers[header] = value
        
        return response
    
    logger.info("✅ Security headers middleware configurado")


def setup_request_logging(app: FastAPI) -> None:
    """
    Setup de logging de requests
    
    Args:
        app: Instância FastAPI
    """
    
    import time  # Import aqui para disponibilizar no escopo
    
    @app.middleware("http")
    async def log_requests(request, call_next):
        """Middleware para log de requests"""
        
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    logger.info("✅ Request logging middleware configurado")


def setup_all_middleware(app: FastAPI) -> None:
    """
    Configurar todos os middlewares
    
    Args:
        app: Instância FastAPI
    """
    
    try:
        # Setup middlewares
        setup_cors(app)
        setup_security_headers(app)
        
        # Request logging apenas se habilitado
        if os.getenv('API_REQUEST_LOGGING', 'false').lower() == 'true':
            setup_request_logging(app)
        
        logger.info("✅ Todos middlewares configurados")
        
    except Exception as e:
        logger.error(f"Erro ao configurar middlewares: {e}")
        raise


# Configuração de Rate Limiting (usando slowapi se disponível)
def setup_rate_limiting(app: FastAPI) -> None:
    """
    Setup de rate limiting (opcional)
    
    Args:
        app: Instância FastAPI
    """
    
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded
        
        # Configurar limiter
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        
        logger.info("✅ Rate limiting configurado")
        
    except ImportError:
        logger.info("Rate limiting não disponível - instale slowapi para habilitar")
    except Exception as e:
        logger.error(f"Erro ao configurar rate limiting: {e}")


def test_cors_setup():
    """Teste básico da configuração CORS"""
    
    print("🧪 TESTE CORS SETUP")
    print("=" * 40)
    
    # 1. Teste get_cors_origins
    origins = get_cors_origins()
    print(f"CORS Origins: {len(origins)} configuradas")
    for origin in origins:
        print(f"   • {origin}")
    
    # 2. Teste configuração com FastAPI
    try:
        from fastapi import FastAPI
        
        app = FastAPI()
        setup_cors(app)
        
        # Verificar middleware
        has_cors = any(
            middleware.__class__.__name__ == 'CORSMiddleware' 
            for middleware in app.user_middleware
        )
        
        print(f"FastAPI CORS: {'✅' if has_cors else '❌'}")
        
    except Exception as e:
        print(f"FastAPI CORS: ❌ - {e}")
    
    print("\n✅ Teste concluído")


if __name__ == "__main__":
    test_cors_setup()