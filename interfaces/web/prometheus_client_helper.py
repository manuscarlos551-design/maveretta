"""
Helper para buscar métricas diretamente do Prometheus
Usado quando API Gateway não está disponível ou para dados complementares
"""
import os
import logging
import requests
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# URL do Prometheus
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
DEFAULT_TIMEOUT = 5

class PrometheusClient:
    """Cliente para consultas diretas ao Prometheus"""
    
    def __init__(self):
        self.base_url = PROMETHEUS_URL.rstrip("/")
    
    def query(self, promql: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """
        Executa query PromQL instantânea
        Returns: {"status": "success", "data": {"resultType": "...", "result": [...]}}
        """
        try:
            url = f"{self.base_url}/api/v1/query"
            response = requests.get(
                url,
                params={"query": promql},
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao consultar Prometheus: {e}")
            return {"status": "error", "data": {"result": []}}
    
    def query_range(self, promql: str, start: str, end: str, step: str = "15s", 
                    timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """
        Executa query PromQL com range de tempo
        """
        try:
            url = f"{self.base_url}/api/v1/query_range"
            response = requests.get(
                url,
                params={
                    "query": promql,
                    "start": start,
                    "end": end,
                    "step": step
                },
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao consultar Prometheus range: {e}")
            return {"status": "error", "data": {"result": []}}
    
    def get_label_values(self, label: str, timeout: int = DEFAULT_TIMEOUT) -> List[str]:
        """
        Obtém valores disponíveis para um label
        Ex: get_label_values("symbol") → ["BTCUSDT", "ETHUSDT", ...]
        """
        try:
            url = f"{self.base_url}/api/v1/label/{label}/values"
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Erro ao buscar label values: {e}")
            return []
    
    def get_equity_brl(self) -> float:
        """Obtém equity total em BRL"""
        result = self.query("sum without() (binance_equity_brl)")
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                return float(value[1]) if len(value) > 1 else 0.0
        return 0.0
    
    def get_equity_usdt(self) -> float:
        """Obtém equity total em USDT"""
        result = self.query("sum without() (binance_equity_usdt)")
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                return float(value[1]) if len(value) > 1 else 0.0
        return 0.0
    
    def get_active_slots(self) -> int:
        """Obtém número de slots ativos"""
        result = self.query("sum without() (bot_slots_active)")
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                return int(float(value[1])) if len(value) > 1 else 0
        return 0
    
    def get_ws_messages_rate(self) -> float:
        """Obtém taxa de mensagens WebSocket por minuto"""
        result = self.query("rate(binance_websocket_messages_total[1m]) * 60")
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                return float(value[1]) if len(value) > 1 else 0.0
        return 0.0
    
    def get_connection_status(self) -> bool:
        """Verifica se conexão com Binance está ativa"""
        result = self.query("binance_connection_status")
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                return float(value[1]) == 1.0 if len(value) > 1 else False
        return False
    
    def get_best_prices(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém top N preços (best ask) de USDT pairs
        Returns: [{"symbol": "BTCUSDT", "price": 45000.0}, ...]
        """
        result = self.query(f"topk({limit}, binance_best_ask{{symbol=~'.*USDT'}})")
        prices = []
        
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            for item in data:
                metric = item.get("metric", {})
                value = item.get("value", [None, "0"])
                if len(value) > 1:
                    prices.append({
                        "symbol": metric.get("symbol", ""),
                        "price": float(value[1])
                    })
        
        return prices
    
    def get_available_symbols(self) -> List[str]:
        """Obtém lista de símbolos disponíveis"""
        return self.get_label_values("symbol")
    
    def get_exchange_equity_usdt(self, exchange: str) -> float:
        """Obtém equity em USDT de uma exchange específica"""
        metric_name = f"{exchange.lower()}_equity_usdt"
        result = self.query(f"sum without() ({metric_name})")
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                return float(value[1]) if len(value) > 1 else 0.0
        return 0.0
    
    def get_exchange_equity_brl(self, exchange: str) -> float:
        """Obtém equity em BRL de uma exchange específica"""
        metric_name = f"{exchange.lower()}_equity_brl"
        result = self.query(f"sum without() ({metric_name})")
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                return float(value[1]) if len(value) > 1 else 0.0
        return 0.0
    
    def get_exchange_connection_status(self, exchange: str) -> bool:
        """Verifica se uma exchange está conectada"""
        metric_name = f"{exchange.lower()}_connection_status"
        result = self.query(metric_name)
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                return float(value[1]) == 1.0 if len(value) > 1 else False
        return False
    
    def get_total_equity_usdt_all_exchanges(self) -> float:
        """Obtém equity total em USDT de todas as exchanges"""
        exchanges = ["binance", "kucoin", "bybit", "coinbase", "okx"]
        total = 0.0
        for exchange in exchanges:
            total += self.get_exchange_equity_usdt(exchange)
        return total
    
    def get_total_equity_brl_all_exchanges(self) -> float:
        """Obtém equity total em BRL de todas as exchanges"""
        exchanges = ["binance", "kucoin", "bybit", "coinbase", "okx"]
        total = 0.0
        for exchange in exchanges:
            total += self.get_exchange_equity_brl(exchange)
        return total
    
    def is_available(self) -> bool:
        """Verifica se Prometheus está disponível"""
        try:
            url = f"{self.base_url}/-/ready"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except Exception:
            return False


# Instância global
_prom_client = PrometheusClient()

# Funções de conveniência
def get_equity_brl() -> float:
    """Obtém equity em BRL via Prometheus"""
    return _prom_client.get_equity_brl()

def get_equity_usdt() -> float:
    """Obtém equity em USDT via Prometheus"""
    return _prom_client.get_equity_usdt()

def get_connection_status() -> bool:
    """Verifica conexão com Binance"""
    return _prom_client.get_connection_status()

def get_best_prices(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtém top preços"""
    return _prom_client.get_best_prices(limit)

def get_available_symbols() -> List[str]:
    """Obtém símbolos disponíveis"""
    return _prom_client.get_available_symbols()

def is_prometheus_available() -> bool:
    """Verifica se Prometheus está disponível"""
    return _prom_client.is_available()
