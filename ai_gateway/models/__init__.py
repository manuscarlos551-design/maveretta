#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Gateway API Models
Modelos Pydantic para requisições e respostas da API
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Resposta do health check"""
    status: str = Field(..., description="Status do serviço")
    timestamp: datetime = Field(default_factory=datetime.now)
    api_version: str = Field(default="1.0.0")
    components_available: Dict[str, bool] = Field(default_factory=dict)


class BotStatusResponse(BaseModel):
    """Resposta do status do bot"""
    status: str = Field(..., description="Status do bot (running/stopped)")
    timestamp: datetime = Field(default_factory=datetime.now)
    components: Dict[str, Any] = Field(default_factory=dict)
    uptime_hours: float = Field(default=0.0)


class BotConfigRequest(BaseModel):
    """Requisição de configuração do bot"""
    symbol: Optional[str] = Field(None, description="Par de trading")
    strategy: Optional[str] = Field(None, description="Estratégia de trading")
    risk_per_trade: Optional[float] = Field(None, ge=0, le=1)
    max_positions: Optional[int] = Field(None, ge=1)
    
    class Config:
        extra = "allow"


class BacktestRequest(BaseModel):
    """Requisição de backtest"""
    symbol: str = Field(..., description="Par de trading")
    start_date: str = Field(..., description="Data inicial (YYYY-MM-DD)")
    end_date: str = Field(..., description="Data final (YYYY-MM-DD)")
    initial_capital: float = Field(default=10000.0, gt=0)
    timeframe: str = Field(default="1h", description="Timeframe (1m, 5m, 1h, etc)")
    strategy: Optional[str] = Field(None, description="Estratégia para testar")
    
    class Config:
        extra = "allow"


class BacktestResponse(BaseModel):
    """Resposta do backtest"""
    backtest_id: str = Field(..., description="ID único do backtest")
    status: str = Field(..., description="Status do backtest")
    config: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    trade_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        extra = "allow"


class PerformanceResponse(BaseModel):
    """Resposta de métricas de performance"""
    timestamp: datetime = Field(default_factory=datetime.now)
    uptime_hours: float = Field(default=0.0)
    api_requests: int = Field(default=0)
    components_health: Dict[str, str] = Field(default_factory=dict)
    last_update: datetime = Field(default_factory=datetime.now)


class TradeSignal(BaseModel):
    """Sinal de trade"""
    symbol: str = Field(..., description="Par de trading")
    action: str = Field(..., description="Ação (buy/sell)")
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=1)
    strategy: str = Field(..., description="Estratégia que gerou o sinal")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class OrderRequest(BaseModel):
    """Requisição de ordem"""
    symbol: str = Field(..., description="Par de trading")
    side: str = Field(..., description="Lado da ordem (buy/sell)")
    order_type: str = Field(..., description="Tipo da ordem (market/limit)")
    quantity: float = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    
    class Config:
        extra = "allow"


class OrderResponse(BaseModel):
    """Resposta de ordem"""
    order_id: str = Field(..., description="ID da ordem")
    status: str = Field(..., description="Status da ordem")
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    filled_quantity: float = Field(default=0.0)
    average_price: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        extra = "allow"


class PositionResponse(BaseModel):
    """Resposta de posição"""
    position_id: str = Field(..., description="ID da posição")
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    opened_at: datetime
    
    class Config:
        extra = "allow"


class MarketDataResponse(BaseModel):
    """Resposta de dados de mercado"""
    symbol: str
    price: float
    volume_24h: float
    change_24h_pct: float
    high_24h: float
    low_24h: float
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        extra = "allow"


class ErrorResponse(BaseModel):
    """Resposta de erro padrão"""
    error: str = Field(..., description="Mensagem de erro")
    error_code: Optional[str] = Field(None, description="Código do erro")
    detail: Optional[str] = Field(None, description="Detalhes adicionais")
    timestamp: datetime = Field(default_factory=datetime.now)


__all__ = [
    "HealthResponse",
    "BotStatusResponse", 
    "BotConfigRequest",
    "BacktestRequest",
    "BacktestResponse",
    "PerformanceResponse",
    "TradeSignal",
    "OrderRequest",
    "OrderResponse",
    "PositionResponse",
    "MarketDataResponse",
    "ErrorResponse"
]
