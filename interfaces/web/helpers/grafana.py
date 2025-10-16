# interfaces/web/helpers/grafana.py
"""Helpers otimizados para Grafana embeds"""
import os
import json
import urllib.parse
import streamlit as st
from pathlib import Path

GRAFANA_BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://localhost/grafana").rstrip("/")
REGISTRY_PATH = Path(__file__).parent.parent / "panel_registry.json"

# Carregar registry uma vez
_panel_registry = None

def load_panel_registry():
    """Carrega registro de painéis (cache)"""
    global _panel_registry
    if _panel_registry is None:
        try:
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                _panel_registry = json.load(f)
        except Exception:
            _panel_registry = {}
    return _panel_registry

def grafana_panel(uid: str, slug: str, panel_id: int, height: int = 300,
                  time_from: str = "now-6h", time_to: str = "now"):
    """
    Renderiza painel Grafana via iframe /d-solo (otimizado)
    """
    params = {
        "orgId": "1",
        "panelId": str(panel_id),
        "theme": "dark",
        "kiosk": "",
        "from": time_from,
        "to": time_to,
    }
    url = f"{GRAFANA_BASE_URL}/d-solo/{uid}/{urllib.parse.quote(slug)}?{urllib.parse.urlencode(params)}"
    st.components.v1.iframe(url, height=height, scrolling=False)

def panel_from_registry(tab: str, key: str, time_from: str = "now-6h", time_to: str = "now"):
    """
    Renderiza painel do registro (mais simples)
    """
    registry = load_panel_registry()
    if tab in registry and key in registry[tab]:
        panel = registry[tab][key]
        grafana_panel(
            uid=panel["uid"],
            slug=panel["slug"],
            panel_id=panel["panel_id"],
            height=panel["height"],
            time_from=time_from,
            time_to=time_to
        )
    else:
        st.error(f"Painel não encontrado: {tab}.{key}")

def section_header(title: str, icon: str = ""):
    """Header de seção estilizado"""
    st.markdown(f'<div class="section-header">{icon} {title}</div>', unsafe_allow_html=True)

def metric_row(cols_data: list):
    """Linha de métricas com colunas"""
    cols = st.columns(len(cols_data))
    for col, data in zip(cols, cols_data):
        with col:
            st.metric(
                label=data.get("label", ""),
                value=data.get("value", ""),
                delta=data.get("delta")
            )
