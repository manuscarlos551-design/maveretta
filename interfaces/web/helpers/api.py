# interfaces/web/helpers/api.py
"""Cliente API otimizado"""
import os
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import streamlit as st

API_URL = os.getenv("API_URL", "http://ai-gateway:8080")
TIMEOUT = 10

@st.cache_data(ttl=30)
def get_agents() -> List[Dict]:
    """Lista agentes (cache 30s)"""
    try:
        response = requests.get(f"{API_URL}/agents", timeout=TIMEOUT)
        return response.json() if response.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=30)
def get_slots() -> List[Dict]:
    """Lista slots (cache 30s)"""
    try:
        response = requests.get(f"{API_URL}/slots", timeout=TIMEOUT)
        return response.json() if response.status_code == 200 else []
    except:
        return []

def start_agent(agent_id: str) -> tuple[bool, str]:
    """Inicia agente"""
    try:
        response = requests.post(f"{API_URL}/agents/{agent_id}/start", timeout=TIMEOUT)
        return response.status_code == 200, response.json().get("message", "")
    except Exception as e:
        return False, str(e)

def stop_agent(agent_id: str) -> tuple[bool, str]:
    """Para agente"""
    try:
        response = requests.post(f"{API_URL}/agents/{agent_id}/stop", timeout=TIMEOUT)
        return response.status_code == 200, response.json().get("message", "")
    except Exception as e:
        return False, str(e)

def set_agent_mode(agent_id: str, mode: str) -> tuple[bool, str]:
    """Muda modo do agente"""
    try:
        response = requests.post(
            f"{API_URL}/agents/{agent_id}/mode",
            json={"mode": mode},
            timeout=TIMEOUT
        )
        return response.status_code == 200, response.json().get("message", "")
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=60)
def get_consensus_history(limit: int = 50) -> List[Dict]:
    """Histórico de consenso (cache 60s)"""
    try:
        response = requests.get(f"{API_URL}/consensus?limit={limit}", timeout=TIMEOUT)
        return response.json() if response.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=60)
def get_trades(limit: int = 100) -> List[Dict]:
    """Histórico de trades (cache 60s)"""
    try:
        response = requests.get(f"{API_URL}/trades?limit={limit}", timeout=TIMEOUT)
        return response.json() if response.status_code == 200 else []
    except:
        return []

def trigger_consensus(symbol: str, agents: List[str], timeframe: str = "5m") -> tuple[bool, str, Dict]:
    """Dispara rodada de consenso"""
    try:
        response = requests.post(
            f"{API_URL}/consensus/trigger",
            json={"symbol": symbol, "agents": agents, "timeframe": timeframe},
            timeout=30
        )
        if response.status_code == 200:
            return True, "Consenso iniciado", response.json()
        return False, "Erro ao iniciar consenso", {}
    except Exception as e:
        return False, str(e), {}
