#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST API Main - Bot AI Multi-Agente
Etapa 6: Interfaces e Controles Avançados

API REST completa para controle do bot, backtesting, analytics e monitoramento.
Inclui integração com plugins avançados.
"""

# Fix imports - adiciona diretório raiz ao Python path  
import sys
import os
from pathlib import Path

# Garantir que o diretório raiz está no sys.path
root_dir = Path(__file__).parent.parent.parent
root_str = str(root_dir)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
    
# Também configurar PYTHONPATH se não estiver definido
if 'PYTHONPATH' not in os.environ:
    os.environ['PYTHONPATH'] = root_str
elif root_str not in os.environ['PYTHONPATH']:
    os.environ['PYTHONPATH'] = f"{root_str}:{os.environ['PYTHONPATH']}"

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# C:\bot\interfaces\api\main.py

from fastapi import FastAPI, Request, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel
import time

# Instrumentação Prometheus
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY

# Slot Context System - importação relativa removida para evitar erro
import importlib.util
import sys

# Função para importar slot_context dinamicamente
def import_slot_context():
    """Importa slot_context de forma segura"""
    try:
        # Tentar importar do mesmo diretório
        spec = importlib.util.spec_from_file_location(
            "slot_context_module", 
            "/app/ai-gateway-slot_context.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    except Exception as e:
        logging.warning(f"Could not import slot_context: {e}")
        # Retornar mock
        class MockModule:
            def bind_slot(self, headers): return {}
            def labels_for_metrics(self): return {
                "slot_stage": "default",
                "slot_strategy": "default", 
                "slot_instance": "ai-gateway-1"
            }
        return MockModule()

slot_context_module = import_slot_context()
bind_slot = slot_context_module.bind_slot
labels_for_metrics = slot_context_module.labels_for_metrics

app = FastAPI(title="AI Gateway", version="1.0.0")

# Constantes para instrumentação
JOB = "ai-gateway"

# Métricas Prometheus slot-aware - usar try/except para evitar duplicação
try:
    # Verificar se já existem no registry
    existing_metrics = [collector for collector in REGISTRY._collector_to_names.keys()]
    metric_names = set()
    for collector in existing_metrics:
        if hasattr(collector, '_name'):
            metric_names.add(collector._name)
    
    # Só criar se não existir
    if "http_request_duration_seconds" not in metric_names:
        LAT = Histogram(
            "http_request_duration_seconds", "HTTP request latency",
            ["path", "method", "job", "slot_stage", "slot_strategy", "slot_instance"],
            buckets=[.05, .1, .2, .3, .5, 1, 2, 5]
        )
    else:
        # Buscar métrica existente
        for collector in existing_metrics:
            if hasattr(collector, '_name') and collector._name == "http_request_duration_seconds":
                LAT = collector
                break
    
    if "http_requests_total" not in metric_names:
        REQ = Counter(
            "http_requests_total", "HTTP requests count",
            ["path", "method", "status", "job", "slot_stage", "slot_strategy", "slot_instance"]
        )
    else:
        # Buscar métrica existente
        for collector in existing_metrics:
            if hasattr(collector, '_name') and collector._name == "http_requests_total":
                REQ = collector
                break
                
except Exception as e:
    logging.error(f"Error setting up Prometheus metrics: {e}")
    # Criar métricas dummy em caso de erro
    class DummyMetric:
        def labels(self, *args, **kwargs): return self
        def observe(self, val): pass
        def inc(self): pass
    LAT = DummyMetric()
    REQ = DummyMetric()

# CORS básico (ajuste origens se quiser travar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para instrumentação slot-aware
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Middleware para coletar métricas slot-aware"""
    
    # Bind slot context do request
    bind_slot(dict(request.headers))
    
    # Obter labels slot-aware para métricas
    slot_labels = labels_for_metrics()
    
    # Medição de latência
    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time
    
    # Coletar métricas
    path = request.url.path
    method = request.method
    status = str(response.status_code)
    
    # Registrar métricas com labels slot-aware
    LAT.labels(path, method, JOB, **slot_labels).observe(duration)
    REQ.labels(path, method, status, JOB, **slot_labels).inc()
    
    return response


@app.get("/metrics")
def metrics():
    """Endpoint Prometheus metrics"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    return {"status": "ok"}

# ponto para plugar routers reais
# from .routes import router as api_router
# app.include_router(api_router, prefix="/api")


# Sistema existente (PRESERVAR COMPATIBILIDADE)
try:
    from core.engine.bot_engine import BotEngine
    from ai.orchestrator.ai_coordinator import AICoordinator
    from backtest.engine.backtest_engine import BacktestEngine
    from core.exchanges.exchange_manager import ExchangeManager as MultiExchangeManager
    BOT_SYSTEM_AVAILABLE = True
except ImportError as e:
    BOT_SYSTEM_AVAILABLE = False
    logging.warning(f"Bot system components not fully available: {e}")
    
    # Classes mock para evitar erros
    class BotEngine:
        def get_status(self): return {'engine': {'running': False}}
        def start(self): pass
        def stop(self): pass
    
    class AICoordinator:
        pass
    
    class BacktestEngine:
        def run_backtest(self, **kwargs): return {'performance_metrics': {}, 'trades': [], 'portfolio_history': []}
    
    class MultiExchangeManager:
        def health_check(self): return {}

# ML System (Etapa 5)
try:
    from ml.ml_manager import MLManager
    ML_SYSTEM_AVAILABLE = True
except ImportError:
    ML_SYSTEM_AVAILABLE = False
    logging.info("ML system not available")

# Plugins System
try:
    from plugins.registry.plugin_registry import setup_all_plugins, get_plugin
    from plugins.rate_limiter import setup_rate_limiting, limit
    from plugins.auth_jwt import setup_jwt_auth, get_current_user, require_roles, create_token, UserCredentials, TokenResponse
    from plugins.structured_logging import setup_structured_logging, get_logger, log_api_request
    from plugins.advanced_cache import setup_cache, cached, cache_get, cache_set
    PLUGINS_AVAILABLE = True
except ImportError as e:
    PLUGINS_AVAILABLE = False
    logging.warning(f"Plugins system not available: {e}")
    
    # Mock functions
    def setup_all_plugins(*args, **kwargs): return True
    def get_plugin(name): return None
    def setup_rate_limiting(*args, **kwargs): return True
    def limit(rate): return lambda f: f
    def setup_jwt_auth(*args, **kwargs): return True
    def get_current_user(): return None
    def require_roles(roles): return lambda: None
    def create_token(username, password): return None
    def setup_structured_logging(*args, **kwargs): return True
    def get_logger(component): return logging.getLogger(component)
    def log_api_request(*args, **kwargs): pass
    def setup_cache(*args, **kwargs): return True
    def cached(*args, **kwargs): return lambda f: f
    def cache_get(key, default=None): return default
    def cache_set(key, value, ttl=None): return True
    
    class UserCredentials(BaseModel):
        username: str
        password: str
        
        class Config:
            # Configuração para compatibilidade
            extra = "forbid"
    
    class TokenResponse(BaseModel):
        access_token: str
        token_type: str = "bearer"
        expires_in: int
        user_info: dict
        
        class Config:
            extra = "forbid"

# Auth e security
try:
    from .auth.security import AuthManager
    from .middleware.cors import setup_cors
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    logging.warning(f"Auth system not available: {e}")
    
    # Mock classes
    class AuthManager:
        def verify_token(self, token): return True
    
    def setup_cors(app): 
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

# Models
try:
    from .models.api_models import (
        BotStatusResponse, BotConfigRequest, BacktestRequest, 
        BacktestResponse, PerformanceResponse, HealthResponse
    )
    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    logging.warning(f"API models not available: {e}")
    
    # Mock models
    from pydantic import BaseModel
    from datetime import datetime
    
    class HealthResponse(BaseModel):
        status: str
        timestamp: datetime
        api_version: str
        components_available: dict
    
    class BotStatusResponse(BaseModel):
        status: str
        timestamp: datetime
        components: dict
        uptime_hours: float
    
    class BacktestRequest(BaseModel):
        symbol: str
        start_date: str
        end_date: str
        initial_capital: float = 10000.0
        timeframe: str = "1h"
    
    class BacktestResponse(BaseModel):
        backtest_id: str
        status: str
        config: dict
        performance_metrics: dict
        trade_count: int
        created_at: datetime
    
    class PerformanceResponse(BaseModel):
        timestamp: datetime
        uptime_hours: float
        api_requests: int
        components_health: dict
        last_update: datetime

# Setup logging
logger = logging.getLogger(__name__)


class BotAPIManager:
    """
    Gerenciador da API do Bot com integração de plugins
    
    Mantém referências aos componentes do sistema existente
    sem modificá-los, fornecendo interface REST sobre eles.
    """
    
    def __init__(self):
        """Inicializar API Manager"""
        
        # Componentes do sistema existente (NUNCA MODIFICAR)
        self.bot_engine = None
        self.ai_coordinator = None
        self.backtest_engine = None
        self.exchange_manager = None
        self.ml_manager = None
        
        # API state
        self.api_stats = {
            'requests_count': 0,
            'start_time': datetime.now(),
            'last_request': None
        }
        
        # Logger estruturado
        self.logger = get_logger("api_manager") if PLUGINS_AVAILABLE else logger
        
        # Inicializar componentes se disponíveis
        self._initialize_components()
        self._initialize_plugins()
    
    def _initialize_components(self):
        """Inicializa componentes do sistema (sem modificar)"""
        
        try:
            if BOT_SYSTEM_AVAILABLE:
                self.bot_engine = BotEngine()
                self.ai_coordinator = AICoordinator()
                self.backtest_engine = BacktestEngine()
                self.exchange_manager = MultiExchangeManager()
                self.logger.info("✅ Bot system components loaded")
            
            if ML_SYSTEM_AVAILABLE:
                self.ml_manager = MLManager()
                self.logger.info("✅ ML system components loaded")
                
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
    
    def _initialize_plugins(self):
        """Inicializa plugins do sistema"""
        
        if not PLUGINS_AVAILABLE:
            self.logger.warning("Plugins system not available")
            return
        
        try:
            # Configurações dos plugins
            plugin_configs = {
                "rate_limiter": {
                    "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    "default_rate": "100/minute",
                    "api_rate": "500/minute"
                },
                "auth_jwt": {
                    "secret_key": os.getenv("API_SECRET_KEY", "botai_secret_key_2025_production"),
                    "token_expire_minutes": 30
                },
                "structured_logging": {
                    "log_level": "INFO",
                    "log_format": "json",
                    "metrics_enabled": True
                },
                "advanced_cache": {
                    "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    "default_ttl": 300,
                    "compression_enabled": True
                }
            }
            
            # Setup automático de plugins
            success = setup_all_plugins(configs=plugin_configs)
            
            if success:
                self.logger.info("✅ Plugins system initialized")
            else:
                self.logger.warning("⚠️ Some plugins failed to initialize")
                
        except Exception as e:
            self.logger.error(f"Error initializing plugins: {e}")
    
    @cached(ttl=60)  # Cache por 1 minuto
    def get_bot_status(self) -> Dict[str, Any]:
        """Obtém status atual do bot"""
        
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'api_available': True,
                'components': {},
                'plugins': {}
            }
            
            # Bot Engine status
            if self.bot_engine:
                engine_status = self.bot_engine.get_status()
                status['components']['bot_engine'] = {
                    'available': True,
                    'running': engine_status.get('engine', {}).get('running', False),
                    'health': 'healthy'
                }
            
            # AI System status
            if self.ai_coordinator:
                status['components']['ai_system'] = {
                    'available': True,
                    'health': 'healthy'
                }
            
            # Exchange Manager status  
            if self.exchange_manager:
                exchanges_health = self.exchange_manager.health_check()
                healthy_count = sum(1 for ex_health in exchanges_health.values() if ex_health.get('healthy'))
                
                status['components']['exchanges'] = {
                    'available': True,
                    'total_exchanges': len(exchanges_health),
                    'healthy_exchanges': healthy_count,
                    'health': 'healthy' if healthy_count > 0 else 'degraded'
                }
            
            # ML System status
            if self.ml_manager:
                ml_status = self.ml_manager.health_check()
                status['components']['ml_system'] = {
                    'available': True,
                    'health': ml_status.get('ml_manager', 'unknown')
                }
            
            # Plugin status
            if PLUGINS_AVAILABLE:
                try:
                    plugin_registry = get_plugin("registry")
                    if plugin_registry:
                        plugin_status = plugin_registry.get_system_status()
                        status['plugins'] = {
                            'available': True,
                            'total': plugin_status.get('total_plugins', 0),
                            'active': plugin_status.get('active_plugins', 0),
                            'status': plugin_status.get('registry_status', 'unknown')
                        }
                except Exception as e:
                    status['plugins'] = {'available': False, 'error': str(e)}
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting bot status: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'api_available': True,
                'error': str(e),
                'components': {}
            }
    
    def start_bot(self) -> Dict[str, Any]:
        """Inicia o bot (se suportado)"""
        
        try:
            if not self.bot_engine:
                return {'success': False, 'error': 'Bot engine not available'}
            
            # Tentar iniciar bot engine
            self.bot_engine.start()
            
            result = {
                'success': True,
                'message': 'Bot started successfully',
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info("Bot started via API", **result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def stop_bot(self) -> Dict[str, Any]:
        """Para o bot (se suportado)"""
        
        try:
            if not self.bot_engine:
                return {'success': False, 'error': 'Bot engine not available'}
            
            # Tentar parar bot engine
            self.bot_engine.stop()
            
            result = {
                'success': True,
                'message': 'Bot stopped successfully', 
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info("Bot stopped via API", **result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @cached(ttl=120)  # Cache por 2 minutos
    def run_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa backtest via API"""
        
        try:
            if not self.backtest_engine:
                return {'success': False, 'error': 'Backtest engine not available'}
            
            # Executar backtest
            results = self.backtest_engine.run_backtest(**config)
            
            # Simplificar resultados para API
            simplified_results = {
                'success': True,
                'backtest_id': f"bt_{int(datetime.now().timestamp())}",
                'config': config,
                'performance_metrics': results.get('performance_metrics', {}),
                'trade_count': len(results.get('trades', [])),
                'start_capital': config.get('initial_capital'),
                'final_capital': results.get('portfolio_history', [{}])[-1].get('equity') if results.get('portfolio_history') else None,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info("Backtest executed via API", backtest_id=simplified_results['backtest_id'], trade_count=simplified_results['trade_count'])
            return simplified_results
            
        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtém métricas de performance"""
        
        # Mock metrics (implementar coleta real posteriormente)
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_hours': (datetime.now() - self.api_stats['start_time']).total_seconds() / 3600,
            'api_requests': self.api_stats['requests_count'],
            'last_request': self.api_stats['last_request'],
            'components_health': {
                'bot_engine': 'healthy' if self.bot_engine else 'unavailable',
                'ai_system': 'healthy' if self.ai_coordinator else 'unavailable', 
                'exchanges': 'healthy' if self.exchange_manager else 'unavailable',
                'ml_system': 'healthy' if self.ml_manager else 'unavailable',
                'plugins': 'healthy' if PLUGINS_AVAILABLE else 'unavailable'
            }
        }


# Instância global do API Manager
api_manager = BotAPIManager()


def create_api_app(bot_runner=None) -> FastAPI:
    """
    Cria aplicação FastAPI
    
    Args:
        bot_runner: Instância do bot runner (opcional)
    
    Returns:
        FastAPI app configurada
    """
    
    # Criar app FastAPI
    app = FastAPI(
        title="Bot AI Multi-Agente API",
        description="API REST completa para controle e monitoramento do trading bot com plugins avançados",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # Setup CORS
    setup_cors(app)
    
    # Setup plugins se disponível
    if PLUGINS_AVAILABLE:
        # Rate limiting
        setup_rate_limiting(app, {
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0")
        })
        
        # JWT Auth
        setup_jwt_auth({
            "secret_key": os.getenv("API_SECRET_KEY", "botai_secret_key_2025_production")
        })
        
        # Structured logging
        setup_structured_logging({
            "log_level": "INFO",
            "metrics_enabled": True
        })
        
        # Cache
        setup_cache({
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0")
        })
    
    # Auth manager
    auth_manager = AuthManager()
    security = HTTPBearer()
    
    # Middleware para tracking e logging
    @app.middleware("http")
    async def track_requests(request: Request, call_next):
        start_time = datetime.now()
        
        # Update stats
        api_manager.api_stats['requests_count'] += 1
        api_manager.api_stats['last_request'] = start_time.isoformat()
        
        # Process request
        response = await call_next(request)
        
        # Log API request
        duration = (datetime.now() - start_time).total_seconds()
        if PLUGINS_AVAILABLE:
            log_api_request(
                method=request.method,
                endpoint=str(request.url.path),
                status_code=response.status_code,
                duration=duration
            )
        
        return response
    
    # ===== PUBLIC ROUTES =====
    
    @app.get("/api/health", response_model=HealthResponse)
    async def health_check():
        """Health check da API"""
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            api_version="1.0.0",
            components_available={
                "bot_system": BOT_SYSTEM_AVAILABLE,
                "ml_system": ML_SYSTEM_AVAILABLE,
                "plugins_system": PLUGINS_AVAILABLE,
                "auth_system": True
            }
        )
    
    @app.post("/api/auth/login")
    async def login(credentials: UserCredentials):
        """Login e obtenção de token JWT"""
        
        if not PLUGINS_AVAILABLE:
            raise HTTPException(status_code=503, detail="Authentication system not available")
        
        token_response = create_token(credentials.username, credentials.password)
        
        if token_response is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        return token_response
    
    @app.get("/api/bot/status", response_model=BotStatusResponse)
    async def get_bot_status():
        """Obtém status atual do bot"""
        
        status_data = api_manager.get_bot_status()
        
        return BotStatusResponse(
            status="running" if status_data.get('components', {}).get('bot_engine', {}).get('running') else "stopped",
            timestamp=datetime.now(),
            components=status_data.get('components', {}),
            uptime_hours=(datetime.now() - api_manager.api_stats['start_time']).total_seconds() / 3600
        )
    
    # ===== PROTECTED ROUTES =====
    
    @app.post("/api/bot/start")
    async def start_bot(current_user: dict = Depends(get_current_user) if PLUGINS_AVAILABLE else None):
        """Inicia o bot"""
        
        result = api_manager.start_bot()
        
        if result['success']:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    
    @app.post("/api/bot/stop")
    async def stop_bot(current_user: dict = Depends(get_current_user) if PLUGINS_AVAILABLE else None):
        """Para o bot"""
        
        result = api_manager.stop_bot()
        
        if result['success']:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    
    @app.post("/api/backtest/run", response_model=BacktestResponse)
    async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks,
                          current_user: dict = Depends(get_current_user) if PLUGINS_AVAILABLE else None):
        """Executa backtest"""
        
        # Converter request para dict
        config = {
            'symbol': request.symbol,
            'start_date': request.start_date,
            'end_date': request.end_date,
            'initial_capital': request.initial_capital,
            'timeframe': request.timeframe
        }
        
        # Executar backtest
        result = api_manager.run_backtest(config)
        
        if result['success']:
            return BacktestResponse(
                backtest_id=result['backtest_id'],
                status="completed",
                config=result['config'],
                performance_metrics=result['performance_metrics'],
                trade_count=result['trade_count'],
                created_at=datetime.now()
            )
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    
    @app.get("/api/analytics/performance", response_model=PerformanceResponse)
    async def get_performance(current_user: dict = Depends(get_current_user) if PLUGINS_AVAILABLE else None):
        """Obtém métricas de performance"""
        
        metrics = api_manager.get_performance_metrics()
        
        return PerformanceResponse(
            timestamp=datetime.now(),
            uptime_hours=metrics['uptime_hours'],
            api_requests=metrics['api_requests'],
            components_health=metrics['components_health'],
            last_update=datetime.now()
        )
    
    @app.get("/api/exchanges/health")
    async def get_exchanges_health(current_user: dict = Depends(get_current_user) if PLUGINS_AVAILABLE else None):
        """Health check das exchanges"""
        
        if not api_manager.exchange_manager:
            raise HTTPException(status_code=503, detail="Exchange manager not available")
        
        try:
            health = api_manager.exchange_manager.health_check()
            return {
                'timestamp': datetime.now().isoformat(),
                'exchanges': health,
                'summary': {
                    'total': len(health),
                    'healthy': sum(1 for h in health.values() if h.get('healthy')),
                    'unhealthy': sum(1 for h in health.values() if not h.get('healthy'))
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Plugin management endpoints
    if PLUGINS_AVAILABLE:
        
        @app.get("/api/plugins/status")
        async def get_plugins_status(current_user: dict = Depends(require_roles(["admin"]) if PLUGINS_AVAILABLE else get_current_user)):
            """Status do sistema de plugins"""
            
            try:
                plugin_registry = get_plugin("registry")
                if not plugin_registry:
                    return {"error": "Plugin registry not available"}
                
                return plugin_registry.get_system_status()
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/plugins/{plugin_name}/execute")
        async def execute_plugin(plugin_name: str, 
                                current_user: dict = Depends(require_roles(["admin"]) if PLUGINS_AVAILABLE else get_current_user)):
            """Executa um plugin específico"""
            
            try:
                plugin_registry = get_plugin("registry")
                if not plugin_registry:
                    raise HTTPException(status_code=503, detail="Plugin registry not available")
                
                result = plugin_registry.execute_plugin(plugin_name)
                return result
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/cache/stats")
        async def get_cache_stats(current_user: dict = Depends(require_roles(["admin"]) if PLUGINS_AVAILABLE else get_current_user)):
            """Estatísticas do sistema de cache"""
            
            try:
                cache_plugin = get_plugin("advanced_cache")
                if not cache_plugin:
                    return {"error": "Cache plugin not available"}
                
                return cache_plugin.get_stats()
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    # ML/AI endpoints (se disponível)
    if ML_SYSTEM_AVAILABLE:
        
        @app.get("/api/ml/status")
        async def get_ml_status():
            """Status do sistema ML"""
            
            if not api_manager.ml_manager:
                raise HTTPException(status_code=503, detail="ML manager not available")
            
            return api_manager.ml_manager.health_check()
        
        @app.post("/api/ml/predict")
        async def get_ml_prediction(market_data: Dict[str, Any],
                                  current_user: dict = Depends(get_current_user) if PLUGINS_AVAILABLE else None):
            """Obter predição ML"""
            
            if not api_manager.ml_manager:
                raise HTTPException(status_code=503, detail="ML manager not available")
            
            try:
                prediction = api_manager.ml_manager.get_prediction(market_data)
                return {
                    'timestamp': datetime.now().isoformat(),
                    'prediction': prediction,
                    'market_data': market_data
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    return app


def run_api_server():
    """Executa servidor de API"""
    
    # Configuração do .env
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 8000))
    debug = os.getenv('API_DEBUG', 'false').lower() == 'true'
    
    # Criar app
    app = create_api_app()
    
    logger.info(f"🚀 Starting API server on {host}:{port}")
    
    # Executar servidor
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )


# Registra extensões da API
try:
    from api_gateway_extensions import register_extensions
    EXTENSIONS_AVAILABLE = True
except ImportError:
    EXTENSIONS_AVAILABLE = False
    logging.warning("API extensions not available")

# Instância global da aplicação FastAPI para uvicorn
app = create_api_app()

# Registra extensões se disponível
if EXTENSIONS_AVAILABLE:
    try:
        register_extensions(app)
        logging.info("✅ API extensions registered successfully")
    except Exception as e:
        logging.error(f"❌ Failed to register API extensions: {e}")

if __name__ == "__main__":
    run_api_server()