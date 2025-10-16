#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slot Context - Sistema de rastreamento de slots em cascata (Bot Version)
Implementa o modelo de slots slot-aware para métricas Prometheus
"""

import contextvars
import uuid
from typing import Dict, Any, Optional

# Context var para armazenar informações do slot atual
slot_ctx = contextvars.ContextVar("slot_ctx", default={})


def bind_slot(headers: dict = None, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Vincula informações de slot do contexto atual
    
    Args:
        headers: Headers HTTP do request (opcional para bot)
        defaults: Valores padrão para campos não informados
        
    Returns:
        Dict com informações do slot vinculado
    """
    h = headers or {}
    d = defaults or {}
    
    slot_data = {
        "slot_id": h.get("x-slot-id") or d.get("slot_id") or uuid.uuid4().hex[:12],
        "slot_parent": h.get("x-slot-parent") or d.get("slot_parent") or "",
        "slot_root": h.get("x-slot-root") or d.get("slot_root") or "",
        "slot_chain": h.get("x-slot-chain") or d.get("slot_chain") or "",
        "slot_stage": h.get("x-slot-stage") or d.get("slot_stage") or "execute",
        "slot_strategy": h.get("x-slot-strategy") or d.get("slot_strategy") or "unknown",
        "slot_instance": h.get("x-slot-instance") or d.get("slot_instance") or "bot-1",
        "slot_tenant": h.get("x-slot-tenant") or d.get("slot_tenant") or "default",
    }
    
    # Auto-definir slot_root se não informado
    if not slot_data["slot_root"]:
        slot_data["slot_root"] = slot_data["slot_id"] if not slot_data["slot_parent"] else slot_data["slot_parent"]
    
    # Vincular ao contexto
    slot_ctx.set(slot_data)
    
    return slot_data


def labels_for_metrics() -> Dict[str, str]:
    """
    Extrai labels slot-aware para métricas Prometheus
    IMPORTANTE: Nunca inclui slot_id (evita cardinalidade alta)
    
    Returns:
        Dict com labels seguros para métricas
    """
    s = slot_ctx.get({})
    
    return {
        "slot_stage": s.get("slot_stage", "execute"),
        "slot_strategy": s.get("slot_strategy", "unknown"), 
        "slot_instance": s.get("slot_instance", "bot-1"),
    }


def get_current_slot() -> Dict[str, Any]:
    """
    Obtém informações completas do slot atual
    
    Returns:
        Dict com todas as informações do slot
    """
    return slot_ctx.get({})


def update_slot_stage(stage: str) -> None:
    """
    Atualiza o stage do slot atual
    
    Args:
        stage: Novo stage (ingest|decide|route|execute|settle)
    """
    current = slot_ctx.get({})
    if current:
        current["slot_stage"] = stage
        slot_ctx.set(current)


def create_child_slot(stage: str, strategy: Optional[str] = None) -> Dict[str, Any]:
    """
    Cria um slot filho baseado no slot atual
    
    Args:
        stage: Stage do slot filho
        strategy: Strategy do slot filho (opcional)
        
    Returns:
        Dict com informações do slot filho criado
    """
    parent = slot_ctx.get({})
    
    child_data = {
        "slot_id": uuid.uuid4().hex[:12],
        "slot_parent": parent.get("slot_id", ""),
        "slot_root": parent.get("slot_root", parent.get("slot_id", "")),
        "slot_chain": f"{parent.get('slot_chain', '')},{parent.get('slot_id', '')}" if parent.get("slot_chain") else parent.get("slot_id", ""),
        "slot_stage": stage,
        "slot_strategy": strategy or parent.get("slot_strategy", "unknown"),
        "slot_instance": parent.get("slot_instance", "bot-1"),
        "slot_tenant": parent.get("slot_tenant", "default"),
    }
    
    return child_data


def init_bot_slot(strategy: str = "unknown", instance: str = "bot-1") -> Dict[str, Any]:
    """
    Inicializa slot para o bot principal
    
    Args:
        strategy: Strategy do bot
        instance: Instância do bot
        
    Returns:
        Dict com informações do slot inicializado
    """
    return bind_slot(defaults={
        "slot_stage": "execute",
        "slot_strategy": strategy,
        "slot_instance": instance,
    })