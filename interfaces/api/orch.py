# interfaces/api/orch.py
"""
Orchestration Router - Define todas as rotas /v1/* do AI Gateway
Usa modelos Pydantic para validação rigorosa e respostas padronizadas
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
import logging

# Import dos serviços e modelos
from interfaces.api.services.core_state import (
    get_ia_health as core_get_ia_health,
    get_exchange_health as core_get_exchange_health,
    get_orchestration_state as core_get_orchestration_state,
    post_override_strategy as core_post_override_strategy,
    get_slots as core_get_slots,
    get_logs as core_get_logs,
    health_check as core_health_check,
    get_operations as core_get_operations,
    get_controls as core_get_controls,
    get_ia_insights as core_get_ia_insights,
    get_alerts as core_get_alerts,
    get_backtests as core_get_backtests,
    get_strategies as core_get_strategies,
    get_wallet_details as core_get_wallet_details
)

# Import do agent registry e slot loader reais
from core.agents.agent_registry import get_all_agent_stats
from core.slots.slot_loader import get_all_slots as get_real_slots

from interfaces.api.schemas import (
    HealthResponse, IAListResponse, ExchangeListResponse, 
    OrchestrationState, SlotListResponse, LogResponse,
    OverrideRequest, OverrideResponse
)

# Configuração de logging
logger = logging.getLogger(__name__)

# Router principal com prefixo /v1
orch_router = APIRouter(prefix="/v1", tags=["core"])

@orch_router.get(
    "/health", 
    response_model=HealthResponse,
    summary="Health Check do Sistema",
    description="Verifica a saúde geral do AI Gateway e serviços dependentes"
)
def health():
    """
    Health check completo do sistema
    - Verifica conectividade com MongoDB, Redis, Bot Core
    - Retorna status geral e saúde por serviço
    """
    try:
        health_data = core_health_check()
        return HealthResponse(
            status=health_data.get('status', 'unknown'),
            timestamp=health_data.get('timestamp'),
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"❌ Erro no health check: {e}")
        return HealthResponse(
            status="error",
            version="1.0.0"
        )

@orch_router.get(
    "/ias/health",
    response_model=IAListResponse,
    summary="Health das IAs",
    description="Retorna o status de saúde de todas as IAs disponíveis"
)
def get_ia_health():
    """
    Status de saúde das IAs de trading
    - Consulta agent registry REAL
    - Retorna lista vazia se não houver IAs disponíveis
    - Inclui métricas de latência e uptime quando disponíveis
    """
    try:
        # CORREÇÃO: Usa agent registry real
        ias = get_all_agent_stats()
        logger.info(f"📊 Retornando {len(ias)} agentes")
        return IAListResponse(ias=ias)
    except Exception as e:
        logger.error(f"❌ Erro ao buscar health das IAs: {e}")
        # Em caso de erro, retorna lista vazia (não quebra o contrato)
        return IAListResponse(ias=[])

@orch_router.get(
    "/exchanges/health",
    response_model=ExchangeListResponse,
    summary="Health das Exchanges",
    description="Retorna o status de conectividade com as exchanges"
)
def get_exchange_health():
    """
    Status de saúde das exchanges conectadas
    - Verifica conectividade em tempo real
    - Inclui métricas de latência e disponibilidade
    - Retorna lista vazia se não houver exchanges disponíveis
    """
    try:
        exchanges = core_get_exchange_health()
        return ExchangeListResponse(exchanges=exchanges)
    except Exception as e:
        logger.error(f"❌ Erro ao buscar health das exchanges: {e}")
        return ExchangeListResponse(exchanges=[])

@orch_router.get(
    "/orchestration/state",
    response_model=OrchestrationState,
    summary="Estado Completo da Orquestração",
    description="Retorna o estado completo do sistema de orquestração"
)
def get_orchestration_state():
    """
    Estado completo do sistema de orquestração
    - Combina dados de IAs, slots, decisões, exchanges, carteira e controles de risco
    - SEMPRE retorna estrutura válida, mesmo que com dados vazios
    - Fonte única de verdade para o dashboard
    """
    try:
        state = core_get_orchestration_state()
        return state
    except Exception as e:
        logger.error(f"❌ Erro ao buscar estado de orquestração: {e}")
        # Retorna estado vazio mas válido em caso de erro
        return OrchestrationState()

@orch_router.get(
    "/slots",
    response_model=SlotListResponse,
    summary="Lista de Slots de Trading",
    description="Retorna todos os slots de trading ativos no sistema"
)
def get_slots():
    """
    Lista de slots de trading
    - Slots ativos com suas estratégias, IAs responsáveis e métricas
    - Retorna lista vazia se não houver slots ativos
    - Ordenados por data de criação (mais recentes primeiro)
    """
    try:
        # CORREÇÃO: Usa slot loader real
        slots = get_real_slots()
        logger.info(f"📊 Retornando {len(slots)} slots")
        return SlotListResponse(slots=slots)
    except Exception as e:
        logger.error(f"❌ Erro ao buscar slots: {e}")
        return SlotListResponse(slots=[])

@orch_router.get(
    "/logs",
    response_model=LogResponse,
    summary="Logs do Sistema",
    description="Retorna logs do sistema com filtros opcionais"
)
def get_logs(
    source: Optional[str] = Query(None, description="Filtrar por fonte do log"),
    level: Optional[str] = Query(None, description="Filtrar por nível (INFO, WARN, ERROR)"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de logs (1-1000)")
):
    """
    Logs do sistema com filtragem
    - Filtros opcionais por fonte e nível
    - Limite padrão de 100 logs (máximo 1000)
    - Retorna logs mais recentes primeiro
    - Estrutura vazia se não houver logs
    """
    try:
        logs_data = core_get_logs(source=source, level=level, limit=limit)
        return logs_data
    except Exception as e:
        logger.error(f"❌ Erro ao buscar logs: {e}")
        return LogResponse(logs=[])

@orch_router.post(
    "/override",
    response_model=OverrideResponse,
    summary="Override de Estratégia",
    description="Aplica override de estratégia em slot específico",
    status_code=status.HTTP_200_OK
)
def post_override(payload: OverrideRequest):
    """
    Override de estratégia em slot
    - Apenas slots em estado AMBER podem receber override
    - Valida paridade do slot (ímpares vs pares)
    - Requer permissões específicas (implementar futuramente)
    """
    try:
        # Converte para dict para o core service
        payload_dict = payload.dict()
        
        # Chama o core service para aplicar o override
        success, message = core_post_override_strategy(payload_dict)
        
        if not success:
            # Retorna 409 Conflict para override não permitido
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message
            )
        
        return OverrideResponse(ok=success, message=message)
        
    except HTTPException:
        # Re-lança exceções HTTP existentes
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar override: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao processar override: {str(e)}"
        )

@orch_router.get(
    "/metrics",
    summary="Métricas Prometheus",
    description="Endpoint de métricas para coleta do Prometheus"
)
def get_metrics():
    """
    Métricas do sistema no formato Prometheus
    - Métricas de performance, erro e saúde do sistema
    - Formato texto plano para o Prometheus scraper
    """
    try:
        # Em uma implementação completa, aqui retornaríamos métricas reais
        # Por enquanto retorna estrutura básica
        metrics_text = """# HELP ai_gateway_requests_total Total de requests no AI Gateway
# TYPE ai_gateway_requests_total counter
ai_gateway_requests_total 0

# HELP ai_gateway_errors_total Total de erros no AI Gateway  
# TYPE ai_gateway_errors_total counter
ai_gateway_errors_total 0

# HELP ai_gateway_health_status Status de saúde do AI Gateway (1=healthy, 0=unhealthy)
# TYPE ai_gateway_health_status gauge
ai_gateway_health_status 1
"""
        return metrics_text
    except Exception as e:
        logger.error(f"❌ Erro ao gerar métricas: {e}")
        return "# ERROR: Não foi possível gerar métricas\n"

# ===== ROTAS DE DESENVOLVIMENTO (OPCIONAIS) =====

@orch_router.get(
    "/debug/connections",
    include_in_schema=False,  # Não aparece na documentação OpenAPI
    summary="Debug de Conexões",
    description="Endpoint de debug para verificar conectividade com serviços"
)
def debug_connections():
    """
    Debug de conectividade com serviços
    - Apenas para desenvolvimento/troubleshooting
    - Não aparece na documentação pública
    """
    try:
        health_data = core_health_check()
        return {
            "status": "debug",
            "services": health_data.get('services', {}),
            "timestamp": health_data.get('timestamp')
        }
    except Exception as e:
        logger.error(f"❌ Erro no debug de conexões: {e}")
        return {"status": "error", "message": str(e)}

@orch_router.get(
    "/version",
    summary="Versão da API",
    description="Retorna a versão atual do AI Gateway"
)
def get_version():
    """
    Informações de versão do sistema
    - Útil para verificar deployments e compatibilidade
    """
    return {
        "version": "1.0.0",
        "name": "Maveretta AI Gateway",
        "environment": "production"
    }

# ===== ENDPOINTS ADICIONAIS PARA DASHBOARD =====

@orch_router.get(
    "/operations",
    summary="Operações de Trading",
    description="Lista as operações de trading recentes"
)
def get_operations(limit: int = Query(50, ge=1, le=200, description="Limite de operações")):
    """
    Lista de operações de trading recentes
    - Busca operações em todas as exchanges
    - Inclui status, P&L e métricas
    - Ordenado por timestamp (mais recente primeiro)
    """
    try:
        operations = core_get_operations(limit=limit)
        return {"operations": operations}
    except Exception as e:
        logger.error(f"❌ Erro ao buscar operações: {e}")
        return {"operations": []}

@orch_router.get(
    "/controls",
    summary="Controles do Sistema",
    description="Estado atual dos controles do sistema"
)
def get_controls():
    """
    Estado dos controles do sistema
    - Controles principais (ativo/inativo)
    - Overrides manuais aplicados
    - Configurações de emergência
    """
    try:
        controls = core_get_controls()
        return controls
    except Exception as e:
        logger.error(f"❌ Erro ao buscar controles: {e}")
        return {"controls": {}, "overrides": {}}

@orch_router.get(
    "/ia/insights",
    summary="Insights das IAs",
    description="Insights e análises das inteligências artificiais"
)
def get_ia_insights():
    """
    Insights das IAs
    - Análises recentes geradas pelas IAs
    - Performance e estatísticas
    - Tendências e padrões identificados
    """
    try:
        insights = core_get_ia_insights()
        return insights
    except Exception as e:
        logger.error(f"❌ Erro ao buscar insights das IAs: {e}")
        return {"insights": [], "performance": {}}

@orch_router.get(
    "/alerts",
    summary="Alertas do Sistema",
    description="Alertas ativos e notificações"
)
def get_alerts():
    """
    Alertas do sistema
    - Alertas críticos que requerem atenção imediata
    - Avisos e notificações
    - Status de resolução
    """
    try:
        alerts = core_get_alerts()
        return alerts
    except Exception as e:
        logger.error(f"❌ Erro ao buscar alertas: {e}")
        return {"alerts": [], "critical": [], "warnings": []}

@orch_router.get(
    "/backtests",
    summary="Resultados de Backtests",
    description="Lista os backtests executados"
)
def get_backtests(limit: int = Query(20, ge=1, le=100, description="Limite de backtests")):
    """
    Backtests executados
    - Resultados de testes históricos
    - Performance por estratégia
    - Comparações e análises
    """
    try:
        backtests = core_get_backtests(limit=limit)
        return {"backtests": backtests}
    except Exception as e:
        logger.error(f"❌ Erro ao buscar backtests: {e}")
        return {"backtests": []}

@orch_router.get(
    "/strategies",
    summary="Estratégias de Trading",
    description="Lista as estratégias configuradas"
)
def get_strategies():
    """
    Estratégias de trading
    - Estratégias ativas e disponíveis
    - Configurações e parâmetros
    - Performance histórica
    """
    try:
        strategies = core_get_strategies()
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"❌ Erro ao buscar estratégias: {e}")
        return {"strategies": []}

@orch_router.get(
    "/wallet",
    summary="Detalhes da Carteira",
    description="Informações detalhadas da carteira"
)
def get_wallet():
    """
    Detalhes da carteira
    - Saldos por exchange
    - Ativos e posições
    - Histórico de transações
    """
    try:
        wallet = core_get_wallet_details()
        return wallet
    except Exception as e:
        logger.error(f"❌ Erro ao buscar detalhes da carteira: {e}")
        return {"exchanges": {}, "balances": {}, "positions": {}}