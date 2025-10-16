from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import logging
import time
from contextlib import asynccontextmanager
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
from interfaces.api.orch import orch_router

# JWT Authentication
from plugins.auth_jwt import setup_jwt_auth, get_current_user

# interfaces/api/main.py
"""
Maveretta AI Gateway - FastAPI Application Principal
Ponto de entrada Ãºnico para todas as APIs do sistema
"""

# Import dos routers
from interfaces.api.routes import (
    backtest_router, 
    hyperopt_router, 
    risk_router,
    logs_router,
    rates_router,
    strategies_router,
    cascade_router,
    ia as ia_router,
    market_analysis # Added for market analysis routes
)

from interfaces.api.routes.operations import router as operations_router
from interfaces.api.routes.orchestration import router as orchestration_router
from interfaces.api.routes.alerts import router as alerts_router
from interfaces.api.routes.risk_config import router as risk_config_router

# ===== CONFIGURAÃ‡ÃƒO DE LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ===== MÃ‰TRICAS PROMETHEUS =====
# MÃ©tricas de requisiÃ§Ãµes HTTP
REQUEST_COUNT = Counter(
    'ai_gateway_requests_total',
    'Total de requests no AI Gateway',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'ai_gateway_request_duration_seconds',
    'DuraÃ§Ã£o das requisiÃ§Ãµes no AI Gateway',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'ai_gateway_active_requests',
    'NÃºmero de requisiÃ§Ãµes ativas no AI Gateway'
)

HEALTH_STATUS = Gauge(
    'ai_gateway_health_status',
    'Status de saÃºde do AI Gateway (1=healthy, 0=unhealthy)'
)

# ===== MIDDLEWARE DE MÃ‰TRICAS =====
class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        method = scope['method']
        path = scope['path']

        # Ignora endpoints de mÃ©tricas e health para evitar loop
        if path in ['/metrics', '/v1/metrics', '/v1/health']:
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        ACTIVE_REQUESTS.inc()

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                status_code = message['status']

                # Registra mÃ©tricas apÃ³s a resposta
                request_duration = time.time() - start_time
                REQUEST_DURATION.labels(method=method, endpoint=path).observe(request_duration)
                REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status_code).inc()
                ACTIVE_REQUESTS.dec()

                logger.info(f"ðŸ“Š {method} {path} - {status_code} - {request_duration:.3f}s")

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            ACTIVE_REQUESTS.dec()
            REQUEST_COUNT.labels(method=method, endpoint=path, status_code=500).inc()
            raise e

# ===== LIFECYCLE DA APLICAÃ‡ÃƒO =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ðŸš€ Iniciando Maveretta AI Gateway...")
    HEALTH_STATUS.set(1)

    # Log de informaÃ§Ãµes do sistema
    import os
    logger.info(f"ðŸ“Š Environment: {os.getenv('ENV', 'development')}")
    logger.info(f"ðŸ”§ Debug Mode: {os.getenv('API_DEBUG', 'false')}")
    logger.info(f"ðŸŒ Host: {os.getenv('API_HOST', '0.0.0.0')}")
    logger.info(f"ðŸ”Œ Port: {os.getenv('API_PORT', '8080')}")

    yield

    # Shutdown
    logger.info("ðŸ›‘ Encerrando Maveretta AI Gateway...")
    HEALTH_STATUS.set(0)

# ===== CRIAÃ‡ÃƒO DA APP FASTAPI =====
app = FastAPI(
    title="Maveretta AI Gateway",
    description="Sistema de OrquestraÃ§Ã£o de Trading com IA - API Gateway Unificado",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/v1/openapi.json",
    lifespan=lifespan
)

# ===== MIDDLEWARES =====
# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Em produÃ§Ã£o, restringir para domÃ­nios especÃ­ficos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics Middleware
app.add_middleware(MetricsMiddleware)

# ===== ROUTERS PRINCIPAIS =====
# Router de orquestraÃ§Ã£o (todas as rotas /v1/*)
app.include_router(orch_router)

# Routers de controles e operações (FASE 3)
app.include_router(orchestration_router)
app.include_router(operations_router)
app.include_router(alerts_router)
app.include_router(risk_config_router)


# Routers dos engines Freqtrade integrados
app.include_router(backtest_router)
app.include_router(hyperopt_router) 
app.include_router(risk_router)

# Routers adicionais do sistema
app.include_router(logs_router)
app.include_router(rates_router)
app.include_router(strategies_router)
app.include_router(cascade_router)
app.include_router(ia_router)
app.include_router(market_analysis_router) # Included market analysis router


# ===== ENDPOINTS DE SISTEMA =====
@app.get("/", include_in_schema=False)
async def root():
    """Redirect para documentaÃ§Ã£o"""
    return JSONResponse(
        content={"message": "Redirecting to docs"},
        status_code=302,
        headers={"Location": "/docs"}
    )

@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check bÃ¡sico para load balancers"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/v1", include_in_schema=False)
async def v1_root():
    """Root da API v1"""
    return {
        "message": "Maveretta AI Gateway v1.0.0",
        "endpoints": {
            "health": "/v1/health",
            "orchestration": "/v1/orchestration/state",
            "ias": "/v1/ias/health",
            "exchanges": "/v1/exchanges/health",
            "slots": "/v1/slots",
            "logs": "/v1/logs",
            "docs": "/docs"
        }
    }

# ===== ENDPOINT DE MÃ‰TRICAS PROMETHEUS =====
# Cria app ASGI para mÃ©tricas Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# TambÃ©m expÃµe em /v1/metrics para consistÃ­ncia
@app.get("/v1/metrics", include_in_schema=False)
async def metrics_endpoint():
    """Endpoint de mÃ©tricas compatÃ­vel com Prometheus"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# ===== HANDLERS DE ERRO GLOBAL =====
@app.exception_handler(404)
async def not_found_exception_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint nÃ£o encontrado"}
    )

@app.exception_handler(500)
async def internal_exception_handler(request, exc):
    logger.error(f"âŒ Erro interno do servidor: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"âš ï¸ HTTP Exception {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# ===== INICIALIZAÃ‡ÃƒO =====
if __name__ == "__main__":
    import uvicorn
    import os

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))
    debug = os.getenv("API_DEBUG", "false").lower() == "true"

    logger.info(f"ðŸŽ¯ Iniciando servidor em {host}:{port} (debug: {debug})")

    uvicorn.run(
        "interfaces.api.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if debug else "warning"
    )