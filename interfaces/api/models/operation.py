# interfaces/api/models/operation.py
"""
Operation Model - Modelo de operações (trades)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OperationSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OperationType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OperationStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Operation(BaseModel):
    """Modelo de uma operação (trade)"""
    
    id: str = Field(..., description="ID único da operação")
    slot_id: str = Field(..., description="ID do slot que executou")
    exchange: str = Field(..., description="Exchange (binance, kucoin, etc)")
    symbol: str = Field(..., description="Par negociado (BTC/USDT)")
    side: OperationSide = Field(..., description="Lado da operação")
    type: OperationType = Field(..., description="Tipo de ordem")
    status: OperationStatus = Field(..., description="Status atual")
    
    # Preços e quantidades
    entry_price: Optional[float] = Field(None, description="Preço de entrada")
    exit_price: Optional[float] = Field(None, description="Preço de saída")
    quantity: float = Field(..., description="Quantidade negociada")
    
    # P&L
    pnl: Optional[float] = Field(None, description="Lucro/Prejuízo em USD")
    pnl_pct: Optional[float] = Field(None, description="P&L percentual")
    fees: Optional[float] = Field(None, description="Taxas pagas")
    
    # Timestamps
    opened_at: datetime = Field(..., description="Data/hora de abertura")
    closed_at: Optional[datetime] = Field(None, description="Data/hora de fechamento")
    
    # Estratégia e decisão
    strategy: Optional[str] = Field(None, description="Estratégia utilizada")
    agent_votes: Optional[Dict[str, Any]] = Field(None, description="Votos dos agentes")
    confidence: Optional[float] = Field(None, description="Confiança da decisão (0-1)")
    
    # Risk management
    stop_loss: Optional[float] = Field(None, description="Preço de stop loss")
    take_profit: Optional[float] = Field(None, description="Preço de take profit")
    trailing_stop: Optional[bool] = Field(False, description="Trailing stop ativo")
    
    # Metadados
    order_id: Optional[str] = Field(None, description="ID da ordem na exchange")
    error_message: Optional[str] = Field(None, description="Mensagem de erro se falhou")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "op_20250112_123456",
                "slot_id": "slot_1",
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy",
                "type": "limit",
                "status": "closed",
                "entry_price": 45000.0,
                "exit_price": 46000.0,
                "quantity": 0.01,
                "pnl": 10.0,
                "pnl_pct": 2.22,
                "fees": 0.5,
                "opened_at": "2025-01-12T10:00:00Z",
                "closed_at": "2025-01-12T12:00:00Z",
                "strategy": "macd_rsi",
                "confidence": 0.85
            }
        }
