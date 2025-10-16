# interfaces/web/grafana_embed.py
"""
Helper centralizado para embeds do Grafana no Streamlit
"""
import os
from urllib.parse import urlencode
from typing import Optional
import streamlit as st
import logging

logger = logging.getLogger(__name__)

# Configuração base do Grafana
GRAFANA_BASE_URL = os.getenv("GRAFANA_URL", "/grafana").rstrip("/")

# UIDs dos dashboards principais (UIDs REAIS extraídos dos JSONs)
DASHBOARD_UIDS = {
    # Dashboards principais
    "dynamic": "maveretta-dynamic-live",
    "overview": "maveretta-overview-live",
    "slots": "maveretta-slots-live",
    "top10": "maveretta-top10-live",
    "market": "maveretta-market-overview",
    "infrastructure": "maveretta-infrastructure",
    
    # Dashboards de orquestração (UIDs corretos com phase3 suffix)
    "consensus": "maveretta-consensus-flow",
    "agents": "agents-overview-phase3",
    "agent_drilldown": "agent-drilldown-phase3",
    
    # Dashboards operacionais (UIDs corretos com hífens)
    "ia_health": "orchestration-ia-health",
    "venue_health": "orchestration-venue-health",
    "slots_timeline": "orchestration-slots-timeline",
    "decision_conf": "orchestration-decision-conf",
    "arbitrage_legs": "orchestration-arbitrage-legs",
    
    # Dashboards por exchange
    "binance": "maveretta-overview-live",  # Usa a overview que já tem dados Binance
    "kucoin": "maveretta-kucoin-live",
    "bybit": "maveretta-bybit-live",
    "coinbase": "maveretta-coinbase-live",
    "okx": "maveretta-okx-live",
}


def get_dashboard_uid(dashboard_key: str) -> Optional[str]:
    """
    Obtém o UID de um dashboard pelo nome
    
    Args:
        dashboard_key: Chave do dashboard (ex: 'dynamic', 'overview', 'consensus')
    
    Returns:
        UID do dashboard ou None se não encontrado
    """
    return DASHBOARD_UIDS.get(dashboard_key)


def test_grafana_dashboard(uid: str) -> bool:
    """
    Testa se um dashboard do Grafana está acessível
    
    Args:
        uid: UID do dashboard
    
    Returns:
        True se acessível, False caso contrário
    """
    if not uid:
        return False
    
    try:
        import requests
        url = f"{GRAFANA_BASE_URL}/api/dashboards/uid/{uid}"
        response = requests.get(url, timeout=3)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Dashboard {uid} não acessível: {e}")
        return False


def grafana_panel_iframe(
    uid: str,
    panel_id: int,
    from_ms: str = "now-6h",
    to_ms: str = "now",
    refresh: str = "10s",
    height: int = 400,
    theme: str = "dark",
    **extra_vars
) -> str:
    """
    Gera HTML de iframe para embed de painel Grafana
    
    Args:
        uid: UID do dashboard
        panel_id: ID do painel dentro do dashboard
        from_ms: Timestamp inicial (formato Grafana: "now-6h", "now-1d", etc)
        to_ms: Timestamp final (formato Grafana: "now")
        refresh: Intervalo de refresh ("5s", "10s", "30s", "1m", etc)
        height: Altura do iframe em pixels
        theme: Tema do Grafana ("dark" ou "light")
        **extra_vars: Variáveis adicionais do dashboard (ex: symbol="BTC/USDT")
    
    Returns:
        HTML do iframe
    """
    if not uid:
        return f'<div style="padding: 1rem; background: var(--panel); border-radius: 8px; text-align: center; color: var(--muted);">Dashboard UID não configurado</div>'
    
    # Monta query parameters
    params = {
        "orgId": 1,
        "refresh": refresh,
        "from": from_ms,
        "to": to_ms,
        "theme": theme,
        "viewPanel": panel_id
    }
    
    # Adiciona variáveis extras
    for key, value in extra_vars.items():
        params[f"var-{key}"] = value
    
    # Monta URL completa
    url = f"{GRAFANA_BASE_URL}/d-solo/{uid}/?{urlencode(params)}"
    
    return f"""
    <div class="grafana-embed" style="border: 1px solid var(--border); border-radius: 8px; overflow: hidden; height: {height}px; margin-bottom: 1rem;">
        <iframe 
            src="{url}" 
            width="100%" 
            height="{height}" 
            frameborder="0"
            style="border: none;">
        </iframe>
    </div>
    """


def render_grafana_panel(
    dashboard_key: str,
    panel_id: int,
    height: int = 400,
    title: str = "",
    from_time: str = "now-6h",
    to_time: str = "now",
    refresh: str = "10s",
    **extra_vars
) -> None:
    """
    Renderiza um painel do Grafana no Streamlit via iframe
    
    Args:
        dashboard_key: Chave do dashboard (ex: 'dynamic', 'overview', 'consensus')
        panel_id: ID do painel dentro do dashboard
        height: Altura do iframe em pixels
        title: Título opcional para exibir acima do painel
        from_time: Timestamp inicial
        to_time: Timestamp final
        refresh: Intervalo de refresh
        **extra_vars: Variáveis do dashboard
    """
    uid = get_dashboard_uid(dashboard_key)
    
    if not uid:
        st.warning(f"⚠️ Dashboard '{dashboard_key}' não configurado")
        return
    
    # Testa se o dashboard está acessível
    if not test_grafana_dashboard(uid):
        st.warning(f"⚠️ Dashboard '{title or dashboard_key}' indisponível no Grafana")
        return
    
    # Renderiza título se fornecido
    if title:
        st.markdown(f"**{title}**")
    
    # Gera e renderiza iframe
    iframe_html = grafana_panel_iframe(
        uid=uid,
        panel_id=panel_id,
        from_ms=from_time,
        to_ms=to_time,
        refresh=refresh,
        height=height,
        **extra_vars
    )
    
    st.markdown(iframe_html, unsafe_allow_html=True)


def render_full_dashboard(
    dashboard_key: str,
    height: int = 600,
    title: str = "",
    from_time: str = "now-6h",
    to_time: str = "now",
    refresh: str = "10s",
    **extra_vars
) -> None:
    """
    Renderiza um dashboard completo do Grafana (sem painel específico)
    
    Args:
        dashboard_key: Chave do dashboard
        height: Altura do iframe
        title: Título opcional
        from_time: Timestamp inicial
        to_time: Timestamp final
        refresh: Intervalo de refresh
        **extra_vars: Variáveis do dashboard
    """
    uid = get_dashboard_uid(dashboard_key)
    
    if not uid:
        st.warning(f"⚠️ Dashboard '{dashboard_key}' não configurado")
        return
    
    if not test_grafana_dashboard(uid):
        st.warning(f"⚠️ Dashboard '{title or dashboard_key}' indisponível")
        return
    
    if title:
        st.markdown(f"**{title}**")
    
    # Monta query parameters
    params = {
        "orgId": 1,
        "refresh": refresh,
        "from": from_time,
        "to": to_time,
        "theme": "dark"
    }
    
    # Adiciona variáveis extras
    for key, value in extra_vars.items():
        params[f"var-{key}"] = value
    
    url = f"{GRAFANA_BASE_URL}/d/{uid}/?{urlencode(params)}"
    
    iframe_html = f"""
    <div class="grafana-embed" style="border: 1px solid var(--border); border-radius: 8px; overflow: hidden; height: {height}px; margin-bottom: 1rem;">
        <iframe 
            src="{url}" 
            width="100%" 
            height="{height}" 
            frameborder="0"
            style="border: none;">
        </iframe>
    </div>
    """
    
    st.markdown(iframe_html, unsafe_allow_html=True)


def list_available_dashboards() -> dict:
    """
    Lista todos os dashboards configurados
    
    Returns:
        Dicionário com chaves e UIDs dos dashboards
    """
    return DASHBOARD_UIDS.copy()
