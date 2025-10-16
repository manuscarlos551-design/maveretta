#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Models - Pydantic Models para API
Bot AI Multi-Agente - Etapa 6
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class BotStatus(str, Enum):
    """Status do bot"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class BacktestStatus(str, Enum):
    """Status do backtest"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ===== REQUEST MODELS =====

class BotConfigRequest(BaseModel):
    """Request para atualizar configuração do bot"""
    
    symbol: Optional[str] = Field(None, description="Símbolo de trading")
    timeframe: Optional[str] = Field(None, description="Timeframe")
    take_profit: Optional[float] = Field(None, ge=0, le=1, description="Take profit %")
    stop_loss: Optional[float] = Field(None, ge=0, le=1, description="Stop loss %")
    ai_score_threshold: Optional[float] = Field(None, ge=0, le=1, description="Threshold IA")
    max_position_size_pct: Optional[float] = Field(None, ge=0, le=100, description="Tamanho máx posição %")
    
    class Config:
        example = {
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "take_profit": 0.10,
            "stop_loss": 0.03,
            "ai_score_threshold": 0.70,
            "max_position_size_pct": 25.0
        }


class BacktestRequest(BaseModel):
    """Request para executar backtest"""
    
    symbol: str = Field(..., description="Símbolo para backtest")
    start_date: str = Field(..., description="Data inicial (YYYY-MM-DD)")
    end_date: str = Field(..., description="Data final (YYYY-MM-DD)")
    initial_capital: float = Field(default=10000.0, gt=0, description="Capital inicial")
    timeframe: str = Field(default="1h", description="Timeframe")
    
    # Parâmetros opcionais da estratégia
    take_profit: Optional[float] = Field(None, ge=0, le=1)
    stop_loss: Optional[float] = Field(None, ge=0, le=1)
    ai_score_threshold: Optional[float] = Field(None, ge=0, le=1)
    
    class Config:
        example = {
            "symbol": "BTC/USDT",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31", 
            "initial_capital": 10000.0,
            "timeframe": "1h",
            "take_profit": 0.10,
            "stop_loss": 0.03,
            "ai_score_threshold": 0.70
        }


class MLPredictionRequest(BaseModel):
    """Request para predição ML"""
    
    symbol: str = Field(..., description="Símbolo")
    price: float = Field(..., gt=0, description="Preço atual")
    volume: Optional[float] = Field(None, ge=0, description="Volume 24h")
    rsi: Optional[float] = Field(None, ge=0, le=100, description="RSI")
    macd: Optional[float] = Field(None, description="MACD")
    
    class Config:
        example = {
            "symbol": "BTC/USDT",
            "price": 45000.0,
            "volume": 2500000000,
            "rsi": 65.5,
            "macd": 0.012
        }


# ===== RESPONSE MODELS =====

class HealthResponse(BaseModel):
    """Response do health check"""
    
    status: str = Field(..., description="Status da API")
    timestamp: datetime = Field(..., description="Timestamp")
    api_version: str = Field(..., description="Versão da API")
    components_available: Dict[str, bool] = Field(..., description="Componentes disponíveis")


class BotStatusResponse(BaseModel):
    """Response do status do bot"""
    
    status: BotStatus = Field(..., description="Status atual")
    timestamp: datetime = Field(..., description="Timestamp")
    components: Dict[str, Any] = Field(default_factory=dict, description="Status dos componentes")
    uptime_hours: float = Field(..., description="Uptime em horas")
    
    class Config:
        example = {
            "status": "running",
            "timestamp": "2024-01-01T12:00:00",
            "components": {
                "bot_engine": {"available": True, "running": True},
                "ai_system": {"available": True, "health": "healthy"}
            },
            "uptime_hours": 24.5
        }


class BacktestResponse(BaseModel):
    """Response do backtest"""
    
    backtest_id: str = Field(..., description="ID do backtest")
    status: BacktestStatus = Field(..., description="Status")
    config: Dict[str, Any] = Field(..., description="Configuração usada")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Métricas de performance")
    trade_count: int = Field(..., description="Número de trades")
    created_at: datetime = Field(..., description="Data de criação")
    
    class Config:
        example = {
            "backtest_id": "bt_1640995200",
            "status": "completed",
            "config": {
                "symbol": "BTC/USDT",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            },
            "performance_metrics": {
                "total_return_pct": 12.34,
                "sharpe_ratio": 1.23,
                "max_drawdown_pct": 5.67
            },
            "trade_count": 45,
            "created_at": "2024-01-01T12:00:00"
        }


class PerformanceResponse(BaseModel):
    """Response das métricas de performance"""
    
    timestamp: datetime = Field(..., description="Timestamp")
    uptime_hours: float = Field(..., description="Uptime em horas")
    api_requests: int = Field(..., description="Total de requests")
    components_health: Dict[str, str] = Field(..., description="Health dos componentes")
    last_update: datetime = Field(..., description="Última atualização")


class TradeResponse(BaseModel):
    """Response de um trade"""
    
    trade_id: str = Field(..., description="ID do trade")
    symbol: str = Field(..., description="Símbolo")
    side: str = Field(..., description="Lado (buy/sell)")
    entry_price: float = Field(..., description="Preço de entrada")
    exit_price: Optional[float] = Field(None, description="Preço de saída")
    quantity: float = Field(..., description="Quantidade")
    pnl_pct: Optional[float] = Field(None, description="P&L em %")
    entry_time: datetime = Field(..., description="Horário de entrada")
    exit_time: Optional[datetime] = Field(None, description="Horário de saída")
    status: str = Field(..., description="Status do trade")


class MLPredictionResponse(BaseModel):
    """Response da predição ML"""
    
    symbol: str = Field(..., description="Símbolo")
    action: str = Field(..., description="Ação recomendada")
    confidence: float = Field(..., ge=0, le=1, description="Confiança")
    reasoning: str = Field(..., description="Reasoning da decisão")
    timestamp: datetime = Field(..., description="Timestamp")
    models_used: List[str] = Field(default_factory=list, description="Modelos utilizados")


class ExchangeHealthResponse(BaseModel):
    """Response do health das exchanges"""
    
    timestamp: datetime = Field(..., description="Timestamp")
    exchanges: Dict[str, Dict[str, Any]] = Field(..., description="Status das exchanges")
    summary: Dict[str, int] = Field(..., description="Resumo")


# ===== ERROR MODELS =====

class ErrorResponse(BaseModel):
    """Response de erro padrão"""
    
    error: str = Field(..., description="Mensagem de erro")
    error_code: Optional[str] = Field(None, description="Código do erro")
    timestamp: datetime = Field(..., description="Timestamp")
    request_id: Optional[str] = Field(None, description="ID da requisição")


class ValidationErrorResponse(BaseModel):
    """Response de erro de validação"""
    
    error: str = Field(..., description="Erro de validação")
    details: List[Dict[str, Any]] = Field(..., description="Detalhes dos erros")
    timestamp: datetime = Field(..., description="Timestamp")


# ===== WEBSOCKET MODELS =====

class WebSocketMessage(BaseModel):
    """Mensagem WebSocket"""
    
    type: str = Field(..., description="Tipo da mensagem")
    payload: Dict[str, Any] = Field(..., description="Dados da mensagem")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")


class BotStatusUpdate(BaseModel):
    """Update de status via WebSocket"""
    
    status: BotStatus = Field(..., description="Novo status")
    components: Dict[str, Any] = Field(..., description="Status dos componentes")
    timestamp: datetime = Field(..., description="Timestamp")


class NewTradeUpdate(BaseModel):
    """Update de novo trade via WebSocket"""
    
    trade: TradeResponse = Field(..., description="Dados do trade")
    portfolio_value: float = Field(..., description="Valor do portfólio")
    timestamp: datetime = Field(..., description="Timestamp")


# ===== PAGINATION MODELS =====

class PaginationParams(BaseModel):
    """Parâmetros de paginação"""
    
    page: int = Field(default=1, ge=1, description="Número da página")
    limit: int = Field(default=50, ge=1, le=1000, description="Itens por página")
    sort_by: Optional[str] = Field(None, description="Campo para ordenação")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="Ordem (asc/desc)")


class PaginatedResponse(BaseModel):
    """Response paginado"""
    
    items: List[Any] = Field(..., description="Itens da página")
    page: int = Field(..., description="Página atual")
    limit: int = Field(..., description="Itens por página")
    total: int = Field(..., description="Total de itens")
    pages: int = Field(..., description="Total de páginas")
    has_next: bool = Field(..., description="Tem próxima página")
    has_prev: bool = Field(..., description="Tem página anterior")