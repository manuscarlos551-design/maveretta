#!/usr/bin/env python3
# -- coding: utf-8 --
"""
Bot Runner Modular - Versão refatorada com arquitetura modular
Mantém 100% compatibilidade com bot_runner.py original
Inclui instrumentação Prometheus slot-aware
"""

import os
import sys
import time
import re
import redis
import threading
import logging
from pathlib import Path
from enum import Enum

# Adiciona path para imports
sys.path.insert(0, str(Path(__file__).parent))
# Instrumentação Prometheus
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Slot Context System
from slot_context import init_bot_slot, labels_for_metrics, update_slot_stage

# Setup logging
logger = logging.getLogger(__name__)

# =============================================================================
# BOT STATE MANAGEMENT - FASE 3
# =============================================================================

class BotState(Enum):
    """Estados possíveis do bot"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    EMERGENCY_STOPPED = "emergency_stopped"

class BotMode(Enum):
    """Modos de operação"""
    AUTO = "auto"
    MANUAL = "manual"
    SIMULATION = "simulation"

# Estado global do bot
bot_state = BotState.STOPPED
bot_mode = BotMode.AUTO
emergency_flag = False

# FUNÇÕES AUXILIARES ADICIONADAS
def _get_env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default

def _build_redis_client():
    url = os.getenv("REDIS_URL")
    if url:
        return redis.from_url(url, decode_responses=True)
    host = os.getenv("REDIS_HOST", "redis")
    port = int(os.getenv("REDIS_PORT", "6379"))
    pwd  = os.getenv("REDIS_PASSWORD") or None
    return redis.Redis(host=host, port=port, password=pwd, decode_responses=True)

def _infer_group_from_slot(slot_id: str) -> str:
    nums = re.findall(r'\d+', slot_id or "")
    if nums:
        return "G1" if (int(nums[-1]) % 2 == 1) else "G2"
    return os.getenv("GROUP", "G1")

def _load_slot_params(instance_suffix: str = "1"):
    slot_id     = os.getenv("SLOT_ID", f"slot-{instance_suffix}")
    symbol      = os.getenv("SYMBOL", "BTC/USDT")
    base_amount = _get_env_float("BASE_AMOUNT", 10.0)
    min_amount  = _get_env_float("MIN_AMOUNT", 5.0)
    group       = os.getenv("GROUP", _infer_group_from_slot(slot_id))
    rclient     = _build_redis_client()
    return rclient, slot_id, base_amount, min_amount, group, symbol

# Prometheus metrics will be exposed via FastAPI on port 9200
# The standalone prometheus HTTP server is no longer needed as FastAPI will handle it
print("🔧 Prometheus metrics will be exposed via FastAPI on port 9200...")

# Constantes para instrumentação
JOB = "bot"

# Métricas Prometheus slot-aware
TRADES = Counter(
    "trades_total", "Executed trades count",
    ["job", "slot_stage", "slot_strategy", "slot_instance"]
)

WS_LAG = Gauge(
    "ws_lag_ms", "WebSocket feed lag in milliseconds",
    ["job", "slot_stage", "slot_strategy", "slot_instance"]
)

DECIDE = Histogram(
    "decide_duration_seconds", "Decision processing time",
    ["job", "slot_stage", "slot_strategy", "slot_instance"],
    buckets=[.005, .01, .02, .05, .1, .2, .5, 1]
)

# Funções auxiliares para métricas
def inc_trade():
    """Incrementa contador de trades executados"""
    labels = labels_for_metrics()
    TRADES.labels(JOB, **labels).inc()

def set_ws_lag(ms: float):
    """Define lag atual do WebSocket"""
    labels = labels_for_metrics()
    WS_LAG.labels(JOB, **labels).set(ms)

def observe_decide(duration: float):
    """Registra tempo de decisão"""
    labels = labels_for_metrics()
    DECIDE.labels(JOB, **labels).observe(duration)

# Inicializar slot context para o bot COM PARÂMETROS COMPLETOS
redis_client, slot_id, base_amount, min_amount, group, symbol = _load_slot_params("1")

init_bot_slot(
    strategy="multi-agent",
    instance="bot-1",
    redis_client=redis_client,
    slot_id=slot_id,
    base_amount=base_amount,
    min_amount=min_amount,
    group=group,
    symbol=symbol,
)
print("✅ Slot context inicializado para bot")

# =============================================================================
# REDIS COMMAND LISTENER - FASE 3
# =============================================================================

def redis_command_listener():
    """
    Thread que escuta comandos do Redis pub/sub
    Controla estado do bot via comandos: START, STOP, PAUSE, EMERGENCY_STOP, MODE:xxx
    """
    global bot_state, bot_mode, emergency_flag
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe("bot:commands")
    
    logger.info("🎧 Redis command listener started")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            command = message['data']
            logger.info(f"📨 Received command: {command}")
            
            if command == "START":
                bot_state = BotState.RUNNING
                logger.info("▶️ Bot state changed to RUNNING")
                
            elif command == "STOP":
                bot_state = BotState.STOPPING
                logger.warning("⏹️ Bot state changed to STOPPING - will close positions")
                close_all_positions()
                bot_state = BotState.STOPPED
                
            elif command == "PAUSE":
                bot_state = BotState.PAUSED
                logger.info("⏸️ Bot state changed to PAUSED - no new positions")
                
            elif command == "EMERGENCY_STOP":
                bot_state = BotState.EMERGENCY_STOPPED
                emergency_flag = True
                logger.critical("🚨 EMERGENCY STOP - closing all positions NOW")
                emergency_close_all_positions()
                
            elif command.startswith("MODE:"):
                mode_str = command.split(":")[1]
                try:
                    bot_mode = BotMode(mode_str)
                    logger.info(f"🔄 Bot mode changed to {bot_mode.value}")
                except ValueError:
                    logger.error(f"❌ Invalid mode received: {mode_str}")
            
            elif command.startswith("CLOSE_OPERATION:"):
                operation_id = command.split(":")[1]
                logger.warning(f"⚠️ Force close requested for operation: {operation_id}")
                # TODO: Implementar fechamento de operação específica via Exchange Executor

# Iniciar listener em thread separada
listener_thread = threading.Thread(target=redis_command_listener, daemon=True)
listener_thread.start()
logger.info("✅ Redis listener thread started")


# =============================================================================
# FUNÇÕES DE FECHAMENTO DE POSIÇÕES - FASE 3
# =============================================================================

def close_all_positions():
    """
    Fecha todas as posições abertas de forma ordenada
    
    TODO: Implementar integração com:
    1. Operations Logger (MongoDB) - buscar operações com status='open'
    2. Exchange Executor (CCXT) - enviar ordem de fechamento para cada exchange
    3. Operations Logger (MongoDB) - atualizar status para 'closed' + registro de P&L
    """
    try:
        logger.info("🔄 Iniciando fechamento ordenado de todas as posições...")
        
        # Estrutura preparada para:
        # - Buscar operações abertas via MongoDB operations collection
        # - Iterar sobre cada operação e fechar via exchange correspondente
        # - Atualizar registros no banco com resultado do fechamento
        
        pass  # Aguardando implementação real

    except Exception as e:
        logger.error(f"❌ Erro ao fechar posições: {e}")

def emergency_close_all_positions():
    """
    Fecha todas as posições IMEDIATAMENTE a mercado (sem validações)
    
    TODO: Implementar integração com:
    1. Operations Logger (MongoDB) - buscar operações com status='open'
    2. Exchange Executor (CCXT) - enviar ordens MARKET para fechamento imediato
    3. Operations Logger (MongoDB) - atualizar status para 'closed' + flag emergency
    """
    try:
        logger.critical("🚨 EMERGENCY CLOSE: Fechamento imediato de todas as posições")
        
        # Estrutura preparada para:
        # - Buscar operações abertas via MongoDB operations collection
        # - Fechar tudo a mercado sem validações de preço/slippage
        # - Registrar no banco com flag de fechamento emergencial
        
        pass  # Aguardando implementação real

    except Exception as e:
        logger.critical(f"❌ Erro crítico no emergency close: {e}")


# Imports da nova arquitetura
from core.engine.bot_engine import BotEngine
from config.settings.config_manager import get_config_manager
from plugins.registry.plugin_registry import get_plugin_registry

# Import do sistema original para compatibilidade TOTAL
try:
    # Importa TODAS as funcionalidades do bot original
    from bot_runner import *  # Importa tudo do sistema original
    print("[BOT_RUNNER_MODULAR] Sistema original importado com sucesso")
    LEGACY_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"[BOT_RUNNER_MODULAR] Sistema original não disponível: {e}")
    LEGACY_SYSTEM_AVAILABLE = False


class ModularBotRunner:
    """
    Runner modular que integra com sistema original
    Executa em modo híbrido: nova arquitetura + compatibilidade total
    """
    
    def __init__(self):
        print("\n" + "="*80)
        print("🤖 BOT AI MULTI-AGENT - ARQUITETURA MODULAR v2.0")
        print("="*80)
        
        # Inicializa componentes modulares
        self.config_manager = get_config_manager()
        self.plugin_registry = get_plugin_registry()
        self.bot_engine = BotEngine()
        
        # Flags de controle
        self.use_legacy_runner = True  # Usa sistema original por padrão
        self.modular_enhancements = True  # Aplica melhorias modulares
        
        print("✅ Arquitetura modular inicializada")
        print(f"✅ Sistema legado {'disponível' if LEGACY_SYSTEM_AVAILABLE else 'indisponível'}")
        print(f"✅ Configurações carregadas: {len(self.config_manager.get_config())} seções")
        
        # =============================================================================
        # FASE 3 COMPONENTS INITIALIZATION
        # =============================================================================
        
        # Inicializa Risk Manager
        try:
            from risk.managers.risk_manager import RiskManager
            risk_config = {
                "max_exposure_pct": float(os.getenv("MAX_EXPOSURE_PCT", "10.0")),
                "max_open_positions": int(os.getenv("MAX_OPEN_POSITIONS", "5")),
                "max_daily_loss_pct": float(os.getenv("MAX_DAILY_LOSS_PCT", "5.0")),
                "max_loss_per_trade_pct": float(os.getenv("MAX_LOSS_PER_TRADE_PCT", "2.0")),
                "max_drawdown_pct": float(os.getenv("MAX_DRAWDOWN_PCT", "15.0")),
                "capital": float(os.getenv("INITIAL_CAPITAL", "10000.0"))
            }
            self.risk_manager = RiskManager(risk_config)
            print("✅ Risk Manager inicializado")
        except Exception as e:
            print(f"⚠️ Risk Manager não inicializado: {e}")
            self.risk_manager = None
        
        # Inicializa Exchange Executor
        try:
            from core.execution.exchange_executor import ExchangeExecutor
            self.exchange_executor = ExchangeExecutor()
            print("✅ Exchange Executor inicializado")
        except Exception as e:
            print(f"⚠️ Exchange Executor não inicializado: {e}")
            self.exchange_executor = None
        
        # Inicializa Operations Logger
        try:
            from core.logging.operations_logger import OperationsLogger
            self.operations_logger = OperationsLogger()
            print("✅ Operations Logger inicializado")
        except Exception as e:
            print(f"⚠️ Operations Logger não inicializado: {e}")
            self.operations_logger = None
        
        # Inicializa Cascade Orchestrator
        try:
            from core.engine.cascade_orchestrator import start_cascade_orchestrator
            self.cascade_orchestrator = start_cascade_orchestrator(
                check_interval_seconds=300  # 5 minutos
            )
            print("✅ Cascade Orchestrator inicializado e rodando")
        except Exception as e:
            print(f"⚠️ Cascade Orchestrator não inicializado: {e}")
            self.cascade_orchestrator = None
        
        self._initialize_plugins()
    
    def _initialize_plugins(self):
        """Inicializa sistema de plugins"""
        try:
            # Registra plugins básicos de exemplo
            self._register_example_plugins()
            
            # Descobre plugins automáticos se habilitado
            if self.config_manager.get('plugins.auto_discover', True):
                plugin_dirs = self.config_manager.get('plugins.directories', ['plugins/implementations'])
                for plugin_dir in plugin_dirs:
                    self.plugin_registry.discover_plugins_in_directory(plugin_dir)
            
            print("✅ Sistema de plugins inicializado")
            print(f"   • Plugins disponíveis: {len(self.plugin_registry.get_available_plugins())}")
            
        except Exception as e:
            print(f"⚠  Erro na inicialização de plugins: {e}")
    
    def _register_example_plugins(self):
        """Registra plugins de exemplo para demonstração"""
        # Aqui você registraria plugins reais quando disponíveis
        # Por enquanto, apenas log de exemplo
        pass
    
    def run_hybrid_mode(self):
        """
        Executa em modo híbrido:
        - Sistema original para lógica principal
        - Melhorias modulares como overlay
        """
        
        print("\n🚀 INICIANDO MODO HÍBRIDO")
        print("-" * 50)
        
        if not LEGACY_SYSTEM_AVAILABLE:
            print("❌ Sistema original não disponível - usando apenas arquitetura modular")
            return self._run_modular_only()
        
        try:
            print("📊 Status dos componentes:")
            self._show_status()
            
            print("\n🔄 Delegando para sistema original...")
            print("   (com melhorias modulares ativas)")
            
            # Executa o main() do sistema original
            # Isso mantém TODA funcionalidade existente
            main()
            
        except KeyboardInterrupt:
            print("\n🛑 Interrupção solicitada pelo usuário")
            self._cleanup()
        except Exception as e:
            print(f"\n❌ Erro na execução: {e}")
            self._cleanup()
            raise
    
    def _run_modular_only(self):
        """Executa apenas com arquitetura modular (fallback)"""
        print("🔧 Executando apenas arquitetura modular")
        
        # Implementação básica para casos onde sistema original não está disponível
        self.bot_engine.start()
        
        try:
            while True:
                print("💭 Sistema modular em execução... (Ctrl+C para parar)")
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("\n🛑 Parando sistema modular...")
            self.bot_engine.stop()
    
    def _show_status(self):
        """Mostra status completo do sistema"""
        
        # Status do Config Manager
        config_status = self.config_manager.get_status()
        print(f"   • Configurações: {config_status['total_sections']} seções carregadas")
        
        # Status do Plugin Registry  
        plugin_status = self.plugin_registry.get_registry_status()
        print(f"   • Plugins: {plugin_status['total_registered_classes']} classes, {plugin_status['total_loaded_plugins']} carregados")
        
        # Status do Bot Engine
        engine_status = self.bot_engine.get_status()
        print(f"   • Engine: {'Rodando' if engine_status['engine']['running'] else 'Parado'}")
        
        # Mostra configurações principais
        trading_config = self.config_manager.get_trading_config()
        print(f"   • Trading: {trading_config.get('symbol', 'N/A')} - {trading_config.get('timeframe', 'N/A')}")
        
        ai_config = self.config_manager.get_ai_config()
        print(f"   • AI Gateway: {ai_config.get('gateway_url', 'N/A')}")
        
        risk_config = self.config_manager.get_risk_config()
        print(f"   • Risk: DD máximo {risk_config.get('max_drawdown_pct', 'N/A')}%")
    
    def _cleanup(self):
        """Limpeza de recursos"""
        print("\n🧹 Limpando recursos...")
        
        try:
            self.plugin_registry.cleanup_all_plugins()
            self.bot_engine.stop()
            print("✅ Limpeza concluída")
        except Exception as e:
            print(f"⚠  Erro na limpeza: {e}")
    
    def get_modular_status(self):
        """Retorna status completo da arquitetura modular"""
        return {
            'modular_system': {
                'version': '2.0.0-modular',
                'legacy_available': LEGACY_SYSTEM_AVAILABLE,
                'hybrid_mode': self.use_legacy_runner,
                'enhancements_active': self.modular_enhancements
            },
            'config_manager': self.config_manager.get_status(),
            'plugin_registry': self.plugin_registry.get_registry_status(),
            'bot_engine': self.bot_engine.get_status()
        }


# =============================================================================
# AGENT ORCHESTRATION - PHASE 1
# FastAPI integration on same port (9200)
# =============================================================================

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn
import threading
import asyncio

# Import orchestration components
from core.orchestrator import agent_engine, register_agent_metrics
from core.orchestrator.router import orchestration_router

# Create FastAPI app
app = FastAPI(title="Bot AI MultiAgent", version="1.0.0")

# Mount orchestration router
app.include_router(orchestration_router)

# Health endpoint (existing compatibility)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "bot-ai-multiagent"}

# Metrics endpoint for Prometheus
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, REGISTRY
    return generate_latest(REGISTRY)

# Metrics endpoint is already handled by prometheus_client on port 9200
# The HTTP server is started at line 57 above

def initialize_orchestration():
    """Initialize agent orchestration system"""
    try:
        print("\n🎯 Initializing Agent Orchestration (Phase 1)...")
        
        # Register metrics with Prometheus
        register_agent_metrics()
        print("✅ Agent metrics registered")
        
        # Initialize agent engine
        success, message = agent_engine.initialize()
        if success:
            print(f"✅ Agent Engine: {message}")
        else:
            print(f"⚠️  Agent Engine: {message}")
        
        print("✅ Agent Orchestration ready")
        
    except Exception as e:
        print(f"❌ Failed to initialize orchestration: {e}")

def run_fastapi_server():
    """Run FastAPI server in background thread"""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run uvicorn server
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=9200,
            log_level="info",
            access_log=False
        )
        server = uvicorn.Server(config)
        loop.run_until_complete(server.serve())
        
    except Exception as e:
        print(f"❌ FastAPI server error: {e}")


def show_modular_info():
    """Mostra informações sobre a nova arquitetura"""
    print("\n" + "="*80)
    print("📋 INFORMAÇÕES DA ARQUITETURA MODULAR")
    print("="*80)
    print()
    print("🎯 MELHORIAS IMPLEMENTADAS:")
    print("   ✅ Arquitetura modular com separação clara de responsabilidades")
    print("   ✅ Sistema de plugins extensível")
    print("   ✅ Gerenciamento centralizado de configurações")
    print("   ✅ Compatibilidade 100% com sistema existente")
    print("   ✅ Estrutura preparada para expansão futura")
    print("   ✅ Agent Orchestration (Phase 1) - Shadow mode")
    print()
    print("📁 NOVA ESTRUTURA DE DIRETÓRIOS:")
    print("   • core/          - Motor principal e componentes centrais")
    print("   • core/orchestrator/ - Agent orchestration system")
    print("   • ai/            - Sistema de IA modular")
    print("   • risk/          - Gerenciamento de risco refatorado")
    print("   • plugins/       - Sistema de plugins")
    print("   • config/        - Configurações centralizadas")
    print("   • config/agents/ - Agent YAML configurations")
    print()
    print("🔄 MODO DE EXECUÇÃO:")
    print("   • HÍBRIDO: Nova arquitetura + sistema original")
    print("   • Funcionalidades existentes preservadas")
    print("   • Melhorias modulares aplicadas como overlay")
    print("   • Agent Orchestration: Shadow mode only (Phase 1)")
    print()
    print("🚀 PRÓXIMAS ETAPAS:")
    print("   • Etapa 2: Sistema multi-exchange")
    print("   • Etapa 3: Engine de backtesting")
    print("   • Etapa 4: Documentação e comunidade")
    print("="*80)


def main():
    """Função principal - mantém compatibilidade"""
    
    # Verifica se deve mostrar info da arquitetura
    if len(sys.argv) > 1 and sys.argv[1] == '--modular-info':
        show_modular_info()
        return
    
    # Initialize Agent Orchestration (Phase 1)
    initialize_orchestration()
    
    # Start FastAPI server in background thread
    print("🚀 Starting FastAPI server on port 9200...")
    fastapi_thread = threading.Thread(target=run_fastapi_server, daemon=True)
    fastapi_thread.start()
    print("✅ FastAPI server started (background)")
    
    # Give FastAPI a moment to start
    time.sleep(2)
    
    # Modo padrão: execução híbrida
    try:
        runner = ModularBotRunner()
        runner.run_hybrid_mode()
        
    except Exception as e:
        print(f"\n💥 Erro crítico: {e}")
        
        # Se falhar, tenta executar sistema original diretamente
        if LEGACY_SYSTEM_AVAILABLE:
            print("🔄 Tentando fallback para sistema original...")
            try:
                # Chama main() original diretamente
                import bot_runner
                bot_runner.main()
            except Exception as fallback_error:
                print(f"❌ Fallback também falhou: {fallback_error}")
                sys.exit(1)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()