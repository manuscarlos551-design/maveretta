# interfaces/api/routes/ia.py  
"""
IA Routes - Sistema de IAs de trading
"""
import logging
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
import redis
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["IA System"])

# Configuração das 7 IAs fixas
FIXED_IAS = {
    'IA_G1_SCALP_GPT4O': {
        'name': 'Scalp GPT-4o',
        'group': 'G1',
        'strategy': 'scalp',
        'description': 'IA especializada em scalping com GPT-4o'
    },
    'IA_G2_TENDENCIA_GPT4O': {
        'name': 'Tendência GPT-4o', 
        'group': 'G2',
        'strategy': 'tendencia',
        'description': 'IA de análise de tendências com GPT-4o'
    },
    'IA_ORQUESTRADORA_CLAUDE': {
        'name': 'Orquestradora Claude',
        'group': 'LEADER',
        'strategy': 'orchestration',
        'description': 'IA líder de orquestração usando Claude'
    },
    'IA_RESERVA_G1_HOT_HAIKU': {
        'name': 'Reserva G1 Hot',
        'group': 'G1_BACKUP', 
        'strategy': 'scalp_backup',
        'description': 'IA de reserva G1 com Haiku'
    },
    'IA_RESERVA_G1_WARM_GPT4ALL': {
        'name': 'Reserva G1 Warm',
        'group': 'G1_BACKUP',
        'strategy': 'multi_strategy', 
        'description': 'IA de reserva G1 com GPT4All'
    },
    'IA_SENTIMENTO_SENTIAI': {
        'name': 'Sentimento SentiAI',
        'group': 'ANALYSIS',
        'strategy': 'sentiment',
        'description': 'IA de análise de sentimento de mercado'
    },
    'IA_ARBITRAGEM_COINGECKO_BINANCE': {
        'name': 'Arbitragem Multi-Exchange',
        'group': 'ARBITRAGE', 
        'strategy': 'arbitrage',
        'description': 'IA de arbitragem entre exchanges'
    }
}

def _get_redis_client():
    """Obtém cliente Redis"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Erro ao conectar Redis: {e}")
        return None

def _get_ia_status_from_redis(ia_id: str, redis_client) -> Dict[str, Any]:
    """Obtém status real da IA do Redis"""
    if not redis_client:
        return {
            'status': 'RED',
            'latency_ms': 0,
            'uptime_h': 0,
            'last_decision': None,
            'error': 'Redis não disponível'
        }
    
    try:
        # Chaves Redis para status da IA
        status_key = f"ia:{ia_id}:status"
        metrics_key = f"ia:{ia_id}:metrics"
        decision_key = f"ia:{ia_id}:last_decision"
        
        # Status básico
        status_data = redis_client.get(status_key)
        if status_data:
            status_info = json.loads(status_data)
        else:
            status_info = {'status': 'RED', 'last_seen': None}
        
        # Métricas
        metrics_data = redis_client.get(metrics_key)
        if metrics_data:
            metrics = json.loads(metrics_data)
        else:
            metrics = {'latency_ms': 0, 'uptime_start': None}
        
        # Última decisão  
        last_decision_data = redis_client.get(decision_key)
        last_decision = None
        if last_decision_data:
            try:
                last_decision = json.loads(last_decision_data)
            except:
                pass
        
        # Calcular uptime
        uptime_h = 0
        if metrics.get('uptime_start'):
            try:
                start_time = datetime.fromisoformat(metrics['uptime_start'])
                uptime_h = (datetime.now() - start_time).total_seconds() / 3600
            except:
                pass
        
        # Determinar status baseado em last_seen
        status = status_info.get('status', 'RED')
        if status_info.get('last_seen'):
            try:
                last_seen = datetime.fromisoformat(status_info['last_seen'])
                minutes_ago = (datetime.now() - last_seen).total_seconds() / 60
                
                if minutes_ago > 10:  # Mais de 10 min sem sinal
                    status = 'RED'
                elif minutes_ago > 5:  # Entre 5-10 min
                    status = 'AMBER'
                elif status != 'GREEN':  # Ativa recente
                    status = 'GREEN'
            except:
                status = 'RED'
        
        return {
            'status': status,
            'latency_ms': metrics.get('latency_ms', 0),
            'uptime_h': round(uptime_h, 1),
            'last_decision': last_decision,
            'last_seen': status_info.get('last_seen'),
            'strategy_active': status_info.get('strategy', 'unknown')
        }
        
    except Exception as e:
        logger.warning(f"Erro ao obter status da IA {ia_id}: {e}")
        return {
            'status': 'RED',
            'latency_ms': 0, 
            'uptime_h': 0,
            'last_decision': None,
            'error': str(e)
        }

@router.get("/ias/health") 
async def get_ias_health() -> Dict[str, Any]:
    """
    Status de saúde de todas as 7 IAs
    """
    try:
        redis_client = _get_redis_client()
        ias_status = []
        
        for ia_id, ia_info in FIXED_IAS.items():
            # Status da IA do Redis
            ia_status = _get_ia_status_from_redis(ia_id, redis_client)
            
            # Combinar com informações fixas
            ia_complete = {
                'id': ia_id,
                'name': ia_info['name'],
                'group': ia_info['group'],
                'strategy': ia_status.get('strategy_active', ia_info['strategy']),
                'description': ia_info['description'],
                **ia_status
            }
            
            ias_status.append(ia_complete)
        
        # Estatísticas gerais
        green_count = len([ia for ia in ias_status if ia['status'] == 'GREEN'])
        amber_count = len([ia for ia in ias_status if ia['status'] == 'AMBER'])  
        red_count = len([ia for ia in ias_status if ia['status'] == 'RED'])
        
        return {
            'ias': ias_status,
            'summary': {
                'total': len(ias_status),
                'green': green_count,
                'amber': amber_count,
                'red': red_count,
                'health_percentage': (green_count / len(ias_status)) * 100
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter health das IAs: {e}")
        
        # Retornar estrutura básica com todas RED se houver erro
        ias_status = []
        for ia_id, ia_info in FIXED_IAS.items():
            ias_status.append({
                'id': ia_id,
                'name': ia_info['name'],
                'group': ia_info['group'],
                'strategy': ia_info['strategy'],
                'description': ia_info['description'],
                'status': 'RED',
                'latency_ms': 0,
                'uptime_h': 0,
                'last_decision': None,
                'error': 'Sistema indisponível'
            })
        
        return {
            'ias': ias_status,
            'summary': {
                'total': len(ias_status),
                'green': 0,
                'amber': 0, 
                'red': len(ias_status),
                'health_percentage': 0
            },
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.get("/ias/{ia_id}/insights")
async def get_ia_insights(ia_id: str) -> Dict[str, Any]:
    """
    Retorna insights detalhados para uma IA específica.
    """
    try:
        if ia_id not in FIXED_IAS:
            raise HTTPException(status_code=404, detail="IA não encontrada")
        
        redis_client = _get_redis_client()
        ia_status = _get_ia_status_from_redis(ia_id, redis_client)
        
        # Adicionar informações fixas
        ia_info = FIXED_IAS[ia_id]
        ia_complete = {
            'id': ia_id,
            'name': ia_info['name'],
            'group': ia_info['group'],
            'strategy': ia_status.get('strategy_active', ia_info['strategy']),
            'description': ia_info['description'],
            **ia_status
        }
        
        # Adicionar insights específicos (ex: performance recente, recomendações)
        # Estes seriam dados mais complexos, aqui é um placeholder
        ia_complete['recent_performance'] = {
            'last_24h_pnl_pct': 'N/A',
            'trades_count_24h': 'N/A',
            'win_rate_24h': 'N/A'
        }
        ia_complete['recommendations'] = [
            'Monitorar volatilidade do par BTC/USDT',
            'Considerar ajuste de stop-loss para estratégias de scalping'
        ]
        
        return ia_complete
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter insights da IA {ia_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

@router.get("/audits")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = None,
    action_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retorna logs de auditoria do sistema.
    """
    try:
        query = {}
        if user_id:
            query["user_id"] = user_id
        if action_type:
            query["action_type"] = action_type
        if start_date or end_date:
            date_query = {}
            if start_date:
                try:
                    date_query["$gte"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                except ValueError:
                    raise HTTPException(400, "Formato de data inicial inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SSZ).")
            if end_date:
                try:
                    date_query["$lte"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                except ValueError:
                    raise HTTPException(400, "Formato de data final inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SSZ).")
            query["timestamp"] = date_query

        audit_logs = await db_client.db.audit_logs.find(query).sort("timestamp", -1).skip(offset).limit(limit).to_list(length=limit)
        
        for log in audit_logs:
            log["id"] = str(log["_id"])
            if "_id" in log: del log["_id"]
            if "timestamp" in log and isinstance(log["timestamp"], datetime):
                log["timestamp"] = log["timestamp"].isoformat() + "Z"

        return {"audit_logs": audit_logs, "total": len(audit_logs)}
    except Exception as e:
        logger.error(f"Erro ao buscar logs de auditoria: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

@router.post("/audits")
async def create_audit_log(log_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cria um novo log de auditoria.
    """
    try:
        log_entry["timestamp"] = datetime.utcnow()
        result = await db_client.db.audit_logs.insert_one(log_entry)
        return {"status": "ok", "message": "Log de auditoria criado", "id": str(result.inserted_id)}
    except Exception as e:
        logger.error(f"Erro ao criar log de auditoria: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

