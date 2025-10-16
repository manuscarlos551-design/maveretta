#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Gateway CORS Module
Configuração de CORS para a API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)


def setup_cors(app: FastAPI, origins: list = None):
    """
    Configura CORS para a aplicação
    
    Args:
        app: Instância do FastAPI
        origins: Lista de origens permitidas (opcional)
    """
    
    # Origens padrão se não especificadas
    if origins is None:
        origins = [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080",
            "http://localhost:8501",
            "*"  # Permitir todas em desenvolvimento
        ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    logger.info(f"✅ CORS configured with {len(origins)} origins")


__all__ = ["setup_cors"]
