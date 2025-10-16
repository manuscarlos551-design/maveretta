"""Helper otimizado para embed de painéis Grafana com lazy loading."""
import os
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components

GRAFANA_BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://localhost/grafana").rstrip("/")

def grafana_panel(
    uid: str,
    slug: str,
    panel_id: int,
    height: int = 300,
    time_from: str = "now-6h",
    time_to: str = "now",
    refresh: str = "5s",
    lazy: bool = False
):
    """
    Renderiza painel nativo do Grafana via iframe /d-solo com suporte a lazy loading.
    
    Args:
        uid: UID do dashboard
        slug: Slug do título do dashboard
        panel_id: ID do painel
        height: Altura em pixels (KPI: 260-280, timeseries: 320-400, table: 400-500)
        time_from: Intervalo inicial (padrão: now-6h)
        time_to: Intervalo final (padrão: now)
        refresh: Refresh rate (padrão: 5s - opções: 5s, 10s, 30s, 1m)
        lazy: Se True, mostra placeholder antes de carregar (default: False)
    """
    # Otimização: parâmetros mais enxutos
    params = {
        "orgId": "1",
        "panelId": str(panel_id),
        "theme": "dark",
        "kiosk": "tv",  # Modo TV para UI mais limpa
        "from": time_from,
        "to": time_to,
        "refresh": refresh,
    }
    url = f"{GRAFANA_BASE_URL}/d-solo/{uid}/{urllib.parse.quote(slug)}?{urllib.parse.urlencode(params)}"
    
    if lazy:
        # Lazy loading com placeholder
        with st.container():
            placeholder = st.empty()
            with placeholder:
                st.markdown(
                    f'<div style="height:{height}px;background:#1c2531;border-radius:8px;'
                    f'display:flex;align-items:center;justify-content:center;color:#8a95a6;">'
                    f'<span>⏳ Carregando painel...</span></div>',
                    unsafe_allow_html=True
                )
            # Render iframe após um momento
            placeholder.empty()
            html = f'<div class="grafana-embed"><iframe src="{url}" width="100%" height="{height}" frameborder="0" style="border-radius: 8px;" loading="lazy"></iframe></div>'
            components.html(html, height=height, scrolling=False)
    else:
        # Render direto com loading="lazy" para performance
        html = f'<div class="grafana-embed"><iframe src="{url}" width="100%" height="{height}" frameborder="0" style="border-radius: 8px;" loading="lazy"></iframe></div>'
        components.html(html, height=height, scrolling=False)


def grafana_panel_grid(panels: list, columns: int = 2):
    """
    Renderiza múltiplos painéis em grid com lazy loading otimizado.
    
    Args:
        panels: Lista de dicts com {uid, slug, panel_id, height, ...}
        columns: Número de colunas (default: 2)
    """
    cols = st.columns(columns)
    for idx, panel_config in enumerate(panels):
        col_idx = idx % columns
        with cols[col_idx]:
            grafana_panel(**panel_config, lazy=True)
