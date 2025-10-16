# interfaces/api/schemas.py
"""
Modelos Pydantic para o Maveretta AI Gateway
Contratos de API rigorosos - sem mocks, sempre estruturas válidas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ===== MODELOS DE SAÚDE =====
class IAHealth(BaseModel):
    """Modelo para saúde das IAs."""
    id: str = Field(..., description="ID único da IA")
    name: str = Field(..., description="Nome da IA")
    role: str = Field(..., description="Função/Especialidade")
    group: str = Field(..., description="Grupo (G1, G2, RESERVE)")
    state: str = Field(..., description="Estado: GREEN, AMBER, RED")
    latency_ms: Optional[float] = Field(None, description="Latência em ms")
    uptime_pct: Optional[float] = Field(None, description="Uptime percentual")
    last_decision: Optional[datetime] = Field(None, description="Última decisão")


class ExchangeHealth(BaseModel):
    """Modelo para saúde das exchanges."""
    id: Optional[str] = Field(None, description="ID único da exchange (opcional)")
    name: str = Field(..., description="Nome da exchange")
    state: str = Field(..., description="Estado: GREEN, AMBER, RED")
    latency_ms: Optional[float] = Field(None, description="Latência em ms")
    clock_skew_ms: Optional[float] = Field(None, description="Diferença de clock em ms")
    last_update: Optional[datetime] = Field(None, description="Última atualização")
    symbols_active: Optional[int] = Field(None, description="Símbolos ativos")


# ===== MODELOS DE TRADING =====
class Slot(BaseModel):
    """Modelo para slots de trading."""
    id: str = Field(..., description="ID único do slot")
    state: str = Field(..., description="Estado: GREEN, AMBER, RED")
    ia_id: str = Field(..., description="IA responsável")
    strategy: str = Field(..., description="Estratégia ativa")
    symbol: str = Field(..., description="Par negociado")
    confidence_pct: Optional[float] = Field(None, description="Confiança %")
    pnl_pct: Optional[float] = Field(None, description="PnL percentual")
    cash_allocated: Optional[float] = Field(None, description="Cash alocado (USDT)")
    position_size: Optional[float] = Field(None, description="Tamanho da posição")
    entry_price: Optional[float] = Field(None, description="Preço de entrada")
    current_price: Optional[float] = Field(None, description="Preço atual")


class Decision(BaseModel):
    """Modelo para decisões das IAs."""
    slot_id: str = Field(..., description="Slot afetado")
    ia_id: str = Field(..., description="IA que decidiu")
    strategy: str = Field(..., description="Estratégia usada")
    confidence_pct: float = Field(..., description="Confiança %")
    decided_at: datetime = Field(..., description="Timestamp da decisão")
    success: bool = Field(..., description="Sucesso da operação")
    latency_ms: Optional[float] = Field(None, description="Latência da decisão")


# ===== MODELOS DE CARTEIRA =====
class Wallet(BaseModel):
    """Modelo para carteira. Todos os campos são opcionais para não forçar mocks."""
    total_usdt: Optional[float] = Field(None, description="Total em USDT")
    total_brl: Optional[float] = Field(None, description="Total em BRL")
    pnl_daily: Optional[float] = Field(None, description="PnL diário (valor)")
    today_pnl_usdt: Optional[float] = Field(None, description="PnL de hoje em USDT")
    today_pnl_pct: Optional[float] = Field(None, description="PnL de hoje em %")
    allocation_pct: Optional[float] = Field(None, description="% do capital alocado")
    completed_cycles: Optional[int] = Field(None, description="Ciclos completos")
    active_positions: Optional[int] = Field(None, description="Posições ativas")
    deposits_7d: Optional[float] = Field(None, description="Depósitos (7 dias)")

    # Observação: saldos específicos podem vir como balance_<asset> via dict livre no payload.
    # Como o contrato é Pydantic, assets dinâmicos devem ser colocados em 'extra' no endpoint,
    # ou o serviço pode mapear esses saldos em campos fixos antes de serializar.
    # Para manter estrito aqui, deixamos apenas os campos comuns.


class RiskControls(BaseModel):
    """Modelo para controles de risco."""
    max_drawdown_pct: Optional[float] = Field(None, description="Max drawdown %")
    max_exposure_pct: Optional[float] = Field(None, description="Max exposição %")
    global_slots_limit: Optional[int] = Field(None, description="Limite global de slots")
    symbol_block_duration_h: Optional[float] = Field(None, description="Bloqueio de símbolo (horas)")


# ===== MODELOS DE ESTADO =====
class OrchestrationState(BaseModel):
    """Estado completo da orquestração (shape estável, sem mocks)."""
    ias: List[IAHealth] = Field(default_factory=list, description="IAs disponíveis")
    slots: List[Slot] = Field(default_factory=list, description="Slots ativos")
    decisions: List[Decision] = Field(default_factory=list, description="Decisões recentes")
    exchanges: List[ExchangeHealth] = Field(default_factory=list, description="Exchanges monitoradas")
    wallet: Wallet = Field(default_factory=Wallet, description="Estado da carteira")
    risk_controls: RiskControls = Field(default_factory=RiskControls, description="Controles de risco")

    class Config:
        schema_extra = {
            "example": {
                "ias": [],
                "slots": [],
                "decisions": [],
                "exchanges": [],
                "wallet": {},
                "risk_controls": {}
            }
        }


# ===== MODELOS DE LOG =====
class LogEntry(BaseModel):
    """Modelo para entradas de log (estruturado)."""
    timestamp: datetime = Field(..., description="Timestamp do log")
    level: str = Field(..., description="Nível: DEBUG, INFO, WARN, ERROR")
    source: str = Field(..., description="Fonte do log: IA, HUMAN, SYSTEM, EXCHANGE, etc.")
    message: str = Field(..., description="Mensagem")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalhes extras (json)")

    # Metadados úteis para deep-link na UI (todos opcionais)
    ia_id: Optional[str] = Field(None, description="IA relacionada ao evento")
    slot_id: Optional[str] = Field(None, description="Slot relacionado ao evento")
    exchange_id: Optional[str] = Field(None, description="Exchange relacionada")
    code: Optional[str] = Field(None, description="Código/erro/identificador do evento")


class LogResponse(BaseModel):
    """Resposta de logs."""
    logs: List[LogEntry] = Field(default_factory=list, description="Lista de logs")


# ===== MODELOS DE OVERRIDE =====
class OverrideRequest(BaseModel):
    """Request para override de estratégia (se/ quando habilitado)."""
    slot_id: str = Field(..., description="Slot para override")
    strategy_code: str = Field(..., description="Código da estratégia")


class OverrideResponse(BaseModel):
    """Resposta de override."""
    ok: bool = Field(..., description="Sucesso da operação")
    message: str = Field(..., description="Mensagem detalhada")


# ===== HEALTH =====
class HealthResponse(BaseModel):
    """Resposta de health check."""
    status: str = Field(..., description="Status: ok, error")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp do servidor")
    version: str = Field("1.0.0", description="Versão da API")


# ===== RESPONSE WRAPPERS (opcionais) =====
class IAListResponse(BaseModel):
    """Wrapper para lista de IAs."""
    ias: List[IAHealth] = Field(default_factory=list)


class SlotListResponse(BaseModel):
    """Wrapper para lista de slots."""
    slots: List[Slot] = Field(default_factory=list)


class ExchangeListResponse(BaseModel):
    """Wrapper para lista de exchanges."""
    exchanges: List[ExchangeHealth] = Field(default_factory=list)
