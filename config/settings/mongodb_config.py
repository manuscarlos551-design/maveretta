#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB Configuration - TURBINADA
Otimizações de connection pooling e índices compostos
"""

import os
from typing import Dict, Any

# ===== CONNECTION POOLING OTIMIZADO (TURBINADA) =====
MONGODB_CONFIG: Dict[str, Any] = {
    # Connection URI
    "uri": os.getenv("MONGO_URI", "mongodb://mongodb:27017"),
    
    # TURBINADA: Connection Pool otimizado para alta concorrência
    "maxPoolSize": 100,          # ⬆️ de 50 para 100 conexões simultâneas
    "minPoolSize": 10,            # ⬆️ de 5 para 10 conexões sempre prontas
    "maxIdleTimeMS": 45000,       # 45s timeout para conexões idle
    "waitQueueTimeoutMS": 5000,   # 5s timeout na fila de espera
    
    # TURBINADA: Read/Write otimizado
    "retryWrites": True,          # Retry automático em falhas de escrita
    "retryReads": True,           # Retry automático em falhas de leitura
    "w": "majority",              # Write concern para durabilidade
    "readPreference": "primaryPreferred",  # Prioriza primary, fallback para secondary
    
    # TURBINADA: Timeouts otimizados
    "serverSelectionTimeoutMS": 5000,  # 5s para selecionar servidor
    "connectTimeoutMS": 10000,         # 10s para conectar
    "socketTimeoutMS": 45000,          # 45s para operações de socket
    
    # TURBINADA: Compression para reduzir latência de rede
    "compressors": "snappy,zlib",      # Compressão snappy + zlib fallback
    
    # Application name para monitoramento
    "appName": "maveretta-bot",
}

# ===== ÍNDICES COMPOSTOS OTIMIZADOS (TURBINADA) =====
INDEXES_CONFIG = {
    # Coleção: agent_decisions
    "agent_decisions": [
        {
            "keys": [("timestamp", -1), ("agent_id", 1)],
            "name": "idx_timestamp_agent",
            "background": True,
        },
        {
            "keys": [("slot_id", 1), ("timestamp", -1)],
            "name": "idx_slot_timestamp",
            "background": True,
        },
        {
            "keys": [("symbol", 1), ("timestamp", -1)],
            "name": "idx_symbol_timestamp",
            "background": True,
        },
    ],
    
    # Coleção: slot_states
    "slot_states": [
        {
            "keys": [("slot_id", 1), ("timestamp", -1)],
            "name": "idx_slot_timestamp",
            "unique": False,
            "background": True,
        },
        {
            "keys": [("status", 1), ("timestamp", -1)],
            "name": "idx_status_timestamp",
            "background": True,
        },
    ],
    
    # Coleção: trades
    "trades": [
        {
            "keys": [("timestamp", -1), ("exchange", 1)],
            "name": "idx_timestamp_exchange",
            "background": True,
        },
        {
            "keys": [("symbol", 1), ("timestamp", -1)],
            "name": "idx_symbol_timestamp",
            "background": True,
        },
        {
            "keys": [("slot_id", 1), ("timestamp", -1)],
            "name": "idx_slot_timestamp",
            "background": True,
        },
    ],
    
    # Coleção: market_data
    "market_data": [
        {
            "keys": [("symbol", 1), ("timestamp", -1)],
            "name": "idx_symbol_timestamp",
            "background": True,
        },
        {
            "keys": [("exchange", 1), ("timestamp", -1)],
            "name": "idx_exchange_timestamp",
            "background": True,
        },
    ],
    
    # Coleção: portfolio_snapshots
    "portfolio_snapshots": [
        {
            "keys": [("timestamp", -1)],
            "name": "idx_timestamp",
            "background": True,
        },
        {
            "keys": [("exchange", 1), ("timestamp", -1)],
            "name": "idx_exchange_timestamp",
            "background": True,
        },
    ],
}

# ===== TTL INDEXES PARA LIMPEZA AUTOMÁTICA (TURBINADA) =====
TTL_INDEXES = {
    # Logs antigos (30 dias)
    "logs": {
        "keys": [("timestamp", 1)],
        "name": "idx_ttl_logs",
        "expireAfterSeconds": 30 * 24 * 3600,  # 30 dias
        "background": True,
    },
    
    # Market data cache (7 dias)
    "market_data_cache": {
        "keys": [("timestamp", 1)],
        "name": "idx_ttl_market_cache",
        "expireAfterSeconds": 7 * 24 * 3600,  # 7 dias
        "background": True,
    },
    
    # Agent decisions antigas (90 dias para auditoria)
    "agent_decisions": {
        "keys": [("timestamp", 1)],
        "name": "idx_ttl_decisions",
        "expireAfterSeconds": 90 * 24 * 3600,  # 90 dias
        "background": True,
    },
}


def get_connection_string() -> str:
    """
    Retorna connection string completa com todos os parâmetros otimizados
    TURBINADA: Connection pooling + compressão + timeouts
    """
    base_uri = MONGODB_CONFIG["uri"]
    
    params = [
        f"maxPoolSize={MONGODB_CONFIG['maxPoolSize']}",
        f"minPoolSize={MONGODB_CONFIG['minPoolSize']}",
        f"maxIdleTimeMS={MONGODB_CONFIG['maxIdleTimeMS']}",
        f"waitQueueTimeoutMS={MONGODB_CONFIG['waitQueueTimeoutMS']}",
        f"serverSelectionTimeoutMS={MONGODB_CONFIG['serverSelectionTimeoutMS']}",
        f"connectTimeoutMS={MONGODB_CONFIG['connectTimeoutMS']}",
        f"socketTimeoutMS={MONGODB_CONFIG['socketTimeoutMS']}",
        f"retryWrites={str(MONGODB_CONFIG['retryWrites']).lower()}",
        f"retryReads={str(MONGODB_CONFIG['retryReads']).lower()}",
        f"w={MONGODB_CONFIG['w']}",
        f"readPreference={MONGODB_CONFIG['readPreference']}",
        f"compressors={MONGODB_CONFIG['compressors']}",
        f"appName={MONGODB_CONFIG['appName']}",
    ]
    
    return f"{base_uri}?{'&'.join(params)}"


async def create_indexes(db):
    """
    Cria todos os índices compostos otimizados
    TURBINADA: Execução em background para não bloquear
    """
    for collection_name, indexes in INDEXES_CONFIG.items():
        collection = db[collection_name]
        
        for index_spec in indexes:
            keys = index_spec.pop("keys")
            await collection.create_index(keys, **index_spec)
            print(f"✅ Index criado: {collection_name}.{index_spec.get('name', 'unnamed')}")
    
    # Criar TTL indexes
    for collection_name, ttl_spec in TTL_INDEXES.items():
        collection = db[collection_name]
        keys = ttl_spec.pop("keys")
        await collection.create_index(keys, **ttl_spec)
        print(f"✅ TTL Index criado: {collection_name}.{ttl_spec.get('name', 'unnamed')}")


if __name__ == "__main__":
    print("MongoDB Configuration - TURBINADA")
    print(f"Connection String: {get_connection_string()}")
    print(f"\nIndexes configurados: {len(INDEXES_CONFIG)} coleções")
    print(f"TTL Indexes: {len(TTL_INDEXES)} coleções")
