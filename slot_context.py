#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slot Context Management - Bot AI Trading
Sistema de gerenciamento de contexto de slots para trading
"""

import os
import logging
from time import time
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

def _key(slot_id: str, prefix: str = None) -> str:
    """Gera chave Redis com prefixo configurado"""
    base_prefix = prefix or os.getenv("REDIS_KEY_PREFIX", "")
    if base_prefix:
        return f"{base_prefix}:slot:{slot_id}"
    return f"slot:{slot_id}"

def _stream_key(prefix: str = None) -> str:
    """Gera chave do stream de decisões"""
    base_prefix = prefix or os.getenv("REDIS_KEY_PREFIX", "")
    if base_prefix:
        return f"{base_prefix}:stream:decisions"
    return "stream:decisions"

def init_bot_slot(
    redis_client, 
    slot_id: str, 
    base_amount: float, 
    min_amount: float, 
    group: str, 
    strategy: str, 
    symbol: str,
    **kwargs
) -> bool:
    """
    Inicializa slot no Redis com dados padrão
    
    Args:
        redis_client: Cliente Redis
        slot_id: ID único do slot
        base_amount: Valor base para trading
        min_amount: Valor mínimo para operações
        group: Grupo do slot (ex: 'spot', 'futures')
        strategy: Estratégia de trading
        symbol: Par de trading (ex: 'BTCUSDT')
        **kwargs: Parâmetros adicionais
    
    Returns:
        bool: True se inicializado com sucesso
    """
    try:
        now = int(time())
        
        # Dados padrão do slot
        slot_data = {
            "status": "idle",
            "base_amount": str(base_amount),
            "running_amount": str(base_amount),
            "min_amount": str(min_amount),
            "group": group,
            "strategy": strategy,
            "symbol": symbol,
            "cascade_index": "0",
            "last_update": str(now),
            "created_at": str(now),
            "active": "true"
        }
        
        # Adicionar parâmetros extras
        for key, value in kwargs.items():
            if value is not None:
                slot_data[key] = str(value)
        
        # Salvar no Redis
        key = _key(slot_id)
        redis_client.hset(key, mapping=slot_data)
        
        logger.info(f"✅ Slot {slot_id} initialized: {group}/{strategy} - {symbol}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing slot {slot_id}: {e}")
        return False

def labels_for_metrics(slot_id: str, group: str, strategy: str) -> Dict[str, str]:
    """
    Retorna labels para métricas Prometheus
    
    Args:
        slot_id: ID do slot
        group: Grupo do slot
        strategy: Estratégia do slot
    
    Returns:
        Dict com labels formatados
    """
    return {
        "slot": str(slot_id),
        "group": str(group),
        "strategy": str(strategy)
    }

def update_slot_stage(
    redis_client,
    slot_id: str,
    stage: str,
    extra: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Atualiza estágio do slot e registra evento
    
    Args:
        redis_client: Cliente Redis
        slot_id: ID do slot
        stage: Novo estágio/status
        extra: Dados adicionais para o evento
    
    Returns:
        bool: True se atualizado com sucesso
    """
    try:
        now = int(time())
        key = _key(slot_id)
        
        # Atualizar status e timestamp no slot
        redis_client.hset(key, mapping={
            "status": stage,
            "last_update": str(now)
        })
        
        # Preparar payload do evento
        event_payload = {
            "slot_id": slot_id,
            "stage": stage,
            "timestamp": now
        }
        
        # Adicionar dados extras se fornecidos
        if extra:
            event_payload.update(extra)
        
        # Registrar evento no stream
        stream_key = _stream_key()
        redis_client.xadd(
            stream_key,
            event_payload,
            maxlen=1000,
            approximate=True
        )
        
        logger.info(f"📊 Slot {slot_id} updated: {stage}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating slot {slot_id}: {e}")
        return False

def get_slot_context(redis_client, slot_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtém contexto completo do slot
    
    Args:
        redis_client: Cliente Redis
        slot_id: ID do slot
    
    Returns:
        Dict com dados do slot ou None se não encontrado
    """
    try:
        key = _key(slot_id)
        data = redis_client.hgetall(key)
        
        if not data:
            return None
        
        # Converter bytes para strings se necessário
        context = {}
        for k, v in data.items():
            if isinstance(k, bytes):
                k = k.decode('utf-8')
            if isinstance(v, bytes):
                v = v.decode('utf-8')
            context[k] = v
        
        return context
        
    except Exception as e:
        logger.error(f"❌ Error getting slot context {slot_id}: {e}")
        return None

def get_slot_metrics(redis_client, group: str = None) -> Dict[str, Any]:
    """
    Obtém métricas agregadas dos slots
    
    Args:
        redis_client: Cliente Redis
        group: Filtrar por grupo específico (opcional)
    
    Returns:
        Dict com métricas dos slots
    """
    try:
        # Buscar todas as chaves de slots
        pattern = _key("*")
        slot_keys = redis_client.keys(pattern)
        
        metrics = {
            "total_slots": 0,
            "active_slots": 0,
            "by_status": {},
            "by_group": {},
            "by_strategy": {}
        }
        
        for key in slot_keys:
            try:
                slot_data = redis_client.hgetall(key)
                if not slot_data:
                    continue
                
                # Converter bytes se necessário
                if isinstance(list(slot_data.keys())[0], bytes):
                    slot_data = {k.decode('utf-8'): v.decode('utf-8') 
                               for k, v in slot_data.items()}
                
                # Filtrar por grupo se especificado
                if group and slot_data.get("group") != group:
                    continue
                
                metrics["total_slots"] += 1
                
                # Contar ativos
                if slot_data.get("active") == "true":
                    metrics["active_slots"] += 1
                
                # Agrupar por status
                status = slot_data.get("status", "unknown")
                metrics["by_status"][status] = metrics["by_status"].get(status, 0) + 1
                
                # Agrupar por grupo
                slot_group = slot_data.get("group", "unknown")
                metrics["by_group"][slot_group] = metrics["by_group"].get(slot_group, 0) + 1
                
                # Agrupar por estratégia
                strategy = slot_data.get("strategy", "unknown")
                metrics["by_strategy"][strategy] = metrics["by_strategy"].get(strategy, 0) + 1
                
            except Exception as e:
                logger.warning(f"Error processing slot key {key}: {e}")
                continue
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Error getting slot metrics: {e}")
        return {
            "total_slots": 0,
            "active_slots": 0,
            "by_status": {},
            "by_group": {},
            "by_strategy": {},
            "error": str(e)
        }

def cleanup_expired_slots(redis_client, max_age_hours: int = 24) -> int:
    """
    Remove slots antigos/expirados
    
    Args:
        redis_client: Cliente Redis
        max_age_hours: Idade máxima em horas
    
    Returns:
        int: Número de slots removidos
    """
    try:
        current_time = int(time())
        max_age_seconds = max_age_hours * 3600
        
        pattern = _key("*")
        slot_keys = redis_client.keys(pattern)
        
        removed_count = 0
        
        for key in slot_keys:
            try:
                slot_data = redis_client.hgetall(key)
                if not slot_data:
                    continue
                
                # Converter bytes se necessário
                if isinstance(list(slot_data.keys())[0], bytes):
                    slot_data = {k.decode('utf-8'): v.decode('utf-8') 
                               for k, v in slot_data.items()}
                
                # Verificar idade do slot
                last_update = int(slot_data.get("last_update", 0))
                age = current_time - last_update
                
                # Remover se muito antigo e inativo
                if (age > max_age_seconds and 
                    slot_data.get("status") in ["idle", "error", "stopped"] and
                    slot_data.get("active") != "true"):
                    
                    redis_client.delete(key)
                    removed_count += 1
                    logger.info(f"🗑️ Removed expired slot: {key}")
                
            except Exception as e:
                logger.warning(f"Error processing slot key {key} for cleanup: {e}")
                continue
        
        if removed_count > 0:
            logger.info(f"🧹 Cleanup completed: {removed_count} slots removed")
        
        return removed_count
        
    except Exception as e:
        logger.error(f"❌ Error during slot cleanup: {e}")
        return 0

# Aliases para compatibilidade
update_slot_status = update_slot_stage
get_slot_data = get_slot_context