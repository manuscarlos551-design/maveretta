# core/logging/operations_logger.py
"""
Operations Logger - Logger de operações no MongoDB
"""

import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)


class OperationsLogger:
    """
    Logger de operações no MongoDB
    Registra abertura e fechamento de trades
    """
    
    def __init__(self):
        # MongoDB connection
        mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client["maveretta"]
        self.operations_collection = self.db["operations"]
        
        logger.info("✅ Operations Logger inicializado")
    
    async def log_operation_open(self, trade_data: Dict[str, Any]) -> str:
        """
        Registra abertura de operação
        
        Args:
            trade_data: Dados do trade
        
        Returns:
            operation_id: ID da operação criada
        """
        try:
            # Gera ID único
            operation_id = f"op_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            
            # Prepara documento
            operation = {
                "id": operation_id,
                "slot_id": trade_data.get("slot_id"),
                "exchange": trade_data.get("exchange"),
                "symbol": trade_data.get("symbol"),
                "side": trade_data.get("side"),  # buy/sell
                "type": trade_data.get("type", "market"),  # market/limit
                "status": "open",
                
                # Preços e quantidades
                "entry_price": trade_data.get("entry_price"),
                "exit_price": None,
                "quantity": trade_data.get("quantity"),
                
                # P&L
                "pnl": None,
                "pnl_pct": None,
                "fees": trade_data.get("fees", 0),
                
                # Timestamps
                "opened_at": datetime.utcnow(),
                "closed_at": None,
                
                # Estratégia e decisão
                "strategy": trade_data.get("strategy"),
                "agent_votes": trade_data.get("agent_votes"),
                "confidence": trade_data.get("confidence"),
                
                # Risk management
                "stop_loss": trade_data.get("stop_loss"),
                "take_profit": trade_data.get("take_profit"),
                "trailing_stop": trade_data.get("trailing_stop", False),
                
                # Metadados
                "order_id": trade_data.get("order_id"),
                "error_message": None
            }
            
            # Insere no MongoDB
            await self.operations_collection.insert_one(operation)
            
            logger.info(f"✅ Operação registrada: {operation_id} - {operation['side']} {operation['quantity']} {operation['symbol']}")
            
            return operation_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar abertura de operação: {e}")
            return None
    
    async def log_operation_close(self, operation_id: str, close_data: Dict[str, Any]) -> bool:
        """
        Registra fechamento de operação
        
        Args:
            operation_id: ID da operação
            close_data: Dados do fechamento
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # Busca operação
            operation = await self.operations_collection.find_one({"id": operation_id})
            
            if not operation:
                logger.error(f"Operação {operation_id} não encontrada")
                return False
            
            # Calcula P&L
            entry_price = operation.get("entry_price", 0)
            exit_price = close_data.get("exit_price", 0)
            quantity = operation.get("quantity", 0)
            side = operation.get("side")
            
            pnl = 0
            pnl_pct = 0
            
            if entry_price and exit_price and quantity:
                if side == "buy":
                    pnl = (exit_price - entry_price) * quantity
                elif side == "sell":
                    pnl = (entry_price - exit_price) * quantity
                
                if entry_price * quantity != 0:
                    pnl_pct = (pnl / (entry_price * quantity)) * 100
            
            # Atualiza operação
            update_data = {
                "status": "closed",
                "exit_price": exit_price,
                "closed_at": datetime.utcnow(),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "fees": close_data.get("fees", operation.get("fees", 0))
            }
            
            await self.operations_collection.update_one(
                {"id": operation_id},
                {"$set": update_data}
            )
            
            logger.info(f"✅ Operação fechada: {operation_id} - P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar fechamento de operação {operation_id}: {e}")
            return False
    
    async def get_open_operations(self) -> list:
        """
        Retorna todas as operações abertas
        
        Returns:
            Lista de operações abertas
        """
        try:
            cursor = self.operations_collection.find({"status": "open"})
            operations = await cursor.to_list(length=None)
            return operations
        except Exception as e:
            logger.error(f"❌ Erro ao buscar operações abertas: {e}")
            return []
    
    async def update_operation(self, operation_id: str, updates: Dict[str, Any]) -> bool:
        """
        Atualiza uma operação
        
        Args:
            operation_id: ID da operação
            updates: Campos a atualizar
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            result = await self.operations_collection.update_one(
                {"id": operation_id},
                {"$set": updates}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Operação {operation_id} atualizada")
                return True
            else:
                logger.warning(f"⚠️ Operação {operation_id} não encontrada ou sem alterações")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar operação {operation_id}: {e}")
            return False
