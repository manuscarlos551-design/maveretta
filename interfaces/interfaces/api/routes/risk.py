# interfaces/api/routes/risk.py
"""
Maveretta Risk Management API Routes
Endpoints para sistema de proteções e gestão de risco
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field

from core.risk import MaverettaProtectionManager, create_protection_manager
from core.risk.cooldown_manager import CooldownReason

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/risk", tags=["Risk Management"])

# Pydantic Models
class RiskEvaluationRequest(BaseModel):
    """Requisição de avaliação de risco"""
    slot_id: str = Field(..., description="ID do slot")
    protection_types: List[str] = Field(default=["stoploss_guard", "drawdown_guard", "cooldown"], description="Tipos de proteção a verificar")
    recent_trades: Optional[List[Dict[str, Any]]] = Field(default=[], description="Trades recentes para análise")
    current_capital: Optional[float] = Field(None, description="Capital atual do slot")

class ProtectionConfigRequest(BaseModel):
    """Requisição de configuração de proteção"""
    slot_id: str = Field(..., description="ID do slot")
    protection_type: str = Field(..., description="Tipo de proteção")
    duration_minutes: int = Field(..., ge=1, le=1440, description="Duração em minutos")
    reason: str = Field(default="Manual protection", description="Motivo da proteção")
    priority: Optional[int] = Field(default=2, ge=1, le=3, description="Prioridade (1=baixa, 2=média, 3=alta)")

class CooldownRequest(BaseModel):
    """Requisição de aplicação de cooldown"""
    slot_id: str = Field(..., description="ID do slot")
    reason: str = Field(..., description="Motivo do cooldown")
    duration_minutes: int = Field(..., ge=1, le=1440, description="Duração em minutos")
    description: str = Field(default="", description="Descrição adicional")

class TradeEventRequest(BaseModel):
    """Requisição de registro de evento de trade"""
    slot_id: str = Field(..., description="ID do slot")
    trade_data: Dict[str, Any] = Field(..., description="Dados do trade")

# Inicializar manager global
protection_manager = create_protection_manager()

@router.post("/evaluate")
async def evaluate_risk(request: RiskEvaluationRequest) -> Dict[str, Any]:
    """
    Avalia risco e proteções para um slot
    
    Args:
        request: Dados para avaliação de risco
        
    Returns:
        Status das proteções e permissões de trading
    """
    try:
        logger.info(f"[API] Evaluating risk for slot {request.slot_id}")
        
        # Processar trades recentes se fornecidos
        if request.recent_trades:
            for trade_data in request.recent_trades:
                protection_manager.register_trade_event(request.slot_id, trade_data)
        
        # Atualizar capital se fornecido
        if request.current_capital is not None:
            protection_manager.update_slot_capital(request.slot_id, request.current_capital)
        
        # Avaliar proteções
        protection_status = protection_manager.evaluate_slot_protection(
            slot_id=request.slot_id,
            recent_trades=request.recent_trades,
            current_capital=request.current_capital
        )
        
        # Adicionar informações detalhadas por tipo de proteção
        detailed_info = {}
        
        if "stoploss_guard" in request.protection_types and protection_manager.stoploss_guard:
            detailed_info["stoploss_guard"] = protection_manager.stoploss_guard.get_slot_protection_info(request.slot_id)
        
        if "drawdown_guard" in request.protection_types and protection_manager.drawdown_guard:
            detailed_info["drawdown_guard"] = protection_manager.drawdown_guard.get_slot_drawdown_info(request.slot_id)
        
        if "cooldown" in request.protection_types and protection_manager.cooldown_manager:
            detailed_info["cooldown"] = protection_manager.cooldown_manager.get_slot_cooldown_info(request.slot_id)
        
        # Preparar resposta
        response = {
            'slot_id': request.slot_id,
            'evaluation_timestamp': datetime.now().isoformat(),
            'can_trade': protection_status.get('can_trade', True),
            'any_protection_active': protection_status.get('any_protection_active', False),
            'protection_summary': protection_status.get('protection_summary', {}),
            'detailed_info': detailed_info,
            'risk_score': _calculate_risk_score(protection_status, detailed_info),
            'recommendations': _generate_recommendations(protection_status, detailed_info)
        }
        
        # Adicionar emergency stop se ativo
        if protection_status.get('emergency_stop'):
            response['emergency_stop'] = protection_status['emergency_stop']
        
        logger.info(f"[API] Risk evaluation completed for slot {request.slot_id}: can_trade={response['can_trade']}")
        
        return response
        
    except Exception as e:
        logger.error(f"[API] Error evaluating risk: {e}")
        raise HTTPException(status_code=500, detail=f"Risk evaluation failed: {str(e)}")

@router.get("/protections/status")
async def get_protections_status() -> Dict[str, Any]:
    """
    Retorna status global de todas as proteções
    
    Returns:
        Status detalhado do sistema de proteções
    """
    try:
        global_status = protection_manager.get_global_protection_status()
        
        return {
            'system_status': global_status,
            'timestamp': datetime.now().isoformat(),
            'components_health': {
                'stoploss_guard': protection_manager.stoploss_guard is not None,
                'drawdown_guard': protection_manager.drawdown_guard is not None,
                'cooldown_manager': protection_manager.cooldown_manager is not None
            }
        }
        
    except Exception as e:
        logger.error(f"[API] Error getting protections status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get protections status: {str(e)}")

@router.post("/protections/configure")
async def configure_protection(request: ProtectionConfigRequest) -> Dict[str, Any]:
    """
    Configura proteção para um slot
    
    Args:
        request: Configuração da proteção
        
    Returns:
        Status da configuração
    """
    try:
        logger.info(f"[API] Configuring {request.protection_type} protection for slot {request.slot_id}")
        
        # Validar tipo de proteção
        valid_types = ['cooldown', 'stoploss', 'drawdown']
        if request.protection_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid protection type. Must be one of: {valid_types}")
        
        # Aplicar proteção
        success = protection_manager.apply_manual_protection(
            slot_id=request.slot_id,
            protection_type=request.protection_type,
            duration_minutes=request.duration_minutes,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to apply {request.protection_type} protection")
        
        return {
            'success': True,
            'slot_id': request.slot_id,
            'protection_type': request.protection_type,
            'duration_minutes': request.duration_minutes,
            'reason': request.reason,
            'applied_at': datetime.now().isoformat(),
            'message': f"{request.protection_type.title()} protection applied to slot {request.slot_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error configuring protection: {e}")
        raise HTTPException(status_code=500, detail=f"Protection configuration failed: {str(e)}")

@router.delete("/protections/{slot_id}")
async def remove_protections(
    slot_id: str = Path(..., description="ID do slot"),
    protection_types: Optional[str] = Query(None, description="Tipos específicos para remover (separados por vírgula)")
) -> Dict[str, Any]:
    """
    Remove proteções de um slot
    
    Args:
        slot_id: ID do slot
        protection_types: Tipos específicos a remover
        
    Returns:
        Status da remoção
    """
    try:
        logger.info(f"[API] Removing protections for slot {slot_id}")
        
        # Processar tipos se especificados
        types_to_remove = None
        if protection_types:
            types_to_remove = [t.strip() for t in protection_types.split(',')]
        
        # Remover proteções
        results = protection_manager.remove_slot_protection(
            slot_id=slot_id,
            protection_types=types_to_remove
        )
        
        removed_protections = [ptype for ptype, success in results.items() if success]
        
        return {
            'success': len(removed_protections) > 0,
            'slot_id': slot_id,
            'removed_protections': removed_protections,
            'removal_results': results,
            'removed_at': datetime.now().isoformat(),
            'message': f"Removed {len(removed_protections)} protection(s) from slot {slot_id}"
        }
        
    except Exception as e:
        logger.error(f"[API] Error removing protections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove protections: {str(e)}")

@router.post("/cooldown/apply/{slot_id}")
async def apply_cooldown(
    request: CooldownRequest,
    slot_id: str = Path(..., description="ID do slot")
) -> Dict[str, Any]:
    """
    Aplica cooldown a um slot específico
    
    Args:
        slot_id: ID do slot
        request: Configuração do cooldown
        
    Returns:
        Status da aplicação do cooldown
    """
    try:
        if not protection_manager.cooldown_manager:
            raise HTTPException(status_code=503, detail="Cooldown manager not available")
        
        logger.info(f"[API] Applying cooldown to slot {slot_id}")
        
        # Mapear reason string para enum
        reason_mapping = {
            'manual': CooldownReason.MANUAL,
            'stoploss': CooldownReason.STOPLOSS,
            'drawdown': CooldownReason.DRAWDOWN,
            'performance': CooldownReason.PERFORMANCE,
            'market_conditions': CooldownReason.MARKET_CONDITIONS,
            'error_recovery': CooldownReason.ERROR_RECOVERY
        }
        
        cooldown_reason = reason_mapping.get(request.reason.lower(), CooldownReason.MANUAL)
        
        # Aplicar cooldown
        success = protection_manager.cooldown_manager.apply_cooldown(
            slot_id=slot_id,
            reason=cooldown_reason,
            duration_minutes=request.duration_minutes,
            description=request.description,
            priority=2  # Prioridade média para API
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to apply cooldown")
        
        # Obter informações do cooldown aplicado
        cooldown_info = protection_manager.cooldown_manager.get_slot_cooldown_info(slot_id)
        
        return {
            'success': True,
            'slot_id': slot_id,
            'cooldown_info': cooldown_info,
            'applied_at': datetime.now().isoformat(),
            'message': f"Cooldown applied to slot {slot_id} for {request.duration_minutes} minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error applying cooldown: {e}")
        raise HTTPException(status_code=500, detail=f"Cooldown application failed: {str(e)}")

@router.post("/events/trade")
async def register_trade_event(request: TradeEventRequest) -> Dict[str, Any]:
    """
    Registra evento de trade para análise de risco
    
    Args:
        request: Dados do evento de trade
        
    Returns:
        Status do registro
    """
    try:
        logger.debug(f"[API] Registering trade event for slot {request.slot_id}")
        
        # Registrar evento
        protection_manager.register_trade_event(
            slot_id=request.slot_id,
            trade_data=request.trade_data
        )
        
        # Verificar se alguma proteção foi ativada após o evento
        protection_status = protection_manager.evaluate_slot_protection(
            slot_id=request.slot_id,
            recent_trades=[request.trade_data]
        )
        
        return {
            'success': True,
            'slot_id': request.slot_id,
            'trade_registered': True,
            'protection_triggered': protection_status.get('any_protection_active', False),
            'can_continue_trading': protection_status.get('can_trade', True),
            'registered_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[API] Error registering trade event: {e}")
        raise HTTPException(status_code=500, detail=f"Trade event registration failed: {str(e)}")

@router.post("/emergency/activate")
async def activate_emergency_stop(
    reason: str = Query(..., description="Motivo do emergency stop")
) -> Dict[str, Any]:
    """
    Ativa emergency stop global
    
    Args:
        reason: Motivo da ativação
        
    Returns:
        Status da ativação
    """
    try:
        logger.warning(f"[API] Activating emergency stop: {reason}")
        
        success = protection_manager.activate_emergency_stop(reason)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to activate emergency stop")
        
        return {
            'success': True,
            'emergency_stop_active': True,
            'reason': reason,
            'activated_at': datetime.now().isoformat(),
            'message': "Emergency stop activated globally"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error activating emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency stop activation failed: {str(e)}")

@router.post("/emergency/deactivate")
async def deactivate_emergency_stop() -> Dict[str, Any]:
    """
    Desativa emergency stop global
    
    Returns:
        Status da desativação
    """
    try:
        logger.info("[API] Deactivating emergency stop")
        
        success = protection_manager.deactivate_emergency_stop()
        
        return {
            'success': success,
            'emergency_stop_active': False,
            'deactivated_at': datetime.now().isoformat(),
            'message': "Emergency stop deactivated" if success else "No active emergency stop"
        }
        
    except Exception as e:
        logger.error(f"[API] Error deactivating emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency stop deactivation failed: {str(e)}")

@router.get("/metrics/summary")
async def get_risk_metrics_summary() -> Dict[str, Any]:
    """
    Retorna resumo das métricas de risco
    
    Returns:
        Métricas agregadas do sistema de risco
    """
    try:
        # Obter resumos de cada componente
        global_status = protection_manager.get_global_protection_status()
        
        # Calcular métricas agregadas
        total_protected = global_status.get('total_protected_slots', 0)
        emergency_active = global_status.get('emergency_stop', {}).get('active', False)
        
        # Eventos recentes por nível de severidade
        recent_events = global_status.get('recent_events', [])
        events_by_level = {}
        for event in recent_events:
            level = event.get('level', 'medium')
            events_by_level[level] = events_by_level.get(level, 0) + 1
        
        return {
            'summary': {
                'total_protected_slots': total_protected,
                'emergency_stop_active': emergency_active,
                'system_health': 'critical' if emergency_active else ('warning' if total_protected > 0 else 'healthy')
            },
            'events_24h': {
                'by_severity': events_by_level,
                'total_events': len(recent_events)
            },
            'component_status': global_status.get('protection_components', {}),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[API] Error getting risk metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get risk metrics: {str(e)}")

def _calculate_risk_score(protection_status: Dict[str, Any], detailed_info: Dict[str, Any]) -> float:
    """Calcula score de risco (0.0 = baixo, 1.0 = alto)"""
    risk_score = 0.0
    
    # Proteções ativas aumentam o score
    if protection_status.get('any_protection_active', False):
        risk_score += 0.3
    
    # Emergency stop é risco máximo
    if protection_status.get('emergency_stop', {}).get('active', False):
        risk_score = 1.0
        return risk_score
    
    # Drawdown alto aumenta risco
    drawdown_info = detailed_info.get('drawdown_guard', {})
    if 'current_drawdown_pct' in drawdown_info:
        drawdown_pct = abs(drawdown_info['current_drawdown_pct'])
        risk_score += min(0.4, drawdown_pct * 2)  # Max 0.4 do drawdown
    
    # Múltiplos stoplosses aumentam risco
    stoploss_info = detailed_info.get('stoploss_guard', {})
    if 'events_count' in stoploss_info:
        events_count = stoploss_info['events_count']
        risk_score += min(0.3, events_count * 0.1)  # Max 0.3 dos stoplosses
    
    return min(1.0, risk_score)

def _generate_recommendations(protection_status: Dict[str, Any], detailed_info: Dict[str, Any]) -> List[str]:
    """Gera recomendações baseadas no status de proteção"""
    recommendations = []
    
    # Se não pode negociar
    if not protection_status.get('can_trade', True):
        recommendations.append("Trading pausado por proteções ativas - aguarde liberação")
    
    # Recomendações por tipo de proteção
    if detailed_info.get('drawdown_guard', {}).get('is_protected', False):
        recommendations.append("Alto drawdown detectado - considere revisar estratégia")
    
    if detailed_info.get('stoploss_guard', {}).get('active', False):
        recommendations.append("Múltiplos stoplosses recentes - revise condições de mercado")
    
    if detailed_info.get('cooldown', {}).get('active', False):
        cooldown_reason = detailed_info['cooldown'].get('reason', '')
        recommendations.append(f"Em cooldown ({cooldown_reason}) - aguarde término")
    
    # Se tudo ok
    if not recommendations:
        recommendations.append("Sistema operando normalmente - risco baixo")
    
    return recommendations

# =============================================================================
# RISK CONFIGURATION AND STATUS - FASE 3 IMPLEMENTATION
# =============================================================================

class RiskConfig(BaseModel):
    max_exposure_pct: float = Field(50.0, ge=0, le=100, description="Exposição máxima permitida em % do capital.")
    max_loss_per_trade_pct: float = Field(2.0, ge=0, le=10, description="Perda máxima permitida por trade em %.")
    max_open_positions: int = Field(5, ge=1, le=20, description="Número máximo de posições abertas simultaneamente.")
    trailing_stop_enabled: bool = Field(True, description="Habilita trailing stop globalmente.")

# Usar um cliente Redis para persistir a configuração de risco
import redis
import json

def _get_redis_client():
    """Obtém cliente Redis"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Erro ao conectar Redis para risco: {e}")
        return None

@router.get("/v1/risk/config", response_model=RiskConfig)
async def get_risk_config() -> RiskConfig:
    """
    Retorna a configuração de risco atual do sistema.
    """
    try:
        redis_client = _get_redis_client()
        if redis_client:
            config_data = redis_client.get("risk:config")
            if config_data:
                return RiskConfig.parse_raw(config_data)
        # Retorna configuração padrão se não houver no Redis ou Redis indisponível
        return RiskConfig()
    except Exception as e:
        logger.error(f"Erro ao obter configuração de risco: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

@router.post("/v1/risk/config", response_model=Dict[str, Any])
async def set_risk_config(config: RiskConfig) -> Dict[str, Any]:
    """
    Atualiza a configuração de risco do sistema.
    """
    try:
        redis_client = _get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis não disponível para salvar configuração de risco")
        
        redis_client.set("risk:config", config.json())
        logger.info(f"Configuração de risco atualizada: {config.dict()}")
        return {"status": "ok", "message": "Configuração de risco atualizada com sucesso", "config": config.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao salvar configuração de risco: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

@router.get("/v1/risk/status", response_model=Dict[str, Any])
async def get_risk_status() -> Dict[str, Any]:
    """
    Retorna o status atual do sistema de risco, incluindo se o emergency stop está ativo.
    """
    try:
        global_status = protection_manager.get_global_protection_status()
        risk_config = await get_risk_config() # Obter a configuração atual

        return {
            "status": "ok",
            "emergency_stop_active": global_status.get("emergency_stop", {}).get("active", False),
            "global_protection_active": global_status.get("global_protection_active", False),
            "total_protected_slots": global_status.get("total_protected_slots", 0),
            "current_risk_config": risk_config.dict(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao obter status de risco: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

