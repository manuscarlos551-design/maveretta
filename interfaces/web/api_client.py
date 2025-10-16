# interfaces/web/api_client.py
"""
API Client Centralizado - Única fonte de chamadas HTTP para o AI Gateway
Implementa retry mechanism em Python puro (sem dependências externas)

Versão FINAL - Padronizada conforme especificações
CORREÇÕES: Tratamento de erro aprimorado, sempre retorna {}/[] em caso de falha
"""
import os
import time
import logging
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin

# Configuração de logging
logger = logging.getLogger(__name__)

# Estratégia: se API_URL começar com "/", usamos como subpath via Nginx (ex.: "/v1")
# Caso contrário, usamos URL completa (ex.: "http://ai-gateway:8080").
API_URL = os.getenv("API_URL", "/v1").rstrip("/") or "/v1"
DEFAULT_TIMEOUT = 3  # timeout fixo 3s para não travar UI

# Configuração de retry
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.5
RETRY_STATUS_FORCELIST = [500, 502, 503, 504]

def _u(path: str) -> str:
    """
    Monta URL final com suporte a:
    - Subpath ("/v1") → "/v1/<path>"
    - URL completa ("http://ai-gateway:8080") → "http://ai-gateway:8080/<path>"
    """
    base = (API_URL or "/v1").rstrip("/")
    p = path.lstrip("/")

    if base.startswith("/"):
        return f"{base}/{p}"
    return urljoin(base + "/", p)

class APIClient:
    """Cliente HTTP com retry automático e timeouts configuráveis"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Configura retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=RETRY_STATUS_FORCELIST,
            allowed_methods=["GET", "POST"]
        )
        
        # Adapter com retry
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers padrão
        self.session.headers.update({
            "User-Agent": "Maveretta-Dashboard/1.0.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
    
    def _request(self, method: str, url: str, timeout: int = DEFAULT_TIMEOUT, **kwargs) -> Dict[str, Any]:
        """
        Método interno para requests com tratamento de erro centralizado
        NUNCA lança exceções - retorna dict/list vazios nos except
        """
        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            
            # Para endpoints que retornam texto puro (como /metrics)
            if response.headers.get('content-type', '').startswith('text/plain'):
                return {"text": response.text}
                
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout na requisição {method} {url}")
            return {}
            
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 Erro de conexão com {url}")
            return {}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"🚨 HTTP Error {e.response.status_code} em {method} {url}")
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro na requisição {method} {url}: {e}")
            return {}
            
        except ValueError as e:  # JSON decode error
            logger.error(f"📄 Erro ao decodificar JSON de {url}: {e}")
            return {}
        except Exception as e:
            logger.error(f"💥 Erro inesperado em {method} {url}: {e}")
            return {}
    
    def health(self) -> Dict[str, Any]:
        """Health check do AI Gateway - nunca lança exception"""
        try:
            result = self._request("GET", _u("/health"), timeout=DEFAULT_TIMEOUT)
            return result if result else {"status": "error", "error": "API indisponível"}
        except Exception:
            return {"status": "error", "error": "API indisponível"}
    
    def get_orchestration_state(self) -> Dict[str, Any]:
        """Estado completo da orquestração - nunca lança exception
        
        Contrato esperado (shape fixo mesmo vazio):
        {
            "ias": [],
            "slots": [],
            "decisions": [],
            "risk_controls": {},
            "wallet": {}
        }
        """
        try:
            result = self._request("GET", _u("/orchestration/state"), timeout=DEFAULT_TIMEOUT)
            if not result:
                # Retorna contrato fixo vazio
                return {
                    "ias": [],
                    "slots": [],
                    "decisions": [],
                    "risk_controls": {},
                    "wallet": {}
                }
            return result
        except Exception:
            return {
                "ias": [],
                "slots": [],
                "decisions": [],
                "risk_controls": {},
                "wallet": {}
            }
    
    def get_ia_health(self) -> List[Dict[str, Any]]:
        """Health das IAs - nunca lança exception, sempre retorna lista"""
        try:
            result = self._request("GET", _u("/ias/health"))
            if isinstance(result, dict):
                return result.get("ias", [])
            elif isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_exchange_health(self) -> List[Dict[str, Any]]:
        """Health das exchanges - nunca lança exception, sempre retorna lista"""
        try:
            result = self._request("GET", _u("/exchanges/health"))
            if isinstance(result, dict):
                return result.get("exchanges", [])
            elif isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_slots(self) -> List[Dict[str, Any]]:
        """Lista de slots - nunca lança exception, sempre retorna lista"""
        try:
            result = self._request("GET", _u("/slots"))
            if isinstance(result, dict):
                return result.get("slots", [])
            elif isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_logs(self, source: Optional[str] = None, level: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Logs do sistema - nunca lança exception, sempre retorna dict com logs"""
        try:
            params = {"limit": limit}
            if source:
                params["source"] = source
            if level:
                params["level"] = level
                
            result = self._request("GET", _u("/logs"), params=params)
            if isinstance(result, dict):
                return result if "logs" in result else {"logs": []}
            return {"logs": []}
        except Exception:
            return {"logs": []}
    
    def post_override_strategy(self, slot_id: str, strategy_code: str) -> Dict[str, Any]:
        """Aplica override - nunca lança exception"""
        try:
            payload = {
                "slot_id": slot_id,
                "strategy_code": strategy_code
            }
            result = self._request("POST", _u("/override"), json=payload)
            return result if result else {"success": False, "error": "Falha na comunicação"}
        except Exception:
            return {"success": False, "error": "Falha na comunicação"}
    
    def get_metrics(self) -> str:
        """Métricas Prometheus - nunca lança exception"""
        try:
            result = self._request("GET", _u("/metrics"))
            return result.get("text", "") if result else ""
        except Exception:
            return ""
    
    def get_version(self) -> Dict[str, Any]:
        """Versão da API - nunca lança exception"""
        try:
            result = self._request("GET", _u("/version"))
            return result if result else {"version": "unknown", "environment": "unknown"}
        except Exception:
            return {"version": "unknown", "environment": "unknown"}
    
    def get_operations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista de operações recentes - nunca lança exception"""
        try:
            result = self._request("GET", _u("/operations"), params={"limit": limit})
            if isinstance(result, dict):
                return result.get("operations", [])
            elif isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_controls(self) -> Dict[str, Any]:
        """Estado dos controles do sistema - nunca lança exception"""
        try:
            result = self._request("GET", _u("/controls"))
            return result if result else {"controls": {}, "overrides": {}}
        except Exception:
            return {"controls": {}, "overrides": {}}
    
    def get_ia_insights(self, ia_id: str) -> Dict[str, Any]:
        """Insights de uma IA específica - nunca lança exception"""
        try:
            result = self._request("GET", _u(f"/v1/ias/{ia_id}/insights"))
            return result if result else {}
        except Exception:
            return {}
    
    def get_audit_logs(self, limit: int = 100) -> Dict[str, Any]:
        """Logs de auditoria - nunca lança exception"""
        try:
            result = self._request("GET", _u("/logs"), params={"source": "audit", "limit": limit})
            return result if result else {"logs": []}
        except Exception:
            return {"logs": []}
    
    def get_alerts(self) -> Dict[str, Any]:
        """Alertas ativos - nunca lança exception"""
        try:
            result = self._request("GET", _u("/alerts"))
            return result if result else {"alerts": [], "critical": [], "warnings": []}
        except Exception:
            return {"alerts": [], "critical": [], "warnings": []}
    
    def get_backtests(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Backtests executados - nunca lança exception"""
        try:
            result = self._request("GET", _u("/backtests"), params={"limit": limit})
            if isinstance(result, dict):
                return result.get("backtests", [])
            elif isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_strategies(self) -> List[Dict[str, Any]]:
        """Estratégias disponíveis - nunca lança exception"""
        try:
            result = self._request("GET", _u("/strategies"))
            if isinstance(result, dict):
                return result.get("strategies", [])
            elif isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_wallet_details(self) -> Dict[str, Any]:
        """Detalhes completos da carteira - nunca lança exception"""
        try:
            result = self._request("GET", _u("/wallet"))
            return result if result else {"exchanges": {}, "balances": {}, "positions": {}}
        except Exception:
            return {"exchanges": {}, "balances": {}, "positions": {}}

    def get_orchestration_status(self) -> Dict[str, Any]:
        """Retorna o status atual do bot (state, mode, emergency) - nunca lança exception"""
        try:
            result = self._request("GET", _u("/v1/orchestration/status"))
            return result if result else {"state": "unknown", "mode": "unknown", "emergency": False}
        except Exception:
            return {"state": "unknown", "mode": "unknown", "emergency": False}

    # =============================================================================
    # FASE 3 METHODS - CONTROLES E OPERAÇÕES
    # =============================================================================
    
    def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET genérico - nunca lança exception"""
        try:
            result = self._request("GET", _u(path), params=params)
            return result if result else {}
        except Exception:
            return {}
    
    def post(self, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """POST genérico - nunca lança exception"""
        try:
            result = self._request("POST", _u(path), json=json)
            return result if result else {}
        except Exception:
            return {}


# Instância global do cliente
_client = APIClient()

# ===== FUNÇÕES DE INTERFACE (backward compatibility) =====

def health() -> Dict[str, Any]:
    """Health check do AI Gateway"""
    return _client.health()

def get_orchestration_state() -> Dict[str, Any]:
    """Estado completo da orquestração"""
    return _client.get_orchestration_state()

def get_ia_health() -> List[Dict[str, Any]]:
    """Health das IAs"""
    return _client.get_ia_health()

def get_exchange_health() -> List[Dict[str, Any]]:
    """Health das exchanges"""
    return _client.get_exchange_health()

def post_override_strategy(slot_id: str, strategy_code: str) -> Dict[str, Any]:
    """Aplica override de estratégia em slot"""
    return _client.post_override_strategy(slot_id, strategy_code)

def get_logs(source: Optional[str] = None, level: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """Logs do sistema com filtros"""
    return _client.get_logs(source, level, limit)

def get_slots() -> List[Dict[str, Any]]:
    """Lista de slots de trading"""
    return _client.get_slots()

def get_metrics() -> str:
    """Métricas Prometheus"""
    return _client.get_metrics()

def get_version() -> Dict[str, Any]:
    """Versão da API"""
    return _client.get_version()

def get_operations(limit: int = 50) -> List[Dict[str, Any]]:
    """Lista de operações recentes"""
    return _client.get_operations(limit)

def get_controls() -> Dict[str, Any]:
    """Estado dos controles do sistema"""
    return _client.get_controls()

def get_ia_insights() -> Dict[str, Any]:
    """Insights das IAs"""
    return _client.get_ia_insights()

def get_audit_logs(limit: int = 100) -> Dict[str, Any]:
    """Logs de auditoria"""
    return _client.get_audit_logs(limit)

def get_alerts() -> Dict[str, Any]:
    """Alertas ativos"""
    return _client.get_alerts()

def get_backtests(limit: int = 20) -> List[Dict[str, Any]]:
    """Backtests executados"""
    return _client.get_backtests(limit)

def get_strategies() -> List[Dict[str, Any]]:
    """Estratégias disponíveis"""
    return _client.get_strategies()

def get_wallet_details() -> Dict[str, Any]:
    """Detalhes completos da carteira"""
    return _client.get_wallet_details()

def get_orchestration_status() -> Dict[str, Any]:
    """Retorna o status atual do bot (state, mode, emergency)"""
    return _client.get_orchestration_status()

# ===== FUNÇÕES DE UTILIDADE =====

def is_api_available() -> bool:
    """Verifica se a API está disponível"""
    try:
        result = health()
        status = result.get('status', '')
        return str(status).lower() in ['ok', 'healthy']
    except Exception:
        return False

def get_api_status() -> Dict[str, Any]:
    """Status detalhado da API"""
    try:
        health_data = health()
        version_data = get_version()
        
        return {
            "available": is_api_available(),
            "status": health_data.get("status"),
            "version": version_data.get("version"),
            "environment": version_data.get("environment"),
            "timestamp": health_data.get("timestamp")
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "timestamp": time.time()
        }

def get(path: str, params: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    GET genérico para qualquer endpoint
    Usado como fallback quando não há método específico
    """
    try:
        return _client._request("GET", _u(path), params=params, timeout=timeout)
    except Exception as e:
        logger.error(f"Erro em GET {path}: {e}")
        return {}

def post(path: str, data: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    POST genérico para qualquer endpoint
    Usado como fallback quando não há método específico
    """
    try:
        return _client._request("POST", _u(path), json=data, timeout=timeout)
    except Exception as e:
        logger.error(f"Erro em POST {path}: {e}")
        return {}

def test_connection() -> Dict[str, Any]:
    """Teste completo de conectividade"""
    start_time = time.time()
    
    try:
        # Testa health básico
        health_result = health()
        
        # Testa endpoints principais
        endpoints_to_test = [
            ("orchestration", get_orchestration_state),
            ("ias", get_ia_health),
            ("exchanges", get_exchange_health),
            ("slots", get_slots)
        ]
        
        endpoint_results = {}
        for name, func in endpoints_to_test:
            try:
                result = func()
                endpoint_results[name] = {
                    "status": "success",
                    "data_count": len(result) if isinstance(result, list) else 1
                }
            except Exception as e:
                endpoint_results[name] = {
                    "status": "error", 
                    "error": str(e)
                }
        
        return {
            "success": True,
            "health_status": health_result.get("status"),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "endpoints": endpoint_results,
            "api_url": API_URL or "relative"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "api_url": API_URL or "relative"
        }

# ===== INIT =====

def init_api_client():
    """Inicializa e testa o cliente API na importação"""
    logger.info(f"🚀 Inicializando API Client para: {API_URL or 'relative paths'}")
    
    # Testa conectividade básica (não bloqueia se falhar)
    try:
        status = get_api_status()
        if status["available"]:
            logger.info(f"✅ API conectada com sucesso: {status['version']}")
        else:
            logger.warning(f"⚠️ API indisponível: {status.get('error', 'Erro desconhecido')}")
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível testar API na inicialização: {e}")

# Registra extensões da API
try:
    from api_client_extensions import *
    EXTENSIONS_AVAILABLE = True
except ImportError:
    EXTENSIONS_AVAILABLE = False
    logger.warning("API client extensions not available")

# Inicialização automática
init_api_client()