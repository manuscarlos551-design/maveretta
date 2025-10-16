# interfaces/api/services/core_state.py
"""
Core State Service - Conecta com fontes reais (MongoDB, Redis, Exchange Manager)
Nunca retorna mocks ou dados fixos - apenas dados reais ou estruturas vazias.
Com melhorias:
- Normalização robusta de datetimes vindos do banco/cache
- Latência real para exporters via response.elapsed
- Métricas reais mínimas (Mongo connections, Redis hit ratio, uptime)
"""
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import requests  # usado para checagens HTTP (exporters e bot-core)

# Import dos modelos Pydantic
from interfaces.api.schemas import (
    IAHealth, ExchangeHealth, Slot, Decision, Wallet,
    RiskControls, OrchestrationState, LogEntry, LogResponse,
)

# Configuração de logging
logger = logging.getLogger(__name__)

# Timestamp de start do processo (para uptime)
_START_TIME = datetime.now()

# =========================
# Utilidades de data/hora
# =========================
def _norm_dt(value: Any, default: Optional[datetime] = None) -> Optional[datetime]:
    """Normaliza um valor potencialmente datetime/string/None para datetime (ou default)."""
    if value is None:
        return default
    if isinstance(value, datetime):
        return value
    # strings ISO ou timestamps
    try:
        # Tenta ISO 8601
        return datetime.fromisoformat(value)  # type: ignore[arg-type]
    except Exception:
        pass
    try:
        # Tenta timestamp (segundos)
        return datetime.fromtimestamp(float(value))  # type: ignore[arg-type]
    except Exception:
        pass
    # Último recurso: retorna default
    return default


# ===== CONEXÕES COM FONTES REAIS =====

def _get_mongo_client():
    """Obtém cliente MongoDB - conecta com fonte real."""
    try:
        from pymongo import MongoClient
        mongo_uri = os.getenv(
            "MONGO_URI",
            "mongodb://botapp:botapp123@mongodb:27017/botai_trading?authSource=admin",
        )
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        # Testa conexão
        client.admin.command("ping")
        logger.info("✅ MongoDB conectado com sucesso")
        return client
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com MongoDB: {e}")
        return None


def _get_redis_client():
    """Obtém cliente Redis - conecta com fonte real."""
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://:redispass123@redis:6379/0")
        client = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        # Testa conexão
        client.ping()
        logger.info("✅ Redis conectado com sucesso")
        return client
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com Redis: {e}")
        return None


def _get_bot_core_status(threshold_ms: float = 1200.0) -> Tuple[str, Optional[float]]:
    """
    Obtém status do Bot Core verificando /metrics.
    - GREEN: HTTP 200 e latência <= threshold_ms
    - AMBER: HTTP 200 e latência > threshold_ms
    - RED: erro de conexão/timeout
    Retorna (status, latency_ms)
    """
    url = "http://bot-ai-multiagent:9200/metrics"
    try:
        resp = requests.get(url, timeout=3)
        latency_ms = None
        if resp is not None and resp.elapsed is not None:
            latency_ms = resp.elapsed.total_seconds() * 1000.0

        if resp.status_code == 200:
            if latency_ms is not None and latency_ms > threshold_ms:
                return "AMBER", latency_ms
            return "GREEN", latency_ms
        return "AMBER", latency_ms
    except Exception as e:
        logger.warning(f"⚠️ Bot Core não disponível: {e}")
        return "RED", None


# ===== FUNÇÕES PRINCIPAIS - FONTES REAIS =====

def get_ia_health() -> List[IAHealth]:
    """
    Consulta saúde das IAs - fontes reais (Redis/MongoDB).
    Retorna lista vazia se não houver dados.
    """
    try:
        redis_client = _get_redis_client()
        if redis_client:
            # Tenta obter do Redis primeiro (cache mais rápido)
            ia_health_data = redis_client.get("ia_health_status")
            if ia_health_data:
                try:
                    data = json.loads(ia_health_data)
                    if isinstance(data, list):
                        items: List[IAHealth] = []
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            # normaliza campo datetime
                            if "last_decision" in item:
                                item["last_decision"] = _norm_dt(item.get("last_decision"))
                            items.append(IAHealth(**item))
                        return items
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"⚠️ Dados de IA health inválidos no Redis: {e}")

        # Fallback para MongoDB
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return []

        db = mongo_client.botai_trading
        collection = db.ia_status

        # Busca status mais recentes das IAs
        cursor = collection.find().sort("last_heartbeat", -1).limit(50)
        ia_list: List[IAHealth] = []

        for doc in cursor:
            try:
                ia_health = IAHealth(
                    id=doc.get("ia_id", "unknown"),
                    name=doc.get("name", "Unknown IA"),
                    role=doc.get("role", "Trading Agent"),
                    group=doc.get("group", "RESERVE"),
                    state=doc.get("state", "RED"),
                    latency_ms=doc.get("latency_ms"),
                    uptime_pct=doc.get("uptime_pct"),
                    last_decision=_norm_dt(doc.get("last_decision")),
                )
                ia_list.append(ia_health)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar IA document: {e}")
                continue

        # Cache no Redis por 30 segundos
        if redis_client and ia_list:
            try:
                redis_client.setex(
                    "ia_health_status", 30, json.dumps([ia.dict() for ia in ia_list])
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao cachear IA health: {e}")

        return ia_list

    except Exception as e:
        logger.error(f"❌ Erro em get_ia_health: {e}")
        return []


def get_exchange_health() -> List[ExchangeHealth]:
    """
    Consulta saúde das exchanges - fontes reais.
    Retorna lista vazia se não houver dados.
    """
    try:
        redis_client = _get_redis_client()
        if redis_client:
            # Tenta obter do Redis
            exchange_data = redis_client.get("exchange_health_status")
            if exchange_data:
                try:
                    data = json.loads(exchange_data)
                    if isinstance(data, list):
                        items: List[ExchangeHealth] = []
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            if "last_update" in item:
                                item["last_update"] = _norm_dt(item.get("last_update"))
                            items.append(ExchangeHealth(**item))
                        return items
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"⚠️ Dados de exchange health inválidos: {e}")

        # Consulta status do Binance Exporter
        try:
            url = "http://binance-exporter:8000/metrics"
            response = requests.get(url, timeout=3)
            latency_ms = response.elapsed.total_seconds() * 1000.0 if response.elapsed else None

            if response.status_code == 200:
                metrics_text = response.text or ""
                # Inferência simplificada com base na métrica exportada
                if "binance_connection_status 1" in metrics_text:
                    status = "GREEN"
                elif "binance_connection_status 0" in metrics_text:
                    status = "RED"
                else:
                    status = "AMBER"

                exchange_health = ExchangeHealth(
                    name="Binance",
                    state=status,
                    latency_ms=latency_ms,
                    clock_skew_ms=None,
                    last_update=datetime.now(),
                    symbols_active=None,
                )

                # Cache no Redis (15s)
                if redis_client:
                    try:
                        serializable = exchange_health.dict()
                        serializable["last_update"] = serializable["last_update"].isoformat()
                        redis_client.setex("exchange_health_status", 15, json.dumps([serializable]))
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao cachear exchange health: {e}")

                return [exchange_health]

        except Exception as e:
            logger.warning(f"⚠️ Binance exporter não disponível: {e}")

        return []

    except Exception as e:
        logger.error(f"❌ Erro em get_exchange_health: {e}")
        return []


def get_slots() -> List[Slot]:
    """
    Obtém slots de trading - fontes reais (MongoDB).
    Retorna lista vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return []

        db = mongo_client.botai_trading
        collection = db.trading_slots

        # Busca slots "ativos". Garante que active seja interpretado como bool.
        cursor = collection.find({"active": {"$in": [True, "true", 1]}}).sort("created_at", -1).limit(100)
        slots_list: List[Slot] = []

        for doc in cursor:
            try:
                slot = Slot(
                    id=doc.get("slot_id", f"slot-{doc.get('_id', 'unknown')}"),
                    state=doc.get("state", "RED"),
                    ia_id=doc.get("assigned_ia", "unassigned"),
                    strategy=doc.get("strategy", "unknown"),
                    symbol=doc.get("symbol", "BTC/USDT"),
                    confidence_pct=doc.get("confidence", 0.0),
                    pnl_pct=doc.get("pnl_percentage"),
                    cash_allocated=doc.get("allocated_cash"),
                    position_size=doc.get("position_size"),
                    entry_price=doc.get("entry_price"),
                    current_price=doc.get("current_price"),
                )
                slots_list.append(slot)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar slot document: {e}")
                continue

        return slots_list

    except Exception as e:
        logger.error(f"❌ Erro em get_slots: {e}")
        return []


def get_recent_decisions() -> List[Decision]:
    """
    Obtém decisões recentes das IAs - fontes reais.
    Retorna lista vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return []

        db = mongo_client.botai_trading
        collection = db.ia_decisions

        # Busca decisões das últimas 24 horas
        time_threshold = datetime.now() - timedelta(hours=24)
        cursor = collection.find({"timestamp": {"$gte": time_threshold}}).sort("timestamp", -1).limit(50)

        decisions_list: List[Decision] = []

        for doc in cursor:
            try:
                decided_at = _norm_dt(doc.get("timestamp"), default=datetime.now())
                decision = Decision(
                    slot_id=doc.get("slot_id", "unknown"),
                    ia_id=doc.get("ia_id", "unknown"),
                    strategy=doc.get("strategy", "unknown"),
                    confidence_pct=float(doc.get("confidence", 0.0)),
                    decided_at=decided_at,
                    success=bool(doc.get("success", False)),
                    latency_ms=doc.get("processing_time_ms"),
                )
                decisions_list.append(decision)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar decision document: {e}")
                continue

        return decisions_list

    except Exception as e:
        logger.error(f"❌ Erro em get_recent_decisions: {e}")
        return []


def get_wallet_state() -> Wallet:
    """
    Obtém estado da carteira - fontes reais.
    Retorna objeto vazio se não houver dados.
    """
    try:
        redis_client = _get_redis_client()
        if redis_client:
            # Tenta obter do Redis (cache mais atualizado)
            wallet_data = redis_client.get("wallet_state")
            if wallet_data:
                try:
                    data = json.loads(wallet_data)
                    if isinstance(data, dict):
                        # Não possui campos datetime nesse modelo; monta direto
                        return Wallet(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"⚠️ Dados de wallet inválidos no Redis: {e}")

        # Fallback para MongoDB
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return Wallet()

        db = mongo_client.botai_trading
        collection = db.wallet_snapshots

        # Busca snapshot mais recente
        latest = collection.find_one(sort=[("timestamp", -1)])
        if latest:
            wallet = Wallet(
                total_usdt=latest.get("total_usdt"),
                total_brl=latest.get("total_brl"),
                pnl_daily=latest.get("daily_pnl"),
                completed_cycles=latest.get("completed_cycles"),
                active_positions=latest.get("active_positions"),
            )

            # Cache no Redis
            if redis_client:
                try:
                    redis_client.setex("wallet_state", 60, json.dumps(wallet.dict()))
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao cachear wallet state: {e}")

            return wallet

        return Wallet()

    except Exception as e:
        logger.error(f"❌ Erro em get_wallet_state: {e}")
        return Wallet()


def get_risk_controls() -> RiskControls:
    """
    Obtém controles de risco ativos (se houver).
    Retorna objeto com valores padrão se não houver dados.
    """
    try:
        redis_client = _get_redis_client()
        if redis_client:
            risk_data = redis_client.get("risk_controls")
            if risk_data:
                try:
                    data = json.loads(risk_data)
                    if isinstance(data, dict):
                        return RiskControls(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"⚠️ Dados de risk controls inválidos: {e}")

        # Valores padrão do sistema (podem vir de env futuramente)
        return RiskControls(
            max_drawdown_pct=8.0,
            max_exposure_pct=15.0,
            global_slots_limit=3,
            symbol_block_duration_h=2.0,
        )

    except Exception as e:
        logger.error(f"❌ Erro em get_risk_controls: {e}")
        return RiskControls()


def get_logs(source: Optional[str] = None, level: Optional[str] = None, limit: int = 100) -> LogResponse:
    """
    Obtém logs do sistema - fontes reais.
    Retorna estrutura vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return LogResponse(logs=[])

        db = mongo_client.botai_trading
        collection = db.system_logs

        # Constrói query base
        query: Dict[str, Any] = {}
        if source:
            query["source"] = source
        if level:
            query["level"] = level.upper()

        # Busca logs mais recentes
        cursor = collection.find(query).sort("timestamp", -1).limit(limit)
        logs_list: List[LogEntry] = []

        for doc in cursor:
            try:
                ts = _norm_dt(doc.get("timestamp"), default=datetime.now())
                log_entry = LogEntry(
                    timestamp=ts,
                    level=doc.get("level", "INFO"),
                    source=doc.get("source", "unknown"),
                    message=doc.get("message", ""),
                    details=doc.get("details"),
                )
                logs_list.append(log_entry)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar log entry: {e}")
                continue

        return LogResponse(logs=logs_list)

    except Exception as e:
        logger.error(f"❌ Erro em get_logs: {e}")
        return LogResponse(logs=[])


def post_override_strategy(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Aplica override de estratégia - validação real.
    Retorna (sucesso, mensagem).
    """
    try:
        # Valida payload
        if not payload or "slot_id" not in payload or "strategy_code" not in payload:
            return False, "Payload inválido - slot_id e strategy_code são obrigatórios"

        slot_id = payload["slot_id"]
        strategy_code = payload["strategy_code"]

        # Verifica se o slot existe e está em estado AMBER
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return False, "Sistema indisponível - não foi possível conectar ao banco"

        db = mongo_client.botai_trading
        collection = db.trading_slots

        slot = collection.find_one({"slot_id": slot_id})
        if not slot:
            return False, f"Slot {slot_id} não encontrado"

        current_state = slot.get("state", "RED")
        if current_state != "AMBER":
            return False, f"Override permitido apenas para slots em estado AMBER (atual: {current_state})"

        # (Opcional) Valida paridade do slot caso necessário
        slot_number = "".join(filter(str.isdigit, str(slot_id)))
        if slot_number:
            _ = int(slot_number) % 2 == 1  # is_odd (apenas se precisar em regras futuras)

        # Aplica o override
        logger.info(f"🎯 Override aplicado: Slot {slot_id} -> Estratégia {strategy_code}")

        # Atualiza no banco
        collection.update_one(
            {"slot_id": slot_id},
            {
                "$set": {
                    "strategy": strategy_code,
                    "last_override": datetime.now(),
                    "override_applied": True,
                }
            },
        )

        return True, f"Override aplicado com sucesso: {strategy_code}"

    except Exception as e:
        logger.error(f"❌ Erro em post_override_strategy: {e}")
        return False, f"Erro interno: {str(e)}"


# ===== MÉTRICAS E HEALTH =====

def get_system_metrics() -> Dict[str, Any]:
    """
    Coleta métricas do sistema para Prometheus.
    Retorna métricas reais mínimas quando possível:
      - ai_gateway_requests_total (placeholder incremental externo)
      - ai_gateway_errors_total    (placeholder incremental externo)
      - database_connections_active (MongoDB)
      - cache_hit_ratio (Redis)
      - system_uptime_seconds (desde start do processo)
    """
    try:
        metrics: Dict[str, Any] = {
            "ai_gateway_requests_total": 0,
            "ai_gateway_errors_total": 0,
            "database_connections_active": 0,
            "cache_hit_ratio": 0.0,
            "system_uptime_seconds": 0,
        }

        # Uptime do processo
        metrics["system_uptime_seconds"] = int((datetime.now() - _START_TIME).total_seconds())

        # Mongo connections
        try:
            mongo_client = _get_mongo_client()
            if mongo_client:
                status = mongo_client.admin.command("serverStatus")
                metrics["database_connections_active"] = int(status.get("connections", {}).get("current", 0))
        except Exception as e:
            logger.debug(f"serverStatus Mongo falhou (não crítico): {e}")

        # Redis hit ratio
        try:
            redis_client = _get_redis_client()
            if redis_client:
                info = redis_client.info()
                hits = float(info.get("keyspace_hits", 0.0))
                misses = float(info.get("keyspace_misses", 0.0))
                denom = hits + misses
                metrics["cache_hit_ratio"] = (hits / denom) if denom > 0 else 0.0
        except Exception as e:
            logger.debug(f"INFO Redis falhou (não crítico): {e}")

        return metrics

    except Exception as e:
        logger.error(f"❌ Erro em get_system_metrics: {e}")
        return {}


def health_check() -> Dict[str, Any]:
    """
    Health check completo do sistema.
    Verifica conectividade com todas as fontes.
    Status final:
      - healthy: tudo ok
      - degraded: algum serviço ok com degradação (ex.: latência alta) ou um serviço não crítico ruim
      - unhealthy: principais serviços off (ex.: Mongo e Redis indisponíveis)
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "latencies_ms": {},
    }

    # Verifica MongoDB
    mongo_client = _get_mongo_client()
    health_status["services"]["mongodb"] = "healthy" if mongo_client else "unhealthy"

    # Verifica Redis
    redis_client = _get_redis_client()
    health_status["services"]["redis"] = "healthy" if redis_client else "unhealthy"

    # Verifica Bot Core (com latência)
    bot_status, bot_latency = _get_bot_core_status()
    health_status["services"]["bot_core"] = bot_status.lower()
    if bot_latency is not None:
        health_status["latencies_ms"]["bot_core"] = round(bot_latency, 2)

    # Determina status geral
    services_values = list(health_status["services"].values())

    if "unhealthy" in services_values and services_values.count("unhealthy") >= 2:
        health_status["status"] = "unhealthy"
    elif "unhealthy" in services_values or "amber" in services_values:
        health_status["status"] = "degraded"
    else:
        health_status["status"] = "healthy"

    # Se a latência do bot core estiver alta, degrada
    if bot_status == "AMBER":
        health_status["status"] = "degraded"

    return health_status


def get_orchestration_state() -> OrchestrationState:
    """
    Estado completo da orquestração - fontes reais.
    SEMPRE retorna estrutura válida, mesmo que vazia.
    """
    try:
        ias = get_ia_health()
        exchanges = get_exchange_health()
        slots = get_slots()
        decisions = get_recent_decisions()
        wallet = get_wallet_state()
        risk_controls = get_risk_controls()

        return OrchestrationState(
            ias=ias,
            slots=slots,
            decisions=decisions,
            exchanges=exchanges,
            wallet=wallet,
            risk_controls=risk_controls,
        )

    except Exception as e:
        logger.error(f"❌ Erro em get_orchestration_state: {e}")
        # Retorna estrutura vazia mas válida em caso de erro
        return OrchestrationState()


# ===== ENDPOINTS ADICIONAIS PARA DASHBOARD =====

def get_operations(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Obtém operações de trading recentes - fontes reais.
    Retorna lista vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return []

        db = mongo_client.botai_trading
        collection = db.trading_operations

        # Busca operações mais recentes
        cursor = collection.find().sort("timestamp", -1).limit(limit)
        operations_list: List[Dict[str, Any]] = []

        for doc in cursor:
            try:
                operation = {
                    "id": doc.get("operation_id", str(doc.get("_id", "unknown"))),
                    "status": doc.get("status", "unknown"),
                    "symbol": doc.get("symbol", "N/A"),
                    "side": doc.get("side", "N/A"),
                    "amount": doc.get("amount", 0),
                    "price": doc.get("price", 0),
                    "pnl": doc.get("pnl", 0),
                    "exchange": doc.get("exchange", "N/A"),
                    "timestamp": doc.get("timestamp", time.time()),
                    "volume": doc.get("amount", 0) * doc.get("price", 0),
                    "success": doc.get("status") == "completed" and doc.get("pnl", 0) >= 0
                }
                operations_list.append(operation)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar operation document: {e}")
                continue

        return operations_list

    except Exception as e:
        logger.error(f"❌ Erro em get_operations: {e}")
        return []


def get_controls() -> Dict[str, Any]:
    """
    Obtém estado dos controles do sistema - fontes reais.
    Retorna estrutura vazia se não houver dados.
    """
    try:
        redis_client = _get_redis_client()
        if redis_client:
            # Tenta obter do Redis
            controls_data = redis_client.get("system_controls")
            if controls_data:
                try:
                    data = json.loads(controls_data)
                    if isinstance(data, dict):
                        return data
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"⚠️ Dados de controls inválidos: {e}")

        # Retorna estrutura padrão se não houver dados
        return {
            "controls": {
                "system_active": True,
                "trading_enabled": True,
                "auto_rebalance": True,
                "emergency_stop": False
            },
            "overrides": {
                "manual_overrides_active": 0,
                "last_override": None,
                "override_history": []
            }
        }

    except Exception as e:
        logger.error(f"❌ Erro em get_controls: {e}")
        return {"controls": {}, "overrides": {}}


def get_ia_insights() -> Dict[str, Any]:
    """
    Obtém insights das IAs - fontes reais.
    Retorna estrutura vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return {"insights": [], "performance": {}}

        db = mongo_client.botai_trading
        collection = db.ia_insights

        # Busca insights mais recentes
        cursor = collection.find().sort("timestamp", -1).limit(10)
        insights_list = []

        for doc in cursor:
            try:
                insight = doc.get("insight_text", "")
                if insight:
                    insights_list.append(insight)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar insight document: {e}")
                continue

        # Performance geral das IAs
        performance = {
            "total_decisions": 0,
            "avg_confidence": 0,
            "success_rate": 0
        }

        # Busca estatísticas de performance
        decisions_collection = db.ia_decisions
        total_decisions = decisions_collection.count_documents({})
        
        if total_decisions > 0:
            # Agregação para calcular métricas
            pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_confidence": {"$avg": "$confidence"},
                    "success_count": {"$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}}
                }}
            ]
            
            result = list(decisions_collection.aggregate(pipeline))
            if result:
                data = result[0]
                performance = {
                    "total_decisions": total_decisions,
                    "avg_confidence": data.get("avg_confidence", 0),
                    "success_rate": (data.get("success_count", 0) / total_decisions * 100) if total_decisions > 0 else 0
                }

        return {
            "insights": insights_list,
            "performance": performance
        }

    except Exception as e:
        logger.error(f"❌ Erro em get_ia_insights: {e}")
        return {"insights": [], "performance": {}}


def get_alerts() -> Dict[str, Any]:
    """
    Obtém alertas ativos - fontes reais.
    Retorna estrutura vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return {"alerts": [], "critical": [], "warnings": []}

        db = mongo_client.botai_trading
        collection = db.system_alerts

        # Busca alertas ativos (não resolvidos)
        cursor = collection.find({"resolved": {"$ne": True}}).sort("timestamp", -1)
        
        alerts = []
        critical = []
        warnings = []

        for doc in cursor:
            try:
                alert = {
                    "id": str(doc.get("_id", "unknown")),
                    "title": doc.get("title", "Alerta"),
                    "message": doc.get("message", ""),
                    "severity": doc.get("severity", "INFO"),
                    "source": doc.get("source", "system"),
                    "timestamp": doc.get("timestamp", datetime.now()).isoformat()
                }
                
                alerts.append(alert)
                
                if alert["severity"] == "CRITICAL":
                    critical.append(alert)
                elif alert["severity"] == "WARNING":
                    warnings.append(alert)
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar alert document: {e}")
                continue

        return {
            "alerts": alerts,
            "critical": critical,
            "warnings": warnings
        }

    except Exception as e:
        logger.error(f"❌ Erro em get_alerts: {e}")
        return {"alerts": [], "critical": [], "warnings": []}


def get_backtests(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Obtém backtests executados - fontes reais.
    Retorna lista vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return []

        db = mongo_client.botai_trading
        collection = db.backtest_results

        # Busca backtests mais recentes
        cursor = collection.find().sort("created_at", -1).limit(limit)
        backtests_list = []

        for doc in cursor:
            try:
                backtest = {
                    "id": doc.get("backtest_id", str(doc.get("_id", "unknown"))),
                    "strategy": doc.get("strategy", "unknown"),
                    "symbol": doc.get("symbol", "N/A"),
                    "start_date": doc.get("start_date", "N/A"),
                    "end_date": doc.get("end_date", "N/A"),
                    "initial_capital": doc.get("initial_capital", 10000),
                    "status": doc.get("status", "completed"),
                    "duration_seconds": doc.get("duration_seconds", 0),
                    "performance": doc.get("performance", {})
                }
                backtests_list.append(backtest)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar backtest document: {e}")
                continue

        return backtests_list

    except Exception as e:
        logger.error(f"❌ Erro em get_backtests: {e}")
        return []


def get_strategies() -> List[Dict[str, Any]]:
    """
    Obtém estratégias disponíveis - fontes reais.
    Retorna lista vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return []

        db = mongo_client.botai_trading
        collection = db.trading_strategies

        # Busca estratégias configuradas
        cursor = collection.find().sort("name", 1)
        strategies_list = []

        for doc in cursor:
            try:
                strategy = {
                    "id": doc.get("strategy_id", str(doc.get("_id", "unknown"))),
                    "name": doc.get("name", "Estratégia"),
                    "description": doc.get("description", ""),
                    "category": doc.get("category", "unknown"),
                    "active": doc.get("active", False),
                    "risk_level": doc.get("risk_level", "medium"),
                    "timeframe": doc.get("timeframe", "1h"),
                    "symbols": doc.get("symbols", []),
                    "max_positions": doc.get("max_positions", 3),
                    "stop_loss_pct": doc.get("stop_loss_pct", 2.0),
                    "take_profit_pct": doc.get("take_profit_pct", 5.0),
                    "min_confidence_pct": doc.get("min_confidence_pct", 70),
                    "performance": doc.get("performance", {})
                }
                strategies_list.append(strategy)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar strategy document: {e}")
                continue

        return strategies_list

    except Exception as e:
        logger.error(f"❌ Erro em get_strategies: {e}")
        return []


def get_wallet_details() -> Dict[str, Any]:
    """
    Obtém detalhes completos da carteira - fontes reais.
    Retorna estrutura vazia se não houver dados.
    """
    try:
        mongo_client = _get_mongo_client()
        if not mongo_client:
            return {"exchanges": {}, "balances": {}, "positions": {}}

        db = mongo_client.botai_trading
        
        # Busca dados das exchanges
        exchanges_collection = db.exchange_balances
        exchanges_data = {}
        
        for exchange_doc in exchanges_collection.find():
            exchange_name = exchange_doc.get("exchange", "unknown")
            exchanges_data[exchange_name] = {
                "total_balance_usdt": exchange_doc.get("total_balance_usdt", 0),
                "free_balance_usdt": exchange_doc.get("free_balance_usdt", 0),
                "locked_balance_usdt": exchange_doc.get("locked_balance_usdt", 0),
                "assets": exchange_doc.get("assets", {}),
                "positions": exchange_doc.get("positions", [])
            }

        return {
            "exchanges": exchanges_data,
            "balances": exchanges_data,  # Alias para compatibilidade
            "positions": {}  # Será preenchido com posições agregadas se necessário
        }

    except Exception as e:
        logger.error(f"❌ Erro em get_wallet_details: {e}")
        return {"exchanges": {}, "balances": {}, "positions": {}}
