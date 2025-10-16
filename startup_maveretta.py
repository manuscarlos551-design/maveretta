#!/usr/bin/env python
"""
Script de Inicialização do Maveretta Bot
Inicializa todos os componentes: Agentes, Slots, Risk Validator
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/maveretta_startup.log')
    ]
)

logger = logging.getLogger(__name__)

async def startup():
    """Inicializa todos os componentes do sistema"""
    
    logger.info("="*80)
    logger.info("🚀 INICIANDO MAVERETTA TRADING BOT")
    logger.info(f"📅 Data/Hora: {datetime.utcnow().isoformat()}")
    logger.info(f"🎮 Modo: {'SIMULAÇÃO' if os.getenv('PAPER_MODE', 'false').lower() == 'true' else 'LIVE'}")
    logger.info("="*80)
    
    # 1. Inicializa Agent Registry
    logger.info("\n📦 ETAPA 1: Inicializando Agent Registry...")
    try:
        from core.agents.agent_registry import get_agent_registry
        
        registry = get_agent_registry()
        agents = registry.get_all_agents()
        
        logger.info(f"✅ Agent Registry inicializado com {len(agents)} agentes")
        
        for agent in agents:
            logger.info(f"  🤖 {agent['id']}: {agent['name']} ({agent['model']}) - {agent['status']}")
    
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar Agent Registry: {e}")
        return False
    
    # 2. Inicializa Slot Loader
    logger.info("\n📦 ETAPA 2: Inicializando Slot Loader...")
    try:
        from core.slots.slot_loader import get_slot_loader
        
        slot_loader = get_slot_loader()
        slots = slot_loader.get_all_slots()
        
        logger.info(f"✅ Slot Loader inicializado com {len(slots)} slots")
        
        for slot in slots:
            logger.info(f"  🎰 {slot['id']}: {slot['symbol']} - {slot['strategy']} ({slot['status']})")
    
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar Slot Loader: {e}")
        return False
    
    # 3. Inicializa Risk Validator
    logger.info("\n📦 ETAPA 3: Inicializando Risk Validator...")
    try:
        from core.risk.risk_validator import get_risk_validator
        
        risk_validator = get_risk_validator()
        
        logger.info(f"✅ Risk Validator inicializado")
        logger.info(f"  🛡️ Max Drawdown: {risk_validator.max_drawdown_pct}%")
        logger.info(f"  🛡️ Risk per Trade: {risk_validator.risk_per_trade * 100}%")
        logger.info(f"  🛡️ Max Daily Loss: {risk_validator.max_daily_loss_pct}%")
    
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar Risk Validator: {e}")
        return False
    
    # 4. Testa conectividade com exchanges
    logger.info("\n📦 ETAPA 4: Testando conectividade com exchanges...")
    try:
        from core.exchanges.market_data_provider import test_all_exchanges
        
        results = test_all_exchanges()
        
        connected = sum(1 for r in results.values() if "✅" in r["status"])
        logger.info(f"✅ Conectadas: {connected}/{len(results)} exchanges")
    
    except Exception as e:
        logger.error(f"❌ Erro ao testar exchanges: {e}")
        # Não é crítico, continua
    
    # 5. Verifica MongoDB
    logger.info("\n📦 ETAPA 5: Verificando MongoDB...")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
        client = AsyncIOMotorClient(mongo_uri)
        
        # Testa conexão
        await client.admin.command('ping')
        logger.info(f"✅ MongoDB conectado: {mongo_uri}")
        
        # Lista databases
        dbs = await client.list_database_names()
        logger.info(f"  📊 Databases disponíveis: {', '.join(dbs)}")
    
    except Exception as e:
        logger.error(f"❌ Erro ao conectar MongoDB: {e}")
        return False
    
    # 6. Verifica Redis (se configurado)
    logger.info("\n📦 ETAPA 6: Verificando Redis...")
    try:
        import redis
        
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        r.ping()
        
        logger.info(f"✅ Redis conectado: {redis_host}:{redis_port}")
    
    except Exception as e:
        logger.warning(f"⚠️ Redis não disponível: {e}")
        # Não é crítico
    
    # 7. Inicializa API Gateway (se não estiver rodando)
    logger.info("\n📦 ETAPA 7: Verificando API Gateway...")
    try:
        import requests
        
        api_url = "http://localhost:8080/v1/health"
        response = requests.get(api_url, timeout=5)
        
        if response.status_code == 200:
            logger.info(f"✅ API Gateway ativo: {api_url}")
        else:
            logger.warning(f"⚠️ API Gateway retornou status {response.status_code}")
    
    except Exception as e:
        logger.warning(f"⚠️ API Gateway não acessível: {e}")
        logger.info("  💡 Certifique-se que o serviço ai-gateway está rodando")
    
    # SUCESSO
    logger.info("\n" + "="*80)
    logger.info("✅ MAVERETTA BOT INICIALIZADO COM SUCESSO!")
    logger.info("="*80)
    logger.info("\n📊 Próximos passos:")
    logger.info("  1. Acesse o dashboard: http://localhost:8501")
    logger.info("  2. Verifique agentes: http://localhost:8080/v1/ias/health")
    logger.info("  3. Verifique slots: http://localhost:8080/v1/slots")
    logger.info("  4. Monitore logs: docker-compose logs -f bot-ai-multiagent")
    logger.info("\n")
    
    return True


if __name__ == "__main__":
    # Executa startup
    result = asyncio.run(startup())
    
    if result:
        logger.info("🎯 Sistema pronto para operar!")
        sys.exit(0)
    else:
        logger.error("💥 Falha na inicialização do sistema")
        sys.exit(1)
