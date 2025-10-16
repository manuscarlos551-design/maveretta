"""Helper otimizado para embed de painéis Grafana com lazy loading."""
import os
import urllib.parse
import streamlit.components.v1 as components

GRAFANA_BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://localhost/grafana").rstrip("/")

def grafana_panel(
    uid: str,
    slug: str,
    panel_id: int,
    height: int = 300,
    time_from: str = "now-6h",
    time_to: str = "now",
    refresh: str = "5s"
):
    """
    Renderiza painel nativo do Grafana via iframe /d-solo com otimizações.
    
    Args:
        uid: UID do dashboard
        slug: Slug do título do dashboard
        panel_id: ID do painel
        height: Altura em pixels (KPI: 260-280, timeseries: 320-400, table: 400-500)
        time_from: Intervalo inicial (padrão: now-6h)
        time_to: Intervalo final (padrão: now)
        refresh: Refresh rate (padrão: 5s - opções: 5s, 10s, 30s, 1m)
    """
    # Otimização: kiosk=tv para UI mais limpa, loading=lazy para performance
    params = {
        "orgId": "1",
        "panelId": str(panel_id),
        "theme": "dark",
        "kiosk": "tv",
        "from": time_from,
        "to": time_to,
        "refresh": refresh,
    }
    url = f"{GRAFANA_BASE_URL}/d-solo/{uid}/{urllib.parse.quote(slug)}?{urllib.parse.urlencode(params)}"
    
    # Render iframe com lazy loading nativo do browser
    html = f'<div class="grafana-embed"><iframe src="{url}" width="100%" height="{height}" frameborder="0" style="border-radius: 8px;" loading="lazy"></iframe></div>'
    components.html(html, height=height, scrolling=False)
